"""Memory-specific exceptions."""

from __future__ import annotations

from typing import Any

from freya.domain.exceptions.base import InfrastructureException


class MemoryError(InfrastructureException):
    """Base exception for memory-related errors."""


class MemoryStorageError(MemoryError):
    """Raised when memory storage operation fails."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        super().__init__(message, details=details, **kwargs)


class MemoryQueryError(MemoryError):
    """Raised when memory query fails."""

    def __init__(
        self,
        message: str,
        query_type: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if query_type:
            details["query_type"] = query_type
        super().__init__(message, details=details, **kwargs)


class MemoryConnectionError(MemoryError):
    """Raised when memory backend connection fails."""

    def __init__(
        self,
        message: str,
        backend: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if backend:
            details["backend"] = backend
        super().__init__(message, details=details, **kwargs)


class MemoryNotFoundError(MemoryError):
    """Raised when requested memory is not found."""

    def __init__(
        self,
        message: str,
        memory_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if memory_id:
            details["memory_id"] = memory_id
        super().__init__(message, details=details, **kwargs)


class MemoryValidationError(MemoryError):
    """Raised when memory data validation fails."""
