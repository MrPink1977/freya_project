"""Agent-specific exceptions."""

from __future__ import annotations

from typing import Any

from freya.domain.exceptions.base import InfrastructureException


class AgentError(InfrastructureException):
    """Base exception for agent-related errors."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if agent_name:
            details["agent_name"] = agent_name
        super().__init__(message, details=details, **kwargs)


class AgentInitializationError(AgentError):
    """Raised when agent initialization fails."""


class AgentStartupError(AgentError):
    """Raised when agent fails to start."""


class AgentShutdownError(AgentError):
    """Raised when agent fails to shutdown gracefully."""


class AgentCommunicationError(AgentError):
    """Raised when agent communication fails."""

    def __init__(
        self,
        message: str,
        source_agent: str | None = None,
        target_agent: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if source_agent:
            details["source_agent"] = source_agent
        if target_agent:
            details["target_agent"] = target_agent
        super().__init__(message, details=details, **kwargs)


class AgentMessageError(AgentError):
    """Raised when message handling fails."""

    def __init__(
        self,
        message: str,
        message_type: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if message_type:
            details["message_type"] = message_type
        super().__init__(message, details=details, **kwargs)


class AgentTimeoutError(AgentError):
    """Raised when agent operation times out."""


class AgentStateError(AgentError):
    """Raised when agent is in invalid state for operation."""

    def __init__(
        self,
        message: str,
        current_state: str | None = None,
        expected_state: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if current_state:
            details["current_state"] = current_state
        if expected_state:
            details["expected_state"] = expected_state
        super().__init__(message, details=details, **kwargs)
