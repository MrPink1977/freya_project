"""Logging utilities for the Freya application."""

from __future__ import annotations

import logging
import logging.handlers
from logging import Logger
from pathlib import Path
from typing import Optional

_LOGGER_NAME = "freya"
_LOG_FILE = Path("freya.log")
_CONFIGURED = False


def configure_logging(
    file_level: int = logging.INFO,
    console_level: int = logging.WARNING,
    *,
    log_file: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB default
    backup_count: int = 5,
    force: bool = False,
) -> None:
    """Configure the root logger for the application.

    Args:
        file_level: Minimum log level for file output
        console_level: Minimum log level for console output
        log_file: Path to log file (defaults to freya.log)
        max_bytes: Maximum size of log file before rotation (default 10MB)
        backup_count: Number of rotated log files to keep (default 5)
        force: Force reconfiguration even if already configured
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return
    if _CONFIGURED and force:
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        _CONFIGURED = False

    # Use rotating file handler to prevent unbounded log growth
    log_path = log_file or _LOG_FILE
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        encoding="utf-8",
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(file_level)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(console_level)

    handlers = [
        file_handler,
        stream_handler,
    ]

    logging.basicConfig(
        level=min(file_level, console_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
    )

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> Logger:
    """Return a logger scoped to the Freya package.

    Args:
        name: Optional name to append to logger namespace (e.g., "stt" -> "freya.stt")

    Returns:
        Logger instance with appropriate namespace
    """
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def set_module_log_level(module_name: str, level: int) -> None:
    """Set log level for a specific module.

    Args:
        module_name: Name of the module (e.g., "stt", "tts", "orchestrator")
        level: Log level (e.g., logging.DEBUG, logging.INFO)

    Example:
        >>> set_module_log_level("stt", logging.DEBUG)  # Enable debug logs for STT only
    """
    logger = get_logger(module_name)
    logger.setLevel(level)
