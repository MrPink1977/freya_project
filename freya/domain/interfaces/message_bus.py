"""Message bus interface protocol."""

from __future__ import annotations

from typing import Awaitable, Callable, Protocol, runtime_checkable

from freya.domain.value_objects.event import Event

EventHandler = Callable[[Event], Awaitable[None]]


@runtime_checkable
class IMessageBus(Protocol):
    """
    Interface for the message bus.
    
    The message bus is the central communication hub for all agents.
    It implements the publish-subscribe pattern.
    """

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish
        """
        ...

    async def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        subscriber_name: str | None = None,
    ) -> None:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to subscribe to
            handler: Async function to handle events
            subscriber_name: Optional name for the subscriber
        """
        ...

    async def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        """
        Unsubscribe from events.
        
        Args:
            event_type: Type of events to unsubscribe from
            handler: Handler to remove
        """
        ...

    async def start(self) -> None:
        """Start the message bus."""
        ...

    async def stop(self) -> None:
        """Stop the message bus and clean up resources."""
        ...

    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get number of subscribers for an event type.
        
        Args:
            event_type: Event type to check
            
        Returns:
            Number of subscribers
        """
        ...
