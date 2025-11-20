"""
Tests for WakeWordAgent - background wake word detection.
"""

import asyncio

import pytest

from freya.agents.wake_word_agent import WakeWordAgent
from freya.core.message_bus import Message, MessageBus, MessagePriority


class MockSTT:
    """Mock STT for testing."""

    def __init__(self):
        self.transcripts = []
        self.current_index = 0

    def set_transcripts(self, transcripts: list[str]):
        """Set sequence of transcripts to return."""
        self.transcripts = transcripts
        self.current_index = 0

    def listen(self) -> str:
        """Return next transcript in sequence."""
        if self.current_index >= len(self.transcripts):
            return ""
        transcript = self.transcripts[self.current_index]
        self.current_index += 1
        return transcript


class MockWakeDetector:
    """Mock lightweight wake detector."""

    def __init__(self):
        self.should_detect = False

    def detect(self) -> bool:
        """Return detection status."""
        return self.should_detect


@pytest.mark.asyncio
async def test_wake_word_detection():
    """Test basic wake word detection."""
    bus = MessageBus()
    stt = MockSTT()
    detector = MockWakeDetector()

    agent = WakeWordAgent(
        agent_id="wake_test",
        bus=bus,
        stt=stt,
        wake_word="Hey, Freya",
        wake_sensitivity=0.75,
        session_window=2.0,
        wake_detector=detector,
    )

    # Collect published messages
    detected_messages = []

    async def collect_wake_detected(message: Message):
        detected_messages.append(message)

    bus.subscribe("wake.detected", collect_wake_detected)

    # Start agent
    await agent.start()

    # Set mock transcripts and detector
    stt.set_transcripts(["Hey, Freya what's the time?"])
    detector.should_detect = True

    # Start listening
    await bus.publish(
        Message(
            topic="wake.start",
            payload={},
            priority=MessagePriority.HIGH,
        )
    )

    # Wait for detection
    await asyncio.sleep(0.3)

    # Verify wake word detected
    assert len(detected_messages) == 1
    msg = detected_messages[0]
    assert msg.topic == "wake.detected"
    assert "what's the time" in msg.payload["transcript"].lower()

    # Stop listening and cleanup
    await bus.publish(
        Message(
            topic="wake.stop",
            payload={},
            priority=MessagePriority.HIGH,
        )
    )

    await asyncio.sleep(0.1)
    await agent.stop()


@pytest.mark.asyncio
async def test_session_window():
    """Test session window continuation (no wake word required)."""
    bus = MessageBus()
    stt = MockSTT()
    detector = MockWakeDetector()

    agent = WakeWordAgent(
        agent_id="wake_session",
        bus=bus,
        stt=stt,
        wake_word="Hey, Freya",
        session_window=3.0,
        wake_detector=detector,
    )

    detected_messages = []

    async def collect_wake(message: Message):
        detected_messages.append(message)

    bus.subscribe("wake.detected", collect_wake)

    await agent.start()

    # Initial wake word
    stt.set_transcripts(
        [
            "Hey, Freya what time is it?",  # Wake word
            "and what's the date?",  # Continuation (no wake word)
        ]
    )
    detector.should_detect = True

    await bus.publish(Message(topic="wake.start", payload={}, priority=MessagePriority.HIGH))

    # Wait for both detections
    await asyncio.sleep(0.5)

    # Verify both messages received
    assert len(detected_messages) == 2

    # First message should have continuation=None or False
    assert detected_messages[0].payload.get("continuation") is not True

    # Second message should have continuation=True
    assert detected_messages[1].payload.get("continuation") is True

    await bus.publish(Message(topic="wake.stop", payload={}, priority=MessagePriority.HIGH))

    await asyncio.sleep(0.1)
    await agent.stop()


@pytest.mark.asyncio
async def test_session_timeout():
    """Test session window expiration."""
    bus = MessageBus()
    stt = MockSTT()
    detector = MockWakeDetector()

    agent = WakeWordAgent(
        agent_id="wake_timeout",
        bus=bus,
        stt=stt,
        wake_word="Hey, Freya",
        session_window=0.2,  # Very short window
        wake_detector=detector,
    )

    timeout_messages = []

    async def collect_timeout(message: Message):
        timeout_messages.append(message)

    bus.subscribe("wake.timeout", collect_timeout)

    await agent.start()

    # Initial wake word
    stt.set_transcripts(
        [
            "Hey, Freya hello",  # Wake word
            "",  # Silence
            "",  # More silence (session expires)
        ]
    )
    detector.should_detect = True

    await bus.publish(Message(topic="wake.start", payload={}, priority=MessagePriority.HIGH))

    # Wait for session to expire
    await asyncio.sleep(0.5)

    # Verify timeout message published
    assert len(timeout_messages) >= 1
    assert timeout_messages[0].topic == "wake.timeout"

    await bus.publish(Message(topic="wake.stop", payload={}, priority=MessagePriority.HIGH))

    await asyncio.sleep(0.1)
    await agent.stop()


@pytest.mark.asyncio
async def test_dynamic_window_update():
    """Test updating session window dynamically."""
    bus = MessageBus()
    stt = MockSTT()
    detector = MockWakeDetector()

    agent = WakeWordAgent(
        agent_id="wake_window",
        bus=bus,
        stt=stt,
        wake_word="Hey, Freya",
        session_window=2.0,
        wake_detector=detector,
    )

    await agent.start()

    # Update session window
    await bus.publish(
        Message(
            topic="wake.set_window",
            payload={"window": 5.0},
            priority=MessagePriority.NORMAL,
        )
    )

    await asyncio.sleep(0.1)

    # Verify window updated
    assert agent._session_window == 5.0

    await agent.stop()


if __name__ == "__main__":
    # Run tests
    print("Running WakeWordAgent tests...")

    print("\n[TEST] Wake word detection...")
    asyncio.run(test_wake_word_detection())
    print("[OK] Wake word detection passed")

    print("\n[TEST] Session window continuation...")
    asyncio.run(test_session_window())
    print("[OK] Session window passed")

    print("\n[TEST] Session timeout...")
    asyncio.run(test_session_timeout())
    print("[OK] Session timeout passed")

    print("\n[TEST] Dynamic window update...")
    asyncio.run(test_dynamic_window_update())
    print("[OK] Dynamic window update passed")

    print("\n[SUCCESS] All WakeWordAgent tests passed!")
