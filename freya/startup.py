"""Startup mode configuration for Freya.

This module contains lightweight startup configuration logic
with no heavy dependencies to allow for easy testing.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import AppConfig


class StartupMode(str, Enum):
    """Available startup display modes for Freya."""

    NORMAL = "normal"
    DIAGNOSTIC = "diagnostic"


def parse_mode(value: str) -> StartupMode:
    """Parse startup mode from string value.

    Args:
        value: Mode string ("normal" or "diagnostic")

    Returns:
        StartupMode enum value, defaults to NORMAL if invalid
    """
    if value.lower() == StartupMode.DIAGNOSTIC.value:
        return StartupMode.DIAGNOSTIC
    return StartupMode.NORMAL


def select_startup_mode(app_config: AppConfig) -> StartupMode:
    """Select startup mode based on configuration.

    This function respects app_config.startup_mode and app_config.prompt_for_mode.
    If prompt_for_mode is enabled the user is prompted (unless non-interactive),
    otherwise the configured default is returned.

    Args:
        app_config: Application configuration

    Returns:
        Selected startup mode
    """
    default_mode = parse_mode(app_config.startup_mode)
    if not app_config.prompt_for_mode:
        return default_mode

    # If stdin is not a TTY (non-interactive), fall back to default without prompting
    try:
        if not os.isatty(0):  # pragma: no cover - environment specific
            return default_mode
    except Exception:
        # If the platform doesn't support isatty, continue to attempt prompt
        pass

    prompt = "Select startup mode - [N]ormal or [D]iagnostic " f"(default: {default_mode.value.title()}): "
    try:
        choice = input(prompt).strip().lower()
    except EOFError:
        choice = ""

    if not choice:
        return default_mode
    if choice in {"n", "normal"}:
        return StartupMode.NORMAL
    if choice in {"d", "diagnostic"}:
        return StartupMode.DIAGNOSTIC
    return default_mode


__all__ = ["StartupMode", "parse_mode", "select_startup_mode"]
