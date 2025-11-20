"""Base classes for Freya tools."""

from __future__ import annotations

import asyncio
import signal
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, TypeVar

from ..logger import get_logger

logger = get_logger("tools.base")

# Default timeout for tool execution (30 seconds)
DEFAULT_TOOL_TIMEOUT = 30.0

T = TypeVar('T')


class ToolTimeoutError(TimeoutError):
    """Raised when tool execution exceeds timeout."""
    
    def __init__(self, tool_name: str, timeout: float):
        super().__init__(f"Tool '{tool_name}' execution exceeded timeout of {timeout}s")
        self.tool_name = tool_name
        self.timeout = timeout


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.output if self.success else f"Error: {self.error}"


class FreyaTool(ABC):
    """Base class for all Freya tools.

    Tools are capabilities that Freya can use to interact with the world.
    Each tool should be focused on a specific task or domain.
    """

    def __init__(self) -> None:
        self._enabled = True

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (lowercase, no spaces)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass

    @property
    def enabled(self) -> bool:
        """Whether this tool is currently enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable this tool."""
        self._enabled = True
        logger.debug("Tool '%s' enabled", self.name)

    def disable(self) -> None:
        """Disable this tool."""
        self._enabled = False
        logger.debug("Tool '%s' disabled", self.name)

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters (may include 'timeout')

        Returns:
            ToolResult with output or error
        """
        pass
    
    def execute_with_timeout(self, timeout: float | None = None, **kwargs) -> ToolResult:
        """Execute tool with timeout protection.
        
        Args:
            timeout: Maximum execution time in seconds (default: DEFAULT_TOOL_TIMEOUT)
            **kwargs: Tool-specific parameters
        
        Returns:
            ToolResult with output or error
        
        Raises:
            ToolTimeoutError: If execution exceeds timeout
        """
        timeout = timeout or DEFAULT_TOOL_TIMEOUT
        
        # Check if execute is async
        import inspect
        if inspect.iscoroutinefunction(self.execute):
            # Handle async execute
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context, can't use run_until_complete
                    logger.warning(
                        "Tool '%s' async execution called from running loop, "
                        "timeout may not be enforced",
                        self.name
                    )
                    return self.execute(**kwargs)
                else:
                    coro = asyncio.wait_for(self.execute(**kwargs), timeout=timeout)
                    return loop.run_until_complete(coro)
            except asyncio.TimeoutError:
                raise ToolTimeoutError(self.name, timeout)
            except RuntimeError:
                # No event loop
                coro = asyncio.wait_for(self.execute(**kwargs), timeout=timeout)
                try:
                    return asyncio.run(coro)
                except asyncio.TimeoutError:
                    raise ToolTimeoutError(self.name, timeout)
        else:
            # Handle sync execute with signal (Unix-like systems only)
            import sys
            if sys.platform == 'win32':
                # Windows doesn't support signal.alarm, use threading instead
                import threading
                result = []
                exception = []
                
                def target():
                    try:
                        result.append(self.execute(**kwargs))
                    except Exception as exc:
                        exception.append(exc)
                
                thread = threading.Thread(target=target, daemon=True)
                thread.start()
                thread.join(timeout=timeout)
                
                if thread.is_alive():
                    logger.error("Tool '%s' execution timed out after %.1fs", self.name, timeout)
                    raise ToolTimeoutError(self.name, timeout)
                
                if exception:
                    raise exception[0]
                if result:
                    return result[0]
                raise RuntimeError(f"Tool '{self.name}' execution failed unexpectedly")
            else:
                # Unix-like: use signal.alarm
                def timeout_handler(signum, frame):
                    raise ToolTimeoutError(self.name, timeout)
                
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout))
                
                try:
                    result = self.execute(**kwargs)
                    signal.alarm(0)  # Cancel alarm
                    return result
                finally:
                    signal.signal(signal.SIGALRM, old_handler)

    def __repr__(self) -> str:
        status = "enabled" if self._enabled else "disabled"
        return f"<{self.__class__.__name__}(name='{self.name}', {status})>"


__all__ = ["FreyaTool", "ToolResult"]
