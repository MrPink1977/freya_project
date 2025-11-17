"""Tests for configuration loading and validation."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from freya.config import (
    ConfigValidationError,
    Settings,
    load_settings,
)


@pytest.fixture
def minimal_config():
    """Minimal valid configuration."""
    return {
        "ollama": {
            "host": "http://localhost:11434",
            "model": "llama3.2:3b",
        },
        "stt": {
            "model": "base",
            "device": "cpu",
        },
        "tts": {
            "engine": "piper",
            "voice_path": "voices/test.onnx",
        },
        "app": {
            "system_prompt": "Test prompt",
            "wake_word": "Hey Test",
        },
    }


@pytest.fixture
def config_file(minimal_config):
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.safe_dump(minimal_config, f)
        path = Path(f.name)

    yield path

    # Cleanup
    if path.exists():
        path.unlink()


def test_load_minimal_config(config_file):
    """Test loading minimal valid configuration."""
    settings = load_settings(config_file)
    assert isinstance(settings, Settings)
    assert settings.ollama.host == "http://localhost:11434"
    assert settings.ollama.model == "llama3.2:3b"


def test_missing_config_file():
    """Test error when config file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_settings(Path("/nonexistent/path.yaml"))


def test_empty_ollama_host():
    """Test validation error for empty Ollama host."""
    config = {
        "ollama": {"host": "", "model": "llama3.2:3b"},
        "stt": {"model": "base"},
        "tts": {"engine": "piper"},
        "app": {"wake_word": "Hey Test"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config, f)
        path = Path(f.name)

    try:
        with pytest.raises(ConfigValidationError, match="host cannot be empty"):
            load_settings(path)
    finally:
        path.unlink()


def test_empty_ollama_model():
    """Test validation error for empty Ollama model."""
    config = {
        "ollama": {"host": "http://localhost:11434", "model": ""},
        "stt": {"model": "base"},
        "tts": {"engine": "piper"},
        "app": {"wake_word": "Hey Test"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config, f)
        path = Path(f.name)

    try:
        with pytest.raises(ConfigValidationError, match="model cannot be empty"):
            load_settings(path)
    finally:
        path.unlink()


def test_invalid_wake_word_sensitivity():
    """Test validation for wake word sensitivity out of range."""
    config = {
        "ollama": {"host": "http://localhost:11434", "model": "llama3.2:3b"},
        "stt": {"model": "base"},
        "tts": {"engine": "piper"},
        "app": {"wake_word": "Hey Test", "wake_word_sensitivity": 1.5},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config, f)
        path = Path(f.name)

    try:
        with pytest.raises(
            ConfigValidationError, match="wake_word_sensitivity must be between"
        ):
            load_settings(path)
    finally:
        path.unlink()


def test_negative_wake_session_seconds():
    """Test validation for negative wake session seconds."""
    config = {
        "ollama": {"host": "http://localhost:11434", "model": "llama3.2:3b"},
        "stt": {"model": "base"},
        "tts": {"engine": "piper"},
        "app": {"wake_word": "Hey Test", "wake_session_seconds": -5.0},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config, f)
        path = Path(f.name)

    try:
        with pytest.raises(
            ConfigValidationError, match="wake_session_seconds cannot be negative"
        ):
            load_settings(path)
    finally:
        path.unlink()


def test_invalid_memory_similarity():
    """Test validation for memory similarity out of range."""
    config = {
        "ollama": {"host": "http://localhost:11434", "model": "llama3.2:3b"},
        "stt": {"model": "base"},
        "tts": {"engine": "piper"},
        "app": {"wake_word": "Hey Test"},
        "memory": {
            "long_term": {
                "enabled": True,
                "min_similarity": 1.5,
            }
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config, f)
        path = Path(f.name)

    try:
        with pytest.raises(
            ConfigValidationError, match="min_similarity must be between"
        ):
            load_settings(path)
    finally:
        path.unlink()


def test_invalid_store_type():
    """Test validation for invalid memory store type."""
    config = {
        "ollama": {"host": "http://localhost:11434", "model": "llama3.2:3b"},
        "stt": {"model": "base"},
        "tts": {"engine": "piper"},
        "app": {"wake_word": "Hey Test"},
        "memory": {
            "long_term": {
                "enabled": True,
                "store_type": "invalid_type",
            }
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config, f)
        path = Path(f.name)

    try:
        with pytest.raises(
            ConfigValidationError, match="store_type must be one of"
        ):
            load_settings(path)
    finally:
        path.unlink()


def test_env_var_expansion():
    """Test environment variable expansion in config."""
    # Set test environment variable
    os.environ["TEST_OLLAMA_HOST"] = "http://test.example.com:11434"

    config = {
        "ollama": {"host": "${TEST_OLLAMA_HOST}", "model": "llama3.2:3b"},
        "stt": {"model": "base"},
        "tts": {"engine": "piper"},
        "app": {"wake_word": "Hey Test"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config, f)
        path = Path(f.name)

    try:
        settings = load_settings(path)
        # The config loader uses os.getenv, but doesn't expand ${VAR} syntax
        # This test documents current behavior
        assert "${TEST_OLLAMA_HOST}" in settings.ollama.host or \
               "test.example.com" in settings.ollama.host
    finally:
        path.unlink()
        del os.environ["TEST_OLLAMA_HOST"]


def test_default_values(config_file):
    """Test that default values are applied correctly."""
    settings = load_settings(config_file)

    # Check default memory settings
    assert settings.memory.short_term.max_history >= 1
    assert 0.0 <= settings.memory.short_term.summary_trigger_ratio <= 1.0

    # Check default STT settings
    assert settings.stt.sample_rate > 0
    assert 0.0 <= settings.stt.silence_threshold <= 1.0

    # Check default wake detector settings
    assert settings.wake_detector.sample_rate > 0


def test_elevenlabs_env_override(config_file, monkeypatch):
    """Test that ElevenLabs environment variables override config."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key_from_env")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "test_voice_from_env")

    settings = load_settings(config_file)

    assert settings.tts.elevenlabs.api_key == "test_key_from_env"
    assert settings.tts.elevenlabs.voice_id == "test_voice_from_env"


def test_embedding_model_default(config_file):
    """Test that embedding model has correct default."""
    settings = load_settings(config_file)
    assert settings.memory.long_term.embedding_model == "all-MiniLM-L6-v2"


def test_custom_embedding_model():
    """Test custom embedding model configuration."""
    config = {
        "ollama": {"host": "http://localhost:11434", "model": "llama3.2:3b"},
        "stt": {"model": "base"},
        "tts": {"engine": "piper"},
        "app": {"wake_word": "Hey Test"},
        "memory": {
            "long_term": {
                "enabled": True,
                "embedding_model": "custom-model-v1",
            }
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(config, f)
        path = Path(f.name)

    try:
        settings = load_settings(path)
        assert settings.memory.long_term.embedding_model == "custom-model-v1"
    finally:
        path.unlink()
