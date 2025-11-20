"""
Integration test for agent architecture.

Tests the complete system end-to-end with all agents working together.
"""

import asyncio
import time

from freya.agents.dialog_agent import DialogAgent
from freya.agents.memory_agent import MemoryAgent
from freya.agents.tool_executor_agent import ToolExecutorAgent
from freya.agents.wake_word_agent import WakeWordAgent
from freya.context import ConversationContext
from freya.core.message_bus import Message, MessageBus, MessagePriority
from freya.memory import ChromaMemoryStore
from freya.tools import ToolManager


class MockOllamaClient:
    """Mock Ollama client for integration testing."""

    def __init__(self):
        self.call_count = 0
        self.responses = {
            "what time is it": "The current time is 3:42 PM.",
            "what's 2 plus 2": "2 plus 2 equals 4.",
            "my name is john": "Nice to meet you, John! I'll remember that.",
        }

    def chat(self, messages):
        self.call_count += 1
        # Extract user message
        user_msg = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_msg = msg.get("content", "").lower()

        # Return appropriate response
        for key, response in self.responses.items():
            if key in user_msg:
                return response

        return "I understand. How can I help you?"

    def chat_stream(self, messages):
        """Stream response character by character."""
        response = self.chat(messages)
        for char in response:
            yield char
            time.sleep(0.001)  # Simulate streaming delay


class MockSTT:
    """Mock STT for testing."""

    def listen(self):
        return ""


class MockWakeDetector:
    """Mock wake detector."""

    def detect(self):
        return True


async def test_full_integration():
    """Test complete agent system integration."""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST: Full Agent Architecture")
    print("=" * 60 + "\n")

    # Create infrastructure
    bus = MessageBus()
    memory_store = ChromaMemoryStore(db_path=":memory:")
    tool_manager = ToolManager()
    context = ConversationContext(system_prompt="You are Freya", max_history=10)
    ollama = MockOllamaClient()
    stt = MockSTT()
    wake_detector = MockWakeDetector()

    # Create agents
    print("[1/5] Creating agents...")
    tool_agent = ToolExecutorAgent("tool_executor", bus, tool_manager)
    memory_agent = MemoryAgent("memory", bus, memory_store, auto_extract_facts=True)
    wake_agent = WakeWordAgent("wake", bus, stt, wake_detector=wake_detector)
    dialog_agent = DialogAgent(
        "dialog",
        bus,
        ollama,
        context,
        default_model="llama3.2:3b",
        enable_escalation=False,
    )
    agents = [tool_agent, memory_agent, wake_agent, dialog_agent]
    print("   ✓ All agents created\n")

    # Start agents
    print("[2/5] Starting agents...")
    for agent in agents:
        await agent.start()
    print("   ✓ All agents started\n")

    # Test 1: Memory storage and retrieval
    print("[3/5] Test: Memory storage and retrieval")
    test_memory_passed = False

    # Store a memory
    await bus.publish(
        Message(
            topic="memory.store",
            payload={"content": "User likes pizza", "role": "user", "importance": 2},
            priority=MessagePriority.NORMAL,
        )
    )
    await asyncio.sleep(0.2)

    # Query memory
    query_results = []

    async def collect_memory_results(msg: Message):
        query_results.append(msg.payload.get("results", []))

    bus.subscribe("memory.results", collect_memory_results)

    await bus.publish(
        Message(
            topic="memory.query",
            payload={"query": "favorite food", "limit": 3},
            priority=MessagePriority.NORMAL,
            correlation_id="test_memory_query",
        )
    )

    await asyncio.sleep(0.3)

    if query_results and len(query_results[0]) > 0:
        result_content = query_results[0][0].get("content", "").lower()
        if "pizza" in result_content:
            test_memory_passed = True
            print("   ✓ Memory storage and retrieval working")
        else:
            print("   ✗ Memory retrieval failed - content not found")
    else:
        print("   ✗ Memory retrieval failed - no results")
    print()

    # Test 2: Dialog agent with streaming
    print("[4/5] Test: Dialog agent streaming")
    test_dialog_passed = False
    dialog_chunks = []
    dialog_complete = []

    async def collect_chunks(msg: Message):
        dialog_chunks.append(msg.payload.get("text", ""))

    async def collect_complete(msg: Message):
        dialog_complete.append(msg.payload)

    bus.subscribe("dialog.chunk", collect_chunks)
    bus.subscribe("dialog.complete", collect_complete)

    await bus.publish(
        Message(
            topic="dialog.request",
            payload={"text": "What's 2 plus 2?", "stream": True},
            priority=MessagePriority.HIGH,
        )
    )

    await asyncio.sleep(0.5)

    if dialog_chunks and dialog_complete:
        full_response = "".join(dialog_chunks)
        if "4" in full_response:
            test_dialog_passed = True
            print(f"   ✓ Dialog streaming working (received {len(dialog_chunks)} chunks)")
            print(f"   Response: {dialog_complete[0]['response']}")
        else:
            print("   ✗ Dialog failed - incorrect response")
    else:
        print("   ✗ Dialog failed - no chunks or complete message")
    print()

    # Test 3: Fact extraction
    print("[5/5] Test: Automatic fact extraction")
    test_facts_passed = False

    await bus.publish(
        Message(
            topic="memory.store",
            payload={"content": "My name is Alice", "role": "user", "importance": 1},
            priority=MessagePriority.NORMAL,
        )
    )

    await asyncio.sleep(0.3)

    # Query for the fact
    fact_results = []

    async def collect_fact_results(msg: Message):
        fact_results.append(msg.payload.get("results", []))

    bus.subscribe("memory.fact.results", collect_fact_results)

    await bus.publish(
        Message(
            topic="memory.fact.query",
            payload={"query": "name", "category": "name", "limit": 3},
            priority=MessagePriority.NORMAL,
        )
    )

    await asyncio.sleep(0.3)

    if fact_results and len(fact_results[0]) > 0:
        fact_value = fact_results[0][0].get("value", "")
        if "Alice" in fact_value:
            test_facts_passed = True
            print("   ✓ Fact extraction working")
            print(f"   Extracted: name = {fact_value}")
        else:
            print(f"   ✗ Fact extraction failed - got: {fact_value}")
    else:
        print("   ✗ Fact extraction failed - no facts stored")
    print()

    # Stop agents
    print("Stopping agents...")
    for agent in agents:
        await agent.stop()
    print("   ✓ All agents stopped\n")

    # Summary
    print("=" * 60)
    print("TEST RESULTS:")
    print("=" * 60)
    print(f"Memory Storage/Retrieval:  {'✓ PASS' if test_memory_passed else '✗ FAIL'}")
    print(f"Dialog Streaming:          {'✓ PASS' if test_dialog_passed else '✗ FAIL'}")
    print(f"Fact Extraction:           {'✓ PASS' if test_facts_passed else '✗ FAIL'}")
    print("=" * 60)

    all_passed = test_memory_passed and test_dialog_passed and test_facts_passed

    if all_passed:
        print("\n✓ ALL TESTS PASSED - Agent architecture ready for merge!\n")
    else:
        print("\n✗ SOME TESTS FAILED - Review before merging\n")

    return all_passed


async def test_coordinator_integration():
    """Test coordinator with agents."""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST: Coordinator")
    print("=" * 60 + "\n")

    from freya.coordination.orchestration_coordinator import OrchestrationCoordinator

    # Create components
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="You are Freya", max_history=10)
    stt = MockSTT()

    class MockTTS:
        def __init__(self):
            self.spoken = []

        def speak(self, text):
            self.spoken.append(text)

    tts = MockTTS()
    memory = ChromaMemoryStore(db_path=":memory:")
    tools = ToolManager()

    print("[1/3] Creating coordinator...")
    coordinator = OrchestrationCoordinator(
        ollama_client=ollama,
        context=context,
        stt=stt,
        tts=tts,
        memory_store=memory,
        tool_manager=tools,
        interaction_mode="text",
    )
    print("   ✓ Coordinator created\n")

    print("[2/3] Starting agents...")
    await coordinator._start_agents()
    await coordinator._subscribe_to_events()
    print("   ✓ Agents started and events subscribed\n")

    print("[3/3] Test: User input processing")
    test_passed = False

    # Simulate user input
    await coordinator._handle_user_input("What time is it?")

    # Wait for processing
    await asyncio.sleep(0.5)

    # Check if TTS was called (in voice mode it would speak)
    # In text mode, chunks are printed directly
    if ollama.call_count > 0:
        test_passed = True
        print(f"   ✓ Input processed (LLM called {ollama.call_count} times)")
    else:
        print("   ✗ Input processing failed")
    print()

    print("Stopping coordinator...")
    await coordinator._stop_agents()
    print("   ✓ Coordinator stopped\n")

    print("=" * 60)
    print(f"Coordinator Test:  {'✓ PASS' if test_passed else '✗ FAIL'}")
    print("=" * 60 + "\n")

    return test_passed


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print(" " * 15 + "FREYA AGENT ARCHITECTURE")
    print(" " * 15 + "INTEGRATION TEST SUITE")
    print("=" * 70)

    # Run tests
    agents_passed = await test_full_integration()
    coordinator_passed = await test_coordinator_integration()

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Agent System:       {'✓ PASS' if agents_passed else '✗ FAIL'}")
    print(f"Coordinator:        {'✓ PASS' if coordinator_passed else '✗ FAIL'}")
    print("=" * 70)

    if agents_passed and coordinator_passed:
        print("\n✓✓✓ ALL INTEGRATION TESTS PASSED ✓✓✓")
        print("\nAgent architecture is ready to merge to main!")
        print("\nNext steps:")
        print("  1. git checkout main")
        print("  2. git merge feature/agent-architecture")
        print("  3. git push origin main")
        return 0
    else:
        print("\n✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("\nReview failures before merging.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
