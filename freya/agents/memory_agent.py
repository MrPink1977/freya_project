"""
MEMORY AGENT - Manages long-term memory storage and retrieval.

Wraps ChromaMemoryStore for async, event-driven memory operations.
"""

from __future__ import annotations

import re
from typing import Optional

from freya.agents.base_agent import AgentCapability, BaseAgent
from freya.core.message_bus import Message, MessageBus, MessagePriority
from freya.exceptions import AgentMessageError, MemoryQueryError, MemoryStorageError
from freya.logger import get_logger
from freya.memory import ChromaMemoryStore
from freya.schemas.messages import MemoryStorePayload, MemoryQueryPayload, FactStorePayload, FactQueryPayload
from freya.schemas.validation import validate_message_payload

logger = get_logger("memory_agent")


class MemoryAgent(BaseAgent):
    """
    Agent managing long-term memory storage and semantic retrieval.

    Subscribes to:
    - "memory.store" - Store conversation or facts
    - "memory.query" - Search for relevant memories
    - "memory.fact.store" - Store structured fact
    - "memory.fact.query" - Query facts

    Publishes to:
    - "memory.stored" - Confirmation of storage
    - "memory.results" - Retrieved memories
    - "memory.fact.stored" - Fact stored
    - "memory.fact.results" - Fact query results
    """

    def __init__(
        self,
        agent_id: str,
        bus: MessageBus,
        memory_store: ChromaMemoryStore,
        auto_extract_facts: bool = True,
    ) -> None:
        """
        Initialize memory agent.

        Args:
            agent_id: Unique agent identifier
            bus: Message bus for communication
            memory_store: ChromaMemoryStore instance
            auto_extract_facts: Automatically extract facts from user messages
        """
        super().__init__(agent_id, bus)
        self.memory_store = memory_store
        self.auto_extract_facts = auto_extract_facts

        # Fact extraction patterns (from orchestrator)
        self._fact_patterns = self._initialize_fact_patterns()

    def _initialize_fact_patterns(self) -> dict:
        """Initialize regex patterns for fact extraction."""
        return {
            "name_is": re.compile(r"my name(?:'s| is) (\w+(?:\s+\w+)?)", re.IGNORECASE),
            "call_me": re.compile(r"(?:you can |just )?call me (\w+)", re.IGNORECASE),
            "birthday_is": re.compile(
                r"my birthday(?:'s| is) ([a-z]+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?)",
                re.IGNORECASE,
            ),
            "born_on": re.compile(
                r"(?:i was )?born (?:on |in )?([a-z]+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?|\d{4}|[a-z]+ \d{4})",
                re.IGNORECASE,
            ),
            "favorite": re.compile(r"my favorite (\w+) is ([^.,!?]+)", re.IGNORECASE),
            "i_like": re.compile(r"i (?:really |absolutely )?like ([^.,!?]+)", re.IGNORECASE),
            "i_love": re.compile(r"i (?:really |absolutely )?love ([^.,!?]+)", re.IGNORECASE),
            "i_hate": re.compile(r"i (?:really |absolutely )?hate ([^.,!?]+)", re.IGNORECASE),
            "i_dislike": re.compile(r"i (?:really |absolutely )?dislike ([^.,!?]+)", re.IGNORECASE),
        }

    async def initialize(self) -> None:
        """Initialize memory agent."""
        stats = self.memory_store.get_stats()
        self.logger.info(
            f"MemoryAgent initialized: {stats['total_memories']} memories, "
            f"{stats['total_facts']} facts"
        )

    def get_capabilities(self) -> list[AgentCapability]:
        """Return memory management capabilities."""
        return [
            AgentCapability(
                name="memory_storage",
                description="Store and retrieve conversation memories",
                input_topics=["memory.store", "memory.query"],
                output_topics=["memory.stored", "memory.results"],
            ),
            AgentCapability(
                name="fact_management",
                description="Store and query structured facts",
                input_topics=["memory.fact.store", "memory.fact.query"],
                output_topics=["memory.fact.stored", "memory.fact.results"],
            ),
        ]

    async def process_message(self, message: Message) -> None:
        """
        Process memory-related messages.

        Args:
            message: Memory command message
        """
        if message.topic == "memory.store":
            await self._handle_store(message)
        elif message.topic == "memory.query":
            await self._handle_query(message)
        elif message.topic == "memory.fact.store":
            await self._handle_fact_store(message)
        elif message.topic == "memory.fact.query":
            await self._handle_fact_query(message)

    async def _handle_store(self, message: Message) -> None:
        """Handle memory storage request."""
        # Validate payload
        try:
            payload = validate_message_payload(message.payload, MemoryStorePayload, self.agent_id)
        except AgentMessageError as exc:
            self.logger.error("Invalid memory store request: %s", exc)
            await self.publish_error(message, exc)
            return
        
        # Use validated data
        content = payload.content
        role = payload.role
        importance = payload.importance

        try:
            # Store in ChromaDB
            memory_id = self.memory_store.store_memory(
                content=content,
                role=role,
                importance=importance,
            )

            # Auto-extract facts if enabled
            if self.auto_extract_facts and role == "user":
                await self._extract_and_store_facts(content)

            # Confirm storage
            await self.publish(
                topic="memory.stored",
                payload={"memory_id": memory_id, "content": content[:100]},
                correlation_id=message.correlation_id,
            )

            self.logger.debug(f"Stored memory {memory_id}")

        except MemoryStorageError as exc:
            self.logger.error(f"Failed to store memory: {exc}")
            await self.publish_error(message, exc)
        except Exception as exc:
            self.logger.exception(f"Unexpected error storing memory: {exc}")
            await self.publish_error(message, exc)

    async def _handle_query(self, message: Message) -> None:
        """Handle memory query request."""
        # Validate payload
        try:
            payload = validate_message_payload(message.payload, MemoryQueryPayload, self.agent_id)
        except AgentMessageError as exc:
            self.logger.error("Invalid memory query request: %s", exc)
            await self.publish(
                topic="memory.results",
                payload={"results": [], "error": str(exc)},
                correlation_id=message.correlation_id,
            )
            return
        
        # Use validated data
        query = payload.query
        limit = payload.limit
        min_score = payload.min_score
        filter_metadata = payload.filter

        try:
            # Search ChromaDB
            memories = self.memory_store.find_similar_memories(
                query=query,
                limit=limit,
                min_score=min_score,
                filter_metadata=filter_metadata,
            )

            # Convert to dict for JSON serialization
            results = [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "score": m.score,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat(),
                }
                for m in memories
            ]

            await self.publish(
                topic="memory.results",
                payload={"results": results, "query": query, "count": len(results)},
                correlation_id=message.correlation_id,
            )

            self.logger.debug(f"Retrieved {len(results)} memories for query: {query[:50]}")

        except MemoryQueryError as exc:
            self.logger.error(f"Failed to query memories: {exc}")
            await self.publish_error(message, exc)
        except Exception as exc:
            self.logger.exception(f"Unexpected error querying memories: {exc}")
            await self.publish_error(message, exc)

    async def _handle_fact_store(self, message: Message) -> None:
        """Handle fact storage request."""
        # Validate payload
        try:
            payload = validate_message_payload(message.payload, FactStorePayload, self.agent_id)
        except AgentMessageError as exc:
            self.logger.error("Invalid fact store request: %s", exc)
            await self.publish_error(message, exc)
            return
        
        # Use validated data
        category = payload.category
        key = payload.key
        value = payload.value
        confidence = payload.confidence

        if not key or not value:
            self.logger.debug("Skipping fact with empty key or value")
            return

        try:
            fact_id = self.memory_store.store_fact(
                category=category,
                key=key,
                value=value,
                confidence=confidence,
            )

            await self.publish(
                topic="memory.fact.stored",
                payload={"fact_id": fact_id, "category": category, "key": key, "value": value},
                correlation_id=message.correlation_id,
            )

            self.logger.debug(f"Stored fact: {category}/{key} = {value}")

        except MemoryStorageError as exc:
            self.logger.error(f"Failed to store fact: {exc}")
            await self.publish_error(message, exc)
        except Exception as exc:
            self.logger.exception(f"Unexpected error storing fact: {exc}")
            await self.publish_error(message, exc)

    async def _handle_fact_query(self, message: Message) -> None:
        """Handle fact query request."""
        # Validate payload
        try:
            payload = validate_message_payload(message.payload, FactQueryPayload, self.agent_id)
        except AgentMessageError as exc:
            self.logger.error("Invalid fact query request: %s", exc)
            await self.publish(
                topic="memory.fact.results",
                payload={"results": [], "error": str(exc)},
                correlation_id=message.correlation_id,
            )
            return
        
        # Use validated data
        query = payload.query
        category = payload.category
        limit = payload.limit

        try:
            facts = self.memory_store.query_facts(
                query=query,
                category=category,
                limit=limit,
            )

            results = [
                {
                    "id": f.id,
                    "category": f.category,
                    "key": f.key,
                    "value": f.value,
                    "confidence": f.confidence,
                }
                for f in facts
            ]

            await self.publish(
                topic="memory.fact.results",
                payload={"results": results, "query": query, "count": len(results)},
                correlation_id=message.correlation_id,
            )

            self.logger.debug(f"Retrieved {len(results)} facts for query: {query[:50]}")

        except MemoryQueryError as exc:
            self.logger.error(f"Failed to query facts: {exc}")
            await self.publish_error(message, exc)
        except Exception as exc:
            self.logger.exception(f"Unexpected error querying facts: {exc}")
            await self.publish_error(message, exc)

    async def _extract_and_store_facts(self, user_text: str) -> None:
        """
        Extract structured facts from user text and store them.

        Args:
            user_text: User's message
        """
        lowered = user_text.lower().strip()

        # Skip questions - they're asking, not telling
        question_indicators = [
            "do you",
            "can you",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "is it",
            "are you",
            "will you",
            "should",
            "could",
            "would",
            "remember my",
            "know my",
            "recall",
        ]
        if any(
            lowered.startswith(indicator) or f" {indicator}" in lowered
            for indicator in question_indicators
        ):
            return

        # Extract name
        match = self._fact_patterns["name_is"].search(lowered)
        if not match:
            match = self._fact_patterns["call_me"].search(lowered)

        if match:
            name = match.group(1).strip().title()
            if len(name) >= 2 and not name.isdigit():
                await self.publish(
                    topic="memory.fact.store",
                    payload={"category": "name", "key": "name", "value": name, "confidence": 1.0},
                    sender=self.agent_id,
                )
                return

        # Extract birthday
        match = self._fact_patterns["birthday_is"].search(lowered)
        if not match:
            match = self._fact_patterns["born_on"].search(lowered)

        if match:
            birthday = match.group(1).strip().title()
            if not birthday.endswith("?") and len(birthday) >= 4:
                await self.publish(
                    topic="memory.fact.store",
                    payload={
                        "category": "birthday",
                        "key": "birthday",
                        "value": birthday,
                        "confidence": 1.0,
                    },
                    sender=self.agent_id,
                )
                return

        # Extract favorites
        match = self._fact_patterns["favorite"].search(user_text)
        if match:
            category = match.group(1).strip().lower()
            value = match.group(2).strip()
            await self.publish(
                topic="memory.fact.store",
                payload={
                    "category": "preference",
                    "key": f"favorite_{category}",
                    "value": value,
                    "confidence": 1.0,
                },
                sender=self.agent_id,
            )
            return

        # Extract likes/loves
        for pattern_name in ["i_like", "i_love"]:
            match = self._fact_patterns[pattern_name].search(user_text)
            if match:
                value = match.group(1).strip()
                sentiment = "love" if "love" in pattern_name else "like"
                await self.publish(
                    topic="memory.fact.store",
                    payload={
                        "category": "preference",
                        "key": f"{sentiment}s",
                        "value": value,
                        "confidence": 0.8 if "like" in pattern_name else 1.0,
                    },
                    sender=self.agent_id,
                )
                return

        # Extract dislikes/hates
        for pattern_name in ["i_dislike", "i_hate"]:
            match = self._fact_patterns[pattern_name].search(user_text)
            if match:
                value = match.group(1).strip()
                sentiment = "hate" if "hate" in pattern_name else "dislike"
                await self.publish(
                    topic="memory.fact.store",
                    payload={
                        "category": "preference",
                        "key": f"{sentiment}s",
                        "value": value,
                        "confidence": 0.8 if "dislike" in pattern_name else 1.0,
                    },
                    sender=self.agent_id,
                )
                return
