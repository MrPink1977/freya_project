"""Date and time tools."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from freya.infrastructure.tools.base_tool import BaseTool


class GetCurrentTimeTool(BaseTool):
    """Tool to get the current time."""

    def __init__(self) -> None:
        """Initialize tool."""
        super().__init__(
            name="get_current_time",
            description="Get the current time in a specified format and timezone",
        )

    def get_parameters_schema(self) -> dict[str, Any]:
        """Get parameter schema."""
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "Time format (12h or 24h)",
                    "enum": ["12h", "24h"],
                    "default": "12h",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone (e.g., UTC, America/New_York)",
                    "default": "local",
                },
            },
            "required": [],
        }

    async def _execute_internal(self, **parameters: Any) -> str:
        """Execute tool."""
        time_format = parameters.get("format", "12h")
        timezone = parameters.get("timezone", "local")

        now = datetime.now()

        if time_format == "12h":
            time_str = now.strftime("%I:%M %p")
        else:
            time_str = now.strftime("%H:%M")

        return f"The current time is {time_str}"


class GetCurrentDateTool(BaseTool):
    """Tool to get the current date."""

    def __init__(self) -> None:
        """Initialize tool."""
        super().__init__(
            name="get_current_date",
            description="Get the current date in a specified format",
        )

    def get_parameters_schema(self) -> dict[str, Any]:
        """Get parameter schema."""
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "Date format (full, short, iso)",
                    "enum": ["full", "short", "iso"],
                    "default": "full",
                },
            },
            "required": [],
        }

    async def _execute_internal(self, **parameters: Any) -> str:
        """Execute tool."""
        date_format = parameters.get("format", "full")

        now = datetime.now()

        if date_format == "full":
            date_str = now.strftime("%A, %B %d, %Y")
        elif date_format == "short":
            date_str = now.strftime("%m/%d/%Y")
        else:  # iso
            date_str = now.strftime("%Y-%m-%d")

        return f"Today's date is {date_str}"


class CalculateDateDifferenceTool(BaseTool):
    """Tool to calculate difference between dates."""

    def __init__(self) -> None:
        """Initialize tool."""
        super().__init__(
            name="calculate_date_difference",
            description="Calculate the difference between two dates",
        )

    def get_parameters_schema(self) -> dict[str, Any]:
        """Get parameter schema."""
        return {
            "type": "object",
            "properties": {
                "date1": {
                    "type": "string",
                    "description": "First date (YYYY-MM-DD format)",
                },
                "date2": {
                    "type": "string",
                    "description": "Second date (YYYY-MM-DD format)",
                },
                "unit": {
                    "type": "string",
                    "description": "Unit for result (days, weeks, months, years)",
                    "enum": ["days", "weeks", "months", "years"],
                    "default": "days",
                },
            },
            "required": ["date1", "date2"],
        }

    async def _execute_internal(self, **parameters: Any) -> str:
        """Execute tool."""
        date1_str = parameters["date1"]
        date2_str = parameters["date2"]
        unit = parameters.get("unit", "days")

        # Parse dates
        date1 = datetime.strptime(date1_str, "%Y-%m-%d")
        date2 = datetime.strptime(date2_str, "%Y-%m-%d")

        # Calculate difference
        diff = abs((date2 - date1).days)

        if unit == "weeks":
            result = diff / 7
            unit_str = "weeks"
        elif unit == "months":
            result = diff / 30.44  # Average month length
            unit_str = "months"
        elif unit == "years":
            result = diff / 365.25  # Account for leap years
            unit_str = "years"
        else:
            result = diff
            unit_str = "days"

        return f"The difference is {result:.1f} {unit_str}"
