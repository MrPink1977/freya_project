"""Memory store interface protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from freya.domain.entities.memory import Fact, Memory, MemoryQuery


@runtime_checkable
class IMemoryStore(Protocol):
    """
    Interface for memory storage backends.
    
    Supports both conversational memory and fact storage
    with semantic search capabilities.
    """

    async def store_memory(self, memory: Memory) -> str:
        """
        Store a conversation memory.
        
        Args:
            memory: Memory to store
            
        Returns:
            Memory ID
            
        Raises:
            MemoryStorageError: If storage fails
        """
        ...

    async def query_memories(
        self,
        query: MemoryQuery,
    ) -> list[Memory]:
        """
        Query memories using semantic search.
        
        Args:
            query: Query parameters
            
        Returns:
            List of matching memories
            
        Raises:
            MemoryQueryError: If query fails
        """
        ...

    async def store_fact(self, fact: Fact) -> str:
        """
        Store a fact.
        
        Args:
            fact: Fact to store
            
        Returns:
            Fact ID
            
        Raises:
            MemoryStorageError: If storage fails
        """
        ...

    async def query_facts(
        self,
        query: str,
        limit: int = 5,
    ) -> list[Fact]:
        """
        Query facts using semantic search.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching facts
            
        Raises:
            MemoryQueryError: If query fails
        """
        ...

    async def clear_memories(self) -> None:
        """
        Clear all memories.
        
        Raises:
            MemoryStorageError: If operation fails
        """
        ...

    async def get_stats(self) -> dict[str, int]:
        """
        Get memory store statistics.
        
        Returns:
            Dictionary with counts (memories, facts, etc.)
        """
        ...

    async def close(self) -> None:
        """Close the memory store and release resources."""
        ...
