"""Message value objects for LLM communication."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MessageRole(Enum):
    """Message role types."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Message:
    """
    Immutable message for LLM conversations.
    
    Represents a single message in a conversation with the LLM.
    
    Attributes:
        role: Message role ("system", "user", "assistant")
        content: Message content
    """

    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for API calls."""
        return {
            "role": self.role,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
        )

    @classmethod
    def system(cls, content: str) -> Message:
        """Create a system message."""
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        """Create a user message."""
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        """Create an assistant message."""
        return cls(role="assistant", content=content)
