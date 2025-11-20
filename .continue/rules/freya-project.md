# Freya Project Rules

## Project Overview

Freya is a voice-first AI assistant running locally with Ollama backend.

**Main Components:**
- `main.py` - Entry point and dependency injection
- `freya/orchestrator.py` (1219 lines) - Core conversation loop, wake word detection, mode switching
- `freya/config.py` - YAML configuration loader with validation
- `freya/memory.py` - Dual memory system (SQLite + semantic search with sentence-transformers)
- `freya/ollama_client.py` - HTTP client for local LLM inference
- `freya/stt.py` - Speech-to-text (Faster Whisper)
- `freya/tts.py` - Text-to-speech (Piper or ElevenLabs)
- `freya/wake.py` - Wake word detection
- `freya/tools/` - Modular tool system (web search, calculator, file ops, datetime, system info)

## Architecture Patterns

- **Config**: Frozen dataclasses for immutability
- **Memory**: Thread-safe SQLite with embeddings for semantic search
- **Tools**: Plugin-based system inheriting from `BaseTool`
- **Error Handling**: Custom exceptions per module (e.g., `OllamaModelNotFoundError`)

## Known Refactoring Needs

1. **orchestrator.py is too large (1219 lines)** - needs splitting into:
   - Wake word detection logic
   - Mode management (voice/text switching)
   - Response handling (TTS/formatting)
   - Core conversation loop

2. **Config override pattern** - Consider using a single apply function instead of multiple `dataclasses.replace()` calls

3. **Dependency injection** - Consider adding a container pattern as dependencies grow

## Coding Standards

- Use type hints for all public functions
- Frozen dataclasses for config/data objects
- Thread safety: Use locks for shared state (see memory.py pattern)
- Logging: Use `get_logger(__name__)` from `freya.logger`
- Testing: Unit tests in `tests/` directory

## Common Tasks

When implementing features:
- New tools go in `freya/tools/` and inherit from `BaseTool`
- Config changes require updating both `config.py` dataclasses and `config/default.yaml`
- Memory operations use the thread-safe lock pattern
- Always handle Ollama connection errors gracefully
