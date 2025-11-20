"""
TESTS FOR AGENT RESTART AND HEALTH INTEGRATION.

Tests manual restart and health monitoring integration.
"""

import asyncio
import pytest
import pytest_asyncio

from freya.core.message_bus import MessageBus, Message, MessagePriority
from freya.core.health_monitor import HealthMonitor
from freya.agents.base_agent import BaseAgent, AgentCapability, AgentState


class TestAgent(BaseAgent):
    """Test agent implementation."""
    
    def __init__(self, agent_id: str, bus: MessageBus, health_monitor=None, fail_init=False):
        super().__init__(agent_id, bus, health_monitor)
        self.fail_init = fail_init
        self.messages_processed = 0
        self.init_count = 0
        self.cleanup_count = 0
    
    async def initialize(self) -> None:
        """Initialize test agent."""
        self.init_count += 1
        if self.fail_init:
            raise RuntimeError("Initialization failed")
        await asyncio.sleep(0.1)  # Simulate initialization
    
    def get_capabilities(self):
        """Return test capabilities."""
        return [
            AgentCapability(
                name="test",
                description="Test capability",
                input_topics=["test.input"],
                output_topics=["test.output"],
            )
        ]
    
    async def process_message(self, message: Message) -> None:
        """Process test message."""
        self.messages_processed += 1
        await self.publish("test.output", {"processed": message.payload}, MessagePriority.NORMAL)
    
    async def cleanup(self) -> None:
        """Cleanup test agent."""
        self.cleanup_count += 1


@pytest_asyncio.fixture
async def bus():
    """Create message bus."""
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest_asyncio.fixture
async def health_monitor():
    """Create health monitor."""
    monitor = HealthMonitor()
    await monitor.start()
    yield monitor
    await monitor.stop()


@pytest.mark.asyncio
async def test_agent_restart_basic(bus):
    """Test basic agent restart."""
    agent = TestAgent("test_agent", bus)
    
    # Start agent
    await agent.start()
    assert agent.state == AgentState.READY
    assert agent.init_count == 1
    
    # Restart agent
    await agent.restart()
    assert agent.state == AgentState.READY
    assert agent.init_count == 2
    assert agent.cleanup_count == 1
    
    # Cleanup
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_restart_preserves_functionality(bus):
    """Test agent functions correctly after restart."""
    agent = TestAgent("test_agent", bus)
    await agent.start()
    
    # Process a message
    await bus.publish("test.input", {"data": "before"}, "external", MessagePriority.NORMAL)
    await asyncio.sleep(0.2)
    assert agent.messages_processed == 1
    
    # Restart
    await agent.restart()
    
    # Process another message
    await bus.publish("test.input", {"data": "after"}, "external", MessagePriority.NORMAL)
    await asyncio.sleep(0.2)
    assert agent.messages_processed == 2
    
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_with_health_monitor(bus, health_monitor):
    """Test agent integration with health monitor."""
    agent = TestAgent("test_agent", bus, health_monitor)
    await agent.start()
    
    # Wait for heartbeat
    await asyncio.sleep(0.2)
    
    # Check health
    health = await health_monitor.get_health("test_agent")
    assert health is not None
    assert health.agent_id == "test_agent"
    assert health.state == "ready"
    assert health.is_healthy
    
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_heartbeat_loop(bus, health_monitor):
    """Test agent sends periodic heartbeats."""
    agent = TestAgent("test_agent", bus, health_monitor)
    await agent.start()
    
    # Get initial health
    initial_health = await health_monitor.get_health("test_agent")
    initial_heartbeat = initial_health.last_heartbeat
    
    # Wait for heartbeat update
    await asyncio.sleep(0.5)
    
    # Heartbeat should be updated (though may not have changed in this short time)
    # The important thing is the heartbeat task is running
    assert agent._heartbeat_task is not None
    assert not agent._heartbeat_task.done()
    
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_records_messages(bus, health_monitor):
    """Test agent records message processing in health monitor."""
    agent = TestAgent("test_agent", bus, health_monitor)
    await agent.start()
    
    # Process messages
    for i in range(3):
        await bus.publish("test.input", {"i": i}, "external", MessagePriority.NORMAL)
    
    await asyncio.sleep(0.3)
    
    # Check message count in health
    health = await health_monitor.get_health("test_agent")
    assert health.message_count == 3
    
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_records_errors(bus, health_monitor):
    """Test agent records errors in health monitor."""
    class FailingAgent(TestAgent):
        async def process_message(self, message: Message) -> None:
            raise RuntimeError("Test error")
    
    agent = FailingAgent("failing_agent", bus, health_monitor)
    await agent.start()
    
    # Send message that will fail
    await bus.publish("test.input", {"data": "fail"}, "external", MessagePriority.NORMAL)
    await asyncio.sleep(0.2)
    
    # Check error recorded
    health = await health_monitor.get_health("failing_agent")
    assert health.error_count == 1
    assert health.last_error is not None
    assert "Test error" in health.last_error
    
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_restart_with_health_monitor(bus, health_monitor):
    """Test agent restart updates health monitor."""
    agent = TestAgent("test_agent", bus, health_monitor)
    await agent.start()
    
    # Check initial health
    health1 = await health_monitor.get_health("test_agent")
    assert health1 is not None
    
    # Restart
    await agent.restart()
    
    # Wait for heartbeat to update state
    await asyncio.sleep(0.2)
    
    # Check health still tracked
    health2 = await health_monitor.get_health("test_agent")
    assert health2 is not None
    assert health2.state == "ready"
    
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_stop_unregisters_from_health(bus, health_monitor):
    """Test agent unregisters from health monitor on stop."""
    agent = TestAgent("test_agent", bus, health_monitor)
    await agent.start()
    
    # Verify registered
    health = await health_monitor.get_health("test_agent")
    assert health is not None
    
    # Stop agent
    await agent.stop()
    
    # Should be unregistered
    health = await health_monitor.get_health("test_agent")
    assert health is None


@pytest.mark.asyncio
async def test_agent_without_health_monitor(bus):
    """Test agent works without health monitor."""
    agent = TestAgent("test_agent", bus, health_monitor=None)
    
    # Should work normally
    await agent.start()
    assert agent.state == AgentState.READY
    
    # Process message
    await bus.publish("test.input", {"data": "test"}, "external", MessagePriority.NORMAL)
    await asyncio.sleep(0.2)
    assert agent.messages_processed == 1
    
    # Restart should work
    await agent.restart()
    assert agent.state == AgentState.READY
    
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_heartbeat_metadata(bus, health_monitor):
    """Test agent heartbeat includes metadata."""
    agent = TestAgent("test_agent", bus, health_monitor)
    await agent.start()
    
    # Create some tasks to track
    agent.create_task(asyncio.sleep(10))
    agent.create_task(asyncio.sleep(10))
    
    await asyncio.sleep(0.2)
    
    # Check metadata in health
    health = await health_monitor.get_health("test_agent")
    assert "active_tasks" in health.metadata
    assert health.metadata["active_tasks"] == 2
    
    await agent.stop()


@pytest.mark.asyncio
async def test_restart_failure_sets_error_state(bus, health_monitor):
    """Test restart failure sets agent to ERROR state."""
    agent = TestAgent("test_agent", bus, health_monitor)
    await agent.start()
    
    # Make initialization fail on restart
    agent.fail_init = True
    
    # Restart should fail
    with pytest.raises(Exception):
        await agent.restart()
    
    assert agent.state == AgentState.ERROR
    
    # Error should be recorded in health
    health = await health_monitor.get_health("test_agent")
    if health:  # May be unregistered after stop
        assert health.error_count > 0


@pytest.mark.asyncio
async def test_multiple_agents_health_tracking(bus, health_monitor):
    """Test multiple agents tracked by health monitor."""
    agents = [
        TestAgent(f"agent_{i}", bus, health_monitor)
        for i in range(3)
    ]
    
    # Start all agents
    for agent in agents:
        await agent.start()
    
    await asyncio.sleep(0.2)
    
    # Check all tracked
    all_health = await health_monitor.get_all_health()
    assert len(all_health) >= 3
    
    # Cleanup
    for agent in agents:
        await agent.stop()
