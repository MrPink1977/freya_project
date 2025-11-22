"""Base system check class for TUI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CheckStatus(Enum):
    """Status of a system check."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

    @property
    def icon(self) -> str:
        """Get icon for status."""
        return {
            CheckStatus.PENDING: "○",
            CheckStatus.RUNNING: "◐",
            CheckStatus.PASSED: "✓",
            CheckStatus.FAILED: "✗",
            CheckStatus.WARNING: "⚠",
            CheckStatus.SKIPPED: "⊘",
        }[self]

    @property
    def color(self) -> str:
        """Get color class for status."""
        return {
            CheckStatus.PENDING: "status-pending",
            CheckStatus.RUNNING: "status-running",
            CheckStatus.PASSED: "status-ok",
            CheckStatus.FAILED: "status-error",
            CheckStatus.WARNING: "status-warning",
            CheckStatus.SKIPPED: "status-pending",
        }[self]


@dataclass
class CheckResult:
    """Result of a system check."""

    status: CheckStatus
    message: str
    details: Optional[str] = None
    fix_suggestion: Optional[str] = None
    duration: Optional[float] = None


class BaseSystemCheck(ABC):
    """Base class for system checks."""

    def __init__(self, name: str, description: str, required: bool = True):
        self.name = name
        self.description = description
        self.required = required
        self.status = CheckStatus.PENDING
        self.result: Optional[CheckResult] = None

    @abstractmethod
    async def run(self) -> CheckResult:
        """Run the check and return result."""
        pass

    async def execute(self) -> CheckResult:
        """Execute check with error handling and timing."""
        import time

        self.status = CheckStatus.RUNNING
        start_time = time.time()

        try:
            self.result = await self.run()
            self.result.duration = time.time() - start_time
            self.status = self.result.status
            return self.result
        except Exception as e:
            duration = time.time() - start_time
            self.result = CheckResult(
                status=CheckStatus.FAILED,
                message=f"Check failed: {e}",
                details=str(e),
                duration=duration,
            )
            self.status = CheckStatus.FAILED
            return self.result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name!r}, status={self.status.value})>"
