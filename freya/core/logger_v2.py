"""Structured logging with correlation ID tracking for Freya.

This module provides a structured logging system using structlog with:
- Correlation ID tracking for request tracing
- JSON output for production environments
- Human-readable output for development
- Integration with enhanced exception system
- Thread-safe context management

Example:
    from freya.core.logger_v2 import get_logger, bind_correlation_id

    logger = get_logger(__name__)

    # Bind correlation ID for request tracing
    with bind_correlation_id("req-12345"):
        logger.info("processing_request", user_id=456, action="search")
        try:
            result = perform_search()
        except Exception as exc:
            logger.error("search_failed", error=str(exc))
"""

from __future__ import annotations

import contextvars
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import structlog
from pythonjsonlogger import jsonlogger

# Thread-safe correlation ID storage
_correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

_LOGGER_NAME = "freya"
_LOG_FILE = Path("freya.log")
_CONFIGURED = False


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context.

    Returns:
        Current correlation ID or None if not set.

    Example:
        correlation_id = get_correlation_id()
        if correlation_id:
            logger.info("operation", correlation_id=correlation_id)
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Set the correlation ID in the current context.

    Args:
        correlation_id: Correlation ID to set, or None to clear.

    Example:
        set_correlation_id("req-12345")
        logger.info("processing_request")  # Will include correlation_id
        set_correlation_id(None)  # Clear when done
    """
    _correlation_id_var.set(correlation_id)


@contextmanager
def bind_correlation_id(correlation_id: str) -> Iterator[None]:
    """Context manager to set correlation ID for a block of code.

    Args:
        correlation_id: Correlation ID to bind for this context.

    Yields:
        None

    Example:
        with bind_correlation_id("req-12345"):
            logger.info("step_1")  # Includes correlation_id=req-12345
            logger.info("step_2")  # Includes correlation_id=req-12345
        # correlation_id cleared after context exits
    """
    token = _correlation_id_var.set(correlation_id)
    try:
        yield
    finally:
        _correlation_id_var.reset(token)


def add_correlation_id(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor to add correlation ID to log entries.

    Args:
        logger: Logger instance (unused).
        method_name: Log method name (unused).
        event_dict: Log event dictionary to modify.

    Returns:
        Modified event dictionary with correlation_id if available.
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_exception_context(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor to add exception context from FreyaError.

    If the log entry contains a FreyaError exception, extracts its
    correlation_id and context for structured logging.

    Args:
        logger: Logger instance (unused).
        method_name: Log method name (unused).
        event_dict: Log event dictionary to modify.

    Returns:
        Modified event dictionary with exception metadata.
    """
    exc_info = event_dict.get("exc_info")
    if exc_info and len(exc_info) >= 2:
        exception = exc_info[1]
        # Check if it's a FreyaError with correlation_id and context
        if hasattr(exception, "correlation_id") and exception.correlation_id:
            event_dict.setdefault("correlation_id", exception.correlation_id)
        if hasattr(exception, "context") and exception.context:
            event_dict.update(exception.context)
    return event_dict


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with correlation ID support.

    Extends python-json-logger to add custom fields and formatting.
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to JSON log record.

        Args:
            log_record: Dictionary to write JSON log fields to.
            record: Python logging LogRecord.
            message_dict: Dictionary of message fields.
        """
        super().add_fields(log_record, record, message_dict)

        # Add correlation_id if available
        correlation_id = get_correlation_id()
        if correlation_id:
            log_record["correlation_id"] = correlation_id

        # Ensure consistent field names
        log_record["logger"] = record.name
        log_record["level"] = record.levelname
        log_record["timestamp"] = self.formatTime(record, self.datefmt)


def configure_logging(
    *,
    json_format: bool = False,
    file_level: int = logging.INFO,
    console_level: int = logging.WARNING,
    log_file: Optional[Path] = None,
    force: bool = False,
) -> None:
    """Configure structured logging for Freya.

    Args:
        json_format: If True, use JSON output. If False, use human-readable.
        file_level: Minimum log level for file output.
        console_level: Minimum log level for console output.
        log_file: Path to log file (default: freya.log).
        force: If True, reconfigure even if already configured.

    Example:
        # Development: human-readable logs
        configure_logging(json_format=False, console_level=logging.DEBUG)

        # Production: JSON logs for aggregation
        configure_logging(json_format=True, file_level=logging.INFO)
    """
    global _CONFIGURED

    if _CONFIGURED and not force:
        return

    if _CONFIGURED and force:
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        _CONFIGURED = False

    log_path = log_file or _LOG_FILE

    # Configure standard library logging
    logging.basicConfig(
        level=min(file_level, console_level),
        format="%(message)s",  # structlog will format
        handlers=[],
    )

    # Structlog processors
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_correlation_id,
        add_exception_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_format:
        # JSON output for production
        processors.extend(
            [
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ]
        )
    else:
        # Human-readable output for development
        processors.extend(
            [
                structlog.processors.ExceptionPrettyPrinter(),
                structlog.dev.ConsoleRenderer(colors=True),
            ]
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Add file handler
    if log_path:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(file_level)
        if json_format:
            file_handler.setFormatter(
                JSONFormatter("(timestamp) (level) (logger) (message)")
            )
        logging.getLogger().addHandler(file_handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    logging.getLogger().addHandler(console_handler)

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger for the specified module.

    Args:
        name: Module name (typically __name__). If None, returns root Freya logger.

    Returns:
        Structured logger bound to the specified name.

    Example:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=123, ip_address="192.168.1.1")
    """
    if name:
        logger_name = f"{_LOGGER_NAME}.{name}"
    else:
        logger_name = _LOGGER_NAME

    return structlog.get_logger(logger_name)


def log_exception(
    logger: structlog.stdlib.BoundLogger,
    exception: Exception,
    message: str = "exception_occurred",
    **extra_context: Any,
) -> None:
    """Log an exception with full context.

    If the exception is a FreyaError, automatically includes correlation_id
    and context. Otherwise, logs with standard exception info.

    Args:
        logger: Logger instance to use.
        exception: Exception to log.
        message: Log message/event name.
        **extra_context: Additional context to include.

    Example:
        try:
            result = perform_operation()
        except ToolExecutionError as exc:
            log_exception(logger, exc, "tool_failed", operation="search")
        except Exception as exc:
            log_exception(logger, exc, "unexpected_error")
    """
    context = dict(extra_context)

    # Extract correlation_id and context from FreyaError
    if hasattr(exception, "correlation_id") and exception.correlation_id:
        context["correlation_id"] = exception.correlation_id
    if hasattr(exception, "context") and exception.context:
        context.update(exception.context)

    # Add exception details
    context["exception_type"] = type(exception).__name__
    context["exception_message"] = str(exception)

    logger.error(message, exc_info=True, **context)


def create_child_logger(
    logger: structlog.stdlib.BoundLogger, **bindings: Any
) -> structlog.stdlib.BoundLogger:
    """Create a child logger with permanent context bindings.

    Args:
        logger: Parent logger.
        **bindings: Key-value pairs to bind to the child logger.

    Returns:
        New logger with bound context.

    Example:
        request_logger = create_child_logger(
            logger,
            request_id="req-123",
            user_id=456
        )
        request_logger.info("step_1")  # Includes request_id and user_id
        request_logger.info("step_2")  # Includes request_id and user_id
    """
    return logger.bind(**bindings)


# Backward compatibility with old logger.py API
def configure_logging_legacy(
    file_level: int = logging.INFO,
    console_level: int = logging.WARNING,
    *,
    force: bool = False,
) -> None:
    """Legacy API compatibility for configure_logging.

    Args:
        file_level: Minimum log level for file output.
        console_level: Minimum log level for console output.
        force: If True, reconfigure even if already configured.
    """
    configure_logging(
        json_format=False,
        file_level=file_level,
        console_level=console_level,
        force=force,
    )


__all__ = [
    "configure_logging",
    "get_logger",
    "get_correlation_id",
    "set_correlation_id",
    "bind_correlation_id",
    "log_exception",
    "create_child_logger",
    "add_correlation_id",
    "add_exception_context",
    "JSONFormatter",
]
