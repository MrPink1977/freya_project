"""
Embedding Model - Converts text to vector embeddings for semantic search.

Uses nomic-embed-text for high-quality embeddings optimized for retrieval.
"""

from typing import List, Union
import numpy as np

from freya.shared.logging.logger import get_logger
from freya.shared.logging.decorators import log_performance


logger = get_logger(__name__)


class NomicEmbedding:
    """
    Nomic embedding model for converting text to vectors.
    
    Features:
    - 768-dimensional embeddings
    - Optimized for semantic search
    - Efficient batching
    - ~500MB VRAM
    """
    
    def __init__(self, model_name: str = "nomic-embed-text"):
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name of the embedding model
        """
        self.model_name = model_name
        self._model = None
        self._dimension = 768  # Nomic-embed-text dimension
        
        logger.info(f"Initializing {model_name} embedding model")
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model."""
        try:
            # Try sentence-transformers first
            from sentence_transformers import SentenceTransformer
            
            # Map model name to sentence-transformers model
            model_map = {
                "nomic-embed-text": "nomic-ai/nomic-embed-text-v1",
                "all-minilm": "sentence-transformers/all-MiniLM-L6-v2",
            }
            
            model_id = model_map.get(self.model_name, self.model_name)
            self._model = SentenceTransformer(model_id)
            self._dimension = self._model.get_sentence_embedding_dimension()
            
            logger.info(
                f"Loaded {self.model_name} (dimension: {self._dimension})",
                extra={"model": model_id, "dimension": self._dimension}
            )
            
        except ImportError:
            # Fallback to Ollama embeddings
            try:
                import ollama
                self._model = "ollama"
                logger.info(f"Using Ollama for {self.model_name} embeddings")
            except ImportError:
                raise ImportError(
                    "No embedding backend available. "
                    "Install sentence-transformers or ollama."
                )
    
    @log_performance
    def encode(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        batch_size: int = 32,
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Convert text(s) to embedding vector(s).
        
        Args:
            texts: Single text or list of texts to embed
            normalize: Whether to normalize vectors (recommended for similarity search)
            batch_size: Batch size for processing multiple texts
            
        Returns:
            Embedding vector(s) as numpy array(s)
        """
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]
        
        try:
            if self._model == "ollama":
                # Use Ollama API
                import ollama
                embeddings = []
                for text in texts:
                    response = ollama.embeddings(
                        model=self.model_name,
                        prompt=text
                    )
                    embeddings.append(np.array(response['embedding']))
                embeddings = np.array(embeddings)
            else:
                # Use sentence-transformers
                embeddings = self._model.encode(
                    texts,
                    batch_size=batch_size,
                    normalize_embeddings=normalize,
                    show_progress_bar=False,
                )
            
            # Ensure numpy array
            if not isinstance(embeddings, np.ndarray):
                embeddings = np.array(embeddings)
            
            # Normalize if requested and not already normalized
            if normalize and self._model != "ollama":
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / (norms + 1e-8)
            
            logger.debug(
                f"Encoded {len(texts)} text(s)",
                extra={"count": len(texts), "dimension": embeddings.shape[1]}
            )
            
            # Return single vector if input was single text
            if is_single:
                return embeddings[0]
            return embeddings
            
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            raise
    
    def similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between -1 and 1 (higher = more similar)
        """
        # Ensure numpy arrays
        if not isinstance(embedding1, np.ndarray):
            embedding1 = np.array(embedding1)
        if not isinstance(embedding2, np.ndarray):
            embedding2 = np.array(embedding2)
        
        # Cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        return dot_product / (norm1 * norm2 + 1e-8)
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension
    
    async def cleanup(self):
        """Clean up model resources."""
        if self._model and self._model != "ollama":
            try:
                del self._model
                self._model = None
                logger.info("Embedding model cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up embedding model: {e}")
