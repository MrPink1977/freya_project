"""Tool manager for Freya - handles registration and execution of tools."""

from __future__ import annotations

from typing import Dict, List, Type

from ..exceptions import (
    ToolExecutionError,
    ToolInputError,
    ToolNetworkError,
    ToolNotFoundError,
    ToolPermissionError,
)
from ..logger import get_logger
from .base import FreyaTool, ToolResult

logger = get_logger("tools.manager")


class ToolManager:
    """Manages all available tools for Freya."""

    def __init__(self) -> None:
        self._tools: Dict[str, FreyaTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register all default tools."""
        from .calculator import CalculatorTool
        from .datetime_tools import CalculateTimeUntil, GetCurrentDate, GetCurrentTime
        from .file_tools import ListFilesTool, ReadFileTool, WriteFileTool
        from .performance_tools import PerformanceMonitorTool
        from .system_tools import ExecuteCommandTool, SystemInfoTool
        from .web_scraper import WebScraperTool

        default_tools: List[Type[FreyaTool]] = [
            # Time/Date
            GetCurrentTime,
            GetCurrentDate,
            CalculateTimeUntil,
            # Files
            ListFilesTool,
            ReadFileTool,
            WriteFileTool,
            # Web
            WebSearchTool,
            WebScraperTool,
            # Utilities
            CalculatorTool,
            SystemInfoTool,
            ExecuteCommandTool,
            PerformanceMonitorTool,
        ]

        for tool_class in default_tools:
            try:
                tool = tool_class()
                self.register_tool(tool)
            except Exception as e:
                logger.warning("Failed to register tool %s: %s", tool_class.__name__, e)

    def register_tool(self, tool: FreyaTool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register
        """
        if tool.name in self._tools:
            logger.warning("Tool '%s' already registered, replacing", tool.name)

        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool.

        Args:
            tool_name: Name of tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.debug("Unregistered tool: %s", tool_name)
            return True
        return False

    def get_tool(self, tool_name: str) -> FreyaTool | None:
        """Get a tool by name.

        Args:
            tool_name: Name of tool

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def list_tools(self, enabled_only: bool = False) -> List[FreyaTool]:
        """List all registered tools.

        Args:
            enabled_only: Only return enabled tools

        Returns:
            List of tool instances
        """
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return sorted(tools, key=lambda t: t.name)

    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult from tool execution
        """
        tool = self.get_tool(tool_name)

        if tool is None:
            available = ", ".join(sorted(self._tools.keys()))
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' not found. Available tools: {available}",
            )

        if not tool.enabled:
            return ToolResult(success=False, output="", error=f"Tool '{tool_name}' is disabled")

        try:
            logger.info("Executing tool '%s' with args: %s", tool_name, kwargs)
            result = tool.execute(**kwargs)
            logger.debug("Tool '%s' result: success=%s", tool_name, result.success)
            return result

        except TypeError as e:
            # Invalid arguments provided to tool
            logger.warning("Tool '%s' received invalid arguments: %s", tool_name, e)
            raise ToolInputError(
                f"Invalid arguments for tool '{tool_name}': {e}",
                tool=tool_name,
                arguments=kwargs,
            )
        except (PermissionError, OSError) as e:
            # Permission denied or file system errors (file tools)
            logger.error("Tool '%s' permission/access error: %s", tool_name, e)
            raise ToolPermissionError(
                f"Permission denied for tool '{tool_name}': {e}",
                tool=tool_name,
                error=str(e),
            )
        except (ConnectionError, TimeoutError) as e:
            # Network-related errors (web search, web scraper)
            logger.error("Tool '%s' network error: %s", tool_name, e)
            raise ToolNetworkError(
                f"Network error in tool '{tool_name}': {e}",
                tool=tool_name,
                error=str(e),
            )
        except ValueError as e:
            # Invalid input data (calculator, datetime tools)
            logger.warning("Tool '%s' input validation error: %s", tool_name, e)
            raise ToolInputError(
                f"Invalid input for tool '{tool_name}': {e}",
                tool=tool_name,
                error=str(e),
            )
        except ToolExecutionError:
            # Already a specific tool error, just re-raise
            raise
        except Exception as e:
            # Unexpected error - log with full traceback
            logger.exception("Tool '%s' raised unexpected exception", tool_name)
            raise ToolExecutionError(
                f"Tool '{tool_name}' execution failed: {e}",
                tool=tool_name,
                error=str(e),
            )

    def get_tools_description(self) -> str:
        """Get a formatted description of all available tools.

        Returns:
            Multi-line string describing all tools
        """
        lines = ["Available Tools:"]
        for tool in self.list_tools(enabled_only=True):
            status = "" if tool.enabled else " (disabled)"
            lines.append(f"  - {tool.name}{status}: {tool.description}")

        return "\n".join(lines)


# Create Web Search Tool wrapper for compatibility
class WebSearchTool(FreyaTool):
    """Web search tool (wraps existing web_search module)."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web using DuckDuckGo"

    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """Execute web search.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            ToolResult with search results
        """
        try:
            from .web_search import search_web

            result = search_web(query, max_results)
            return ToolResult(success=True, output=result)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


__all__ = ["ToolManager", "WebSearchTool"]
