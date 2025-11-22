"""Memory repository implementation with query builder pattern."""

from __future__ import annotations

from typing import Any

from freya.domain.entities.memory import Fact, Memory, MemoryQuery
from freya.domain.exceptions import MemoryQueryError, MemoryStorageError
from freya.domain.interfaces.memory_store import IMemoryStore
from freya.infrastructure.memory.backends.chroma_backend import ChromaBackend
from freya.infrastructure.memory.query_builder import QueryBuilder
from freya.shared.logging.decorators import log_async_performance
from freya.shared.logging.logger import get_logger

logger = get_logger(__name__)


class MemoryRepository(IMemoryStore):
    """
    Memory repository implementing the repository pattern.
    
    Provides a clean interface to memory storage with query builder support.
    """

    def __init__(
        self,
        backend: ChromaBackend,
    ) -> None:
        """
        Initialize memory repository.
        
        Args:
            backend: Storage backend (ChromaDB, SQLite, etc.)
        """
        self._backend = backend
        self._query_builder = QueryBuilder()

        logger.info("MemoryRepository initialized", backend=type(backend).__name__)

    @log_async_performance(threshold_ms=100)
    async def store_memory(self, memory: Memory) -> str:
        """
        Store a conversation memory.
        
        Args:
            memory: Memory to store
            
        Returns:
            Memory ID
        """
        try:
            memory_id = await self._backend.store_memory(memory)

            logger.debug(
                "Memory stored",
                memory_id=memory_id,
                role=memory.role,
                content_length=len(memory.content),
            )

            return memory_id

        except Exception as e:
            logger.error("Failed to store memory", error=str(e), exc_info=e)
            raise MemoryStorageError(
                "Failed to store memory",
                operation="store_memory",
                cause=e,
            ) from e

    @log_async_performance(threshold_ms=50)
    async def query_memories(self, query: MemoryQuery) -> list[Memory]:
        """
        Query memories using semantic search.
        
        Uses query builder for complex queries.
        """
        try:
            # Build query using query builder
            built_query = (
                self._query_builder.reset()
                .with_text(query.query_text)
                .with_limit(query.limit)
                .with_similarity_threshold(query.min_similarity)
            )

            if query.role_filter:
                built_query.with_metadata_filter("role", query.role_filter)

            if query.time_range:
                built_query.with_time_range(*query.time_range)

            for key, value in query.metadata_filters.items():
                built_query.with_metadata_filter(key, value)

            # Execute query
            memories = await self._backend.query_memories(built_query.build())

            logger.debug(
                "Memories queried",
                query_text=query.query_text[:50],
                result_count=len(memories),
            )

            return memories

        except Exception as e:
            logger.error("Failed to query memories", error=str(e), exc_info=e)
            raise MemoryQueryError(
                "Failed to query memories",
                query_type="semantic_search",
                cause=e,
            ) from e

    @log_async_performance(threshold_ms=100)
    async def store_fact(self, fact: Fact) -> str:
        """Store a fact."""
        try:
            fact_id = await self._backend.store_fact(fact)

            logger.debug(
                "Fact stored",
                fact_id=fact_id,
                category=fact.category,
                confidence=fact.confidence,
            )

            return fact_id

        except Exception as e:
            logger.error("Failed to store fact", error=str(e), exc_info=e)
            raise MemoryStorageError(
                "Failed to store fact",
                operation="store_fact",
                cause=e,
            ) from e

    @log_async_performance(threshold_ms=50)
    async def query_facts(self, query: str, limit: int = 5) -> list[Fact]:
        """Query facts using semantic search."""
        try:
            facts = await self._backend.query_facts(query, limit)

            logger.debug(
                "Facts queried",
                query=query[:50],
                result_count=len(facts),
            )

            return facts

        except Exception as e:
            logger.error("Failed to query facts", error=str(e), exc_info=e)
            raise MemoryQueryError(
                "Failed to query facts",
                query_type="fact_search",
                cause=e,
            ) from e

    async def clear_memories(self) -> None:
        """Clear all memories."""
        try:
            await self._backend.clear_memories()
            logger.info("All memories cleared")

        except Exception as e:
            logger.error("Failed to clear memories", error=str(e), exc_info=e)
            raise MemoryStorageError(
                "Failed to clear memories",
                operation="clear_memories",
                cause=e,
            ) from e

    async def get_stats(self) -> dict[str, int]:
        """Get memory store statistics."""
        try:
            stats = await self._backend.get_stats()
            return stats

        except Exception as e:
            logger.warning("Failed to get stats", error=str(e))
            return {"error": str(e)}

    async def close(self) -> None:
        """Close the memory store."""
        await self._backend.close()
        logger.info("MemoryRepository closed")
