"""
MESSAGE BUS FOR EVENT-DRIVEN AGENT COMMUNICATION.

Provides async pub/sub pattern for decoupled agent interaction.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from freya.logger import get_logger
from freya.core.persistence import MessagePersistence


logger = get_logger(__name__)


class MessagePriority(Enum):
    """Message priority levels for queue ordering."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class BackpressureStrategy(Enum):
    """Backpressure strategies when queue is full."""

    DROP_NEWEST = "drop_newest"  # Drop incoming message (current behavior)
    DROP_OLDEST = "drop_oldest"  # Drop oldest message from queue


@dataclass
class Message:
    """Message passed between agents via the bus."""

    topic: str
    payload: Any
    sender: str
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = None
    correlation_id: Optional[str] = None  # For request/response tracking

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MessageBus:
    """
    Async message bus for agent communication.

    Provides pub/sub pattern with:
    - Priority-based message queuing
    - Topic-based routing
    - Async delivery with error handling
    - Message history for debugging
    - Correlation ID support for request/response
    """

    def __init__(
        self,
        max_history: int = 100,
        max_queue_size: int = 1000,
        backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST,
        enable_persistence: bool = False,
        db_path: str = "data/message_history.db",
    ) -> None:
        """
        Initialize message bus.

        Args:
            max_history: Maximum messages to keep in history for debugging
            max_queue_size: Maximum pending messages in queue (prevents memory overflow)
            backpressure_strategy: How to handle full queue (DROP_OLDEST recommended)
            enable_persistence: Enable SQLite persistence for debugging
            db_path: Path to SQLite database file
        """
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[Message] = []
        self._max_history = max_history
        self._max_queue_size = max_queue_size
        self._backpressure_strategy = backpressure_strategy
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        self._sequence = 0  # Sequence number for queue ordering
        self._dropped_messages = 0  # Track dropped messages due to full queue
        self._persistence = MessagePersistence(
            db_path=db_path,
            enable_persistence=enable_persistence,
        )
        logger.info(
            "MessageBus initialized (max_queue_size=%d, backpressure=%s, persistence=%s)",
            max_queue_size,
            backpressure_strategy.value,
            enable_persistence,
        )

    async def start(self) -> None:
        """Start message bus dispatch loop."""
        if self._running:
            logger.warning("MessageBus already running")
            return

        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("MessageBus started")

    async def stop(self) -> None:
        """Stop message bus and cleanup."""
        if not self._running:
            return

        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        # Close persistence
        self._persistence.close()
        logger.info("MessageBus stopped")

    def subscribe(self, topic: str, handler: Callable[[Message], Coroutine]) -> None:
        """
        Subscribe to messages on a topic.

        Args:
            topic: Topic pattern (supports wildcards: "agent.*" or "agent.memory.*")
            handler: Async callback function(message) -> None
        """
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError(f"Handler for topic '{topic}' must be async (coroutine)")

        self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed to topic: {topic} (handler: {handler.__name__})")

    def unsubscribe(self, topic: str, handler: Callable) -> None:
        """
        Unsubscribe handler from topic.

        Args:
            topic: Topic to unsubscribe from
            handler: Handler to remove
        """
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(handler)
                logger.debug(f"Unsubscribed from topic: {topic}")
            except ValueError:
                logger.warning(f"Handler not found for topic: {topic}")

    async def publish(
        self,
        topic: str,
        payload: Any,
        sender: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Publish message to topic.

        Args:
            topic: Message topic (e.g., "agent.memory.store")
            payload: Message data (any JSON-serializable type)
            sender: Agent ID sending the message
            priority: Message priority for queue ordering
            correlation_id: Optional ID to track request/response chains
        """
        message = Message(
            topic=topic,
            payload=payload,
            sender=sender,
            priority=priority,
            correlation_id=correlation_id,
        )

        # Add to history
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Store to persistence (async, fire-and-forget)
        if self._persistence.enabled:
            asyncio.create_task(self._persistence.store_message(message))

        # Queue with inverted priority and sequence number for stable ordering
        # (lower number = higher priority in asyncio)
        priority_value = -priority.value
        self._sequence += 1

        try:
            # Try to add to queue without blocking
            self._queue.put_nowait((priority_value, self._sequence, message))
            logger.debug(
                f"Published: {topic} from {sender} (priority: {priority.name}, "
                f"correlation_id: {correlation_id})"
            )
        except asyncio.QueueFull:
            # Queue is full - apply backpressure strategy
            self._dropped_messages += 1

            if self._backpressure_strategy == BackpressureStrategy.DROP_OLDEST:
                # Remove oldest message from queue and add new one
                try:
                    dropped_item = self._queue.get_nowait()
                    dropped_msg = dropped_item[2]  # Extract message from tuple
                    logger.warning(
                        f"MessageBus queue full! Dropping OLDEST message: "
                        f"{dropped_msg.topic} from {dropped_msg.sender} "
                        f"(to make room for: {topic} from {sender})"
                    )
                    # Now add the new message
                    self._queue.put_nowait((priority_value, self._sequence, message))
                except Exception as exc:
                    logger.error(f"Failed to apply DROP_OLDEST backpressure: {exc}")
            else:
                # DROP_NEWEST - just drop the incoming message
                logger.warning(
                    f"MessageBus queue full ({self._max_queue_size} messages)! "
                    f"Dropping NEWEST message: {topic} from {sender} "
                    f"(total dropped: {self._dropped_messages})"
                )

    async def _dispatch_loop(self) -> None:
        """Main dispatch loop - runs continuously while bus is active."""
        logger.debug("Dispatch loop started")
        while self._running:
            try:
                # Wait for next message (blocks until available)
                # Unpack priority, sequence, and message
                _, _, message = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                await self._deliver_message(message)
            except asyncio.TimeoutError:
                # No messages, continue loop
                continue
            except asyncio.CancelledError:
                logger.debug("Dispatch loop cancelled")
                break
            except Exception as exc:
                logger.exception(f"Error in dispatch loop: {exc}")

    async def _deliver_message(self, message: Message) -> None:
        """
        Deliver message to all matching subscribers.

        Args:
            message: Message to deliver
        """
        matching_handlers = self._find_handlers(message.topic)

        if not matching_handlers:
            logger.debug(f"No subscribers for topic: {message.topic}")
            return

        # Deliver to all handlers concurrently
        delivery_tasks = [
            self._safe_call_handler(handler, message) for handler in matching_handlers
        ]
        await asyncio.gather(*delivery_tasks, return_exceptions=True)

    def _find_handlers(self, topic: str) -> List[Callable]:
        """
        Find all handlers matching topic (supports wildcards).

        Args:
            topic: Topic to match

        Returns:
            List of handler functions
        """
        handlers = []

        for pattern, pattern_handlers in self._subscribers.items():
            if self._topic_matches(topic, pattern):
                handlers.extend(pattern_handlers)

        return handlers

    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        """
        Check if topic matches pattern (supports wildcards).

        Examples:
            "agent.memory.store" matches "agent.memory.*"
            "agent.memory.store" matches "agent.*"
            "agent.memory.store" matches "agent.memory.store"

        Args:
            topic: Actual topic
            pattern: Pattern with optional wildcards

        Returns:
            True if topic matches pattern
        """
        if pattern == topic:
            return True

        if "*" not in pattern:
            return False

        pattern_parts = pattern.split(".")
        topic_parts = topic.split(".")

        if len(pattern_parts) > len(topic_parts):
            return False

        for pattern_part, topic_part in zip(pattern_parts, topic_parts):
            if pattern_part == "*":
                continue
            if pattern_part != topic_part:
                return False

        return True

    async def _safe_call_handler(self, handler: Callable, message: Message) -> None:
        """
        Call handler with error handling.

        Args:
            handler: Handler function to call
            message: Message to pass to handler
        """
        try:
            await handler(message)
        except Exception as exc:
            logger.exception(
                f"Error in handler {handler.__name__} for topic {message.topic}: {exc}"
            )

    def get_history(self, topic: Optional[str] = None, limit: int = 10) -> List[Message]:
        """
        Get message history for debugging.

        Args:
            topic: Optional topic filter
            limit: Maximum messages to return

        Returns:
            List of recent messages
        """
        history = self._history
        if topic:
            history = [m for m in history if m.topic == topic]
        return history[-limit:]

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get message bus statistics.

        Returns:
            Dictionary with bus stats
        """
        stats = {
            "running": self._running,
            "topics": len(self._subscribers),
            "total_handlers": sum(len(h) for h in self._subscribers.values()),
            "history_size": len(self._history),
            "queue_size": self._queue.qsize(),
            "dropped_messages": self._dropped_messages,
            "backpressure_strategy": self._backpressure_strategy.value,
        }

        # Add persistence stats if enabled
        if self._persistence.enabled:
            persistence_stats = await self._persistence.get_stats()
            stats["persistence"] = persistence_stats

        return stats
