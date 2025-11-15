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


class PersistentMemoryStore:
    """SQLite-backed semantic memory store with lightweight retrieval.

    Thread Safety:
        This class uses check_same_thread=False with SQLite to allow multi-threaded
        access, which is necessary for concurrent voice processing. All database
        operations are protected by a threading lock to ensure thread safety and
        prevent database corruption.
    """

    _DEFAULT_SEARCH_WINDOW = 200

    def __init__(self, db_path: str, search_window: int | None = None) -> None:
        path = Path(db_path).expanduser()
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._lock = threading.Lock()
        self._search_window = max(10, int(search_window or self._DEFAULT_SEARCH_WINDOW))
        # check_same_thread=False allows multi-threaded access; all operations
        # are protected by self._lock to ensure thread safety
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._initialise_schema()
        logger.debug("PersistentMemoryStore ready at %s", self._path)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "PersistentMemoryStore":  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - convenience
        self.close()

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
            logger.debug("Stored memory %s (%s)", memory_id, role)
            return memory_id

    def find_similar_memories(
        self,
        query: str,
        *,
        limit: int = 5,
        min_score: float = 0.15,
    ) -> List[MemoryRecord]:
        """Return the most similar memories for the provided text query."""

        normalized = (query or "").strip()
        if not normalized:
            return []

        query_tokens = self._tokenize(normalized)
        if not query_tokens:
            return []

        limit = max(1, int(limit))
        min_score = max(0.0, float(min_score))

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
            logger.debug("Retrieved %s memory matches", len(selected))
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

    def _initialise_schema(self) -> None:
        with self._lock:
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


__all__ = ["MemoryRecord", "PersistentMemoryStore"]