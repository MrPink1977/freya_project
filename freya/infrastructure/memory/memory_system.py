"""
Memory System - Semantic memory storage and retrieval with ChromaDB.

Integrates embedding model with ChromaDB for efficient semantic search.
Stores conversation history, facts, and context for retrieval.
"""

import time
import uuid
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime

from freya.shared.logging.logger import get_logger
from freya.shared.logging.decorators import log_performance
from freya.domain.entities.memory import Memory, Fact, MemoryType
from freya.infrastructure.memory.embedding import NomicEmbedding


logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Result from memory search."""
    memory: Memory
    similarity: float
    rank: int


class MemorySystem:
    """
    Semantic memory system with ChromaDB backend.
    
    Features:
    - Semantic search using embeddings
    - Conversation history storage
    - Fact extraction and storage
    - Time-based filtering
    - Metadata tagging
    
    Architecture:
    - Embedding model converts text → vectors
    - ChromaDB stores vectors + metadata
    - Search finds similar memories by vector similarity
    """
    
    def __init__(
        self,
        embedding_model: NomicEmbedding,
        persist_directory: str = "data/memory",
        collection_name: str = "freya_memory",
    ):
        """
        Initialize memory system.
        
        Args:
            embedding_model: Embedding model for vectorization
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the ChromaDB collection
        """
        self.embedding_model = embedding_model
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        self._client = None
        self._collection = None
        
        logger.info(
            "Initializing MemorySystem",
            extra={
                "persist_dir": persist_directory,
                "collection": collection_name
            }
        )
        
        self._initialize_chroma()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Create persistent client
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Freya's semantic memory"}
            )
            
            count = self._collection.count()
            logger.info(
                f"ChromaDB initialized with {count} memories",
                extra={"collection": self.collection_name, "count": count}
            )
            
        except ImportError:
            raise ImportError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    @log_performance
    def store(
        self,
        text: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Store a memory in the system.
        
        Args:
            text: The memory content
            memory_type: Type of memory
            metadata: Additional metadata
            user_id: User ID associated with this memory
            
        Returns:
            Memory ID
        """
        # Generate unique ID
        memory_id = str(uuid.uuid4())
        
        # Convert text to embedding
        try:
            embedding = self.embedding_model.encode(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
        
        # Prepare metadata
        meta = metadata or {}
        meta.update({
            "memory_type": memory_type.value,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id or "default",
        })
        
        # Store in ChromaDB
        try:
            self._collection.add(
                ids=[memory_id],
                embeddings=[embedding.tolist()],
                documents=[text],
                metadatas=[meta]
            )
            
            logger.info(
                f"Stored memory: {text[:50]}...",
                extra={
                    "memory_id": memory_id,
                    "type": memory_type.value,
                    "length": len(text)
                }
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise
    
    @log_performance
    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        time_range: Optional[tuple] = None,
    ) -> List[SearchResult]:
        """
        Search for similar memories.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            memory_type: Filter by memory type
            user_id: Filter by user ID
            time_range: Filter by time range (start, end)
            
        Returns:
            List of search results ranked by similarity
        """
        # Convert query to embedding
        try:
            query_embedding = self.embedding_model.encode(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise
        
        # Build where clause for filtering
        where = {}
        if memory_type:
            where["memory_type"] = memory_type.value
        if user_id:
            where["user_id"] = user_id
        
        # Search ChromaDB
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k,
                where=where if where else None,
            )
            
            # Parse results
            search_results = []
            if results['ids'] and results['ids'][0]:
                for i, memory_id in enumerate(results['ids'][0]):
                    text = results['documents'][0][i]
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if 'distances' in results else 0.0
                    
                    # Convert distance to similarity (ChromaDB uses L2 distance)
                    # For cosine similarity: similarity = 1 - distance
                    similarity = 1.0 - distance
                    
                    # Create Memory object
                    memory = Memory(
                        id=memory_id,
                        content=text,
                        memory_type=MemoryType(metadata.get('memory_type', 'conversation')),
                        timestamp=datetime.fromisoformat(metadata['timestamp']),
                        metadata=metadata,
                    )
                    
                    search_results.append(SearchResult(
                        memory=memory,
                        similarity=similarity,
                        rank=i + 1
                    ))
            
            logger.info(
                f"Found {len(search_results)} memories for query: {query[:50]}...",
                extra={"query": query, "results": len(search_results)}
            )
            
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            raise
    
    def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            Memory object or None if not found
        """
        try:
            result = self._collection.get(ids=[memory_id])
            
            if result['ids']:
                text = result['documents'][0]
                metadata = result['metadatas'][0]
                
                return Memory(
                    id=memory_id,
                    content=text,
                    memory_type=MemoryType(metadata.get('memory_type', 'conversation')),
                    timestamp=datetime.fromisoformat(metadata['timestamp']),
                    metadata=metadata,
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None
    
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            self._collection.delete(ids=[memory_id])
            logger.info(f"Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False
    
    def get_recent(
        self,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
    ) -> List[Memory]:
        """
        Get recent memories.
        
        Args:
            limit: Maximum number of memories to return
            memory_type: Filter by memory type
            user_id: Filter by user ID
            
        Returns:
            List of recent memories
        """
        # Build where clause
        where = {}
        if memory_type:
            where["memory_type"] = memory_type.value
        if user_id:
            where["user_id"] = user_id
        
        try:
            # Get all matching memories
            result = self._collection.get(
                where=where if where else None,
                limit=limit,
            )
            
            memories = []
            if result['ids']:
                for i, memory_id in enumerate(result['ids']):
                    text = result['documents'][i]
                    metadata = result['metadatas'][i]
                    
                    memories.append(Memory(
                        id=memory_id,
                        content=text,
                        memory_type=MemoryType(metadata.get('memory_type', 'conversation')),
                        timestamp=datetime.fromisoformat(metadata['timestamp']),
                        metadata=metadata,
                    ))
            
            # Sort by timestamp (most recent first)
            memories.sort(key=lambda m: m.timestamp, reverse=True)
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []
    
    def count(
        self,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
    ) -> int:
        """
        Count memories matching filters.
        
        Args:
            memory_type: Filter by memory type
            user_id: Filter by user ID
            
        Returns:
            Number of matching memories
        """
        if memory_type is None and user_id is None:
            return self._collection.count()
        
        # Build where clause
        where = {}
        if memory_type:
            where["memory_type"] = memory_type.value
        if user_id:
            where["user_id"] = user_id
        
        try:
            result = self._collection.get(where=where)
            return len(result['ids']) if result['ids'] else 0
        except Exception as e:
            logger.error(f"Failed to count memories: {e}")
            return 0
    
    def clear(self, user_id: Optional[str] = None):
        """
        Clear memories (optionally for specific user).
        
        Args:
            user_id: If provided, only clear memories for this user
        """
        if user_id:
            # Delete specific user's memories
            try:
                result = self._collection.get(where={"user_id": user_id})
                if result['ids']:
                    self._collection.delete(ids=result['ids'])
                    logger.info(f"Cleared {len(result['ids'])} memories for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to clear memories for user {user_id}: {e}")
        else:
            # Clear all memories
            try:
                self._client.delete_collection(self.collection_name)
                self._collection = self._client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Freya's semantic memory"}
                )
                logger.info("Cleared all memories")
            except Exception as e:
                logger.error(f"Failed to clear all memories: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get memory system status."""
        return {
            "total_memories": self.count(),
            "collection": self.collection_name,
            "persist_directory": self.persist_directory,
            "embedding_dimension": self.embedding_model.dimension,
        }
