"""Freya tools package - provides capabilities for web search, file ops, calculations, etc."""

from .base import FreyaTool, ToolResult
from .calculator import CalculatorTool
from .datetime_tools import CalculateTimeUntil, GetCurrentDate, GetCurrentTime
from .file_tools import ListFilesTool, ReadFileTool, WriteFileTool
from .manager import ToolManager
from .system_tools import ExecuteCommandTool, SystemInfoTool
from .web_scraper import WebScraperTool
from .web_search import WebSearchError, search_web

__all__ = [
    # Base
    "FreyaTool",
    "ToolResult",
    # Manager
    "ToolManager",
    # Individual tools
    "GetCurrentTime",
    "GetCurrentDate",
    "CalculateTimeUntil",
    "ListFilesTool",
    "ReadFileTool",
    "WriteFileTool",
    "WebScraperTool",
    "CalculatorTool",
    "SystemInfoTool",
    "ExecuteCommandTool",
    # Legacy web search
    "search_web",
    "WebSearchError",
]
