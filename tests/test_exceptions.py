"""
Unit tests for Freya custom exception hierarchy.

Tests exception inheritance, context metadata, error classification,
and proper exception propagation through the system.
"""
import pytest

from freya.core.exceptions import (
    AgentCleanupError,
    AgentCommunicationError,
    AgentError,
    AgentInitializationError,
    AgentMessageError,
    ConfigFileError,
    ConfigSchemaError,
    ConfigValidationError,
    FreyaConfigError,
    FreyaError,
    FreyaMemoryError,
    FreyaServiceError,
    HotkeyError,
    HotkeyRegistrationError,
    HotkeyUnregistrationError,
    MemoryConnectionError,
    MemoryQueryError,
    MemoryStorageError,
    ServiceTimeoutError,
    ServiceUnavailableError,
    STTAudioError,
    STTBackendError,
    STTError,
    STTHardwareError,
    ToolError,
    ToolExecutionError,
    ToolInputError,
    ToolNetworkError,
    ToolNotFoundError,
    ToolPermissionError,
    TTSAPIError,
    TTSBackendError,
    TTSError,
    TTSHardwareError,
    TTSVoiceNotFoundError,
)


class TestExceptionHierarchy:
    """Test exception inheritance structure."""

    def test_base_exception_inheritance(self):
        """All custom exceptions inherit from FreyaError."""
        assert issubclass(FreyaConfigError, FreyaError)
        assert issubclass(FreyaServiceError, FreyaError)
        assert issubclass(AgentError, FreyaError)
        assert issubclass(ToolError, FreyaError)
        assert issubclass(FreyaMemoryError, FreyaError)
        assert issubclass(TTSError, FreyaError)
        assert issubclass(STTError, FreyaError)
        assert issubclass(HotkeyError, FreyaError)

    def test_config_exception_hierarchy(self):
        """Config exceptions have proper hierarchy."""
        assert issubclass(ConfigFileError, FreyaConfigError)
        assert issubclass(ConfigSchemaError, FreyaConfigError)
        assert issubclass(ConfigValidationError, FreyaConfigError)

    def test_service_exception_hierarchy(self):
        """Service exceptions have proper hierarchy."""
        assert issubclass(ServiceUnavailableError, FreyaServiceError)
        assert issubclass(ServiceTimeoutError, FreyaServiceError)

    def test_agent_exception_hierarchy(self):
        """Agent exceptions have proper hierarchy."""
        assert issubclass(AgentInitializationError, AgentError)
        assert issubclass(AgentCommunicationError, AgentError)
        assert issubclass(AgentMessageError, AgentError)
        assert issubclass(AgentCleanupError, AgentError)

    def test_tool_exception_hierarchy(self):
        """Tool exceptions have proper hierarchy."""
        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(ToolExecutionError, ToolError)
        assert issubclass(ToolPermissionError, ToolError)
        assert issubclass(ToolNetworkError, ToolError)
        assert issubclass(ToolInputError, ToolError)

    def test_memory_exception_hierarchy(self):
        """Memory exceptions have proper hierarchy."""
        assert issubclass(MemoryStorageError, FreyaMemoryError)
        assert issubclass(MemoryQueryError, FreyaMemoryError)
        assert issubclass(MemoryConnectionError, FreyaMemoryError)

    def test_tts_exception_hierarchy(self):
        """TTS exceptions have proper hierarchy."""
        assert issubclass(TTSBackendError, TTSError)
        assert issubclass(TTSHardwareError, TTSError)
        assert issubclass(TTSAPIError, TTSError)
        assert issubclass(TTSVoiceNotFoundError, TTSError)

    def test_stt_exception_hierarchy(self):
        """STT exceptions have proper hierarchy."""
        assert issubclass(STTBackendError, STTError)
        assert issubclass(STTHardwareError, STTError)
        assert issubclass(STTAudioError, STTError)

    def test_hotkey_exception_hierarchy(self):
        """Hotkey exceptions have proper hierarchy."""
        assert issubclass(HotkeyRegistrationError, HotkeyError)
        assert issubclass(HotkeyUnregistrationError, HotkeyError)


class TestExceptionMessages:
    """Test exception message handling."""

    def test_basic_message(self):
        """Exceptions store and display messages."""
        exc = FreyaError("Test message")
        assert str(exc) == "Test message"

    def test_context_metadata(self):
        """Exceptions store context metadata."""
        exc = ToolExecutionError("Tool failed", tool_name="calculator", error="Division by zero")
        assert exc.context["tool_name"] == "calculator"
        assert exc.context["error"] == "Division by zero"

    def test_config_file_error_context(self):
        """ConfigFileError stores file path context."""
        exc = ConfigFileError("Config not found", file_path="/path/to/config.yaml")
        assert exc.context["file_path"] == "/path/to/config.yaml"

    def test_agent_error_context(self):
        """AgentError stores agent ID context."""
        exc = AgentInitializationError("Failed to start", agent_id="memory_agent")
        assert exc.context["agent_id"] == "memory_agent"

    def test_memory_error_context(self):
        """MemoryError stores collection and operation context."""
        exc = MemoryStorageError("Failed to store", collection="conversations", operation="add")
        assert exc.context["collection"] == "conversations"
        assert exc.context["operation"] == "add"

    def test_tool_error_context(self):
        """ToolError stores tool name and input context."""
        exc = ToolInputError("Invalid input", tool_name="calculator", input_data={"expression": "invalid"})
        assert exc.context["tool_name"] == "calculator"
        assert exc.context["input_data"] == {"expression": "invalid"}


class TestExceptionCatching:
    """Test exception catching patterns."""

    def test_catch_specific_exception(self):
        """Specific exceptions can be caught."""
        with pytest.raises(ToolNotFoundError) as exc_info:
            raise ToolNotFoundError("Tool not found", tool_name="unknown")
        assert "Tool not found" in str(exc_info.value)

    def test_catch_by_base_class(self):
        """Exceptions can be caught by base class."""
        with pytest.raises(ToolError):
            raise ToolExecutionError("Execution failed")

    def test_catch_by_freya_error(self):
        """All Freya exceptions can be caught by FreyaError."""
        with pytest.raises(FreyaError):
            raise AgentInitializationError("Init failed")

    def test_catch_multiple_specific_exceptions(self):
        """Multiple specific exceptions can be handled differently."""
        def risky_operation(error_type: str):
            if error_type == "input":
                raise ToolInputError("Invalid input")
            elif error_type == "permission":
                raise ToolPermissionError("Permission denied")
            else:
                raise ToolExecutionError("Unknown error")

        with pytest.raises(ToolInputError):
            risky_operation("input")

        with pytest.raises(ToolPermissionError):
            risky_operation("permission")

        with pytest.raises(ToolExecutionError):
            risky_operation("other")


class TestErrorClassification:
    """Test error classification logic patterns."""

    def test_classify_type_error(self):
        """TypeError should map to ToolInputError."""
        try:
            raise TypeError("Invalid argument type")
        except TypeError as exc:
            tool_exc = ToolInputError("Invalid input", original_error=str(exc))
            assert isinstance(tool_exc, ToolInputError)
            assert "Invalid argument type" in tool_exc.context["original_error"]

    def test_classify_permission_error(self):
        """PermissionError should map to ToolPermissionError."""
        try:
            raise PermissionError("Access denied")
        except PermissionError as exc:
            tool_exc = ToolPermissionError("Permission denied", original_error=str(exc))
            assert isinstance(tool_exc, ToolPermissionError)

    def test_classify_connection_error(self):
        """ConnectionError should map to ToolNetworkError."""
        try:
            raise ConnectionError("Network unreachable")
        except ConnectionError as exc:
            tool_exc = ToolNetworkError("Network error", original_error=str(exc))
            assert isinstance(tool_exc, ToolNetworkError)

    def test_classify_value_error(self):
        """ValueError should map to ToolInputError."""
        try:
            raise ValueError("Invalid value")
        except ValueError as exc:
            tool_exc = ToolInputError("Invalid input", original_error=str(exc))
            assert isinstance(tool_exc, ToolInputError)


class TestExceptionPropagation:
    """Test exception propagation through layers."""

    def test_tool_error_propagation(self):
        """Tool errors propagate with context."""
        def tool_operation():
            raise ToolExecutionError("Tool failed", tool_name="calculator")

        def orchestrator_handler():
            try:
                tool_operation()
            except ToolExecutionError as exc:
                assert exc.context["tool_name"] == "calculator"
                raise

        with pytest.raises(ToolExecutionError):
            orchestrator_handler()

    def test_memory_error_propagation(self):
        """Memory errors propagate with collection context."""
        def memory_operation():
            raise MemoryStorageError("Storage failed", collection="conversations")

        def agent_handler():
            try:
                memory_operation()
            except MemoryStorageError as exc:
                assert exc.context["collection"] == "conversations"
                raise

        with pytest.raises(MemoryStorageError):
            agent_handler()

    def test_agent_error_wrapping(self):
        """Agent errors can wrap underlying errors."""
        def underlying_failure():
            raise ValueError("Invalid data")

        def agent_operation():
            try:
                underlying_failure()
            except ValueError as exc:
                raise AgentMessageError("Failed to process message", agent_id="test_agent", original_error=str(exc))

        with pytest.raises(AgentMessageError) as exc_info:
            agent_operation()
        assert "Invalid data" in exc_info.value.context["original_error"]


class TestLegacyCompatibility:
    """Test backward compatibility with legacy exceptions."""

    def test_legacy_exceptions_exist(self):
        """Legacy exception names are still available."""
        from freya.core.exceptions import (
            FaceRecognitionError,
            OllamaError,
            SpeechToTextError,
            TextToSpeechError,
            WakeWordDetectorError,
            WebSearchError,
        )
        assert issubclass(OllamaError, FreyaError)
        assert issubclass(WebSearchError, FreyaError)
        assert issubclass(TextToSpeechError, FreyaError)
        assert issubclass(SpeechToTextError, FreyaError)
        assert issubclass(WakeWordDetectorError, FreyaError)
        assert issubclass(FaceRecognitionError, FreyaError)


class TestExceptionDocstrings:
    """Test that exceptions have proper documentation."""

    def test_base_exception_docstring(self):
        """FreyaError has docstring."""
        assert FreyaError.__doc__ is not None
        assert "Base exception" in FreyaError.__doc__

    def test_specific_exceptions_documented(self):
        """Specific exceptions have docstrings."""
        assert ToolExecutionError.__doc__ is not None
        assert MemoryStorageError.__doc__ is not None
        assert AgentInitializationError.__doc__ is not None
