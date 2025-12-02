"""Custom exception hierarchy for Freya AI Assistant.

This module defines a comprehensive exception hierarchy for better error
handling, debugging, and recovery across the Freya codebase.

Exception Hierarchy:
    FreyaError (base)
    ├── FreyaConfigError
    │   ├── ConfigValidationError (already exists in config.py)
    │   ├── ConfigFileError
    │   └── ConfigSchemaError
    ├── FreyaServiceError
    │   ├── ServiceUnavailableError
    │   └── ServiceTimeoutError
    ├── AgentError
    │   ├── AgentInitializationError
    │   ├── AgentCommunicationError
    │   ├── AgentMessageError
    │   └── AgentCleanupError
    ├── ToolError
    │   ├── ToolNotFoundError
    │   ├── ToolExecutionError
    │   ├── ToolPermissionError
    │   ├── ToolNetworkError
    │   └── ToolInputError
    ├── MemoryError (shadows builtin, use FreyaMemoryError)
    │   ├── MemoryStorageError
    │   ├── MemoryQueryError
    │   └── MemoryConnectionError
    ├── TTSError
    │   ├── TTSBackendError
    │   ├── TTSHardwareError
    │   ├── TTSAPIError
    │   └── TTSVoiceNotFoundError
    ├── STTError
    │   ├── STTBackendError
    │   ├── STTHardwareError
    │   └── STTAudioError
    └── HotkeyError
        ├── HotkeyRegistrationError
        └── HotkeyUnregistrationError
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# =============================================================================
# Base Exception
# =============================================================================


class FreyaError(Exception):
    """Base exception for all Freya-specific errors.

    All custom exceptions in Freya should inherit from this class to enable
    systematic error handling and logging.

    Attributes:
        message: Human-readable error description
        correlation_id: Optional request/operation ID for tracing
        context: Additional context data as key-value pairs
    """

    def __init__(
        self,
        message: str,
        *args,
        correlation_id: Optional[str] = None,
        **context
    ):
        """Initialize FreyaError with message, correlation ID, and context.

        Args:
            message: Human-readable error description
            *args: Additional positional arguments for Exception
            correlation_id: Optional correlation ID for request tracing
            **context: Additional context data (available in self.context)

        Example:
            raise ToolExecutionError(
                "Web search failed",
                correlation_id="req-12345",
                tool_name="web_search",
                query="Python tutorials"
            )
        """
        super().__init__(message, *args)
        self.message = message
        self.correlation_id = correlation_id
        self.context = context

    def __str__(self) -> str:
        """Human-readable error message with correlation ID and context.

        Returns:
            Formatted error string including correlation ID and context if present.

        Example:
            Failed to execute web search [correlation_id=req-12345] (tool_name='web_search', query='Python tutorials')
        """
        parts = [self.message]
        if self.correlation_id:
            parts.append(f"[correlation_id={self.correlation_id}]")
        if self.context:
            context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            parts.append(f"({context_str})")
        return " ".join(parts)

    def __repr__(self) -> str:
        """Developer-friendly representation showing class name and key attributes.

        Returns:
            String representation suitable for debugging.

        Example:
            ToolExecutionError('Web search failed', correlation_id='req-12345')
        """
        return f"{self.__class__.__name__}({self.message!r}, correlation_id={self.correlation_id!r})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to JSON-serializable dictionary.

        Returns:
            Dictionary with error_type, message, correlation_id, and context.

        Example:
            {
                "error_type": "ToolExecutionError",
                "message": "Web search failed",
                "correlation_id": "req-12345",
                "context": {"tool_name": "web_search", "query": "Python tutorials"}
            }
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "context": self.context,
        }


# =============================================================================
# Configuration Errors
# =============================================================================


class FreyaConfigError(FreyaError):
    """Base exception for configuration-related errors."""


class ConfigFileError(FreyaConfigError):
    """Configuration file could not be read or parsed."""


class ConfigSchemaError(FreyaConfigError):
    """Configuration data doesn't match expected schema."""


# Note: ConfigValidationError already exists in freya/config.py
# It should be moved here and inherit from FreyaConfigError


# =============================================================================
# Service Errors
# =============================================================================


class FreyaServiceError(FreyaError):
    """Base exception for external service failures."""


class ServiceUnavailableError(FreyaServiceError):
    """Required service is not available or not responding."""


class ServiceTimeoutError(FreyaServiceError):
    """Service request timed out."""


# =============================================================================
# Agent Errors
# =============================================================================


class AgentError(FreyaError):
    """Base exception for agent-related errors.

    Agents are the core components of Freya's architecture. This exception
    hierarchy enables the coordinator to implement smart retry and fallback
    strategies based on error type.
    """


class AgentInitializationError(AgentError):
    """Agent failed to initialize or start.

    This typically indicates a fatal error that prevents the agent from
    operating. The coordinator should not retry automatically.
    """


class AgentCommunicationError(AgentError):
    """Agent failed to communicate via MessageBus.

    This may be transient (message queue full) or permanent (bus shutdown).
    Coordinator may retry with exponential backoff.
    """


class AgentMessageError(AgentError):
    """Agent failed to process a message.

    This indicates an error in message handling logic. The message should be
    logged and potentially moved to a dead-letter queue.
    """


class AgentCleanupError(AgentError):
    """Agent failed to clean up resources during shutdown.

    This is typically logged but not re-raised, as shutdown is already in
    progress and we want to attempt cleanup of other agents.
    """


# =============================================================================
# Tool Errors
# =============================================================================


class ToolError(FreyaError):
    """Base exception for tool execution errors.

    Tools are functions the AI can execute. This exception hierarchy allows
    the dialog agent to provide helpful error messages to users and decide
    whether to retry operations.
    """


class ToolNotFoundError(ToolError):
    """Requested tool does not exist.

    This usually indicates a bug in the LLM's tool selection or the tool
    manager's registration logic.
    """


class ToolExecutionError(ToolError):
    """Tool execution failed.

    Generic tool execution failure. More specific subclasses should be used
    when the failure type is known.
    """


class ToolPermissionError(ToolError):
    """Tool execution denied due to insufficient permissions.

    Common for file operations, system commands, and network requests.
    Should not be retried without addressing permission issue.
    """


class ToolNetworkError(ToolError):
    """Tool execution failed due to network issues.

    Common for web search, web scraping, and API calls. May be transient,
    retry with exponential backoff.
    """


class ToolInputError(ToolError):
    """Tool execution failed due to invalid input.

    The AI provided arguments that don't match the tool's requirements.
    Should not retry without fixing input.
    """


# =============================================================================
# Memory Errors
# =============================================================================


class FreyaMemoryError(FreyaError):
    """Base exception for memory system errors.

    Note: Named FreyaMemoryError to avoid shadowing builtin MemoryError.
    The memory system uses ChromaDB for vector storage and SQLite for
    structured data. These exceptions help distinguish storage vs query
    failures.
    """


class MemoryStorageError(FreyaMemoryError):
    """Failed to store data in memory system.

    This could indicate database corruption, disk full, or ChromaDB issues.
    Should log detailed context and potentially alert operators.
    """


class MemoryQueryError(FreyaMemoryError):
    """Failed to query data from memory system.

    This could indicate corrupted indices, invalid query parameters, or
    embedding generation failures. May be transient.
    """


class MemoryConnectionError(FreyaMemoryError):
    """Failed to connect to memory backend.

    ChromaDB or SQLite is unavailable. Check database paths and permissions.
    """


# =============================================================================
# Text-to-Speech Errors
# =============================================================================


class TTSError(FreyaError):
    """Base exception for text-to-speech errors.

    TTS failures can stem from backend issues (Piper, ElevenLabs), hardware
    problems (audio device), or API issues (rate limits, invalid keys).
    """


class TTSBackendError(TTSError):
    """TTS backend (Piper/ElevenLabs) failed to generate audio."""


class TTSHardwareError(TTSError):
    """Audio playback device is unavailable or malfunctioning."""


class TTSAPIError(TTSError):
    """TTS API (ElevenLabs) returned an error.

    Common causes: invalid API key, rate limit exceeded, quota exhausted.
    """


class TTSVoiceNotFoundError(TTSError):
    """Requested voice is not available."""


# =============================================================================
# Speech-to-Text Errors
# =============================================================================


class STTError(FreyaError):
    """Base exception for speech-to-text errors.

    STT failures typically involve microphone access, audio processing, or
    Whisper model issues.
    """


class STTBackendError(STTError):
    """STT backend (faster-whisper) failed to transcribe audio."""


class STTHardwareError(STTError):
    """Microphone is unavailable or malfunctioning."""


class STTAudioError(STTError):
    """Audio data is invalid or corrupted."""


# =============================================================================
# Hotkey Errors
# =============================================================================


class HotkeyError(FreyaError):
    """Base exception for hotkey registration/unregistration errors."""


class HotkeyRegistrationError(HotkeyError):
    """Failed to register a keyboard hotkey.

    Common causes: hotkey already in use, insufficient permissions.
    """


class HotkeyUnregistrationError(HotkeyError):
    """Failed to unregister a keyboard hotkey."""


# =============================================================================
# Hardware Abstraction Layer Errors
# =============================================================================


class HALError(FreyaError):
    """Base exception for hardware abstraction layer errors.

    The HAL provides protocol-based interfaces for camera, audio, memory, and
    IoT modules. These exceptions enable consistent error handling across all
    hardware-dependent operations.
    """


class CameraUnavailableError(HALError):
    """Camera device cannot be accessed or is not available.

    Common causes: camera in use by another process, permission denied,
    hardware disconnected.
    """


class FaceDetectionError(HALError):
    """Face detection operation failed.

    This could indicate image quality issues, missing face detection models,
    or processing errors.
    """


class AudioCaptureError(HALError):
    """Audio recording/capture failed.

    Common causes: microphone not available, permission denied, audio device
    malfunction.
    """


class TranscriptionError(HALError):
    """Speech-to-text transcription failed.

    This could indicate model loading issues, invalid audio format, or
    processing errors.
    """


class SpeechSynthesisError(HALError):
    """Text-to-speech synthesis failed.

    Common causes: TTS backend unavailable, invalid text input, voice model
    not found.
    """


class DeviceConnectionError(HALError):
    """IoT device connection failed.

    This indicates failure to connect to smart home devices via Home Assistant
    or other IoT protocols.
    """


class DeviceCommandError(HALError):
    """IoT device command execution failed.

    Device is connected but failed to execute the requested command.
    """


# =============================================================================
# Legacy Exception Compatibility
# =============================================================================

# These exceptions already exist in other modules. We define them here for
# import convenience and to establish the hierarchy. The actual implementations
# in other files should be updated to import from this module.

# From freya/config.py
class ConfigValidationError(FreyaConfigError):
    """Configuration validation failed."""


# From freya/stt.py
class SpeechToTextError(STTError):
    """Legacy alias for STTError. Use STTError subclasses instead."""


# From freya/tts.py and freya/tts_elevenlabs.py
class TextToSpeechError(TTSError):
    """Legacy alias for TTSError. Use TTSError subclasses instead."""


# From freya/wake.py
class WakeWordDetectorError(FreyaError):
    """Wake word detector failed."""


# From freya/facial_recognition.py
class FaceRecognitionError(FreyaError):
    """Facial recognition failed."""


# From freya/ollama_client.py
class OllamaError(FreyaServiceError):
    """Ollama client error."""


class OllamaModelNotFoundError(OllamaError):
    """Ollama model not found."""


class OllamaStreamNotSupported(OllamaError):
    """Ollama streaming not supported."""


# From freya/tools/web_search.py
class WebSearchError(ToolNetworkError):
    """Web search failed."""


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base
    "FreyaError",
    # Config
    "FreyaConfigError",
    "ConfigFileError",
    "ConfigSchemaError",
    "ConfigValidationError",
    # Service
    "FreyaServiceError",
    "ServiceUnavailableError",
    "ServiceTimeoutError",
    # Agent
    "AgentError",
    "AgentInitializationError",
    "AgentCommunicationError",
    "AgentMessageError",
    "AgentCleanupError",
    # Tool
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolPermissionError",
    "ToolNetworkError",
    "ToolInputError",
    # Memory
    "FreyaMemoryError",
    "MemoryStorageError",
    "MemoryQueryError",
    "MemoryConnectionError",
    # TTS
    "TTSError",
    "TTSBackendError",
    "TTSHardwareError",
    "TTSAPIError",
    "TTSVoiceNotFoundError",
    # STT
    "STTError",
    "STTBackendError",
    "STTHardwareError",
    "STTAudioError",
    # Hotkey
    "HotkeyError",
    "HotkeyRegistrationError",
    "HotkeyUnregistrationError",
    # HAL
    "HALError",
    "CameraUnavailableError",
    "FaceDetectionError",
    "AudioCaptureError",
    "TranscriptionError",
    "SpeechSynthesisError",
    "DeviceConnectionError",
    "DeviceCommandError",
    # Legacy
    "SpeechToTextError",
    "TextToSpeechError",
    "WakeWordDetectorError",
    "FaceRecognitionError",
    "OllamaError",
    "OllamaModelNotFoundError",
    "OllamaStreamNotSupported",
    "WebSearchError",
]
