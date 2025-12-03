"""Freya - Voice-enabled AI Assistant."""

__version__ = "0.1.0"

# Lazy imports to avoid circular dependencies and heavy imports
# when only using MCP servers
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

def __getattr__(name):
    """Lazy import of freya components."""
    if name == "Settings":
        from freya.core.config import Settings
        return Settings
    elif name == "ConversationContext":
        from freya.core.context import ConversationContext
        return ConversationContext
    elif name == "get_logger":
        from freya.core.logger import get_logger
        return get_logger
    elif name == "OllamaClient":
        from freya.core.ollama_client import OllamaClient
        return OllamaClient
    elif name == "ChromaMemoryStore":
        from freya.memory import ChromaMemoryStore
        return ChromaMemoryStore
    elif name == "MemoryRecord":
        from freya.memory import MemoryRecord
        return MemoryRecord
    elif name == "PersistentMemoryStore":
        from freya.memory import PersistentMemoryStore
        return PersistentMemoryStore
    elif name == "SpeechToText":
        from freya.voice import SpeechToText
        return SpeechToText
    elif name == "TextToSpeech":
        from freya.voice import TextToSpeech
        return TextToSpeech
    elif name == "WakeWordDetector":
        from freya.voice import WakeWordDetector
        return WakeWordDetector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
