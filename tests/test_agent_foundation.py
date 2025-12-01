"""
Test MessageBus and BaseAgent foundation.

Run with: python -m pytest tests/test_agent_foundation.py -v
Or: python tests/test_agent_foundation.py
"""

import asyncio

from freya.agents import AgentCapability, BaseAgent
from freya.core import Message, MessageBus, MessagePriority


class TestAgent(BaseAgent):
    """Simple test agent for verification."""

    def __init__(self, agent_id: str, bus: MessageBus) -> None:
        super().__init__(agent_id, bus)
        self.messages_received = []

    async def initialize(self) -> None:
        """Initialize test agent."""
        self.logger.info(f"Initializing {self.agent_id}")

    def get_capabilities(self) -> list[AgentCapability]:
        """Return test capabilities."""
        return [
            AgentCapability(
                name="test_handler",
                description="Handles test messages",
                input_topics=["test.message"],
                output_topics=["test.response"],
            )
        ]

    async def process_message(self, message: Message) -> None:
        """Process test message."""
        self.messages_received.append(message)
        self.logger.info(f"Received: {message.topic} - {message.payload}")

        # Echo back
        await self.publish(
            topic="test.response",
            payload={"echo": message.payload, "from": self.agent_id},
            correlation_id=message.correlation_id,
        )


async def test_message_bus():
    """Test basic message bus functionality."""
    print("\n=== Testing MessageBus ===")

    bus = MessageBus()
    await bus.start()

    messages_received = []

    async def test_handler(message: Message) -> None:
        messages_received.append(message)
        print(f"Handler received: {message.topic} - {message.payload}")

    # Subscribe and publish
    bus.subscribe("test.topic", test_handler)
    await bus.publish(topic="test.topic", payload={"data": "hello"}, sender="test_sender")

    # Give dispatch loop time to process
    await asyncio.sleep(0.2)

    assert len(messages_received) == 1
    assert messages_received[0].topic == "test.topic"
    assert messages_received[0].payload["data"] == "hello"

    await bus.stop()
    print("✅ MessageBus test passed")


async def test_base_agent():
    """Test BaseAgent functionality."""
    print("\n=== Testing BaseAgent ===")

    bus = MessageBus()
    await bus.start()

    # Create test agent
    agent = TestAgent("test_agent_1", bus)
    await agent.start()

    # Check agent status
    status = agent.get_status()
    print(f"Agent status: {status}")
    assert status["state"] == "ready"

    # Publish message to agent
    await bus.publish(
        topic="test.message",
        payload={"command": "echo", "data": "test data"},
        sender="tester",
    )

    # Wait for processing
    await asyncio.sleep(0.2)

    # Verify agent received message
    assert len(agent.messages_received) == 1
    assert agent.messages_received[0].payload["command"] == "echo"

    # Check message history
    history = bus.get_history()
    print(f"Message history ({len(history)} messages):")
    for msg in history[-3:]:
        print(f"  {msg.topic}: {msg.payload}")

    await agent.stop()
    await bus.stop()

    print("✅ BaseAgent test passed")


async def test_agent_communication():
    """Test two agents communicating."""
    print("\n=== Testing Agent Communication ===")

    bus = MessageBus()
    await bus.start()

    # Create two agents
    agent1 = TestAgent("agent_1", bus)
    agent2 = TestAgent("agent_2", bus)

    await agent1.start()
    await agent2.start()

    # Both subscribe to test.message
    # Agent1 publishes to test.response (via process_message)
    # Let's have agent2 also subscribe to test.response
    response_received = []

    async def response_handler(message: Message) -> None:
        response_received.append(message)
        print(f"Response: {message.payload}")

    bus.subscribe("test.response", response_handler)

    # Trigger communication
    await bus.publish(
        topic="test.message",
        payload={"ping": "hello agents"},
        sender="orchestrator",
        correlation_id="test-123",
    )

    await asyncio.sleep(0.3)

    # Both agents should have received the message
    assert len(agent1.messages_received) == 1
    assert len(agent2.messages_received) == 1

    # Should have 2 responses (one from each agent)
    assert len(response_received) == 2

    await agent1.stop()
    await agent2.stop()
    await bus.stop()

    print("✅ Agent communication test passed")


async def test_priority_messages():
    """Test message priority handling."""
    print("\n=== Testing Message Priority ===")

    bus = MessageBus()
    await bus.start()

    received_order = []

    async def priority_handler(message: Message) -> None:
        received_order.append(message.payload["order"])

    bus.subscribe("priority.test", priority_handler)

    # Publish in reverse priority order
    await bus.publish("priority.test", {"order": 1}, "test", priority=MessagePriority.LOW)
    await bus.publish("priority.test", {"order": 2}, "test", priority=MessagePriority.NORMAL)
    await bus.publish("priority.test", {"order": 3}, "test", priority=MessagePriority.HIGH)
    await bus.publish("priority.test", {"order": 4}, "test", priority=MessagePriority.CRITICAL)

    await asyncio.sleep(0.2)

    # Should be processed in priority order: CRITICAL, HIGH, NORMAL, LOW
    print(f"Processing order: {received_order}")
    assert received_order == [4, 3, 2, 1]

    await bus.stop()
    print("✅ Priority test passed")


async def main():
    """Run all tests."""
    print("🚀 Starting Agent Foundation Tests")
    print("=" * 50)

    try:
        await test_message_bus()
        await test_base_agent()
        await test_agent_communication()
        await test_priority_messages()

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)

    except Exception as exc:
        print(f"\n❌ Test failed: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
