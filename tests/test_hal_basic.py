"""Basic tests for Hardware Abstraction Layer (HAL)."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import HAL modules directly (avoid importing full freya package)
from freya.hal.factory import (
    create_audio,
    create_iot,
    create_memory,
    create_vision,
)
from freya.hal.interfaces import TTSEngine, DeviceCommand


def test_mock_vision():
    """Test mock vision driver."""
    print("\n=== Testing Mock Vision Driver ===")

    vision = create_vision(driver="mock", behavior="normal")

    # Test capture
    image = vision.capture(correlation_id="test-001")
    print(f"✓ Captured image: {image.width}x{image.height} from {image.source}")

    # Test face detection
    faces = vision.detect_faces(image, correlation_id="test-002")
    print(f"✓ Detected {len(faces)} face(s)")
    for face in faces:
        print(f"  - {face.name} (confidence: {face.confidence:.2f})")

    # Test health check
    health = vision.health_check(correlation_id="test-003")
    print(f"✓ Health check: {health.status} (healthy={health.is_healthy})")


async def test_mock_memory():
    """Test mock memory driver."""
    print("\n=== Testing Mock Memory Driver ===")

    memory = create_memory(driver="mock", behavior="normal")

    # Test store
    mem1 = await memory.store(
        content="The user likes Python programming",
        memory_type="fact",
        correlation_id="test-004",
    )
    print(f"✓ Stored memory: {mem1.id}")

    mem2 = await memory.store(
        content="The user asked about machine learning",
        memory_type="conversation",
        correlation_id="test-005",
    )
    print(f"✓ Stored memory: {mem2.id}")

    # Test retrieve
    results = await memory.retrieve(
        query="Python programming",
        top_k=5,
        correlation_id="test-006",
    )
    print(f"✓ Retrieved {len(results)} result(s)")
    for result in results:
        print(f"  - {result.memory.content[:50]}... (score: {result.score:.2f})")

    # Test health check
    health = memory.health_check(correlation_id="test-007")
    print(f"✓ Health check: {health.status} (healthy={health.is_healthy})")


def test_mock_audio():
    """Test mock audio driver."""
    print("\n=== Testing Mock Audio Driver ===")

    audio = create_audio(driver="mock", behavior="normal")

    # Test listen
    audio_bytes = audio.listen(duration_sec=2.0, correlation_id="test-008")
    print(f"✓ Captured {len(audio_bytes)} bytes of audio")

    # Test transcribe
    transcription = audio.transcribe(audio_bytes, correlation_id="test-009")
    print(f"✓ Transcription: '{transcription.text}' (confidence: {transcription.confidence:.2f})")

    # Test speak
    audio.speak("Hello from Freya HAL", engine=TTSEngine.PIPER, correlation_id="test-010")
    print(f"✓ Speech synthesis completed")

    # Test wake word detection
    detected = audio.detect_wake_word(audio_bytes, wake_word="freya", correlation_id="test-011")
    print(f"✓ Wake word detection: {detected}")

    # Test health check
    health = audio.health_check(correlation_id="test-012")
    print(f"✓ Health check: {health.status} (healthy={health.is_healthy})")


async def test_mock_iot():
    """Test mock IoT driver."""
    print("\n=== Testing Mock IoT Driver ===")

    iot = create_iot(driver="mock", behavior="normal")

    # Test discover devices
    devices = await iot.discover_devices(correlation_id="test-013")
    print(f"✓ Discovered {len(devices)} device(s)")
    for device in devices:
        print(f"  - {device.name} ({device.device_type}): {device.state}")

    # Test send command
    command = DeviceCommand(
        device_id="light.living_room",
        action="turn_on",
        parameters={"brightness": 200},
        correlation_id="test-014",
    )
    success = await iot.send_command(command)
    print(f"✓ Command executed: {success}")

    # Test query state
    device = await iot.query_state("light.living_room", correlation_id="test-015")
    print(f"✓ Device state: {device.name} = {device.state}")

    # Test health check
    health = iot.health_check(correlation_id="test-016")
    print(f"✓ Health check: {health.status} (healthy={health.is_healthy})")


async def main():
    """Run all HAL tests."""
    print("=" * 70)
    print("Hardware Abstraction Layer (HAL) - Basic Tests")
    print("=" * 70)

    try:
        # Test Vision
        test_mock_vision()

        # Test Memory
        await test_mock_memory()

        # Test Audio
        test_mock_audio()

        # Test IoT
        await test_mock_iot()

        print("\n" + "=" * 70)
        print("✅ All HAL tests passed!")
        print("=" * 70)

    except Exception as exc:
        print("\n" + "=" * 70)
        print(f"❌ HAL tests failed: {exc}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
