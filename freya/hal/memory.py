"""Memory hardware abstraction layer implementations."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from freya.core.logger import get_logger
from freya.memory.memory_store import (
    ChromaMemoryStore,
    MemoryRecord as ChromaMemoryRecord,
)

from .interfaces import (
    HealthStatus,
    Memory,
    MemoryInterface,
    MemoryStoreError,
    SearchResult,
)

logger = get_logger("hal.memory")


class ChromaMemoryDriver:
    """
    MemoryInterface implementation wrapping ChromaDB memory store.

    Adapts the existing ChromaMemoryStore to conform to the MemoryInterface protocol.
    """

    def __init__(self, memory_store: ChromaMemoryStore):
        """
        Initialize ChromaDB memory driver.

        Args:
            memory_store: Configured ChromaMemoryStore instance
        """
        self._store = memory_store
        logger.info("Initialized ChromaDB memory driver")

    async def store(
        self,
        content: str,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Memory:
        """
        Store a memory entry.

        Args:
            content: Memory content text
            memory_type: Type of memory (conversation, fact, event)
            metadata: Optional metadata dictionary
            correlation_id: Optional request correlation ID

        Returns:
            Stored memory object with ID

        Raises:
            MemoryStoreError: If storage fails
        """
        start_time = time.time()

        try:
            # Add correlation_id to metadata
            meta = metadata.copy() if metadata else {}
            if correlation_id:
                meta["correlation_id"] = correlation_id

            # Use existing ChromaMemoryStore implementation
            # Determine role from memory_type
            role = "user" if memory_type == "conversation" else "system"

            memory_id = await self._store.store_memory(
                content=content,
                role=role,
                importance=1,
                metadata=meta,
            )

            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Stored memory %s in %.1fms (type=%s, correlation_id=%s)",
                memory_id,
                latency_ms,
                memory_type,
                correlation_id,
            )

            return Memory(
                id=memory_id,
                content=content,
                memory_type=memory_type,
                timestamp=time.time(),
                metadata=meta,
                correlation_id=correlation_id,
            )

        except Exception as exc:
            logger.error(
                "Memory storage failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise MemoryStoreError(
                f"Failed to store memory: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Semantic search for relevant memories.

        Args:
            query: Search query text
            top_k: Maximum number of results
            memory_type: Optional filter by memory type
            correlation_id: Optional request correlation ID

        Returns:
            List of search results sorted by relevance

        Raises:
            MemoryStoreError: If query fails
        """
        start_time = time.time()

        try:
            # Use existing ChromaMemoryStore implementation
            # Run sync method in thread pool to avoid blocking
            filter_metadata = None
            if memory_type:
                # Map memory_type to role for filtering
                role = "user" if memory_type == "conversation" else "system"
                filter_metadata = {"role": role}

            results = await asyncio.to_thread(
                self._store.find_similar_memories,
                query=query,
                limit=top_k,
                min_score=0.15,
                filter_metadata=filter_metadata,
            )

            # Convert ChromaMemoryRecord to HAL SearchResult
            search_results = []
            for record in results:
                memory = Memory(
                    id=record.id,
                    content=record.content,
                    memory_type=record.metadata.get("memory_type", "conversation"),
                    timestamp=record.created_at.timestamp(),
                    metadata=record.metadata,
                    correlation_id=correlation_id,
                )

                search_result = SearchResult(
                    memory=memory,
                    score=record.score,
                    distance=1.0 - record.score,  # Convert score to distance
                )
                search_results.append(search_result)

            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Retrieved %d memories in %.1fms (query='%s', correlation_id=%s)",
                len(search_results),
                latency_ms,
                query[:50],
                correlation_id,
            )

            return search_results

        except Exception as exc:
            logger.error(
                "Memory retrieval failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise MemoryStoreError(
                f"Failed to retrieve memories: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """
        Check memory store health.

        Returns:
            Health status with diagnostics
        """
        start_time = time.time()

        try:
            # Get store statistics
            stats = self._store.get_stats()

            is_healthy = True
            status = "healthy"
            error_message = None

            # Check if store is accessible
            memory_count = stats.get("total_memories", 0)

            if memory_count == 0:
                status = "degraded"
                error_message = "No memories stored yet"
                is_healthy = False

            latency_ms = (time.time() - start_time) * 1000

            return HealthStatus(
                is_healthy=is_healthy,
                status=status,
                last_check=time.time(),
                latency_ms=latency_ms,
                error_message=error_message,
                metadata={
                    **stats,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as exc:
            logger.error(
                "Memory health check failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            return HealthStatus(
                is_healthy=False,
                status="offline",
                last_check=time.time(),
                error_message=str(exc),
                metadata={"correlation_id": correlation_id},
            )


class MockMemoryDriver:
    """
    Mock MemoryInterface implementation for testing without storage backend.

    Stores memories in-memory only (not persisted).
    """

    def __init__(self, behavior: str = "normal"):
        """
        Initialize mock memory driver.

        Args:
            behavior: Mock behavior mode:
                - "normal": Returns synthetic data successfully
                - "slow": Simulates slow storage
                - "offline": Always fails as if backend unavailable
        """
        self._behavior = behavior
        self._memories: Dict[str, Memory] = {}
        self._memory_counter = 0
        logger.info("Initialized mock memory driver (behavior=%s)", behavior)

    async def store(
        self,
        content: str,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Memory:
        """Store a mock memory."""
        if self._behavior == "offline":
            raise MemoryStoreError(
                "Mock memory store offline", correlation_id=correlation_id
            )

        if self._behavior == "slow":
            await asyncio.sleep(0.5)  # Simulate slow storage

        self._memory_counter += 1
        memory_id = f"mock_mem_{self._memory_counter}"

        meta = metadata.copy() if metadata else {}
        if correlation_id:
            meta["correlation_id"] = correlation_id

        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            timestamp=time.time(),
            metadata=meta,
            correlation_id=correlation_id,
        )

        self._memories[memory_id] = memory
        logger.debug("Stored mock memory %s", memory_id)

        return memory

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """Retrieve mock memories (simple substring match)."""
        if self._behavior == "offline":
            raise MemoryStoreError(
                "Mock memory store offline", correlation_id=correlation_id
            )

        if self._behavior == "slow":
            await asyncio.sleep(0.3)  # Simulate slow retrieval

        # Simple substring matching for mock
        results = []
        query_lower = query.lower()

        for memory in list(self._memories.values())[::-1]:  # Most recent first
            if memory_type and memory.memory_type != memory_type:
                continue

            if query_lower in memory.content.lower():
                # Mock relevance score based on position
                score = 0.8 if query_lower in memory.content.lower()[:50] else 0.5

                results.append(
                    SearchResult(
                        memory=memory,
                        score=score,
                        distance=1.0 - score,
                    )
                )

            if len(results) >= top_k:
                break

        logger.debug(
            "Retrieved %d mock memories for query '%s'", len(results), query[:50]
        )

        return results

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """Return mock health status."""
        if self._behavior == "offline":
            return HealthStatus(
                is_healthy=False,
                status="offline",
                last_check=time.time(),
                error_message="Mock memory store offline",
                metadata={"correlation_id": correlation_id},
            )

        return HealthStatus(
            is_healthy=True,
            status="healthy",
            last_check=time.time(),
            latency_ms=2.0,
            metadata={
                "memory_count": len(self._memories),
                "behavior": self._behavior,
                "correlation_id": correlation_id,
            },
        )


# Verify protocol conformance at module load time
_: MemoryInterface
_ = ChromaMemoryDriver  # type: ignore[assignment]
_ = MockMemoryDriver  # type: ignore[assignment]

__all__ = [
    "ChromaMemoryDriver",
    "MockMemoryDriver",
]
