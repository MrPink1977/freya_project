"""
Wrapper to make root main.py accessible as freya.main for testing.
"""
# Import everything from the root main module
import sys
from pathlib import Path

# Add parent directory to path to import root main.py
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

import main

# Re-export all public and private symbols for testing
from main import *  # noqa: F401, F403
from main import _parse_mode, _select_startup_mode  # noqa: F401

# Make the main module available as well
__all__ = ['main', 'StartupMode', '_parse_mode', '_select_startup_mode']
