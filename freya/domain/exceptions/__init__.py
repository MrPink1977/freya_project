"""Domain exceptions package."""

from freya.domain.exceptions.agent_exceptions import (
    AgentCommunicationError,
    AgentError,
    AgentInitializationError,
    AgentMessageError,
    AgentShutdownError,
    AgentStartupError,
    AgentStateError,
    AgentTimeoutError,
)
from freya.domain.exceptions.base import (
    ApplicationException,
    BusinessRuleViolation,
    ConfigurationError,
    CoordinationError,
    DatabaseError,
    DomainException,
    EntityNotFoundError,
    EventHandlingError,
    FreyaException,
    HardwareError,
    InfrastructureException,
    ModelError,
    ModelLoadError,
    ModelNotFoundError,
    ModelUnloadError,
    NetworkError,
    ServiceUnavailableError,
    TimeoutError,
    UseCaseError,
    ValidationError,
    VRAMExceededError,
)
from freya.domain.exceptions.memory_exceptions import (
    MemoryConnectionError,
    MemoryError,
    MemoryNotFoundError,
    MemoryQueryError,
    MemoryStorageError,
    MemoryValidationError,
)
from freya.domain.exceptions.tool_exceptions import (
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
)

__all__ = [
    # Base exceptions
    "FreyaException",
    "DomainException",
    "ApplicationException",
    "InfrastructureException",
    # Domain exceptions
    "ValidationError",
    "BusinessRuleViolation",
    "EntityNotFoundError",
    # Application exceptions
    "UseCaseError",
    "CoordinationError",
    "EventHandlingError",
    # Infrastructure exceptions
    "DatabaseError",
    "NetworkError",
    "HardwareError",
    "ConfigurationError",
    "ServiceUnavailableError",
    "TimeoutError",
    "ModelError",
    "ModelLoadError",
    "ModelNotFoundError",
    "ModelUnloadError",
    "VRAMExceededError",
    # Agent exceptions
    "AgentError",
    "AgentInitializationError",
    "AgentStartupError",
    "AgentShutdownError",
    "AgentCommunicationError",
    "AgentMessageError",
    "AgentTimeoutError",
    "AgentStateError",
    # Memory exceptions
    "MemoryError",
    "MemoryStorageError",
    "MemoryQueryError",
    "MemoryConnectionError",
    "MemoryNotFoundError",
    "MemoryValidationError",
    # Tool exceptions
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolValidationError",
    "ToolPermissionError",
    "ToolTimeoutError",
]
