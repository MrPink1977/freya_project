"""Message bus implementation."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from freya.domain.exceptions import EventHandlingError
from freya.domain.interfaces.message_bus import EventHandler, IMessageBus
from freya.domain.value_objects.event import Event
from freya.shared.logging.decorators import log_async_errors, log_async_performance
from freya.shared.logging.logger import get_logger

logger = get_logger(__name__)


class MessageBus(IMessageBus):
    """
    In-memory message bus implementation.
    
    Implements publish-subscribe pattern for event-driven communication.
    Thread-safe and async-compatible.
    """

    def __init__(self) -> None:
        """Initialize the message bus."""
        self._subscribers: dict[str, list[tuple[EventHandler, str | None]]] = defaultdict(
            list
        )
        self._lock = asyncio.Lock()
        self._running = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None

        logger.info("MessageBus initialized")

    @log_async_performance(threshold_ms=100)
    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.
        
        Events are queued and processed asynchronously.
        """
        if not self._running:
            logger.warning(
                "Publishing to stopped message bus",
                event_type=event.event_type,
            )
            return

        await self._event_queue.put(event)

        logger.debug(
            "Event published",
            event_type=event.event_type,
            event_id=event.event_id,
            source=event.source,
            queue_size=self._event_queue.qsize(),
        )

    async def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        subscriber_name: str | None = None,
    ) -> None:
        """Subscribe to events of a specific type."""
        async with self._lock:
            self._subscribers[event_type].append((handler, subscriber_name))

        logger.info(
            "Subscriber registered",
            event_type=event_type,
            subscriber=subscriber_name or "anonymous",
            total_subscribers=len(self._subscribers[event_type]),
        )

    async def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        """Unsubscribe from events."""
        async with self._lock:
            self._subscribers[event_type] = [
                (h, name) for h, name in self._subscribers[event_type] if h != handler
            ]

        logger.info(
            "Subscriber removed",
            event_type=event_type,
            remaining_subscribers=len(self._subscribers[event_type]),
        )

    async def start(self) -> None:
        """Start the message bus worker."""
        if self._running:
            logger.warning("MessageBus already running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())

        logger.info("MessageBus started")

    async def stop(self) -> None:
        """Stop the message bus and clean up."""
        if not self._running:
            return

        self._running = False

        # Wait for worker to finish
        if self._worker_task:
            try:
                await asyncio.wait_for(self._worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("MessageBus worker did not stop gracefully")
                self._worker_task.cancel()

        # Clear queue
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("MessageBus stopped")

    def get_subscriber_count(self, event_type: str) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))

    @log_async_errors()
    async def _process_events(self) -> None:
        """Worker coroutine that processes events from the queue."""
        logger.info("MessageBus worker started")

        while self._running:
            try:
                # Wait for event with timeout to allow checking _running flag
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=0.1,
                )
            except asyncio.TimeoutError:
                continue

            await self._dispatch_event(event)

        logger.info("MessageBus worker stopped")

    @log_async_performance(threshold_ms=500)
    async def _dispatch_event(self, event: Event) -> None:
        """Dispatch an event to all subscribers."""
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            logger.debug(
                "No subscribers for event",
                event_type=event.event_type,
                event_id=event.event_id,
            )
            return

        logger.debug(
            "Dispatching event",
            event_type=event.event_type,
            event_id=event.event_id,
            subscriber_count=len(handlers),
        )

        # Dispatch to all handlers concurrently
        tasks = [
            self._invoke_handler(handler, subscriber_name, event)
            for handler, subscriber_name in handlers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                handler, subscriber_name = handlers[i]
                logger.error(
                    "Handler failed",
                    event_type=event.event_type,
                    subscriber=subscriber_name or "anonymous",
                    error=str(result),
                    exc_info=result,
                )

    @log_async_errors()
    async def _invoke_handler(
        self,
        handler: EventHandler,
        subscriber_name: str | None,
        event: Event,
    ) -> None:
        """Invoke a single event handler."""
        try:
            await handler(event)
        except Exception as e:
            # Wrap in EventHandlingError for consistency
            raise EventHandlingError(
                f"Handler {subscriber_name or 'anonymous'} failed",
                event_type=event.event_type,
                details={
                    "subscriber": subscriber_name,
                    "event_id": event.event_id,
                },
                cause=e,
            ) from e

    def get_stats(self) -> dict[str, Any]:
        """Get message bus statistics."""
        return {
            "running": self._running,
            "queue_size": self._event_queue.qsize(),
            "event_types": len(self._subscribers),
            "total_subscribers": sum(
                len(handlers) for handlers in self._subscribers.values()
            ),
            "subscribers_by_type": {
                event_type: len(handlers) for event_type, handlers in self._subscribers.items()
            },
        }
