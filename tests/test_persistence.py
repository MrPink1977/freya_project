"""
TESTS FOR MESSAGE PERSISTENCE.

Tests SQLite persistence functionality.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from pathlib import Path

from freya.core.message_bus import Message, MessagePriority
from freya.core.persistence import MessagePersistence


@pytest_asyncio.fixture
async def persistence(tmp_path):
    """Create persistence instance with temp database."""
    db_path = tmp_path / "test_messages.db"
    persist = MessagePersistence(
        db_path=str(db_path),
        max_messages=100,
        enable_persistence=True,
    )
    yield persist
    persist.close()


@pytest_asyncio.fixture
async def persistence_disabled():
    """Create disabled persistence instance."""
    persist = MessagePersistence(enable_persistence=False)
    yield persist
    persist.close()


@pytest.mark.asyncio
async def test_persistence_initialization(tmp_path):
    """Test persistence initializes correctly."""
    db_path = tmp_path / "test.db"
    persist = MessagePersistence(db_path=str(db_path))
    
    assert persist.enabled
    assert persist.db_path == db_path
    assert db_path.exists()
    
    persist.close()


@pytest.mark.asyncio
async def test_persistence_disabled():
    """Test persistence can be disabled."""
    persist = MessagePersistence(enable_persistence=False)
    
    assert not persist.enabled
    assert persist._conn is None
    
    persist.close()


@pytest.mark.asyncio
async def test_store_message(persistence):
    """Test storing a message."""
    message = Message(
        topic="test.topic",
        sender="test_agent",
        payload={"data": "test"},
        priority=MessagePriority.NORMAL,
    )
    
    await persistence.store_message(message)
    
    # Query the message
    messages = await persistence.query_messages(topic="test.topic")
    assert len(messages) == 1
    assert messages[0]["topic"] == "test.topic"
    assert messages[0]["sender"] == "test_agent"
    assert messages[0]["payload"] == {"data": "test"}


@pytest.mark.asyncio
async def test_store_multiple_messages(persistence):
    """Test storing multiple messages."""
    for i in range(5):
        message = Message(
            topic=f"test.topic.{i}",
            sender="test_agent",
            payload={"count": i},
            priority=MessagePriority.NORMAL,
        )
        await persistence.store_message(message)
    
    messages = await persistence.query_messages()
    assert len(messages) == 5


@pytest.mark.asyncio
async def test_query_by_topic(persistence):
    """Test querying messages by topic."""
    await persistence.store_message(Message("topic.one", {}, "agent", MessagePriority.NORMAL))
    await persistence.store_message(Message("topic.two", {}, "agent", MessagePriority.NORMAL))
    await persistence.store_message(Message("topic.one", {}, "agent", MessagePriority.NORMAL))
    
    messages = await persistence.query_messages(topic="topic.one")
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_query_by_sender(persistence):
    """Test querying messages by sender."""
    await persistence.store_message(Message("topic", {}, "agent1", MessagePriority.NORMAL))
    await persistence.store_message(Message("topic", {}, "agent2", MessagePriority.NORMAL))
    await persistence.store_message(Message("topic", {}, "agent1", MessagePriority.NORMAL))
    
    messages = await persistence.query_messages(sender="agent1")
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_query_with_wildcard(persistence):
    """Test querying with wildcard topics."""
    await persistence.store_message(Message("agent.memory.store", {}, "agent", MessagePriority.NORMAL))
    await persistence.store_message(Message("agent.memory.query", {}, "agent", MessagePriority.NORMAL))
    await persistence.store_message(Message("system.startup", {}, "agent", MessagePriority.NORMAL))
    
    messages = await persistence.query_messages(topic="agent.memory.*")
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_query_with_limit(persistence):
    """Test query limit."""
    for i in range(10):
        await persistence.store_message(Message("topic", {"i": i}, "agent", MessagePriority.NORMAL))
    
    messages = await persistence.query_messages(limit=5)
    assert len(messages) == 5


@pytest.mark.asyncio
async def test_cleanup_old_messages(persistence):
    """Test automatic cleanup of old messages."""
    # Store more than max_messages
    for i in range(120):  # max is 100
        await persistence.store_message(Message("topic", {"i": i}, "agent", MessagePriority.NORMAL))
    
    # Should have cleaned up to max_messages
    messages = await persistence.query_messages(limit=200)
    assert len(messages) == 100


@pytest.mark.asyncio
async def test_get_stats(persistence):
    """Test getting persistence stats."""
    await persistence.store_message(Message("topic1", {}, "agent1", MessagePriority.NORMAL))
    await persistence.store_message(Message("topic2", {}, "agent1", MessagePriority.NORMAL))
    await persistence.store_message(Message("topic1", {}, "agent2", MessagePriority.NORMAL))
    
    stats = await persistence.get_stats()
    
    assert stats["enabled"]
    assert stats["total_messages"] == 3
    assert stats["unique_topics"] == 2
    assert stats["unique_senders"] == 2
    assert "db_size_bytes" in stats


@pytest.mark.asyncio
async def test_clear_all(persistence):
    """Test clearing all messages."""
    for i in range(5):
        await persistence.store_message(Message("topic", {}, "agent", MessagePriority.NORMAL))
    
    await persistence.clear_all()
    
    messages = await persistence.query_messages()
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_disabled_persistence_no_op(persistence_disabled):
    """Test disabled persistence doesn't store anything."""
    message = Message("topic", {}, "agent", MessagePriority.NORMAL)
    await persistence_disabled.store_message(message)
    
    messages = await persistence_disabled.query_messages()
    assert len(messages) == 0
    
    stats = await persistence_disabled.get_stats()
    assert not stats["enabled"]


@pytest.mark.asyncio
async def test_correlation_id_query(persistence):
    """Test querying by correlation ID."""
    corr_id = "test-correlation-123"
    
    await persistence.store_message(
        Message("topic", {}, "agent", MessagePriority.NORMAL, correlation_id=corr_id)
    )
    await persistence.store_message(
        Message("topic", {}, "agent", MessagePriority.NORMAL, correlation_id="other")
    )
    
    messages = await persistence.query_messages(correlation_id=corr_id)
    assert len(messages) == 1
    assert messages[0]["correlation_id"] == corr_id
