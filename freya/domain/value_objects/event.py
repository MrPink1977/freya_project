"""Event value objects for the message bus."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    """
    Immutable event object for inter-agent communication.
    
    Events are the primary communication mechanism between agents.
    They are immutable and contain all necessary context.
    
    Attributes:
        event_type: Type of event (e.g., "wake.detected", "dialog.request")
        data: Event payload
        event_id: Unique event identifier
        timestamp: When the event was created
        source: Agent that created the event
        correlation_id: ID for tracking related events
    """

    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str | None = None
    correlation_id: str | None = None

    def with_correlation_id(self, correlation_id: str) -> Event:
        """
        Create a new event with a correlation ID.
        
        Args:
            correlation_id: Correlation ID to set
            
        Returns:
            New event with correlation ID
        """
        return Event(
            event_type=self.event_type,
            data=self.data,
            event_id=self.event_id,
            timestamp=self.timestamp,
            source=self.source,
            correlation_id=correlation_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """
        Create event from dictionary.
        
        Args:
            data: Event data dictionary
            
        Returns:
            Event instance
        """
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            event_type=data["event_type"],
            data=data.get("data", {}),
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=timestamp or datetime.utcnow(),
            source=data.get("source"),
            correlation_id=data.get("correlation_id"),
        )


# Common event types
class EventType:
    """Standard event types used throughout the system."""

    # Wake word events
    WAKE_DETECTED = "wake.detected"
    WAKE_TIMEOUT = "wake.timeout"

    # Dialog events
    DIALOG_REQUEST = "dialog.request"
    DIALOG_CHUNK = "dialog.chunk"
    DIALOG_COMPLETE = "dialog.complete"
    DIALOG_ERROR = "dialog.error"

    # Memory events
    MEMORY_STORE = "memory.store"
    MEMORY_QUERY = "memory.query"
    MEMORY_RESULT = "memory.result"
    MEMORY_STORED = "memory.stored"

    # Tool events
    TOOL_EXECUTE = "tool.execute"
    TOOL_RESULT = "tool.result"
    TOOL_ERROR = "tool.error"

    # Speech events
    SPEECH_START = "speech.start"
    SPEECH_CHUNK = "speech.chunk"
    SPEECH_COMPLETE = "speech.complete"
    SPEECH_ERROR = "speech.error"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
