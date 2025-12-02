# Structured Logging Implementation

**Status**: ✅ COMPLETE
**Date**: 2025-12-02
**Branch**: `claude/code-quality-improvements-01DfQmKpX`

## Summary

Implemented comprehensive structured logging system for Freya with:

1. ✅ **Correlation ID tracking** - Thread-safe request tracing
2. ✅ **JSON output** - Machine-parseable logs for production
3. ✅ **Human-readable output** - Colored output for development
4. ✅ **Exception integration** - Automatic extraction of FreyaError context
5. ✅ **Backward compatibility** - Works with existing logging code
6. ✅ **Thread-safe context** - Using contextvars for async/threading support

## Architecture

### Technology Stack

- **structlog**: Structured logging with processors
- **python-json-logger**: JSON formatting for production logs
- **contextvars**: Thread-safe correlation ID storage

Both dependencies are already in `requirements.txt`.

### Key Components

```
freya/core/logger_v2.py
├── get_correlation_id()        # Get current correlation ID
├── set_correlation_id()        # Set correlation ID
├── bind_correlation_id()       # Context manager for correlation ID
├── configure_logging()         # Setup logging system
├── get_logger()                # Get structured logger
├── log_exception()             # Log exceptions with full context
├── create_child_logger()       # Create logger with bound context
├── add_correlation_id()        # Structlog processor
└── add_exception_context()     # Extract FreyaError context
```

## Usage Examples

### Basic Logging

```python
from freya.core.logger_v2 import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("user_logged_in", user_id=123, username="alice")

# Structured data automatically added
logger.warning("rate_limit_exceeded", user_id=123, limit=100, current=105)

# Error with exception
try:
    result = risky_operation()
except Exception as exc:
    logger.error("operation_failed", exc_info=True)
```

**Output (development mode)**:
```
2025-12-02T10:30:45.123456Z [info     ] user_logged_in    user_id=123 username=alice
2025-12-02T10:30:46.234567Z [warning  ] rate_limit_exceeded user_id=123 limit=100 current=105
2025-12-02T10:30:47.345678Z [error    ] operation_failed
Traceback (most recent call last):
  ...
```

**Output (production mode - JSON)**:
```json
{"timestamp": "2025-12-02T10:30:45.123456Z", "level": "info", "event": "user_logged_in", "user_id": 123, "username": "alice", "logger": "freya.auth"}
{"timestamp": "2025-12-02T10:30:46.234567Z", "level": "warning", "event": "rate_limit_exceeded", "user_id": 123, "limit": 100, "current": 105, "logger": "freya.api"}
{"timestamp": "2025-12-02T10:30:47.345678Z", "level": "error", "event": "operation_failed", "exception": "...", "logger": "freya.core"}
```

### Correlation ID Tracking

```python
from freya.core.logger_v2 import get_logger, bind_correlation_id

logger = get_logger(__name__)

async def process_request(request_id: str):
    # Bind correlation ID for entire request
    with bind_correlation_id(request_id):
        logger.info("request_started", method="POST", path="/api/search")

        # All logs in this context include correlation_id
        result = await search_database(query)
        logger.info("database_query_completed", rows=len(result))

        response = await generate_response(result)
        logger.info("response_generated", tokens=len(response))

        return response
```

**Output**:
```json
{"timestamp": "...", "level": "info", "event": "request_started", "correlation_id": "req-12345", "method": "POST", "path": "/api/search"}
{"timestamp": "...", "level": "info", "event": "database_query_completed", "correlation_id": "req-12345", "rows": 42}
{"timestamp": "...", "level": "info", "event": "response_generated", "correlation_id": "req-12345", "tokens": 150}
```

### Exception Logging

```python
from freya.core.logger_v2 import get_logger, log_exception
from freya.core.exceptions import ToolExecutionError

logger = get_logger(__name__)

try:
    result = execute_tool(
        "web_search",
        query="Python tutorials"
    )
except ToolExecutionError as exc:
    # Automatically extracts correlation_id and context from FreyaError
    log_exception(
        logger,
        exc,
        "tool_execution_failed",
        tool_name="web_search",
        retry_count=3
    )
```

**Output**:
```json
{
  "timestamp": "2025-12-02T10:30:45Z",
  "level": "error",
  "event": "tool_execution_failed",
  "correlation_id": "req-12345",
  "exception_type": "ToolExecutionError",
  "exception_message": "Web search API timeout",
  "tool_name": "web_search",
  "retry_count": 3,
  "query": "Python tutorials",
  "timeout_seconds": 30
}
```

### Child Loggers

```python
from freya.core.logger_v2 import get_logger, create_child_logger

logger = get_logger(__name__)

# Create logger with permanent context
request_logger = create_child_logger(
    logger,
    request_id="req-12345",
    user_id=456,
    session_id="sess-789"
)

# All logs from this logger include bound context
request_logger.info("authentication_started")
request_logger.info("authentication_completed", method="oauth")
request_logger.info("data_fetched", records=100)
```

**Output**:
```json
{"event": "authentication_started", "request_id": "req-12345", "user_id": 456, "session_id": "sess-789"}
{"event": "authentication_completed", "request_id": "req-12345", "user_id": 456, "session_id": "sess-789", "method": "oauth"}
{"event": "data_fetched", "request_id": "req-12345", "user_id": 456, "session_id": "sess-789", "records": 100}
```

## Configuration

### Development Mode

Human-readable, colored output for debugging:

```python
from freya.core.logger_v2 import configure_logging
import logging

configure_logging(
    json_format=False,
    console_level=logging.DEBUG,
    file_level=logging.INFO
)
```

### Production Mode

JSON output for log aggregation (ELK, Splunk, CloudWatch):

```python
from freya.core.logger_v2 import configure_logging
import logging

configure_logging(
    json_format=True,
    console_level=logging.INFO,
    file_level=logging.INFO,
    log_file=Path("/var/log/freya/app.log")
)
```

### Environment-Based Configuration

```python
import os
from freya.core.logger_v2 import configure_logging
import logging

# Use JSON in production, human-readable in development
is_production = os.getenv("ENVIRONMENT") == "production"

configure_logging(
    json_format=is_production,
    console_level=logging.INFO if is_production else logging.DEBUG,
    file_level=logging.INFO
)
```

## Integration with Exception System

The logging system automatically extracts context from FreyaError exceptions:

```python
from freya.core.logger_v2 import get_logger
from freya.core.exceptions import MemoryStorageError

logger = get_logger(__name__)

try:
    memory_store.save(data)
except Exception as exc:
    # Raise FreyaError with correlation_id and context
    raise MemoryStorageError(
        "Failed to store memory",
        correlation_id="req-12345",
        collection="conversations",
        entry_id=789,
        size_bytes=1024
    ) from exc
```

When caught and logged:

```python
try:
    operation()
except MemoryStorageError as exc:
    logger.error("memory_operation_failed", exc_info=True)
```

**Output**:
```json
{
  "event": "memory_operation_failed",
  "correlation_id": "req-12345",
  "collection": "conversations",
  "entry_id": 789,
  "size_bytes": 1024,
  "exception_type": "MemoryStorageError",
  "exception_message": "Failed to store memory",
  "exception": "Traceback (most recent call last)..."
}
```

## Structlog Processors

### add_correlation_id

Automatically adds correlation_id to all log entries:

```python
def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID from context to log entry."""
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict
```

### add_exception_context

Extracts correlation_id and context from FreyaError exceptions:

```python
def add_exception_context(logger, method_name, event_dict):
    """Extract context from FreyaError exceptions."""
    exc_info = event_dict.get("exc_info")
    if exc_info:
        exception = exc_info[1]
        if hasattr(exception, "correlation_id"):
            event_dict["correlation_id"] = exception.correlation_id
        if hasattr(exception, "context"):
            event_dict.update(exception.context)
    return event_dict
```

## Thread Safety

The correlation ID uses `contextvars.ContextVar` for thread-safe and async-safe storage:

```python
import asyncio
from freya.core.logger_v2 import get_logger, bind_correlation_id

logger = get_logger(__name__)

async def handle_request(request_id: str):
    with bind_correlation_id(request_id):
        logger.info("request_started")
        await asyncio.sleep(1)
        logger.info("request_completed")

# Each coroutine has its own correlation_id
await asyncio.gather(
    handle_request("req-001"),
    handle_request("req-002"),
    handle_request("req-003"),
)
```

**Output**:
```
[info] request_started     correlation_id=req-001
[info] request_started     correlation_id=req-002
[info] request_started     correlation_id=req-003
[info] request_completed   correlation_id=req-001
[info] request_completed   correlation_id=req-002
[info] request_completed   correlation_id=req-003
```

## Backward Compatibility

Existing code using `freya.core.logger` continues to work:

```python
# Old code (still works)
from freya.core.logger import get_logger, configure_logging

configure_logging(
    file_level=logging.INFO,
    console_level=logging.WARNING
)

logger = get_logger(__name__)
logger.info("This still works")
```

To migrate to structured logging:

```python
# New code
from freya.core.logger_v2 import get_logger, configure_logging

configure_logging(
    json_format=False,
    file_level=logging.INFO,
    console_level=logging.WARNING
)

logger = get_logger(__name__)
logger.info("user_action", user_id=123, action="login")
```

## Migration Guide

### Step 1: Update Imports

**Before**:
```python
from freya.core.logger import get_logger
```

**After**:
```python
from freya.core.logger_v2 import get_logger
```

### Step 2: Add Structured Context

**Before**:
```python
logger.info(f"User {user_id} performed action {action}")
```

**After**:
```python
logger.info("user_action", user_id=user_id, action=action)
```

### Step 3: Add Correlation IDs

**Before**:
```python
async def process_request():
    logger.info("Processing request")
    result = await database.query()
    logger.info("Query completed")
```

**After**:
```python
from freya.core.logger_v2 import bind_correlation_id
import uuid

async def process_request():
    request_id = str(uuid.uuid4())
    with bind_correlation_id(request_id):
        logger.info("processing_request")
        result = await database.query()
        logger.info("query_completed", rows=len(result))
```

### Step 4: Use log_exception

**Before**:
```python
try:
    result = operation()
except Exception as exc:
    logger.error(f"Operation failed: {exc}")
```

**After**:
```python
from freya.core.logger_v2 import log_exception

try:
    result = operation()
except Exception as exc:
    log_exception(logger, exc, "operation_failed", operation="search")
```

## Log Aggregation

### ELK Stack (Elasticsearch, Logstash, Kibana)

JSON logs can be ingested directly:

```json
{"timestamp": "2025-12-02T10:30:45Z", "level": "error", "correlation_id": "req-123", "event": "tool_failed"}
```

**Kibana query**:
```
correlation_id:"req-123" AND level:"error"
```

### CloudWatch Logs

Configure CloudWatch agent to parse JSON:

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/freya/app.log",
            "log_group_name": "/aws/freya",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          }
        ]
      }
    }
  }
}
```

**CloudWatch Insights query**:
```
fields @timestamp, level, event, correlation_id
| filter correlation_id = "req-123"
| sort @timestamp desc
```

### Splunk

HEC (HTTP Event Collector) with JSON:

```python
import logging
from pythonjsonlogger import jsonlogger

handler = logging.handlers.HTTPHandler(
    "splunk.example.com:8088",
    "/services/collector/event",
    method="POST"
)
handler.setFormatter(jsonlogger.JsonFormatter())
```

## Performance Considerations

### Lazy Evaluation

Structlog uses lazy evaluation - expensive operations only execute if the log level is enabled:

```python
# This is efficient - only evaluated if DEBUG is enabled
logger.debug("expensive_debug_info", data=expensive_function())

# Better: Use lambda for very expensive operations
logger.debug("expensive_debug_info", data=lambda: expensive_function())
```

### Async Logging

For high-throughput applications, use QueueHandler:

```python
from logging.handlers import QueueHandler, QueueListener
import queue

# Create queue for async logging
log_queue = queue.Queue(-1)
queue_handler = QueueHandler(log_queue)

# File handler runs in background thread
file_handler = logging.FileHandler("freya.log")
listener = QueueListener(log_queue, file_handler)
listener.start()
```

## Best Practices

### 1. Use Event Names, Not Messages

❌ **Bad**:
```python
logger.info("User logged in successfully")
logger.info("User login failed due to invalid password")
```

✅ **Good**:
```python
logger.info("user_login_success", user_id=123)
logger.error("user_login_failed", user_id=123, reason="invalid_password")
```

### 2. Include Correlation IDs

❌ **Bad**:
```python
logger.info("Processing request")
```

✅ **Good**:
```python
with bind_correlation_id(request.id):
    logger.info("processing_request", method="POST", path="/api/search")
```

### 3. Use Structured Context

❌ **Bad**:
```python
logger.error(f"Tool {tool_name} failed with error: {error}")
```

✅ **Good**:
```python
logger.error("tool_execution_failed", tool_name=tool_name, error=str(error))
```

### 4. Don't Log Secrets

❌ **Bad**:
```python
logger.info("api_request", api_key="sk_live_1234567890")
```

✅ **Good**:
```python
logger.info("api_request", api_key_prefix="sk_live_...890")
```

## Benefits

### 1. Request Tracing

Correlation IDs enable tracing a single request through the entire system:

```bash
# Find all logs for a specific request
grep "req-12345" freya.log

# Or in JSON logs
jq 'select(.correlation_id == "req-12345")' freya.log
```

### 2. Structured Queries

JSON logs enable powerful queries:

```bash
# Find all errors in the last hour
jq 'select(.level == "error" and .timestamp > "2025-12-02T09:00:00Z")' freya.log

# Find all tool failures
jq 'select(.event == "tool_execution_failed")' freya.log | jq -s 'group_by(.tool_name) | map({tool: .[0].tool_name, count: length})'
```

### 3. Metrics and Alerting

Extract metrics from structured logs:

```python
# Count errors by type
jq 'select(.level == "error") | .exception_type' freya.log | sort | uniq -c

# Calculate average response time
jq 'select(.event == "request_completed") | .duration_ms' freya.log | awk '{sum+=$1} END {print sum/NR}'
```

### 4. Better Debugging

Correlation IDs and structured context make debugging much easier:

```
Without correlation_id:
  [10:30:45] Processing request
  [10:30:46] Query started
  [10:30:46] Processing request  # Which request?
  [10:30:47] Query failed       # Which query?

With correlation_id:
  [10:30:45] processing_request    correlation_id=req-001
  [10:30:46] query_started        correlation_id=req-001
  [10:30:46] processing_request    correlation_id=req-002
  [10:30:47] query_failed         correlation_id=req-001  # Clear!
```

## Testing

### Unit Tests

```python
from freya.core.logger_v2 import get_logger, bind_correlation_id, get_correlation_id

def test_correlation_id_binding():
    with bind_correlation_id("test-123"):
        assert get_correlation_id() == "test-123"
    assert get_correlation_id() is None

def test_structured_logging():
    logger = get_logger(__name__)
    logger.info("test_event", key="value", count=42)
    # Verify log output contains structured data
```

### Integration Tests

```python
import json
from pathlib import Path

def test_json_logging(tmp_path):
    log_file = tmp_path / "test.log"
    configure_logging(json_format=True, log_file=log_file)

    logger = get_logger(__name__)
    logger.info("test_event", user_id=123)

    # Parse and verify JSON log
    with open(log_file) as f:
        log_entry = json.loads(f.readline())
        assert log_entry["event"] == "test_event"
        assert log_entry["user_id"] == 123
```

## Conclusion

The structured logging system provides:

- **Request tracing** via correlation IDs
- **Machine-parseable logs** with JSON output
- **Human-readable logs** for development
- **Exception integration** with FreyaError
- **Thread-safe context** for async operations
- **Backward compatibility** with existing code

This completes **Recommendation #4: Standardize Logging**.

---

**Next**: Add docstrings to 89 functions missing them (Recommendation #2)
