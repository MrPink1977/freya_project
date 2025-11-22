"""Context builder service for constructing LLM conversation context."""

from __future__ import annotations

from typing import Any

from freya.domain.interfaces.memory_store import IMemoryStore
from freya.domain.value_objects.message import Message
from freya.shared.logging.decorators import log_async_performance
from freya.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ContextBuilder:
    """
    Builds conversation context for LLM requests.
    
    Responsibilities:
    - Maintain conversation history
    - Inject relevant memories
    - Add system prompts
    - Manage context window size
    """

    def __init__(
        self,
        memory_store: IMemoryStore,
        system_prompt: str,
        max_context_messages: int = 20,
    ) -> None:
        """
        Initialize context builder.
        
        Args:
            memory_store: Memory store for retrieving context
            system_prompt: System prompt to prepend
            max_context_messages: Maximum messages to include
        """
        self._memory_store = memory_store
        self._system_prompt = system_prompt
        self._max_messages = max_context_messages
        self._conversation_history: list[Message] = []

    @log_async_performance(threshold_ms=100)
    async def build_context(
        self,
        user_text: str,
        event_data: dict[str, Any] | None = None,
    ) -> list[Message]:
        """
        Build conversation context.
        
        Args:
            user_text: Current user message
            event_data: Optional event data with additional context
            
        Returns:
            List of messages for LLM
        """
        messages: list[Message] = []

        # 1. Add system prompt
        messages.append(Message.system(self._system_prompt))

        # 2. Add relevant memories if available
        if event_data and event_data.get("include_memories", True):
            memories = await self._retrieve_relevant_memories(user_text)
            if memories:
                memory_context = self._format_memories(memories)
                messages.append(Message.system(memory_context))

        # 3. Add conversation history (limited)
        history = self._get_recent_history()
        messages.extend(history)

        # 4. Add current user message
        user_message = Message.user(user_text)
        messages.append(user_message)

        # Store in history
        self._conversation_history.append(user_message)

        logger.debug(
            "Context built",
            message_count=len(messages),
            has_memories=bool(memories) if event_data else False,
        )

        return messages

    async def add_assistant_response(self, response: str) -> None:
        """
        Add assistant response to history.
        
        Args:
            response: Assistant's response
        """
        message = Message.assistant(response)
        self._conversation_history.append(message)

        # Trim history if needed
        if len(self._conversation_history) > self._max_messages:
            removed = len(self._conversation_history) - self._max_messages
            self._conversation_history = self._conversation_history[-self._max_messages :]
            logger.debug("Trimmed conversation history", removed_messages=removed)

    async def clear_context(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()
        logger.info("Conversation history cleared")

    def _get_recent_history(self) -> list[Message]:
        """Get recent conversation history."""
        # Return last N messages (excluding current)
        return self._conversation_history[-self._max_messages :]

    async def _retrieve_relevant_memories(self, query: str) -> list[str]:
        """
        Retrieve relevant memories for context.
        
        Args:
            query: Query text
            
        Returns:
            List of relevant memory contents
        """
        try:
            facts = await self._memory_store.query_facts(query, limit=3)
            return [fact.content for fact in facts]
        except Exception as e:
            logger.warning("Failed to retrieve memories", error=str(e))
            return []

    def _format_memories(self, memories: list[str]) -> str:
        """
        Format memories for injection into context.
        
        Args:
            memories: List of memory contents
            
        Returns:
            Formatted memory context
        """
        if not memories:
            return ""

        formatted = "Relevant context from memory:\n"
        for i, memory in enumerate(memories, 1):
            formatted += f"{i}. {memory}\n"

        return formatted

    def get_stats(self) -> dict[str, Any]:
        """Get context builder statistics."""
        return {
            "history_length": len(self._conversation_history),
            "max_messages": self._max_messages,
        }
