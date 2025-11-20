"""Debug wake word detection."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from freya.config import load_settings
from freya.stt import SpeechToText
from freya.agents.wake_word_agent import WakeWordAgent
from freya.core.message_bus import MessageBus, Message


async def main():
    print("=== Wake Word Debug Test ===\n")

    # Load config
    config = load_settings(Path("config/default.yaml"))
    print(f"Config loaded: {config.wake_word.wake_word}")

    # Create components
    bus = MessageBus()
    await bus.start()
    print("MessageBus started")

    # Create STT
    stt = SpeechToText(
        model=config.stt.model,
        device=config.stt.device,
        compute_type=config.stt.compute_type,
    )
    print(f"STT created: model={config.stt.model}")

    # Create wake word agent
    wake_agent = WakeWordAgent(
        agent_id="wake",
        bus=bus,
        stt=stt,
        wake_word=config.wake_word.wake_word,
        wake_sensitivity=config.wake_word.sensitivity,
        session_window=config.wake_word.session_window,
        channel_id="pc",
    )
    print("WakeWordAgent created")

    # Subscribe to wake.detected
    detections = []

    async def on_wake_detected(msg: Message):
        print(f"\n🎤 WAKE WORD DETECTED!")
        print(f"   Payload: {msg.payload}")
        detections.append(msg)

    bus.subscribe("wake.detected", on_wake_detected)

    # Subscribe to wake.listening
    async def on_listening(msg: Message):
        print(f"📻 Listening status: {msg.payload}")

    bus.subscribe("wake.listening", on_listening)

    # Start agent
    await wake_agent.start()
    print("WakeWordAgent started")

    # Send wake.start
    await bus.publish(
        topic="wake.start",
        payload={},
        sender="test",
    )
    print("\n✅ Sent wake.start message")
    print("\n🎤 Say 'Hey, Freya' now...")
    print("   (Will listen for 30 seconds)")

    # Wait and check
    for i in range(30):
        await asyncio.sleep(1)
        if detections:
            print(f"\n✅ Detection successful after {i+1} seconds!")
            break
    else:
        print("\n❌ No wake word detected in 30 seconds")

    # Cleanup
    await wake_agent.stop()
    await bus.stop()
    print("\nTest complete")


if __name__ == "__main__":
    asyncio.run(main())
