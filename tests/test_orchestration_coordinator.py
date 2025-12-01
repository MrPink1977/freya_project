"""
Tests for OrchestrationCoordinator - agent orchestration.
"""

import asyncio

import pytest

from freya.core.context import ConversationContext
from freya.coordination.orchestration_coordinator import OrchestrationCoordinator
from freya.memory.memory_store import ChromaMemoryStore
from freya.tools import ToolManager


class MockSTT:
    """Mock STT."""

    def listen(self) -> str:
        return ""


class MockTTS:
    """Mock TTS."""

    def __init__(self):
        self.spoken = []

    def speak(self, text: str):
        self.spoken.append(text)


class MockOllamaClient:
    """Mock Ollama."""

    def __init__(self):
        self.responses = ["Test response"]
        self.index = 0

    def chat(self, messages):
        return self.responses[0]

    def chat_stream(self, messages):
        for char in self.responses[0]:
            yield char


@pytest.mark.asyncio
async def test_coordinator_initialization():
    """Test coordinator can initialize all agents."""
    # Create mocks
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="Test", max_history=10)
    stt = MockSTT()
    tts = MockTTS()
    memory = ChromaMemoryStore(db_path=":memory:")
    tools = ToolManager()

    coordinator = OrchestrationCoordinator(
        ollama_client=ollama,
        context=context,
        stt=stt,
        tts=tts,
        memory_store=memory,
        tool_manager=tools,
        interaction_mode="text",
    )

    # Verify agents created
    assert coordinator._tool_agent is not None
    assert coordinator._memory_agent is not None
    assert coordinator._wake_agent is not None
    assert coordinator._dialog_agent is not None
    assert len(coordinator._agents) == 4


@pytest.mark.asyncio
async def test_coordinator_agent_lifecycle():
    """Test coordinator starts and stops agents."""
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="Test", max_history=10)
    stt = MockSTT()
    tts = MockTTS()
    memory = ChromaMemoryStore(db_path=":memory:")
    tools = ToolManager()

    coordinator = OrchestrationCoordinator(
        ollama_client=ollama,
        context=context,
        stt=stt,
        tts=tts,
        memory_store=memory,
        tool_manager=tools,
        interaction_mode="text",
    )

    # Start agents
    await coordinator._start_agents()

    # Verify all agents running
    for agent in coordinator._agents:
        assert agent._state.name == "RUNNING"

    # Stop agents
    await coordinator._stop_agents()

    # Verify all agents stopped
    for agent in coordinator._agents:
        assert agent._state.name == "STOPPED"


@pytest.mark.asyncio
async def test_coordinator_event_wiring():
    """Test coordinator subscribes to key events."""
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="Test", max_history=10)
    stt = MockSTT()
    tts = MockTTS()
    memory = ChromaMemoryStore(db_path=":memory:")
    tools = ToolManager()

    coordinator = OrchestrationCoordinator(
        ollama_client=ollama,
        context=context,
        stt=stt,
        tts=tts,
        memory_store=memory,
        tool_manager=tools,
        interaction_mode="text",
    )

    await coordinator._start_agents()
    await coordinator._subscribe_to_events()

    # Verify subscriptions exist
    assert len(coordinator.bus._subscribers["wake.detected"]) > 0
    assert len(coordinator.bus._subscribers["dialog.chunk"]) > 0
    assert len(coordinator.bus._subscribers["dialog.complete"]) > 0

    await coordinator._stop_agents()


@pytest.mark.asyncio
async def test_coordinator_memory_query():
    """Test coordinator can query memory."""
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="Test", max_history=10)
    stt = MockSTT()
    tts = MockTTS()
    memory = ChromaMemoryStore(db_path=":memory:")
    tools = ToolManager()

    coordinator = OrchestrationCoordinator(
        ollama_client=ollama,
        context=context,
        stt=stt,
        tts=tts,
        memory_store=memory,
        tool_manager=tools,
        interaction_mode="text",
    )

    await coordinator._start_agents()
    await coordinator._subscribe_to_events()

    # Store a memory
    memory.store_memory("User likes pizza", role="user", importance=2)

    # Query memory
    result = await coordinator._query_relevant_memories("favorite food")

    # Should find the memory
    assert "pizza" in result.lower()

    await coordinator._stop_agents()


if __name__ == "__main__":
    print("Running OrchestrationCoordinator tests...")

    print("\n[TEST] Coordinator initialization...")
    asyncio.run(test_coordinator_initialization())
    print("[OK] Initialization passed")

    print("\n[TEST] Agent lifecycle...")
    asyncio.run(test_coordinator_agent_lifecycle())
    print("[OK] Lifecycle passed")

    print("\n[TEST] Event wiring...")
    asyncio.run(test_coordinator_event_wiring())
    print("[OK] Event wiring passed")

    print("\n[TEST] Memory query...")
    asyncio.run(test_coordinator_memory_query())
    print("[OK] Memory query passed")

    print("\n[SUCCESS] All coordinator tests passed!")
