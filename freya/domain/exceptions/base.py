"""
Base exception hierarchy for Freya assistant.

This module defines the exception hierarchy following clean architecture principles.
All exceptions inherit from FreyaException and are organized by layer.
"""

from __future__ import annotations

from typing import Any


class FreyaException(Exception):
    """
    Base exception for all Freya-related errors.
    
    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        details: Additional context about the error
        cause: Original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            code: Machine-readable error code (e.g., "AGENT_001")
            details: Additional context as key-value pairs
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.code = code or self._default_code()
        self.details = details or {}
        self.cause = cause

    def _default_code(self) -> str:
        """Generate default error code from class name."""
        return self.__class__.__name__.upper()

    def __str__(self) -> str:
        """String representation of the exception."""
        parts = [f"[{self.code}] {self.message}"]
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            parts.append(f"Details: {details_str}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"details={self.details!r}, "
            f"cause={self.cause!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


# ============================================================================
# Domain Layer Exceptions
# ============================================================================


class DomainException(FreyaException):
    """Base exception for domain layer errors (business logic)."""


class ValidationError(DomainException):
    """Raised when domain validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message, details=details, **kwargs)


class BusinessRuleViolation(DomainException):
    """Raised when a business rule is violated."""

    def __init__(
        self,
        message: str,
        rule: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if rule:
            details["rule"] = rule
        super().__init__(message, details=details, **kwargs)


class EntityNotFoundError(DomainException):
    """Raised when a domain entity is not found."""

    def __init__(
        self,
        message: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if entity_type:
            details["entity_type"] = entity_type
        if entity_id:
            details["entity_id"] = entity_id
        super().__init__(message, details=details, **kwargs)


# ============================================================================
# Application Layer Exceptions
# ============================================================================


class ApplicationException(FreyaException):
    """Base exception for application layer errors (use cases)."""


class UseCaseError(ApplicationException):
    """Raised when a use case fails to execute."""

    def __init__(
        self,
        message: str,
        use_case: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if use_case:
            details["use_case"] = use_case
        super().__init__(message, details=details, **kwargs)


class CoordinationError(ApplicationException):
    """Raised when coordination between components fails."""


class EventHandlingError(ApplicationException):
    """Raised when event handling fails."""

    def __init__(
        self,
        message: str,
        event_type: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if event_type:
            details["event_type"] = event_type
        super().__init__(message, details=details, **kwargs)


# ============================================================================
# Infrastructure Layer Exceptions
# ============================================================================


class InfrastructureException(FreyaException):
    """Base exception for infrastructure layer errors (technical)."""


class DatabaseError(InfrastructureException):
    """Raised when database operations fail."""

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


class NetworkError(InfrastructureException):
    """Raised when network operations fail."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if url:
            details["url"] = url
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details=details, **kwargs)


class HardwareError(InfrastructureException):
    """Raised when hardware access fails."""

    def __init__(
        self,
        message: str,
        device: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if device:
            details["device"] = device
        super().__init__(message, details=details, **kwargs)


class ConfigurationError(InfrastructureException):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details=details, **kwargs)


class ServiceUnavailableError(InfrastructureException):
    """Raised when an external service is unavailable."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if service:
            details["service"] = service
        super().__init__(message, details=details, **kwargs)


class TimeoutError(InfrastructureException):
    """Raised when an operation times out."""

    def __init__(
        self,
        message: str,
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, details=details, **kwargs)


class ModelError(InfrastructureException):
    """Base exception for model-related errors."""

    def __init__(
        self,
        message: str,
        model_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if model_name:
            details["model_name"] = model_name
        super().__init__(message, details=details, **kwargs)


class ModelLoadError(ModelError):
    """Raised when a model fails to load."""


class ModelNotFoundError(ModelError):
    """Raised when a requested model is not found."""


class ModelUnloadError(ModelError):
    """Raised when a model fails to unload."""


class VRAMExceededError(ModelError):
    """Raised when VRAM capacity is exceeded."""

    def __init__(
        self,
        message: str,
        required_vram: float | None = None,
        available_vram: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if required_vram:
            details["required_vram_gb"] = required_vram
        if available_vram:
            details["available_vram_gb"] = available_vram
        super().__init__(message, details=details, **kwargs)

