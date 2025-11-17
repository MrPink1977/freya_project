"""Base classes for Freya tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..logger import get_logger

logger = get_logger("tools.base")


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
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with output or error
        """
        pass

    def __repr__(self) -> str:
        status = "enabled" if self._enabled else "disabled"
        return f"<{self.__class__.__name__}(name='{self.name}', {status})>"


__all__ = ["FreyaTool", "ToolResult"]
