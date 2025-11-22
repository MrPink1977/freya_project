"""Memory domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class MemoryType(Enum):
    """Types of memory storage."""
    CONVERSATION = "conversation"
    FACT = "fact"
    CONTEXT = "context"
    SYSTEM = "system"


@dataclass
class Memory:
    """
    Conversation memory entity.
    
    Represents a single conversational exchange or context.
    """

    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    memory_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            memory_id=data.get("memory_id", str(uuid4())),
            content=data["content"],
            role=data["role"],
            timestamp=timestamp or datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Fact:
    """
    Fact entity.
    
    Represents a discrete piece of knowledge extracted from conversations.
    """

    content: str
    category: str
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    fact_id: str = field(default_factory=lambda: str(uuid4()))
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "fact_id": self.fact_id,
            "content": self.content,
            "category": self.category,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Fact:
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            fact_id=data.get("fact_id", str(uuid4())),
            content=data["content"],
            category=data["category"],
            confidence=data.get("confidence", 1.0),
            timestamp=timestamp or datetime.utcnow(),
            source=data.get("source"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MemoryQuery:
    """
    Memory query parameters.
    
    Defines how to search for memories.
    """

    query_text: str
    limit: int = 10
    min_similarity: float = 0.7
    role_filter: str | None = None
    time_range: tuple[datetime, datetime] | None = None
    metadata_filters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query_text": self.query_text,
            "limit": self.limit,
            "min_similarity": self.min_similarity,
            "role_filter": self.role_filter,
            "time_range": (
                (self.time_range[0].isoformat(), self.time_range[1].isoformat())
                if self.time_range
                else None
            ),
            "metadata_filters": self.metadata_filters,
        }
