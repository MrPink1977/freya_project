"""
SQLite PERSISTENCE FOR MESSAGE BUS.

Provides simple persistence for debugging and message replay.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from freya.core.message_bus import Message, MessagePriority

from freya.logger import get_logger


logger = get_logger(__name__)


class MessagePersistence:
    """
    SQLite-based message persistence for debugging.
    
    Features:
    - Async-safe database operations
    - Message storage with full metadata
    - Query by topic, sender, time range
    - Automatic cleanup of old messages
    """

    def __init__(
        self,
        db_path: str = "data/message_history.db",
        max_messages: int = 10000,
        enable_persistence: bool = True,
    ) -> None:
        """
        Initialize message persistence.

        Args:
            db_path: Path to SQLite database file
            max_messages: Maximum messages to keep (oldest deleted first)
            enable_persistence: Whether to enable persistence (useful for disabling in tests)
        """
        self.db_path = Path(db_path)
        self.max_messages = max_messages
        self.enabled = enable_persistence
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()

        if self.enabled:
            self._init_database()
            logger.info(f"MessagePersistence initialized (db_path={db_path})")
        else:
            logger.info("MessagePersistence disabled")

    def _init_database(self) -> None:
        """Initialize database schema."""
        # Create parent directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create connection
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # Create table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                sender TEXT NOT NULL,
                priority TEXT NOT NULL,
                payload TEXT NOT NULL,
                correlation_id TEXT,
                timestamp TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)

        # Create indices for common queries
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_topic ON messages(topic)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_correlation_id ON messages(correlation_id)"
        )

        self._conn.commit()
        logger.debug("Database schema initialized")

    async def store_message(self, message: "Message") -> None:
        """
        Store message to database.

        Args:
            message: Message to store
        """
        if not self.enabled or not self._conn:
            return

        async with self._lock:
            try:
                # Serialize payload to JSON
                payload_json = json.dumps(message.payload, default=str)

                # Insert message
                self._conn.execute(
                    """
                    INSERT INTO messages 
                    (topic, sender, priority, payload, correlation_id, timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.topic,
                        message.sender,
                        message.priority.name,
                        payload_json,
                        message.correlation_id,
                        message.timestamp.isoformat(),
                        datetime.now().timestamp(),
                    ),
                )
                self._conn.commit()

                # Cleanup old messages if needed
                await self._cleanup_old_messages()

                logger.debug(f"Stored message: {message.topic} from {message.sender}")

            except Exception as exc:
                logger.error(f"Failed to store message: {exc}")

    async def _cleanup_old_messages(self) -> None:
        """Remove oldest messages if over limit."""
        try:
            cursor = self._conn.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]

            if count > self.max_messages:
                to_delete = count - self.max_messages
                self._conn.execute(
                    """
                    DELETE FROM messages 
                    WHERE id IN (
                        SELECT id FROM messages 
                        ORDER BY created_at ASC 
                        LIMIT ?
                    )
                    """,
                    (to_delete,),
                )
                self._conn.commit()
                logger.debug(f"Cleaned up {to_delete} old messages")

        except Exception as exc:
            logger.error(f"Failed to cleanup old messages: {exc}")

    async def query_messages(
        self,
        topic: Optional[str] = None,
        sender: Optional[str] = None,
        correlation_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query messages from database.

        Args:
            topic: Filter by topic (supports wildcards with %)
            sender: Filter by sender
            correlation_id: Filter by correlation ID
            since: Only messages after this time
            limit: Maximum messages to return

        Returns:
            List of message dictionaries
        """
        if not self.enabled or not self._conn:
            return []

        async with self._lock:
            try:
                # Build query
                query = "SELECT * FROM messages WHERE 1=1"
                params = []

                if topic:
                    query += " AND topic LIKE ?"
                    params.append(topic.replace("*", "%"))

                if sender:
                    query += " AND sender = ?"
                    params.append(sender)

                if correlation_id:
                    query += " AND correlation_id = ?"
                    params.append(correlation_id)

                if since:
                    query += " AND timestamp >= ?"
                    params.append(since.isoformat())

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                # Execute query
                cursor = self._conn.execute(query, params)
                rows = cursor.fetchall()

                # Convert to dictionaries
                messages = []
                for row in rows:
                    try:
                        messages.append({
                            "id": row["id"],
                            "topic": row["topic"],
                            "sender": row["sender"],
                            "priority": row["priority"],
                            "payload": json.loads(row["payload"]),
                            "correlation_id": row["correlation_id"],
                            "timestamp": row["timestamp"],
                        })
                    except Exception as exc:
                        logger.error(f"Failed to deserialize message {row['id']}: {exc}")

                logger.debug(f"Query returned {len(messages)} messages")
                return messages

            except Exception as exc:
                logger.error(f"Failed to query messages: {exc}")
                return []

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get persistence statistics.

        Returns:
            Dictionary with stats
        """
        if not self.enabled or not self._conn:
            return {"enabled": False}

        async with self._lock:
            try:
                cursor = self._conn.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]

                cursor = self._conn.execute(
                    "SELECT COUNT(DISTINCT topic) FROM messages"
                )
                unique_topics = cursor.fetchone()[0]

                cursor = self._conn.execute(
                    "SELECT COUNT(DISTINCT sender) FROM messages"
                )
                unique_senders = cursor.fetchone()[0]

                # Get database file size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

                return {
                    "enabled": True,
                    "total_messages": total_messages,
                    "unique_topics": unique_topics,
                    "unique_senders": unique_senders,
                    "db_size_bytes": db_size,
                    "db_path": str(self.db_path),
                    "max_messages": self.max_messages,
                }

            except Exception as exc:
                logger.error(f"Failed to get stats: {exc}")
                return {"enabled": True, "error": str(exc)}

    async def clear_all(self) -> None:
        """Clear all messages from database (useful for testing)."""
        if not self.enabled or not self._conn:
            return

        async with self._lock:
            try:
                self._conn.execute("DELETE FROM messages")
                self._conn.commit()
                logger.info("Cleared all messages from database")
            except Exception as exc:
                logger.error(f"Failed to clear messages: {exc}")

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("MessagePersistence closed")
