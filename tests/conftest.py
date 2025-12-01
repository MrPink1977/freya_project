"""
Centralized pytest fixtures and mocks for Freya tests.

This file provides shared fixtures that can be used across all test files.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from freya.core.config import Settings


# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config() -> Settings:
    """Provide a test configuration with safe defaults."""
    from freya.core.config import load_settings
    
    config_path = Path("config/default.yaml")
    if not config_path.exists():
        pytest.skip("Config file not found")
    
    config = load_settings(config_path)
    
    # Override with test-safe values
    config.app.interaction_mode = "text"
    config.memory.enabled = False  # Disable memory for faster tests
    
    return config


@pytest.fixture
def minimal_config() -> Settings:
    """Provide a minimal configuration for unit tests."""
    from dataclasses import replace
    from freya.core.config import load_settings
    
    config = load_settings(Path("config/default.yaml"))
    
    # Minimal settings for isolated unit tests
    config = replace(
        config,
        app=replace(config.app, interaction_mode="text"),
        memory=replace(config.memory, enabled=False),
        wake_detector=replace(config.wake_detector, enabled=False),
    )
    
    return config


# ============================================================================
# LLM Client Mocks
# ============================================================================

@pytest.fixture
def mock_ollama_client() -> MagicMock:
    """Provide a mocked OllamaClient for testing."""
    mock = MagicMock()
    
    # Mock generate method
    mock.generate = AsyncMock(return_value={
        "response": "This is a test response from the mocked LLM.",
        "done": True,
    })
    
    # Mock list_models
    mock.list_models = AsyncMock(return_value=[
        {"name": "llama3.2:latest"},
        {"name": "dolphin-mixtral:latest"},
    ])
    
    # Mock pull_model
    mock.pull_model = AsyncMock(return_value=True)
    
    return mock


@pytest.fixture
def mock_streaming_ollama() -> MagicMock:
    """Provide a mocked OllamaClient with streaming responses."""
    mock = MagicMock()
    
    async def fake_stream():
        """Simulate streaming response."""
        chunks = ["Hello", " ", "world", "!"]
        for chunk in chunks:
            yield {"response": chunk, "done": False}
        yield {"response": "", "done": True}
    
    mock.generate_stream = fake_stream
    mock.generate = AsyncMock(return_value={
        "response": "Hello world!",
        "done": True,
    })
    
    return mock


# ============================================================================
# Speech Mocks (STT/TTS)
# ============================================================================

@pytest.fixture
def mock_stt() -> MagicMock:
    """Provide a mocked SpeechToText service."""
    mock = MagicMock()
    
    # Mock transcribe method
    mock.transcribe = AsyncMock(return_value="This is test transcription")
    
    # Mock listen method
    mock.listen = AsyncMock(return_value="User said something")
    
    return mock


@pytest.fixture
def mock_tts() -> MagicMock:
    """Provide a mocked TextToSpeech service."""
    mock = MagicMock()
    
    # Mock speak method
    mock.speak = AsyncMock(return_value=True)
    
    # Mock generate_audio
    mock.generate_audio = MagicMock(return_value=b"fake_audio_data")
    
    return mock


@pytest.fixture
def mock_wake_detector() -> MagicMock:
    """Provide a mocked wake word detector."""
    mock = MagicMock()
    
    # Mock detect method
    mock.detect = AsyncMock(return_value=True)
    
    # Mock is_wake_word
    mock.is_wake_word = MagicMock(return_value=False)
    
    return mock


# ============================================================================
# Memory Mocks
# ============================================================================

@pytest.fixture
def mock_memory() -> MagicMock:
    """Provide a mocked Memory service."""
    mock = MagicMock()
    
    # Mock store method
    mock.store = AsyncMock(return_value=True)
    
    # Mock retrieve method
    mock.retrieve = AsyncMock(return_value=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ])
    
    # Mock search method
    mock.search = AsyncMock(return_value=[
        {"content": "Previous conversation", "similarity": 0.95}
    ])
    
    return mock


# ============================================================================
# Agent Mocks
# ============================================================================

@pytest.fixture
def mock_message_bus() -> MagicMock:
    """Provide a mocked MessageBus for agent communication."""
    mock = MagicMock()
    
    # Mock publish method
    mock.publish = AsyncMock(return_value=None)
    
    # Mock subscribe method
    mock.subscribe = MagicMock(return_value=None)
    
    # Mock request method
    mock.request = AsyncMock(return_value={"status": "ok"})
    
    return mock


@pytest.fixture
def mock_base_agent() -> MagicMock:
    """Provide a mocked BaseAgent."""
    mock = MagicMock()
    
    # Mock lifecycle methods
    mock.start = AsyncMock(return_value=None)
    mock.stop = AsyncMock(return_value=None)
    mock.handle_message = AsyncMock(return_value=None)
    
    # Agent properties
    mock.agent_id = "test_agent"
    mock.is_running = True
    
    return mock


# ============================================================================
# Tool Mocks
# ============================================================================

@pytest.fixture
def mock_tool_manager() -> MagicMock:
    """Provide a mocked ToolManager."""
    mock = MagicMock()
    
    # Mock execute_tool method
    mock.execute_tool = MagicMock(return_value=MagicMock(
        success=True,
        output="Tool executed successfully",
        error=None
    ))
    
    # Mock list_tools
    mock.list_tools = MagicMock(return_value=[
        MagicMock(name="calculator", description="Math operations"),
        MagicMock(name="get_current_time", description="Get current time"),
    ])
    
    return mock


# ============================================================================
# Async Helpers
# ============================================================================

@pytest.fixture
async def async_cleanup():
    """Provide cleanup for async tests."""
    tasks = []
    
    def add_task(task):
        tasks.append(task)
    
    yield add_task
    
    # Cleanup all tasks
    for task in tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_conversation():
    """Provide sample conversation data."""
    return [
        {"role": "user", "content": "What time is it?"},
        {"role": "assistant", "content": "It's 3:45 PM."},
        {"role": "user", "content": "Calculate 25 * 4"},
        {"role": "assistant", "content": "The result is 100."},
    ]


@pytest.fixture
def sample_tools():
    """Provide sample tool definitions."""
    return [
        {
            "name": "calculator",
            "description": "Perform mathematical calculations",
            "parameters": {"expression": "string"},
        },
        {
            "name": "get_current_time",
            "description": "Get the current time",
            "parameters": {"timezone": "string", "format": "string"},
        },
    ]


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Provide a temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_config_file(tmp_path, test_config):
    """Create a temporary config file for testing."""
    import yaml
    
    config_file = tmp_path / "test_config.yaml"
    
    # Write minimal config
    config_data = {
        "app": {"interaction_mode": "text"},
        "ollama": {"host": "http://localhost:11434", "model": "llama3.2:latest"},
        "memory": {"enabled": False},
    }
    
    config_file.write_text(yaml.dump(config_data))
    return config_file
