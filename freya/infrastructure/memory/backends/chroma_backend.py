"""ChromaDB backend implementation for memory storage."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from freya.domain.entities.memory import Fact, Memory
from freya.domain.exceptions import MemoryConnectionError, MemoryStorageError
from freya.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ChromaBackend:
    """
    ChromaDB backend for vector-based memory storage.
    
    Provides semantic search capabilities using embeddings.
    """

    def __init__(
        self,
        persist_directory: str | Path,
        collection_name: str = "freya_memory",
    ) -> None:
        """
        Initialize ChromaDB backend.
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the collection
        """
        self._persist_dir = Path(persist_directory)
        self._collection_name = collection_name
        self._client = None
        self._memory_collection = None
        self._fact_collection = None

        logger.info(
            "ChromaBackend initialized",
            persist_directory=str(self._persist_dir),
            collection_name=collection_name,
        )

    async def connect(self) -> None:
        """
        Connect to ChromaDB.
        
        Raises:
            MemoryConnectionError: If connection fails
        """
        try:
            # Import here to avoid hard dependency
            import chromadb
            from chromadb.config import Settings

            # Create persist directory
            self._persist_dir.mkdir(parents=True, exist_ok=True)

            # Initialize client
            self._client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(self._persist_dir),
                )
            )

            # Get or create collections
            self._memory_collection = self._client.get_or_create_collection(
                name=f"{self._collection_name}_memories",
                metadata={"description": "Conversation memories"},
            )

            self._fact_collection = self._client.get_or_create_collection(
                name=f"{self._collection_name}_facts",
                metadata={"description": "Extracted facts"},
            )

            logger.info("Connected to ChromaDB")

        except ImportError as e:
            raise MemoryConnectionError(
                "ChromaDB not installed. Install with: pip install chromadb",
                backend="chromadb",
                cause=e,
            ) from e
        except Exception as e:
            raise MemoryConnectionError(
                "Failed to connect to ChromaDB",
                backend="chromadb",
                cause=e,
            ) from e

    async def store_memory(self, memory: Memory) -> str:
        """Store a conversation memory."""
        if not self._memory_collection:
            await self.connect()

        try:
            self._memory_collection.add(
                ids=[memory.memory_id],
                documents=[memory.content],
                metadatas=[
                    {
                        "role": memory.role,
                        "timestamp": memory.timestamp.isoformat(),
                        **memory.metadata,
                    }
                ],
            )

            return memory.memory_id

        except Exception as e:
            raise MemoryStorageError(
                "Failed to store memory in ChromaDB",
                operation="add",
                cause=e,
            ) from e

    async def query_memories(self, query_params: dict[str, Any]) -> list[Memory]:
        """Query memories using semantic search."""
        if not self._memory_collection:
            await self.connect()

        try:
            query_text = query_params.get("query_text", "")
            limit = query_params.get("limit", 10)
            metadata_filters = query_params.get("metadata_filters", {})

            # Build where clause for metadata filtering
            where = None
            if metadata_filters:
                where = metadata_filters

            # Query ChromaDB
            results = self._memory_collection.query(
                query_texts=[query_text],
                n_results=limit,
                where=where,
            )

            # Convert to Memory objects
            memories = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    memory = Memory(
                        memory_id=results["ids"][0][i],
                        content=doc,
                        role=metadata.get("role", "user"),
                        timestamp=datetime.fromisoformat(metadata.get("timestamp")),
                        metadata={
                            k: v for k, v in metadata.items() if k not in ["role", "timestamp"]
                        },
                    )
                    memories.append(memory)

            return memories

        except Exception as e:
            logger.error("Failed to query memories", error=str(e), exc_info=e)
            return []

    async def store_fact(self, fact: Fact) -> str:
        """Store a fact."""
        if not self._fact_collection:
            await self.connect()

        try:
            self._fact_collection.add(
                ids=[fact.fact_id],
                documents=[fact.content],
                metadatas=[
                    {
                        "category": fact.category,
                        "confidence": fact.confidence,
                        "timestamp": fact.timestamp.isoformat(),
                        "source": fact.source or "",
                        **fact.metadata,
                    }
                ],
            )

            return fact.fact_id

        except Exception as e:
            raise MemoryStorageError(
                "Failed to store fact in ChromaDB",
                operation="add",
                cause=e,
            ) from e

    async def query_facts(self, query: str, limit: int = 5) -> list[Fact]:
        """Query facts using semantic search."""
        if not self._fact_collection:
            await self.connect()

        try:
            results = self._fact_collection.query(
                query_texts=[query],
                n_results=limit,
            )

            # Convert to Fact objects
            facts = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    fact = Fact(
                        fact_id=results["ids"][0][i],
                        content=doc,
                        category=metadata.get("category", "general"),
                        confidence=metadata.get("confidence", 1.0),
                        timestamp=datetime.fromisoformat(metadata.get("timestamp")),
                        source=metadata.get("source"),
                        metadata={
                            k: v
                            for k, v in metadata.items()
                            if k not in ["category", "confidence", "timestamp", "source"]
                        },
                    )
                    facts.append(fact)

            return facts

        except Exception as e:
            logger.error("Failed to query facts", error=str(e), exc_info=e)
            return []

    async def clear_memories(self) -> None:
        """Clear all memories."""
        if self._memory_collection:
            self._memory_collection.delete()
        if self._fact_collection:
            self._fact_collection.delete()

        logger.info("All memories cleared")

    async def get_stats(self) -> dict[str, int]:
        """Get statistics."""
        stats = {}

        if self._memory_collection:
            stats["memories"] = self._memory_collection.count()

        if self._fact_collection:
            stats["facts"] = self._fact_collection.count()

        return stats

    async def close(self) -> None:
        """Close the backend."""
        # ChromaDB client doesn't need explicit closing
        logger.info("ChromaBackend closed")
