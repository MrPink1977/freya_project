# Exception System Enhancements

**Status**: ✅ ENHANCED
**Date**: 2025-12-02
**Branch**: `claude/code-quality-improvements-01DfQmKpX`

## Summary

Enhanced Freya's existing exception hierarchy with:
1. ✅ **Correlation ID tracking** - All exceptions support correlation_id
2. ✅ **Structured error context** - Better error metadata
3. ✅ **Integration with HAL** - HAL exceptions added to hierarchy
4. ✅ **Better string representations** - Improved __str__ and __repr__
5. ✅ **Error serialization** - JSON-serializable error context

## Current State

Freya already has an **excellent** exception hierarchy:
- ✅ `FreyaError` base class (all exceptions inherit from this)
- ✅ Well-organized categories (Config, Service, Agent, Tool, Memory, TTS, STT, Hotkey)
- ✅ Comprehensive docstrings
- ✅ Context dict support
- ✅ Legacy aliases for backward compatibility

## Enhancements Made

### 1. Added Correlation ID Support

All exceptions now support correlation_id for request tracing:

```python
class FreyaError(Exception):
    """Base exception with correlation ID and context support."""

    def __init__(
        self,
        message: str,
        *args,
        correlation_id: Optional[str] = None,
        **context
    ):
        super().__init__(message, *args)
        self.message = message
        self.correlation_id = correlation_id
        self.context = context
```

**Usage:**
```python
raise ToolExecutionError(
    "Failed to execute web search",
    correlation_id="req-12345",
    tool_name="web_search",
    query="Python tutorials"
)
```

### 2. Improved String Representation

Better __str__ and __repr__ for debugging:

```python
def __str__(self) -> str:
    """Human-readable error message."""
    parts = [self.message]
    if self.correlation_id:
        parts.append(f"[correlation_id={self.correlation_id}]")
    if self.context:
        context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        parts.append(f"({context_str})")
    return " ".join(parts)

def __repr__(self) -> str:
    """Developer-friendly representation."""
    return f"{self.__class__.__name__}({self.message!r}, correlation_id={self.correlation_id!r})"
```

**Output:**
```python
ToolExecutionError("Failed to execute web search", correlation_id='req-12345')
# str: Failed to execute web search [correlation_id=req-12345] (tool_name='web_search', query='Python tutorials')
```

### 3. Error Serialization

Convert exceptions to JSON for logging:

```python
def to_dict(self) -> Dict[str, Any]:
    """Convert exception to JSON-serializable dictionary."""
    return {
        "error_type": self.__class__.__name__,
        "message": self.message,
        "correlation_id": self.correlation_id,
        "context": self.context,
    }
```

**Usage:**
```python
try:
    tool.execute()
except ToolExecutionError as e:
    logger.error("Tool failed", extra=e.to_dict())
```

### 4. HAL Exception Integration

Added HAL exceptions to the hierarchy:

```python
# =============================================================================
# Hardware Abstraction Layer Errors
# =============================================================================

class HALError(FreyaError):
    """Base exception for hardware abstraction layer."""

class CameraUnavailableError(HALError):
    """Camera cannot be accessed."""

class FaceDetectionError(HALError):
    """Face detection failed."""

class AudioCaptureError(HALError):
    """Audio recording failed."""

class TranscriptionError(HALError):
    """Speech-to-text failed."""

class SpeechSynthesisError(HALError):
    """Text-to-speech failed."""

class DeviceConnectionError(HALError):
    """IoT device connection failed."""

class DeviceCommandError(HALError):
    """IoT device command failed."""
```

These replace the duplicate definitions in `freya/hal/interfaces.py`.

### 5. Exception Context Guidelines

Added best practices for using context:

```python
# Good: Include relevant debugging information
raise ToolExecutionError(
    "Web search API returned error",
    correlation_id=request_id,
    status_code=response.status_code,
    api_endpoint=url,
    query_params=params
)

# Bad: Too much information (security risk)
raise ToolExecutionError(
    "API auth failed",
    api_key="sk_live_123..."  # Don't include secrets!
)

# Good: Sanitized information
raise ToolExecutionError(
    "API auth failed",
    correlation_id=request_id,
    api_key_prefix="sk_live_...123"  # Only include safe parts
)
```

## Exception Usage Patterns

### Pattern 1: Try-Except with Context

```python
from freya.core.exceptions import ToolExecutionError

def execute_tool(tool_name: str, correlation_id: str):
    try:
        result = tool_manager.execute(tool_name)
        return result
    except Exception as exc:
        raise ToolExecutionError(
            f"Tool '{tool_name}' execution failed: {exc}",
            correlation_id=correlation_id,
            tool_name=tool_name,
            original_error=str(exc),
        ) from exc
```

### Pattern 2: Exception Chaining

```python
try:
    memory_store.save(data)
except ChromaDBError as exc:
    raise MemoryStorageError(
        "Failed to store memory in ChromaDB",
        correlation_id=correlation_id,
        collection="conversations",
        entry_id=entry.id,
    ) from exc  # Preserves original traceback
```

### Pattern 3: Correlation ID Propagation

```python
async def process_request(request_id: str):
    try:
        # Pass correlation_id through all calls
        memory = await store_memory(content, correlation_id=request_id)
        response = await generate_response(memory, correlation_id=request_id)
        await speak(response, correlation_id=request_id)
    except FreyaError as exc:
        # Exception already has correlation_id
        logger.error(f"Request failed: {exc}")
        raise
```

### Pattern 4: Recovery with Exception Types

```python
async def robust_tool_execution(tool_name: str):
    try:
        return await execute_tool(tool_name)
    except ToolNetworkError as exc:
        # Network errors are transient - retry
        logger.warning(f"Network error, retrying: {exc}")
        await asyncio.sleep(1)
        return await execute_tool(tool_name)
    except ToolPermissionError as exc:
        # Permission errors are permanent - don't retry
        logger.error(f"Permission denied: {exc}")
        return{"error": "Permission denied"}
    except ToolInputError as exc:
        # Input errors need fixing - don't retry
        logger.error(f"Invalid input: {exc}")
        return {"error": "Invalid input parameters"}
```

## Integration with Logging

Exceptions integrate with structured logging:

```python
import structlog

logger = structlog.get_logger()

try:
    process_request()
except FreyaError as exc:
    logger.error(
        "Request processing failed",
        correlation_id=exc.correlation_id,
        error_type=exc.__class__.__name__,
        **exc.context
    )
```

Output:
```json
{
  "event": "Request processing failed",
  "correlation_id": "req-12345",
  "error_type": "ToolExecutionError",
  "tool_name": "web_search",
  "query": "Python tutorials",
  "timestamp": "2025-12-02T10:30:45.123Z"
}
```

## Exception Statistics

### Coverage

| Category | Exceptions | Purpose |
|----------|-----------|---------|
| Base | 1 | Root exception class |
| Configuration | 4 | Config loading/validation |
| Service | 2 | External service failures |
| Agent | 5 | Agent lifecycle/communication |
| Tool | 6 | Tool execution failures |
| Memory | 4 | Memory storage/retrieval |
| Audio (TTS/STT) | 8 | Speech processing |
| Vision | 2 | Camera/face recognition |
| HAL | 7 | Hardware abstraction |
| Hotkey | 3 | Keyboard hotkeys |
| Legacy | 6 | Backward compatibility |

**Total: 48 exception types**

### Hierarchy Depth

```
FreyaError (depth 0)
├── FreyaConfigError (depth 1)
│   ├── ConfigFileError (depth 2)
│   ├── ConfigSchemaError (depth 2)
│   └── ConfigValidationError (depth 2)
├── FreyaServiceError (depth 1)
│   ├── ServiceUnavailableError (depth 2)
│   ├── ServiceTimeoutError (depth 2)
│   └── OllamaError (depth 2)
│       ├── OllamaModelNotFoundError (depth 3)
│       └── OllamaStreamNotSupported (depth 3)
├── AgentError (depth 1)
│   └── [5 specialized exceptions]
├── ToolError (depth 1)
│   └── [6 specialized exceptions]
├── FreyaMemoryError (depth 1)
│   └── [3 specialized exceptions]
├── TTSError (depth 1)
│   └── [4 specialized exceptions]
├── STTError (depth 1)
│   └── [3 specialized exceptions]
├── HALError (depth 1)
│   └── [7 specialized exceptions]
└── [Other categories...]
```

Maximum depth: 3 levels (appropriate complexity)

## Migration Guide

### Step 1: Update Imports

**Before:**
```python
from freya.config import ConfigValidationError
from freya.stt import SpeechToTextError
from freya.tts import TextToSpeechError
```

**After:**
```python
from freya.core.exceptions import (
    ConfigValidationError,
    STTError,  # More specific than SpeechToTextError
    TTSError,  # More specific than TextToSpeechError
)
```

### Step 2: Add Correlation IDs

**Before:**
```python
raise ToolExecutionError("Failed to execute tool")
```

**After:**
```python
raise ToolExecutionError(
    "Failed to execute tool",
    correlation_id=request.correlation_id,
    tool_name=tool.name
)
```

### Step 3: Add Context

**Before:**
```python
raise MemoryStorageError(f"Failed to store: {error}")
```

**After:**
```python
raise MemoryStorageError(
    "Failed to store memory entry",
    correlation_id=correlation_id,
    collection="conversations",
    entry_id=entry_id,
    original_error=str(error)
)
```

## Benefits

### 1. Better Debugging
- Correlation IDs trace requests across modules
- Context provides relevant details
- Exception chaining preserves full stack trace

### 2. Smarter Error Handling
- Exception hierarchy enables targeted catch blocks
- Different recovery strategies based on error type
- Clear distinction between transient and permanent failures

### 3. Improved Logging
- Structured error context
- JSON serialization for log aggregation
- Consistent error format

### 4. Better User Experience
- Clear error messages
- Actionable error information
- No exposure of sensitive data

## Recommendations

### 1. Always Use Specific Exceptions

❌ **Bad:**
```python
raise Exception("Something went wrong")
raise FreyaError("Tool failed")
```

✅ **Good:**
```python
raise ToolExecutionError("Tool failed", correlation_id=..., tool_name=...)
raise ToolNetworkError("Network timeout", correlation_id=..., timeout_sec=30)
```

### 2. Include Correlation IDs

❌ **Bad:**
```python
raise MemoryQueryError("Query failed")
```

✅ **Good:**
```python
raise MemoryQueryError(
    "Query failed",
    correlation_id=request_id,
    query=query_text
)
```

### 3. Add Relevant Context

❌ **Bad:**
```python
raise ToolExecutionError("Failed")
```

✅ **Good:**
```python
raise ToolExecutionError(
    "Web search API timeout",
    correlation_id=request_id,
    api_endpoint=url,
    timeout_seconds=30,
    query=search_query
)
```

### 4. Use Exception Chaining

❌ **Bad:**
```python
try:
    database.save(data)
except DBError as exc:
    raise MemoryStorageError(str(exc))  # Lost original traceback
```

✅ **Good:**
```python
try:
    database.save(data)
except DBError as exc:
    raise MemoryStorageError(
        "Database save failed",
        correlation_id=request_id
    ) from exc  # Preserves original traceback
```

## Testing

### Test Exception Creation

```python
def test_exception_with_correlation_id():
    exc = ToolExecutionError(
        "Tool failed",
        correlation_id="test-123",
        tool_name="web_search"
    )

    assert exc.message == "Tool failed"
    assert exc.correlation_id == "test-123"
    assert exc.context["tool_name"] == "web_search"
```

### Test Exception Serialization

```python
def test_exception_to_dict():
    exc = MemoryStorageError(
        "Storage failed",
        correlation_id="req-456",
        collection="test",
        entry_id=789
    )

    data = exc.to_dict()
    assert data["error_type"] == "MemoryStorageError"
    assert data["correlation_id"] == "req-456"
    assert data["context"]["collection"] == "test"
```

### Test Exception Hierarchy

```python
def test_exception_hierarchy():
    exc = ToolNetworkError("Network failed")

    assert isinstance(exc, ToolNetworkError)
    assert isinstance(exc, ToolError)
    assert isinstance(exc, FreyaError)
    assert isinstance(exc, Exception)
```

## Conclusion

Freya's exception system is **already excellent** and follows best practices. The enhancements add:
- Correlation ID support for request tracing
- Better string representations for debugging
- JSON serialization for structured logging
- HAL exception integration

This completes **Recommendation #3: Refine Error Handling**.

---

**Next:** Implement structured JSON logging with correlation_id tracking (Recommendation #4)
