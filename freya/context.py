"""Conversation context management for Freya."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Deque, Iterable, List, Optional

from .logger import get_logger

logger = get_logger("context")


@dataclass
class Message:
    """Single conversational message stored within the rolling context."""

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None


Summarizer = Callable[[Iterable[Message]], str]


@dataclass
class ConversationContext:
    """Maintain the rolling conversation history with optional summarisation."""

    system_prompt: str
    max_history: int = 10
    enable_summarization: bool = False
    summary_trigger_ratio: float = 0.8
    max_summaries: int = 3
    summarizer: Optional[Summarizer] = None
    _messages: Deque[Message] = field(default_factory=deque, init=False)
    _archived: List[Message] = field(default_factory=list, init=False)
    _summaries: Deque[str] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self.max_history = max(1, int(self.max_history))
        self.summary_trigger_ratio = max(0.1, min(float(self.summary_trigger_ratio), 1.0))
        self._messages = deque(self._messages)
        self._summaries = deque(self._summaries, maxlen=max(1, int(self.max_summaries)))

    def add_user_message(self, content: str) -> None:
        self._add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        self._add_message("assistant", content)

    def get_recent_dialogue(self, count: int) -> List[dict]:
        """Return the latest ``count`` turns formatted for Ollama."""

        count = max(0, int(count))
        recent = list(self._messages)[-count:] if count else list(self._messages)
        payload = [{"role": msg.role, "content": msg.content} for msg in recent]
        logger.debug("Recent dialogue (%s messages): %s", count or len(recent), payload)
        return payload

    def summarize_archived(self) -> Optional[str]:
        """Summarize archived messages, returning the created summary."""

        if not self._archived:
            return None

        archived_copy = list(self._archived)
        if self.summarizer is not None:
            summary = self.summarizer(archived_copy)
        else:
            joined = " ".join(
                message.content.strip() for message in archived_copy if message.content
            )
            summary = joined.strip()

        self._archived.clear()

        if summary:
            logger.debug("Archived %s messages into summary: %s", len(archived_copy), summary)
            self._summaries.append(summary)
            return summary
        return None

    def as_messages(self) -> List[dict]:
        """Return the conversation history formatted for Ollama."""

        # Replace template variables in system prompt
        current_date = datetime.now().strftime("%B %d, %Y")
        processed_system_prompt = self.system_prompt.replace("{{CURRENT_DATE}}", current_date)

        payload: List[dict] = [{"role": "system", "content": processed_system_prompt}]
        payload.extend({"role": "system", "content": summary} for summary in self._summaries)
        payload.extend({"role": msg.role, "content": msg.content} for msg in self._messages)
        logger.debug("Current message payload: %s", payload)
        return payload

    def _add_message(self, role: str, content: str) -> None:
        message = Message(role=role, content=content)
        logger.debug("Adding message: %s", message)
        self._messages.append(message)
        self._truncate_if_needed()

    def _truncate_if_needed(self) -> None:
        if len(self._messages) <= self.max_history:
            return

        while len(self._messages) > self.max_history:
            evicted = self._messages.popleft()
            logger.debug("Evicting message from context: %s", evicted)
            self._archived.append(evicted)

        if not self.enable_summarization:
            logger.debug(
                "Summarisation disabled; dropping %s archived messages", len(self._archived)
            )
            self._archived.clear()
            return

        trigger_threshold = max(1, int(self.max_history * self.summary_trigger_ratio))
        if len(self._archived) >= trigger_threshold:
            self.summarize_archived()
        else:
            logger.debug(
                "Archived messages below trigger threshold (%s/%s); deferring summary",
                len(self._archived),
                trigger_threshold,
            )

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._messages)


__all__ = ["ConversationContext", "Message"]
