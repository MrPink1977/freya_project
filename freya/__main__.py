"""Expose main module functions for testing."""

import sys
from pathlib import Path

# Add parent directory to path to import main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import StartupMode, _parse_mode, _select_startup_mode  # noqa: E402, F401
