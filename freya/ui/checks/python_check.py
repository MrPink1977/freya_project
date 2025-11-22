"""Python version and environment check."""

from __future__ import annotations

import sys
from pathlib import Path

from . import BaseSystemCheck, CheckResult, CheckStatus


class PythonCheck(BaseSystemCheck):
    """Check Python version and virtual environment."""

    def __init__(self, min_version: tuple[int, int] = (3, 11)):
        super().__init__(
            name="Python Environment",
            description=f"Check Python version >= {min_version[0]}.{min_version[1]}",
            required=True,
        )
        self.min_version = min_version

    async def run(self) -> CheckResult:
        """Check Python version."""
        current_version = sys.version_info[:2]

        if current_version < self.min_version:
            return CheckResult(
                status=CheckStatus.FAILED,
                message=f"Python {current_version[0]}.{current_version[1]} < {self.min_version[0]}.{self.min_version[1]}",
                fix_suggestion=f"Upgrade to Python {self.min_version[0]}.{self.min_version[1]}+",
            )

        # Check if in virtual environment
        in_venv = sys.prefix != sys.base_prefix

        venv_info = "virtual environment" if in_venv else "system Python"
        details = f"Python {current_version[0]}.{current_version[1]} ({venv_info})\nExecutable: {sys.executable}"

        return CheckResult(
            status=CheckStatus.PASSED,
            message=f"Python {current_version[0]}.{current_version[1]} ✓",
            details=details,
        )
