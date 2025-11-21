"""
TESTS FOR HEALTH MONITORING.

Tests health monitoring and heartbeat functionality.
"""

import asyncio
import time

import pytest
import pytest_asyncio

from freya.core.health_monitor import HealthMonitor


@pytest_asyncio.fixture
async def monitor():
    """Create health monitor instance."""
    monitor = HealthMonitor(heartbeat_interval=30.0)
    await monitor.start()
    yield monitor
    await monitor.stop()


@pytest.mark.asyncio
async def test_monitor_initialization():
    """Test monitor initializes correctly."""
    monitor = HealthMonitor(heartbeat_interval=10.0)

    assert monitor.heartbeat_interval == 10.0
    assert not monitor._running
    assert len(monitor._agents) == 0

    await monitor.start()
    assert monitor._running

    await monitor.stop()
    assert not monitor._running


@pytest.mark.asyncio
async def test_register_agent(monitor):
    """Test registering an agent."""
    await monitor.register_agent("agent1", state="ready")

    health = await monitor.get_health("agent1")
    assert health is not None
    assert health.agent_id == "agent1"
    assert health.state == "ready"
    assert health.is_healthy


@pytest.mark.asyncio
async def test_register_with_metadata(monitor):
    """Test registering agent with metadata."""
    metadata = {"type": "dialog", "model": "llama3"}
    await monitor.register_agent("agent1", state="ready", metadata=metadata)

    health = await monitor.get_health("agent1")
    assert health.metadata == metadata


@pytest.mark.asyncio
async def test_unregister_agent(monitor):
    """Test unregistering an agent."""
    await monitor.register_agent("agent1")
    await monitor.unregister_agent("agent1")

    health = await monitor.get_health("agent1")
    assert health is None


@pytest.mark.asyncio
async def test_heartbeat(monitor):
    """Test recording heartbeat."""
    await monitor.register_agent("agent1")

    initial_health = await monitor.get_health("agent1")
    initial_time = initial_health.last_heartbeat

    await asyncio.sleep(0.1)
    await monitor.heartbeat("agent1")

    updated_health = await monitor.get_health("agent1")
    assert updated_health.last_heartbeat > initial_time


@pytest.mark.asyncio
async def test_heartbeat_auto_register(monitor):
    """Test heartbeat auto-registers unknown agents."""
    await monitor.heartbeat("new_agent", state="ready")

    health = await monitor.get_health("new_agent")
    assert health is not None
    assert health.agent_id == "new_agent"


@pytest.mark.asyncio
async def test_heartbeat_updates_state(monitor):
    """Test heartbeat can update agent state."""
    await monitor.register_agent("agent1", state="initializing")
    await monitor.heartbeat("agent1", state="ready")

    health = await monitor.get_health("agent1")
    assert health.state == "ready"


@pytest.mark.asyncio
async def test_record_message(monitor):
    """Test recording message processing."""
    await monitor.register_agent("agent1")

    await monitor.record_message("agent1")
    await monitor.record_message("agent1")
    await monitor.record_message("agent1")

    health = await monitor.get_health("agent1")
    assert health.message_count == 3


@pytest.mark.asyncio
async def test_record_error(monitor):
    """Test recording errors."""
    await monitor.register_agent("agent1")

    await monitor.record_error("agent1", "Test error 1")
    await monitor.record_error("agent1", "Test error 2")

    health = await monitor.get_health("agent1")
    assert health.error_count == 2
    assert health.last_error == "Test error 2"


@pytest.mark.asyncio
async def test_get_all_health(monitor):
    """Test getting all agent health."""
    await monitor.register_agent("agent1")
    await monitor.register_agent("agent2")
    await monitor.register_agent("agent3")

    all_health = await monitor.get_all_health()
    assert len(all_health) == 3
    assert "agent1" in all_health
    assert "agent2" in all_health
    assert "agent3" in all_health


@pytest.mark.asyncio
async def test_is_healthy_recent_heartbeat(monitor):
    """Test agent is healthy with recent heartbeat."""
    await monitor.register_agent("agent1")
    await monitor.heartbeat("agent1")

    health = await monitor.get_health("agent1")
    assert health.is_healthy
    assert health.seconds_since_heartbeat < 1.0


@pytest.mark.asyncio
async def test_is_unhealthy_old_heartbeat():
    """Test agent is unhealthy with old heartbeat."""
    monitor = HealthMonitor(heartbeat_interval=0.5)  # Short interval for testing
    await monitor.start()

    try:
        await monitor.register_agent("agent1")

        # Manually set old heartbeat
        health = await monitor.get_health("agent1")
        health.last_heartbeat = time.time() - 35.0  # 35 seconds ago

        assert not health.is_healthy
        assert health.seconds_since_heartbeat > 30.0
    finally:
        await monitor.stop()


@pytest.mark.asyncio
async def test_get_unhealthy_agents():
    """Test getting unhealthy agents."""
    monitor = HealthMonitor(heartbeat_interval=0.5)
    await monitor.start()

    try:
        # Create healthy and unhealthy agents
        await monitor.register_agent("healthy1")
        await monitor.register_agent("healthy2")
        await monitor.register_agent("unhealthy1")

        # Make one unhealthy
        health = await monitor.get_health("unhealthy1")
        health.last_heartbeat = time.time() - 35.0

        unhealthy = await monitor.get_unhealthy_agents()
        assert len(unhealthy) == 1
        assert "unhealthy1" in unhealthy
    finally:
        await monitor.stop()


@pytest.mark.asyncio
async def test_get_stats(monitor):
    """Test getting monitor stats."""
    await monitor.register_agent("agent1")
    await monitor.register_agent("agent2")
    await monitor.record_message("agent1")
    await monitor.record_message("agent1")
    await monitor.record_error("agent2", "test error")

    stats = await monitor.get_stats()

    assert stats["running"]
    assert stats["total_agents"] == 2
    assert stats["healthy_agents"] == 2
    assert stats["unhealthy_agents"] == 0
    assert stats["total_messages"] == 2
    assert stats["total_errors"] == 1
    assert stats["heartbeat_interval"] == 30.0


@pytest.mark.asyncio
async def test_monitor_loop_detects_unhealthy():
    """Test monitor loop detects unhealthy agents."""
    monitor = HealthMonitor(heartbeat_interval=0.2)  # Very short for testing
    await monitor.start()

    try:
        await monitor.register_agent("agent1")

        # Make agent unhealthy
        health = await monitor.get_health("agent1")
        health.last_heartbeat = time.time() - 35.0

        # Wait for monitor loop to detect
        await asyncio.sleep(0.5)

        # Check it's detected as unhealthy
        unhealthy = await monitor.get_unhealthy_agents()
        assert "agent1" in unhealthy
    finally:
        await monitor.stop()


@pytest.mark.asyncio
async def test_heartbeat_metadata_update(monitor):
    """Test heartbeat updates metadata."""
    await monitor.register_agent("agent1", metadata={"count": 0})

    await monitor.heartbeat("agent1", metadata={"count": 5, "status": "active"})

    health = await monitor.get_health("agent1")
    assert health.metadata["count"] == 5
    assert health.metadata["status"] == "active"
