"""Freya - Voice-enabled AI Assistant."""

__version__ = "0.1.0"

# Re-export commonly used components for convenience
from freya.core.config import Settings
from freya.core.context import ConversationContext
from freya.core.logger import get_logger
from freya.core.ollama_client import OllamaClient
from freya.memory import ChromaMemoryStore, MemoryRecord, PersistentMemoryStore
from freya.voice import SpeechToText, TextToSpeech, WakeWordDetector

__all__ = [
    "__version__",
    "Settings",
    "ConversationContext",
    "get_logger",
    "OllamaClient",
    "ChromaMemoryStore",
    "MemoryRecord",
    "PersistentMemoryStore",
    "SpeechToText",
    "TextToSpeech",
    "WakeWordDetector",
]
