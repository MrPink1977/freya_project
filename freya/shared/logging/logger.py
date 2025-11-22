"""
Structured logging infrastructure for Freya.

This module provides a comprehensive logging system with:
- Structured logging with context
- Multiple output formats (JSON, console)
- Log levels and filtering
- Performance tracking
- Error tracking with stack traces
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from pythonjsonlogger import jsonlogger


class FreyaLogger:
    """
    Structured logger for Freya assistant.
    
    Provides context-aware logging with structured data support.
    """

    def __init__(self, name: str, context: dict[str, Any] | None = None) -> None:
        """
        Initialize logger.
        
        Args:
            name: Logger name (typically module name)
            context: Default context to include in all log messages
        """
        self._name = name
        self._context = context or {}
        self._logger = structlog.get_logger(name)

    def bind(self, **kwargs: Any) -> FreyaLogger:
        """
        Create a new logger with additional context.
        
        Args:
            **kwargs: Context key-value pairs
            
        Returns:
            New logger instance with bound context
        """
        new_context = {**self._context, **kwargs}
        return FreyaLogger(self._name, new_context)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log("debug", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log("info", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log("warning", message, **kwargs)

    def error(
        self,
        message: str,
        exc_info: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Log error message.
        
        Args:
            message: Error message
            exc_info: Exception to log with stack trace
            **kwargs: Additional context
        """
        if exc_info:
            kwargs["exc_info"] = exc_info
        self._log("error", message, **kwargs)

    def critical(
        self,
        message: str,
        exc_info: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Log critical message.
        
        Args:
            message: Critical message
            exc_info: Exception to log with stack trace
            **kwargs: Additional context
        """
        if exc_info:
            kwargs["exc_info"] = exc_info
        self._log("critical", message, **kwargs)

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Internal logging method."""
        context = {**self._context, **kwargs}
        log_method = getattr(self._logger, level)
        log_method(message, **context)


def configure_logging(
    level: str = "INFO",
    json_logs: bool = False,
    log_file: Path | None = None,
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output JSON-formatted logs
        log_file: Optional file path for log output
    """
    # Convert level string to logging constant
    log_level = getattr(logging, level.upper())

    # Configure standard library logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[],
    )

    # Create handlers
    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if json_logs:
        # JSON formatter for structured logs
        json_formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "name": "logger"},
        )
        console_handler.setFormatter(json_formatter)
    else:
        # Human-readable formatter
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)

    handlers.append(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)

        # Always use JSON for file logs
        json_formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "name": "logger"},
        )
        file_handler.setFormatter(json_formatter)
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = handlers

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **context: Any) -> FreyaLogger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        **context: Default context for this logger
        
    Returns:
        Configured logger instance
    """
    return FreyaLogger(name, context)


# Convenience function for module-level usage
def create_logger(name: str) -> FreyaLogger:
    """
    Create a logger for a module.
    
    Args:
        name: Module name (use __name__)
        
    Returns:
        Logger instance
    """
    return get_logger(name)
