"""
Tests for DialogAgent - LLM conversation management.
"""

import asyncio
from unittest.mock import Mock

import pytest

from freya.agents.dialog_agent import DialogAgent
from freya.context import ConversationContext
from freya.core.message_bus import Message, MessageBus, MessagePriority


class MockOllamaClient:
    """Mock Ollama client for testing."""

    def __init__(self):
        self.responses = []
        self.streaming_responses = []
        self.current_response_index = 0
        self.current_stream_index = 0
        self.last_messages = None
        self.chat_called = False
        self.stream_called = False

    def set_responses(self, responses: list[str]):
        """Set sequence of non-streaming responses."""
        self.responses = responses
        self.current_response_index = 0

    def set_streaming_responses(self, streaming_responses: list[list[str]]):
        """Set sequence of streaming responses (each is list of chunks)."""
        self.streaming_responses = streaming_responses
        self.current_stream_index = 0

    def chat(self, messages: list[dict]) -> str:
        """Return next non-streaming response."""
        self.chat_called = True
        self.last_messages = messages
        if self.current_response_index >= len(self.responses):
            return "I don't have a response configured"
        response = self.responses[self.current_response_index]
        self.current_response_index += 1
        return response

    def chat_stream(self, messages: list[dict]):
        """Yield next streaming response chunks."""
        self.stream_called = True
        self.last_messages = messages
        if self.current_stream_index >= len(self.streaming_responses):
            yield "Default stream chunk"
            return

        for chunk in self.streaming_responses[self.current_stream_index]:
            yield chunk
        self.current_stream_index += 1


@pytest.mark.asyncio
async def test_streaming_response():
    """Test streaming LLM response with chunks."""
    bus = MessageBus()
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="You are Freya", max_history=10)

    agent = DialogAgent(
        agent_id="dialog_test",
        bus=bus,
        ollama_client=ollama,
        context_manager=context,
        default_model="llama3.2:3b",
    )

    # Collect chunks and complete messages
    chunks = []
    complete_messages = []

    async def collect_chunks(message: Message):
        chunks.append(message.payload["text"])

    async def collect_complete(message: Message):
        complete_messages.append(message)

    bus.subscribe("dialog.chunk", collect_chunks)
    bus.subscribe("dialog.complete", collect_complete)

    # Set streaming response
    ollama.set_streaming_responses([["The answer ", "is 42. ", "This is ", "the truth."]])

    await agent.start()

    # Send conversation request
    await bus.publish(
        Message(
            topic="dialog.request",
            payload={"text": "What is the answer?", "stream": True},
            priority=MessagePriority.HIGH,
        )
    )

    # Wait for processing
    await asyncio.sleep(0.3)

    # Verify chunks published
    assert len(chunks) > 0
    assert any("42" in chunk for chunk in chunks)

    # Verify complete message
    assert len(complete_messages) == 1
    complete = complete_messages[0]
    assert "42" in complete.payload["response"]
    assert complete.payload["streaming"] is True
    assert "tokens" in complete.payload
    assert "duration_ms" in complete.payload

    await agent.stop()


@pytest.mark.asyncio
async def test_confusion_escalation():
    """Test model escalation on confusion detection."""
    bus = MessageBus()
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="You are Freya", max_history=10)

    agent = DialogAgent(
        agent_id="dialog_escalate",
        bus=bus,
        ollama_client=ollama,
        context_manager=context,
        default_model="llama3.2:3b",
        reasoning_model="dolphin-mixtral:8x7b",
        enable_escalation=True,
    )

    complete_messages = []

    async def collect_complete(message: Message):
        complete_messages.append(message)

    bus.subscribe("dialog.complete", collect_complete)

    # First response: confusion signal
    # Second response: better answer (after escalation)
    ollama.set_streaming_responses(
        [
            ["I don't know the answer."],  # Confusion
            ["The answer is 42!"],  # After escalation
        ]
    )

    await agent.start()

    await bus.publish(
        Message(
            topic="dialog.request",
            payload={"text": "What is the answer?", "stream": True},
            priority=MessagePriority.HIGH,
        )
    )

    await asyncio.sleep(0.4)

    # Should have escalated and generated second response
    assert len(complete_messages) == 1
    response = complete_messages[0].payload["response"]
    assert "42" in response

    await agent.stop()


@pytest.mark.asyncio
async def test_context_transfer():
    """Test automatic context transfer to long-term memory."""
    bus = MessageBus()
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="You are Freya", max_history=50)

    agent = DialogAgent(
        agent_id="dialog_context",
        bus=bus,
        ollama_client=ollama,
        context_manager=context,
        context_limit=1000,  # Low limit for testing
        transfer_threshold=0.75,
        keep_recent_turns=5,
    )

    memory_stores = []

    async def collect_memory(message: Message):
        memory_stores.append(message)

    bus.subscribe("memory.store", collect_memory)

    ollama.set_streaming_responses([["Response " + str(i)] for i in range(15)])

    await agent.start()

    # Add many turns to exceed context
    for i in range(15):
        context.add_user_message("Question " + str(i) + " " * 50)  # Pad to increase size
        context.add_assistant_message("Response " + str(i) + " " * 50)

    # Trigger context check
    await bus.publish(
        Message(
            topic="dialog.request",
            payload={"text": "Final question", "stream": True},
            priority=MessagePriority.HIGH,
        )
    )

    await asyncio.sleep(0.3)

    # Verify old turns transferred to memory
    assert len(memory_stores) > 0

    await agent.stop()


@pytest.mark.asyncio
async def test_context_injection():
    """Test injecting external context (tool results, memories)."""
    bus = MessageBus()
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="You are Freya", max_history=10)

    agent = DialogAgent(
        agent_id="dialog_inject",
        bus=bus,
        ollama_client=ollama,
        context_manager=context,
    )

    ollama.set_streaming_responses([["Using context: relevant info"]])

    await agent.start()

    # Inject context
    await bus.publish(
        Message(
            topic="dialog.inject_context",
            payload={"context": "Tool result: User's birthday is March 15th"},
            priority=MessagePriority.NORMAL,
        )
    )

    await asyncio.sleep(0.1)

    # Send conversation request
    await bus.publish(
        Message(
            topic="dialog.request",
            payload={"text": "When is my birthday?", "stream": True},
            priority=MessagePriority.HIGH,
        )
    )

    await asyncio.sleep(0.3)

    # Verify context was included in messages
    assert ollama.last_messages is not None
    messages_str = str(ollama.last_messages)
    assert "March 15th" in messages_str

    await agent.stop()


@pytest.mark.asyncio
async def test_clear_context():
    """Test clearing conversation context."""
    bus = MessageBus()
    ollama = MockOllamaClient()
    context = ConversationContext(system_prompt="You are Freya", max_history=10)

    agent = DialogAgent(
        agent_id="dialog_clear",
        bus=bus,
        ollama_client=ollama,
        context_manager=context,
    )

    await agent.start()

    # Add some context
    context.add_user_message("First question")
    context.add_assistant_message("First answer")

    assert len(context._messages) == 2

    # Clear context
    await bus.publish(
        Message(
            topic="dialog.clear_context",
            payload={},
            priority=MessagePriority.NORMAL,
        )
    )

    await asyncio.sleep(0.1)

    # Verify cleared
    assert len(context._messages) == 0

    await agent.stop()


if __name__ == "__main__":
    print("Running DialogAgent tests...")

    print("\n[TEST] Streaming response...")
    asyncio.run(test_streaming_response())
    print("[OK] Streaming response passed")

    print("\n[TEST] Confusion escalation...")
    asyncio.run(test_confusion_escalation())
    print("[OK] Confusion escalation passed")

    print("\n[TEST] Context transfer...")
    asyncio.run(test_context_transfer())
    print("[OK] Context transfer passed")

    print("\n[TEST] Context injection...")
    asyncio.run(test_context_injection())
    print("[OK] Context injection passed")

    print("\n[TEST] Clear context...")
    asyncio.run(test_clear_context())
    print("[OK] Clear context passed")

    print("\n[SUCCESS] All DialogAgent tests passed!")
