"""Time and date tools for Freya."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .base import FreyaTool, ToolResult


class GetCurrentTime(FreyaTool):
    """Get the current time in a specified timezone."""

    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "Get the current time (optionally in a specific timezone)"

    def execute(self, timezone: str = "UTC", format: str = "12h") -> ToolResult:
        """Get current time.

        Args:
            timezone: Timezone name (e.g., 'America/New_York', 'Europe/London', 'UTC')
            format: Time format ('12h' for 12-hour, '24h' for 24-hour)

        Returns:
            ToolResult with formatted current time
        """
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)

            if format == "12h":
                time_str = now.strftime("%I:%M:%S %p")
            else:
                time_str = now.strftime("%H:%M:%S")

            date_str = now.strftime("%A, %B %d, %Y")
            output = f"{time_str} on {date_str} ({timezone})"

            return ToolResult(
                success=True,
                output=output,
                metadata={"timestamp": now.isoformat(), "timezone": timezone},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to get time: {e}")


class GetCurrentDate(FreyaTool):
    """Get the current date."""

    @property
    def name(self) -> str:
        return "get_current_date"

    @property
    def description(self) -> str:
        return "Get the current date in various formats"

    def execute(self, format: str = "long") -> ToolResult:
        """Get current date.

        Args:
            format: Date format ('long', 'short', 'iso')

        Returns:
            ToolResult with formatted date
        """
        try:
            now = datetime.now()

            if format == "long":
                output = now.strftime("%A, %B %d, %Y")
            elif format == "short":
                output = now.strftime("%m/%d/%Y")
            elif format == "iso":
                output = now.strftime("%Y-%m-%d")
            else:
                output = now.strftime("%A, %B %d, %Y")

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "year": now.year,
                    "month": now.month,
                    "day": now.day,
                    "weekday": now.strftime("%A"),
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to get date: {e}")


class CalculateTimeUntil(FreyaTool):
    """Calculate time remaining until a future date/time."""

    @property
    def name(self) -> str:
        return "calculate_time_until"

    @property
    def description(self) -> str:
        return "Calculate how much time until a specific date or time"

    def execute(self, target_date: str) -> ToolResult:
        """Calculate time until target.

        Args:
            target_date: Target date/time in ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)

        Returns:
            ToolResult with time remaining
        """
        try:
            # Parse target date
            try:
                target = datetime.fromisoformat(target_date)
            except ValueError:
                # Try date only format
                target = datetime.strptime(target_date, "%Y-%m-%d")

            now = datetime.now()
            delta = target - now

            if delta.total_seconds() < 0:
                return ToolResult(
                    success=True, output=f"That date has already passed {abs(delta.days)} days ago"
                )

            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

            if not parts:
                parts.append(f"{seconds} seconds")

            output = f"{', '.join(parts)} until {target.strftime('%B %d, %Y at %I:%M %p')}"

            return ToolResult(
                success=True,
                output=output,
                metadata={"total_seconds": delta.total_seconds(), "days": days},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to calculate time: {e}")


__all__ = ["GetCurrentTime", "GetCurrentDate", "CalculateTimeUntil"]
