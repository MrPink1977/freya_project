"""Tool-specific exceptions."""

from __future__ import annotations

from typing import Any

from freya.domain.exceptions.base import ApplicationException


class ToolError(ApplicationException):
    """Base exception for tool-related errors."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if tool_name:
            details["tool_name"] = tool_name
        super().__init__(message, details=details, **kwargs)


class ToolNotFoundError(ToolError):
    """Raised when requested tool is not found."""


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if parameters:
            details["parameters"] = parameters
        super().__init__(message, tool_name=tool_name, details=details, **kwargs)


class ToolValidationError(ToolError):
    """Raised when tool parameter validation fails."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        parameter: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if parameter:
            details["parameter"] = parameter
        super().__init__(message, tool_name=tool_name, details=details, **kwargs)


class ToolPermissionError(ToolError):
    """Raised when tool lacks required permissions."""


class ToolTimeoutError(ToolError):
    """Raised when tool execution times out."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, tool_name=tool_name, details=details, **kwargs)
