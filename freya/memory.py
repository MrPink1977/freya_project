"""Persistence-backed memory utilities for Freya."""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

try:  # pragma: no cover - optional dependency
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - runtime check
    SentenceTransformer = None  # type: ignore[assignment, misc]

from .logger import get_logger

logger = get_logger("memory")


@dataclass
class MemoryRecord:
    """Representation of a memory retrieved from persistent storage."""

    id: int
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

    id: int
    category: str  # 'name', 'birthday', 'likes', 'dislikes', 'preference', 'custom'
    key: str
    value: str
    confidence: float
    created_at: datetime
    updated_at: datetime


class PersistentMemoryStore:
    """SQLite-backed semantic memory store with lightweight retrieval.

    Thread Safety:
        This class uses check_same_thread=False with SQLite to allow multi-threaded
        access, which is necessary for concurrent voice processing. All database
        operations are protected by a threading lock to ensure thread safety and
        prevent database corruption.
    """

    _DEFAULT_SEARCH_WINDOW = 200
    _DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, lightweight, 384-dim embeddings

    def __init__(self, db_path: str, search_window: int | None = None, use_embeddings: bool = True) -> None:
        path = Path(db_path).expanduser()
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._lock = threading.Lock()
        self._search_window = max(10, int(search_window or self._DEFAULT_SEARCH_WINDOW))

        # Initialize embedding model for semantic search
        self._use_embeddings = use_embeddings and SentenceTransformer is not None
        self._embedding_model: Optional[SentenceTransformer] = None

        if self._use_embeddings:
            try:
                logger.info("Loading embedding model: %s", self._DEFAULT_EMBEDDING_MODEL)
                self._embedding_model = SentenceTransformer(self._DEFAULT_EMBEDDING_MODEL)
                logger.debug("Embedding model loaded successfully (384 dimensions)")
            except Exception as exc:  # pragma: no cover - model loading
                logger.warning("Failed to load embedding model: %s. Falling back to lexical search.", exc)
                self._use_embeddings = False
        elif use_embeddings and SentenceTransformer is None:
            logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")

        # check_same_thread=False allows multi-threaded access; all operations
        # are protected by self._lock to ensure thread safety
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._initialise_schema()
        logger.debug("PersistentMemoryStore ready at %s (embeddings: %s)", self._path, self._use_embeddings)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "PersistentMemoryStore":  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - convenience
        self.close()

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate a semantic embedding vector for the given text."""
        if not self._use_embeddings or self._embedding_model is None:
            return None

        try:
            embedding = self._embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as exc:  # pragma: no cover - model runtime
            logger.warning("Failed to generate embedding: %s", exc)
            return None

    @staticmethod
    def _cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def store_memory(
        self,
        *,
        content: str,
        role: str,
        importance: int = 1,
        metadata: Optional[dict] = None,
        embedding: Optional[Sequence[float]] = None,
    ) -> int:
        """Persist a memory entry and return its database identifier."""

        text = (content or "").strip()
        if not text:
            raise ValueError("content must be a non-empty string")

        # Auto-generate embedding if not provided and embeddings are enabled
        if embedding is None and self._use_embeddings:
            embedding = self._generate_embedding(text)

        metadata_json = json.dumps(metadata or {})
        embedding_json = json.dumps(list(embedding)) if embedding is not None else None
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO memories (role, content, metadata, importance, embedding, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (role, text, metadata_json, int(max(1, importance)), embedding_json, now, now),
            )
            self._conn.commit()
            memory_id = int(cursor.lastrowid)
            logger.debug("Stored memory %s (%s) [embedding: %s]", memory_id, role, embedding is not None)
            return memory_id

    def find_similar_memories(
        self,
        query: str,
        *,
        limit: int = 5,
        min_score: float = 0.15,
    ) -> List[MemoryRecord]:
        """Return the most similar memories for the provided text query using semantic search."""

        normalized = (query or "").strip()
        if not normalized:
            return []

        limit = max(1, int(limit))
        min_score = max(0.0, float(min_score))

        # Use semantic search if embeddings are enabled
        if self._use_embeddings:
            return self._semantic_search(normalized, limit=limit, min_score=min_score)

        # Fallback to lexical search if embeddings disabled
        return self._lexical_search(normalized, limit=limit, min_score=min_score)

    def _semantic_search(
        self,
        query: str,
        *,
        limit: int = 5,
        min_score: float = 0.15,
    ) -> List[MemoryRecord]:
        """Semantic vector search using embeddings and cosine similarity."""

        # Generate embedding for query
        query_embedding = self._generate_embedding(query)
        if query_embedding is None:
            logger.debug("Could not generate query embedding; falling back to lexical search")
            return self._lexical_search(query, limit=limit, min_score=min_score)

        with self._lock:
            cursor = self._conn.execute(
                """
                SELECT id, role, content, metadata, importance, embedding, created_at, last_accessed
                FROM memories
                WHERE embedding IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self._search_window,),
            )

            candidates: List[MemoryRecord] = []
            for row in cursor:
                embedding_json = row["embedding"]
                if not embedding_json:
                    continue

                try:
                    memory_embedding = json.loads(embedding_json)
                except (json.JSONDecodeError, TypeError):
                    continue

                # Calculate cosine similarity
                semantic_score = self._cosine_similarity(query_embedding, memory_embedding)

                if semantic_score < min_score:
                    continue

                importance = max(1, int(row["importance"]))
                created_at = self._parse_timestamp(row["created_at"])
                last_accessed = self._parse_timestamp(row["last_accessed"])
                metadata_json = row["metadata"]
                metadata = json.loads(metadata_json) if metadata_json else {}

                # Combine semantic score with importance and recency
                score = semantic_score + 0.05 * importance + self._recency_boost(created_at)
                candidates.append(
                    MemoryRecord(
                        id=int(row["id"]),
                        role=row["role"],
                        content=row["content"],
                        metadata=metadata,
                        importance=importance,
                        created_at=created_at,
                        last_accessed=last_accessed,
                        score=score,
                    )
                )

            candidates.sort(key=lambda record: record.score, reverse=True)
            selected = candidates[:limit]

            if not selected:
                return []

            now = datetime.now(timezone.utc).isoformat()
            self._conn.executemany(
                "UPDATE memories SET last_accessed = ? WHERE id = ?",
                ((now, record.id) for record in selected),
            )
            self._conn.commit()
            logger.debug("Retrieved %s semantic memory matches (avg score: %.2f)",
                        len(selected), sum(r.score for r in selected) / len(selected))
            return selected

    def _lexical_search(
        self,
        query: str,
        *,
        limit: int = 5,
        min_score: float = 0.15,
    ) -> List[MemoryRecord]:
        """Fallback lexical search using token matching."""

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        with self._lock:
            cursor = self._conn.execute(
                """
                SELECT id, role, content, metadata, importance, embedding, created_at, last_accessed
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self._search_window,),
            )
            candidates: List[MemoryRecord] = []
            for row in cursor:
                content = row["content"]
                tokens = self._tokenize(content)
                lexical_score = self._lexical_similarity(query_tokens, tokens)
                if lexical_score < min_score:
                    continue

                importance = max(1, int(row["importance"]))
                created_at = self._parse_timestamp(row["created_at"])
                last_accessed = self._parse_timestamp(row["last_accessed"])
                metadata_json = row["metadata"]
                metadata = json.loads(metadata_json) if metadata_json else {}

                score = lexical_score + 0.05 * importance + self._recency_boost(created_at)
                candidates.append(
                    MemoryRecord(
                        id=int(row["id"]),
                        role=row["role"],
                        content=content,
                        metadata=metadata,
                        importance=importance,
                        created_at=created_at,
                        last_accessed=last_accessed,
                        score=score,
                    )
                )

            candidates.sort(key=lambda record: record.score, reverse=True)
            selected = candidates[:limit]
            if not selected:
                return []

            now = datetime.now(timezone.utc).isoformat()
            self._conn.executemany(
                "UPDATE memories SET last_accessed = ? WHERE id = ?",
                ((now, record.id) for record in selected),
            )
            self._conn.commit()
            logger.debug("Retrieved %s lexical memory matches", len(selected))
            return selected

    def prune(self, max_entries: int) -> None:
        """Keep the memory store bounded by deleting the oldest entries."""

        max_entries = max(0, int(max_entries))
        if max_entries <= 0:
            return

        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM memories")
            count = int(cursor.fetchone()[0])
            if count <= max_entries:
                return

            to_remove = count - max_entries
            self._conn.execute(
                "DELETE FROM memories WHERE id IN (SELECT id FROM memories ORDER BY created_at ASC LIMIT ?)",
                (to_remove,),
            )
            self._conn.commit()
            logger.debug("Pruned %s old memory entries", to_remove)

    def store_fact(
        self,
        *,
        category: str,
        key: str,
        value: str,
        confidence: float = 1.0,
    ) -> int:
        """Store or update a structured fact about the user.

        Args:
            category: Type of fact ('name', 'birthday', 'likes', 'dislikes', 'preference', 'custom')
            key: Specific identifier for this fact ('name', 'coffee', 'color', etc.)
            value: The actual value
            confidence: How confident we are in this fact (0.0-1.0)

        Returns:
            The fact ID
        """
        category = (category or "").strip().lower()
        key = (key or "").strip().lower()
        value = (value or "").strip()

        if not category or not key or not value:
            raise ValueError("category, key, and value must all be non-empty")

        confidence = max(0.0, min(1.0, float(confidence)))
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            # Check if fact already exists
            cursor = self._conn.execute(
                "SELECT id FROM facts WHERE category = ? AND key = ?",
                (category, key),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing fact
                self._conn.execute(
                    """
                    UPDATE facts
                    SET value = ?, confidence = ?, updated_at = ?
                    WHERE category = ? AND key = ?
                    """,
                    (value, confidence, now, category, key),
                )
                fact_id = int(existing[0])
                logger.debug("Updated fact %s: %s.%s = '%s'", fact_id, category, key, value)
            else:
                # Insert new fact
                cursor = self._conn.execute(
                    """
                    INSERT INTO facts (category, key, value, confidence, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (category, key, value, confidence, now, now),
                )
                fact_id = int(cursor.lastrowid)
                logger.debug("Stored new fact %s: %s.%s = '%s'", fact_id, category, key, value)

            self._conn.commit()
            return fact_id

    def get_fact(self, category: str, key: Optional[str] = None) -> Optional[Fact] | List[Fact]:
        """Retrieve a fact or facts by category and optional key.

        Args:
            category: The fact category to search
            key: Optional specific key within that category

        Returns:
            Single Fact if key provided, List[Fact] if only category, None if not found
        """
        category = (category or "").strip().lower()
        if not category:
            return None if key is not None else []

        with self._lock:
            if key is not None:
                # Get specific fact
                key = key.strip().lower()
                cursor = self._conn.execute(
                    """
                    SELECT id, category, key, value, confidence, created_at, updated_at
                    FROM facts
                    WHERE category = ? AND key = ?
                    """,
                    (category, key),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                return Fact(
                    id=int(row["id"]),
                    category=row["category"],
                    key=row["key"],
                    value=row["value"],
                    confidence=float(row["confidence"]),
                    created_at=self._parse_timestamp(row["created_at"]),
                    updated_at=self._parse_timestamp(row["updated_at"]),
                )
            else:
                # Get all facts in category
                cursor = self._conn.execute(
                    """
                    SELECT id, category, key, value, confidence, created_at, updated_at
                    FROM facts
                    WHERE category = ?
                    ORDER BY updated_at DESC
                    """,
                    (category,),
                )
                facts = []
                for row in cursor:
                    facts.append(
                        Fact(
                            id=int(row["id"]),
                            category=row["category"],
                            key=row["key"],
                            value=row["value"],
                            confidence=float(row["confidence"]),
                            created_at=self._parse_timestamp(row["created_at"]),
                            updated_at=self._parse_timestamp(row["updated_at"]),
                        )
                    )
                return facts

    def search_facts(self, query: str) -> List[Fact]:
        """Search for facts whose values match the query.

        Args:
            query: Text to search for in fact values

        Returns:
            List of matching facts
        """
        query = (query or "").strip().lower()
        if not query:
            return []

        with self._lock:
            cursor = self._conn.execute(
                """
                SELECT id, category, key, value, confidence, created_at, updated_at
                FROM facts
                WHERE LOWER(value) LIKE ?
                ORDER BY confidence DESC, updated_at DESC
                """,
                (f"%{query}%",),
            )
            facts = []
            for row in cursor:
                facts.append(
                    Fact(
                        id=int(row["id"]),
                        category=row["category"],
                        key=row["key"],
                        value=row["value"],
                        confidence=float(row["confidence"]),
                        created_at=self._parse_timestamp(row["created_at"]),
                        updated_at=self._parse_timestamp(row["updated_at"]),
                    )
                )
            return facts

    def _initialise_schema(self) -> None:
        with self._lock:
            # Memories table - semantic memory storage
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    importance INTEGER NOT NULL DEFAULT 1,
                    embedding TEXT,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_created_at
                ON memories (created_at DESC)
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_importance
                ON memories (importance DESC)
                """
            )

            # Facts table - structured user facts for instant lookup
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(category, key)
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_facts_category
                ON facts (category)
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_facts_key
                ON facts (key)
                """
            )

            self._conn.commit()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token for token in re.split(r"[^A-Za-z0-9]+", text.lower()) if token]

    @staticmethod
    def _lexical_similarity(query_tokens: Iterable[str], content_tokens: Iterable[str]) -> float:
        query_set = set(query_tokens)
        content_set = set(content_tokens)
        if not query_set or not content_set:
            return 0.0
        intersection = query_set & content_set
        if not intersection:
            return 0.0
        union = query_set | content_set
        return len(intersection) / len(union)

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)

    @staticmethod
    def _recency_boost(created_at: datetime) -> float:
        delta = datetime.now(timezone.utc) - created_at
        hours = max(0.0, delta.total_seconds() / 3600.0)
        if hours >= 168:  # one week
            return 0.0
        return max(0.0, 0.1 * (1 - hours / 168))


__all__ = ["MemoryRecord", "Fact", "PersistentMemoryStore"]