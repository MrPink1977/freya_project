"""Memory store check."""

from __future__ import annotations

from pathlib import Path

from . import BaseSystemCheck, CheckResult, CheckStatus


class MemoryCheck(BaseSystemCheck):
    """Check ChromaDB memory store."""

    def __init__(self, db_path: str = "data/chroma_db"):
        super().__init__(
            name="Memory Store",
            description="Check ChromaDB vector database",
            required=False,
        )
        self.db_path = Path(db_path)

    async def run(self) -> CheckResult:
        """Check memory store."""
        try:
            import chromadb
        except ImportError:
            return CheckResult(
                status=CheckStatus.FAILED,
                message="chromadb not installed",
                fix_suggestion="pip install chromadb",
            )

        try:
            # Check if DB path exists
            if not self.db_path.exists():
                return CheckResult(
                    status=CheckStatus.WARNING,
                    message="Database not initialized",
                    details=f"Path: {self.db_path}",
                    fix_suggestion="Database will be created on first run",
                )

            # Try to connect to existing database
            client = chromadb.PersistentClient(path=str(self.db_path))
            collections = client.list_collections()

            return CheckResult(
                status=CheckStatus.PASSED,
                message=f"ChromaDB ready ({len(collections)} collections)",
                details=f"Path: {self.db_path}",
            )

        except Exception as e:
            return CheckResult(
                status=CheckStatus.WARNING,
                message=f"Cannot access database: {type(e).__name__}",
                details=str(e),
                fix_suggestion="Database may need to be recreated",
            )
