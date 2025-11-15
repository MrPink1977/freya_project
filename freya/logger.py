"""Logging utilities for the Freya application."""

from __future__ import annotations

import logging
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
    force: bool = False,
) -> None:
    """Configure the root logger for the application."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return
    if _CONFIGURED and force:
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        _CONFIGURED = False

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
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
    """Return a logger scoped to the Freya package."""
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)