"""Quick validation test for agent architecture."""

import asyncio

import pytest


class TestImports:
    """Test that all critical imports work."""

    def test_message_bus_import(self):
        """Test MessageBus import."""
        from freya.core.message_bus import MessageBus
        assert MessageBus is not None

    def test_base_agent_import(self):
        """Test BaseAgent import."""
        from freya.agents.base_agent import BaseAgent
        assert BaseAgent is not None

    def test_dialog_agent_import(self):
        """Test DialogAgent import."""
        from freya.agents.dialog_agent import DialogAgent
        assert DialogAgent is not None

    def test_memory_agent_import(self):
        """Test MemoryAgent import."""
        from freya.agents.memory_agent import MemoryAgent
        assert MemoryAgent is not None

    def test_tool_executor_agent_import(self):
        """Test ToolExecutorAgent import."""
        from freya.agents.tool_executor_agent import ToolExecutorAgent
        assert ToolExecutorAgent is not None

    def test_wake_word_agent_import(self):
        """Test WakeWordAgent import."""
        from freya.agents.wake_word_agent import WakeWordAgent
        assert WakeWordAgent is not None

    def test_orchestration_coordinator_import(self):
        """Test OrchestrationCoordinator import."""
        from freya.coordination.orchestration_coordinator import OrchestrationCoordinator
        assert OrchestrationCoordinator is not None


class TestMessageBusPubSub:
    """Test basic MessageBus pub/sub functionality."""

    @pytest.mark.asyncio
    async def test_message_bus_pubsub(self):
        """Test basic MessageBus pub/sub."""
        from freya.core.message_bus import MessageBus, MessagePriority

        bus = MessageBus()
        await bus.start()

        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("test.topic", handler)

        await bus.publish("test.topic", {"data": "test"}, "test", MessagePriority.NORMAL)

        await asyncio.sleep(0.1)

        await bus.stop()

        assert len(received) == 1
        assert received[0].payload == {"data": "test"}
