"""
ChromaDB-based memory store for Freya - Professional vector storage.

Migration from SQLite to ChromaDB for better performance and scalability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:  # pragma: no cover
    chromadb = None  # type: ignore

from .logger import get_logger

logger = get_logger("memory")


@dataclass
class MemoryRecord:
    """Representation of a memory retrieved from storage."""

    id: str
    role: str
    content: str
    metadata: dict
    importance: int
    created_at: datetime
    last_accessed: datetime
    score: float


@dataclass
class Fact:
    """Structured fact about the user."""

    id: str
    category: str  # 'name', 'birthday', 'likes', 'dislikes', 'preference', 'custom'
    key: str
    value: str
    confidence: float
    created_at: datetime
    updated_at: datetime


class ChromaMemoryStore:
    """
    ChromaDB-backed semantic memory store for Freya.

    Features:
    - Vector similarity search with HNSW indexing
    - Built-in embedding generation
    - Metadata filtering
    - Local and private (no cloud)
    - Fast even with 100K+ memories
    """

    _DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, 384-dim embeddings
    _COLLECTION_NAME = "freya_memories"
    _FACTS_COLLECTION = "freya_facts"

    def __init__(
        self,
        db_path: str,
        embedding_model: Optional[str] = None,
    ) -> None:
        """
        Initialize ChromaDB memory store.

        Args:
            db_path: Path to ChromaDB storage directory
            embedding_model: Sentence-transformers model name
        """
        if chromadb is None:
            raise ImportError("chromadb not installed. Install with: pip install chromadb")

        self._db_path = Path(db_path).expanduser()
        self._db_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client (persistent, local)
        self._client = chromadb.PersistentClient(
            path=str(self._db_path),
            settings=Settings(
                anonymized_telemetry=False,  # Privacy
                allow_reset=True,
            ),
        )

        self._embedding_model = embedding_model or self._DEFAULT_EMBEDDING_MODEL

        # Get or create collection for memories
        self._memories = self._client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            embedding_function=chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self._embedding_model
            ),
            metadata={"hnsw:space": "cosine"},  # Cosine similarity
        )

        # Get or create collection for facts
        self._facts = self._client.get_or_create_collection(
            name=self._FACTS_COLLECTION,
            embedding_function=chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self._embedding_model
            ),
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            f"ChromaMemoryStore initialized at {self._db_path} "
            f"({self._memories.count()} memories, {self._facts.count()} facts)"
        )

    def store_memory(
        self,
        *,
        content: str,
        role: str,
        importance: int = 1,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Store a memory entry.

        Args:
            content: Memory text
            role: Speaker role (user/assistant/system)
            importance: Importance level (1-5)
            metadata: Additional metadata

        Returns:
            Memory ID (string)
        """
        text = (content or "").strip()
        if not text:
            raise ValueError("content must be a non-empty string")

        now = datetime.now(timezone.utc)
        memory_id = f"mem_{now.timestamp()}"

        # Prepare metadata
        meta = {
            "role": role,
            "importance": max(1, min(5, importance)),
            "created_at": now.isoformat(),
            "last_accessed": now.isoformat(),
            **(metadata or {}),
        }

        # Add to ChromaDB (auto-generates embedding)
        self._memories.add(
            ids=[memory_id],
            documents=[text],
            metadatas=[meta],
        )

        logger.debug(f"Stored memory {memory_id} ({role})")
        return memory_id

    def find_similar_memories(
        self,
        query: str,
        *,
        limit: int = 5,
        min_score: float = 0.15,
        filter_metadata: Optional[dict] = None,
    ) -> List[MemoryRecord]:
        """
        Find similar memories using semantic search.

        Args:
            query: Search query
            limit: Maximum results
            min_score: Minimum similarity score (0-1)
            filter_metadata: Optional metadata filters (e.g., {"role": "user"})

        Returns:
            List of matching memories, sorted by relevance
        """
        normalized = (query or "").strip()
        if not normalized:
            return []

        limit = max(1, min(100, limit))
        min_score = max(0.0, min(1.0, min_score))

        # Query ChromaDB
        results = self._memories.query(
            query_texts=[normalized],
            n_results=limit,
            where=filter_metadata,  # Optional metadata filtering
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        # Convert to MemoryRecord objects
        memories = []
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for idx, (mem_id, doc, meta, distance) in enumerate(
            zip(ids, documents, metadatas, distances)
        ):
            # Convert distance to similarity score (ChromaDB returns distance, not similarity)
            # For cosine distance: similarity = 1 - distance
            score = 1.0 - distance

            if score < min_score:
                continue

            # Boost score by importance and recency
            importance = meta.get("importance", 1)
            created_at = self._parse_timestamp(meta.get("created_at"))
            recency_boost = self._recency_boost(created_at)

            adjusted_score = score + 0.05 * importance + recency_boost

            memories.append(
                MemoryRecord(
                    id=mem_id,
                    role=meta.get("role", "unknown"),
                    content=doc,
                    metadata=meta,
                    importance=importance,
                    created_at=created_at,
                    last_accessed=self._parse_timestamp(meta.get("last_accessed")),
                    score=adjusted_score,
                )
            )

        # Update last_accessed timestamps
        now = datetime.now(timezone.utc).isoformat()
        for memory in memories:
            memory.last_accessed = self._parse_timestamp(now)
            self._memories.update(
                ids=[memory.id],
                metadatas=[{**memory.metadata, "last_accessed": now}],
            )

        # Sort by adjusted score
        memories.sort(key=lambda m: m.score, reverse=True)

        logger.debug(
            f"Retrieved {len(memories)} memories (avg score: "
            f"{sum(m.score for m in memories) / len(memories):.2f})"
        )

        return memories

    def store_fact(
        self,
        *,
        category: str,
        key: str,
        value: str,
        confidence: float = 1.0,
    ) -> str:
        """
        Store a structured fact.

        Args:
            category: Fact category (name, birthday, preference, etc.)
            key: Fact key
            value: Fact value
            confidence: Confidence level (0-1)

        Returns:
            Fact ID
        """
        if not key or not value:
            raise ValueError("key and value must be non-empty strings")

        now = datetime.now(timezone.utc)
        fact_id = f"fact_{category}_{key}_{now.timestamp()}"

        # Create searchable text from fact
        fact_text = f"{category}: {key} is {value}"

        meta = {
            "category": category,
            "key": key,
            "value": value,
            "confidence": max(0.0, min(1.0, confidence)),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        self._facts.add(
            ids=[fact_id],
            documents=[fact_text],
            metadatas=[meta],
        )

        logger.debug(f"Stored fact: {category}/{key} = {value}")
        return fact_id

    def query_facts(
        self,
        query: str,
        *,
        category: Optional[str] = None,
        limit: int = 3,
    ) -> List[Fact]:
        """
        Query facts using semantic search.

        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of matching facts
        """
        normalized = (query or "").strip()
        if not normalized:
            return []

        where = {"category": category} if category else None

        results = self._facts.query(
            query_texts=[normalized],
            n_results=limit,
            where=where,
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        facts = []
        for fact_id, meta in zip(results["ids"][0], results["metadatas"][0]):
            facts.append(
                Fact(
                    id=fact_id,
                    category=meta.get("category", ""),
                    key=meta.get("key", ""),
                    value=meta.get("value", ""),
                    confidence=meta.get("confidence", 1.0),
                    created_at=self._parse_timestamp(meta.get("created_at")),
                    updated_at=self._parse_timestamp(meta.get("updated_at")),
                )
            )

        return facts

    def get_all_facts(self, category: Optional[str] = None) -> List[Fact]:
        """
        Get all stored facts, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of all facts
        """
        where = {"category": category} if category else None

        results = self._facts.get(where=where)

        if not results["ids"]:
            return []

        facts = []
        for fact_id, meta in zip(results["ids"], results["metadatas"]):
            facts.append(
                Fact(
                    id=fact_id,
                    category=meta.get("category", ""),
                    key=meta.get("key", ""),
                    value=meta.get("value", ""),
                    confidence=meta.get("confidence", 1.0),
                    created_at=self._parse_timestamp(meta.get("created_at")),
                    updated_at=self._parse_timestamp(meta.get("updated_at")),
                )
            )

        return facts

    def clear_memories(self) -> int:
        """Clear all memories. Returns count deleted."""
        count = self._memories.count()
        self._client.delete_collection(self._COLLECTION_NAME)
        self._memories = self._client.create_collection(
            name=self._COLLECTION_NAME,
            embedding_function=chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self._embedding_model
            ),
        )
        logger.info(f"Cleared {count} memories")
        return count

    def get_stats(self) -> dict:
        """Get memory store statistics."""
        return {
            "total_memories": self._memories.count(),
            "total_facts": self._facts.count(),
            "embedding_model": self._embedding_model,
            "db_path": str(self._db_path),
        }

    @staticmethod
    def _parse_timestamp(ts: str | datetime | None) -> datetime:
        """Parse timestamp string to datetime."""
        if isinstance(ts, datetime):
            return ts
        if ts is None:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.now(timezone.utc)

    @staticmethod
    def _recency_boost(created_at: datetime) -> float:
        """Calculate recency boost for scoring (0-0.1)."""
        age_days = (datetime.now(timezone.utc) - created_at).total_seconds() / 86400
        if age_days < 1:
            return 0.1
        elif age_days < 7:
            return 0.05
        elif age_days < 30:
            return 0.02
        return 0.0

    def close(self) -> None:
        """Close the memory store (ChromaDB handles cleanup automatically)."""
        logger.debug("ChromaMemoryStore closed")


# Alias for backward compatibility
PersistentMemoryStore = ChromaMemoryStore

__all__ = ["ChromaMemoryStore", "PersistentMemoryStore", "MemoryRecord", "Fact"]
