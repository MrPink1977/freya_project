"""Tests for tool execution timeouts."""

import asyncio
import time

import pytest

from freya.tools.base import (
    FreyaTool,
    ToolResult,
    ToolTimeoutError,
)
from freya.tools.manager import ToolManager


class SlowSyncTool(FreyaTool):
    """Test tool that takes a long time to execute (synchronous)."""

    @property
    def name(self) -> str:
        return "slow_sync_tool"

    @property
    def description(self) -> str:
        return "A tool that runs slowly (sync)"

    def execute(self, delay: float = 1.0, **kwargs) -> ToolResult:
        """Execute slowly."""
        time.sleep(delay)
        return ToolResult(success=True, output=f"Completed after {delay}s")


class SlowAsyncTool(FreyaTool):
    """Test tool that takes a long time to execute (asynchronous)."""

    @property
    def name(self) -> str:
        return "slow_async_tool"

    @property
    def description(self) -> str:
        return "A tool that runs slowly (async)"

    async def execute(self, delay: float = 1.0, **kwargs) -> ToolResult:
        """Execute slowly."""
        await asyncio.sleep(delay)
        return ToolResult(success=True, output=f"Completed after {delay}s")


class FastTool(FreyaTool):
    """Test tool that executes quickly."""

    @property
    def name(self) -> str:
        return "fast_tool"

    @property
    def description(self) -> str:
        return "A tool that runs quickly"

    def execute(self, **kwargs) -> ToolResult:
        """Execute quickly."""
        return ToolResult(success=True, output="Fast completion")


class TestToolTimeouts:
    """Test tool execution timeout functionality."""

    def test_fast_tool_completes_within_timeout(self):
        """Fast tool completes without timeout."""
        tool = FastTool()
        result = tool.execute_with_timeout(timeout=5.0)
        assert result.success
        assert "Fast completion" in result.output

    def test_slow_sync_tool_times_out(self):
        """Slow synchronous tool times out."""
        tool = SlowSyncTool()

        with pytest.raises(ToolTimeoutError) as exc_info:
            tool.execute_with_timeout(timeout=0.5, delay=2.0)

        assert "slow_sync_tool" in str(exc_info.value)
        assert "0.5" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_slow_async_tool_times_out(self):
        """Slow asynchronous tool times out."""
        tool = SlowAsyncTool()

        with pytest.raises(ToolTimeoutError) as exc_info:
            tool.execute_with_timeout(timeout=0.5, delay=2.0)

        assert "slow_async_tool" in str(exc_info.value)

    def test_default_timeout_used_when_not_specified(self):
        """Default timeout is used when not specified."""
        tool = SlowSyncTool()

        # Should complete within default timeout
        result = tool.execute_with_timeout(delay=0.1)
        assert result.success

    def test_custom_timeout_honored(self):
        """Custom timeout value is respected."""
        tool = SlowSyncTool()

        # Should timeout with short custom timeout
        with pytest.raises(ToolTimeoutError):
            tool.execute_with_timeout(timeout=0.2, delay=1.0)

        # Should complete with longer custom timeout
        result = tool.execute_with_timeout(timeout=2.0, delay=0.5)
        assert result.success

    def test_timeout_error_includes_tool_name(self):
        """ToolTimeoutError includes tool name."""
        tool = SlowSyncTool()

        try:
            tool.execute_with_timeout(timeout=0.1, delay=1.0)
        except ToolTimeoutError as exc:
            assert exc.tool_name == "slow_sync_tool"
            assert exc.timeout == 0.1

    def test_tool_manager_executes_with_timeout(self):
        """ToolManager can execute tools with timeout."""
        manager = ToolManager()
        slow_tool = SlowSyncTool()
        manager.register_tool(slow_tool)

        # Should timeout
        result = manager.execute_tool("slow_sync_tool", timeout=0.2, delay=2.0)
        assert not result.success
        assert "timed out" in result.error.lower()

    def test_tool_manager_completes_within_timeout(self):
        """ToolManager successfully executes fast tools."""
        manager = ToolManager()
        fast_tool = FastTool()
        manager.register_tool(fast_tool)

        result = manager.execute_tool("fast_tool", timeout=5.0)
        assert result.success


class TestTimeoutEdgeCases:
    """Test edge cases for timeout functionality."""

    def test_zero_timeout_raises_immediately(self):
        """Zero timeout should fail immediately."""
        tool = SlowSyncTool()

        with pytest.raises(ToolTimeoutError):
            tool.execute_with_timeout(timeout=0.0, delay=0.1)

    def test_very_large_timeout_allows_completion(self):
        """Very large timeout allows completion."""
        tool = SlowSyncTool()

        result = tool.execute_with_timeout(timeout=1000.0, delay=0.1)
        assert result.success

    def test_timeout_with_no_delay_completes(self):
        """Tool with no delay completes instantly."""
        tool = FastTool()

        result = tool.execute_with_timeout(timeout=0.1)
        assert result.success
