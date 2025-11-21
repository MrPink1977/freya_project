"""Comprehensive tests for datetime tools."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from freya.tools.datetime_tools import CalculateTimeUntil, GetCurrentDate, GetCurrentTime

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def get_current_time_tool():
    """Provide GetCurrentTime instance."""
    return GetCurrentTime()


@pytest.fixture
def get_current_date_tool():
    """Provide GetCurrentDate instance."""
    return GetCurrentDate()


@pytest.fixture
def calculate_time_until_tool():
    """Provide CalculateTimeUntil instance."""
    return CalculateTimeUntil()


# ============================================================================
# GET CURRENT TIME TESTS
# ============================================================================


class TestGetCurrentTime:
    """Test current time retrieval."""

    def test_get_time_utc(self, get_current_time_tool):
        """Get current time in UTC."""
        result = get_current_time_tool.execute(timezone="UTC")

        assert result.success is True
        assert "UTC" in result.output
        assert "metadata" in dir(result)
        assert result.metadata["timezone"] == "UTC"

    def test_get_time_12h_format(self, get_current_time_tool):
        """Get time in 12-hour format."""
        result = get_current_time_tool.execute(timezone="UTC", format="12h")

        assert result.success is True
        # Should contain AM or PM
        assert "AM" in result.output or "PM" in result.output

    def test_get_time_24h_format(self, get_current_time_tool):
        """Get time in 24-hour format."""
        result = get_current_time_tool.execute(timezone="UTC", format="24h")

        assert result.success is True
        # Should not contain AM/PM
        assert "AM" not in result.output
        assert "PM" not in result.output

    @pytest.mark.parametrize("timezone", [
        "America/New_York",
        "Europe/London",
        "Asia/Tokyo",
        "Australia/Sydney",
    ])
    def test_various_timezones(self, get_current_time_tool, timezone):
        """Test various valid timezones."""
        result = get_current_time_tool.execute(timezone=timezone)

        assert result.success is True
        assert timezone in result.output
        assert result.metadata["timezone"] == timezone

    def test_invalid_timezone(self, get_current_time_tool):
        """Handle invalid timezone gracefully."""
        result = get_current_time_tool.execute(timezone="Invalid/Timezone")

        assert result.success is False
        assert result.error is not None

    def test_metadata_includes_timestamp(self, get_current_time_tool):
        """Metadata includes ISO timestamp."""
        result = get_current_time_tool.execute(timezone="UTC")

        assert result.success is True
        assert "timestamp" in result.metadata
        # Validate ISO format can be parsed
        datetime.fromisoformat(result.metadata["timestamp"])

    def test_result_structure(self, get_current_time_tool):
        """Validate ToolResult structure."""
        result = get_current_time_tool.execute()

        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert hasattr(result, "metadata")


# ============================================================================
# GET CURRENT DATE TESTS
# ============================================================================


class TestGetCurrentDate:
    """Test current date retrieval."""

    def test_get_date_long_format(self, get_current_date_tool):
        """Get date in long format."""
        result = get_current_date_tool.execute(format="long")

        assert result.success is True
        # Long format includes day name and full month
        now = datetime.now()
        assert now.strftime("%Y") in result.output  # Year should be present

    def test_get_date_short_format(self, get_current_date_tool):
        """Get date in short format."""
        result = get_current_date_tool.execute(format="short")

        assert result.success is True
        # Short format is MM/DD/YYYY
        assert "/" in result.output
        parts = result.output.split("/")
        assert len(parts) == 3

    def test_get_date_iso_format(self, get_current_date_tool):
        """Get date in ISO format."""
        result = get_current_date_tool.execute(format="iso")

        assert result.success is True
        # ISO format is YYYY-MM-DD
        assert "-" in result.output
        parts = result.output.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # Year is 4 digits

    def test_metadata_includes_date_parts(self, get_current_date_tool):
        """Metadata includes year, month, day, weekday."""
        result = get_current_date_tool.execute()

        assert result.success is True
        assert "year" in result.metadata
        assert "month" in result.metadata
        assert "day" in result.metadata
        assert "weekday" in result.metadata

        # Validate values are reasonable
        now = datetime.now()
        assert result.metadata["year"] == now.year
        assert result.metadata["month"] == now.month
        assert result.metadata["day"] == now.day

    def test_default_format(self, get_current_date_tool):
        """Default format should be long."""
        result = get_current_date_tool.execute()

        assert result.success is True
        # Long format includes month name
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        assert any(month in result.output for month in months)

    def test_result_structure(self, get_current_date_tool):
        """Validate ToolResult structure."""
        result = get_current_date_tool.execute()

        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert hasattr(result, "metadata")


# ============================================================================
# CALCULATE TIME UNTIL TESTS
# ============================================================================


class TestCalculateTimeUntil:
    """Test time calculation functionality."""

    def test_future_date_days_away(self, calculate_time_until_tool):
        """Calculate time until future date (days)."""
        # Date 5 days from now
        future = datetime.now() + timedelta(days=5)
        target = future.strftime("%Y-%m-%d")

        result = calculate_time_until_tool.execute(target_date=target)

        assert result.success is True
        assert "day" in result.output
        assert result.metadata["days"] >= 4  # At least 4 days (allowing for rounding)

    def test_future_datetime_hours_away(self, calculate_time_until_tool):
        """Calculate time until future datetime (hours)."""
        # 3 hours from now
        future = datetime.now() + timedelta(hours=3)
        target = future.strftime("%Y-%m-%d %H:%M:%S")

        result = calculate_time_until_tool.execute(target_date=target)

        assert result.success is True
        assert "hour" in result.output

    def test_past_date(self, calculate_time_until_tool):
        """Handle past dates correctly."""
        # Date 10 days ago
        past = datetime.now() - timedelta(days=10)
        target = past.strftime("%Y-%m-%d")

        result = calculate_time_until_tool.execute(target_date=target)

        assert result.success is True
        assert "passed" in result.output or "ago" in result.output

    def test_date_only_format(self, calculate_time_until_tool):
        """Accept date-only format (YYYY-MM-DD)."""
        future = datetime.now() + timedelta(days=2)
        target = future.strftime("%Y-%m-%d")

        result = calculate_time_until_tool.execute(target_date=target)

        assert result.success is True

    def test_datetime_format(self, calculate_time_until_tool):
        """Accept datetime format (YYYY-MM-DD HH:MM:SS)."""
        future = datetime.now() + timedelta(hours=6)
        target = future.strftime("%Y-%m-%d %H:%M:%S")

        result = calculate_time_until_tool.execute(target_date=target)

        assert result.success is True

    def test_invalid_date_format(self, calculate_time_until_tool):
        """Handle invalid date format."""
        invalid_dates = [
            "not-a-date",
            "13/45/2025",
            "2025-13-45",
            "tomorrow",
        ]

        for date in invalid_dates:
            result = calculate_time_until_tool.execute(target_date=date)
            assert result.success is False
            assert result.error is not None

    def test_metadata_includes_calculation(self, calculate_time_until_tool):
        """Metadata includes total_seconds and days."""
        future = datetime.now() + timedelta(days=3, hours=2)
        target = future.strftime("%Y-%m-%d %H:%M:%S")

        result = calculate_time_until_tool.execute(target_date=target)

        assert result.success is True
        assert "total_seconds" in result.metadata
        assert "days" in result.metadata
        assert result.metadata["total_seconds"] > 0

    def test_very_near_future(self, calculate_time_until_tool):
        """Handle very near future (seconds)."""
        # 30 seconds from now
        future = datetime.now() + timedelta(seconds=30)
        target = future.strftime("%Y-%m-%d %H:%M:%S")

        result = calculate_time_until_tool.execute(target_date=target)

        assert result.success is True
        assert "second" in result.output

    def test_result_structure(self, calculate_time_until_tool):
        """Validate ToolResult structure."""
        future = datetime.now() + timedelta(days=1)
        target = future.strftime("%Y-%m-%d")
        result = calculate_time_until_tool.execute(target_date=target)

        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert hasattr(result, "metadata")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestDateTimeToolsIntegration:
    """Test datetime tools working together."""

    def test_all_tools_have_consistent_structure(
        self, get_current_time_tool, get_current_date_tool, calculate_time_until_tool
    ):
        """All tools return consistent ToolResult structure."""
        tools_and_args = [
            (get_current_time_tool, {}),
            (get_current_date_tool, {}),
            (calculate_time_until_tool, {"target_date": "2025-12-25"}),
        ]

        for tool, kwargs in tools_and_args:
            result = tool.execute(**kwargs)

            assert hasattr(result, "success")
            assert hasattr(result, "output")
            assert hasattr(result, "error")
            assert hasattr(result, "metadata")

            if result.success:
                assert isinstance(result.output, str)
                assert len(result.output) > 0

    def test_tools_handle_errors_gracefully(
        self, get_current_time_tool, calculate_time_until_tool
    ):
        """All tools handle errors with proper structure."""
        error_cases = [
            (get_current_time_tool, {"timezone": "Invalid/Zone"}),
            (calculate_time_until_tool, {"target_date": "invalid"}),
        ]

        for tool, kwargs in error_cases:
            result = tool.execute(**kwargs)

            assert result.success is False
            assert result.error is not None
            assert isinstance(result.error, str)
            assert len(result.error) > 0
