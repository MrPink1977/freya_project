"""
TESTS FOR MESSAGE BUS BACKPRESSURE AND PERSISTENCE INTEGRATION.

Tests DROP_OLDEST backpressure and SQLite persistence.
"""

import asyncio

import pytest

from freya.core.message_bus import BackpressureStrategy, MessageBus, MessagePriority


@pytest.mark.asyncio
async def test_drop_oldest_backpressure():
    """Test DROP_OLDEST backpressure strategy."""
    bus = MessageBus(
        max_queue_size=3,
        backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
    )
    await bus.start()

    try:
        # Fill queue
        await bus.publish("topic", "msg1", "sender", MessagePriority.NORMAL)
        await bus.publish("topic", "msg2", "sender", MessagePriority.NORMAL)
        await bus.publish("topic", "msg3", "sender", MessagePriority.NORMAL)

        # Queue should be full
        assert bus._queue.qsize() == 3

        # Publish one more - should drop oldest
        await bus.publish("topic", "msg4", "sender", MessagePriority.NORMAL)

        # Queue should still be at capacity
        assert bus._queue.qsize() == 3
        assert bus._dropped_messages == 1

        # The oldest message (msg1) should be dropped
        # The queue should now have msg2, msg3, msg4

    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_drop_newest_backpressure():
    """Test DROP_NEWEST backpressure strategy."""
    bus = MessageBus(
        max_queue_size=3,
        backpressure_strategy=BackpressureStrategy.DROP_NEWEST,
    )
    await bus.start()

    try:
        # Fill queue
        await bus.publish("topic", "msg1", "sender", MessagePriority.NORMAL)
        await bus.publish("topic", "msg2", "sender", MessagePriority.NORMAL)
        await bus.publish("topic", "msg3", "sender", MessagePriority.NORMAL)

        # Publish one more - should drop newest
        await bus.publish("topic", "msg4", "sender", MessagePriority.NORMAL)

        # Queue should still be at capacity
        assert bus._queue.qsize() == 3
        assert bus._dropped_messages == 1

    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_persistence_integration(tmp_path):
    """Test persistence integration with message bus."""
    db_path = tmp_path / "test_messages.db"

    bus = MessageBus(
        enable_persistence=True,
        db_path=str(db_path),
    )
    await bus.start()

    try:
        # Publish some messages
        await bus.publish("topic1", {"data": "test1"}, "agent1", MessagePriority.NORMAL)
        await bus.publish("topic2", {"data": "test2"}, "agent2", MessagePriority.HIGH)

        # Give persistence time to write
        await asyncio.sleep(0.2)

        # Check persistence stats
        stats = await bus.get_stats()
        assert "persistence" in stats
        assert stats["persistence"]["enabled"]

        # Query messages from persistence
        messages = await bus._persistence.query_messages()
        assert len(messages) >= 2  # May have more from dispatch loop

    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_get_stats_includes_backpressure():
    """Test get_stats includes backpressure strategy."""
    bus = MessageBus(backpressure_strategy=BackpressureStrategy.DROP_OLDEST)
    await bus.start()

    try:
        stats = await bus.get_stats()

        assert "backpressure_strategy" in stats
        assert stats["backpressure_strategy"] == "drop_oldest"
        assert "dropped_messages" in stats

    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_backpressure_with_priorities():
    """Test backpressure respects message priorities."""
    bus = MessageBus(
        max_queue_size=3,
        backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
    )
    await bus.start()

    try:
        # Fill with normal priority
        await bus.publish("topic", "msg1", "sender", MessagePriority.NORMAL)
        await bus.publish("topic", "msg2", "sender", MessagePriority.NORMAL)
        await bus.publish("topic", "msg3", "sender", MessagePriority.NORMAL)

        # Add high priority - should drop oldest normal priority
        await bus.publish("topic", "msg4", "sender", MessagePriority.HIGH)

        assert bus._queue.qsize() == 3
        assert bus._dropped_messages == 1

    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_disabled_persistence_no_stats():
    """Test disabled persistence doesn't appear in stats."""
    bus = MessageBus(enable_persistence=False)
    await bus.start()

    try:
        stats = await bus.get_stats()
        assert "persistence" not in stats

    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_persistence_cleanup_on_stop(tmp_path):
    """Test persistence is properly closed on bus stop."""
    db_path = tmp_path / "test_messages.db"

    bus = MessageBus(
        enable_persistence=True,
        db_path=str(db_path),
    )
    await bus.start()

    await bus.publish("topic", "msg", "sender", MessagePriority.NORMAL)
    await asyncio.sleep(0.1)

    # Stop should close persistence
    await bus.stop()

    # Connection should be closed
    assert bus._persistence._conn is None


@pytest.mark.asyncio
async def test_backpressure_under_load():
    """Test backpressure handles burst of messages."""
    bus = MessageBus(
        max_queue_size=10,
        backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
    )
    await bus.start()

    try:
        # Create burst of messages
        for i in range(20):
            await bus.publish("topic", f"msg{i}", "sender", MessagePriority.NORMAL)

        # Should have dropped some messages
        assert bus._dropped_messages > 0

        # Queue should be at max
        assert bus._queue.qsize() <= 10

    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_message_history_unaffected_by_backpressure():
    """Test message history tracks all messages even when dropped from queue."""
    bus = MessageBus(
        max_queue_size=2,
        max_history=10,
        backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
    )
    await bus.start()

    try:
        # Publish more than queue size
        for i in range(5):
            await bus.publish("topic", f"msg{i}", "sender", MessagePriority.NORMAL)

        # History should have all messages
        history = bus.get_history()
        assert len(history) == 5

    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_persistence_stores_dropped_messages(tmp_path):
    """Test persistence stores all messages even if dropped from queue."""
    db_path = tmp_path / "test_messages.db"

    bus = MessageBus(
        max_queue_size=2,
        backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        enable_persistence=True,
        db_path=str(db_path),
    )
    await bus.start()

    try:
        # Publish more than queue size
        for i in range(5):
            await bus.publish("topic", f"msg{i}", "sender", MessagePriority.NORMAL)

        # Give persistence time to write
        await asyncio.sleep(0.2)

        # All messages should be in persistence
        messages = await bus._persistence.query_messages()
        assert len(messages) >= 5

    finally:
        await bus.stop()
