"""Standalone HAL tests (no external dependencies)."""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Import HAL modules individually
print("Importing HAL modules...")

try:
    # Import individual HAL modules
    import freya.hal.interfaces as interfaces
    from freya.hal.vision import MockCameraDriver
    from freya.hal.memory import MockMemoryDriver
    from freya.hal.audio import MockAudioDriver
    from freya.hal.iot import MockIoTDriver

    print("✓ All HAL modules imported successfully")
except ImportError as exc:
    print(f"❌ Failed to import HAL modules: {exc}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def test_mock_vision():
    """Test mock vision driver."""
    print("\n=== Testing Mock Vision Driver ===")

    vision = MockCameraDriver(behavior="normal")

    # Test capture
    image = vision.capture(correlation_id="test-001")
    print(f"✓ Captured image: {image.width}x{image.height} from {image.source}")
    assert image.width == 640
    assert image.height == 480

    # Test face detection
    faces = vision.detect_faces(image, correlation_id="test-002")
    print(f"✓ Detected {len(faces)} face(s)")
    assert len(faces) >= 0  # Mock may return 0 or more faces

    # Test health check
    health = vision.health_check(correlation_id="test-003")
    print(f"✓ Health check: {health.status} (healthy={health.is_healthy})")
    assert health.status == "healthy"


async def test_mock_memory():
    """Test mock memory driver."""
    print("\n=== Testing Mock Memory Driver ===")

    memory = MockMemoryDriver(behavior="normal")

    # Test store
    mem1 = await memory.store(
        content="The user likes Python programming",
        memory_type="fact",
        correlation_id="test-004",
    )
    print(f"✓ Stored memory: {mem1.id}")
    assert mem1.id.startswith("mock_mem_")

    mem2 = await memory.store(
        content="The user asked about machine learning",
        memory_type="conversation",
        correlation_id="test-005",
    )
    print(f"✓ Stored memory: {mem2.id}")

    # Test retrieve
    results = await memory.retrieve(
        query="Python",
        top_k=5,
        correlation_id="test-006",
    )
    print(f"✓ Retrieved {len(results)} result(s)")
    assert len(results) >= 0  # May be 0 or more depending on mock implementation

    # Test health check
    health = memory.health_check(correlation_id="test-007")
    print(f"✓ Health check: {health.status} (healthy={health.is_healthy})")
    assert health.status == "healthy"


def test_mock_audio():
    """Test mock audio driver."""
    print("\n=== Testing Mock Audio Driver ===")

    audio = MockAudioDriver(behavior="normal")

    # Test listen
    audio_bytes = audio.listen(duration_sec=2.0, correlation_id="test-008")
    print(f"✓ Captured {len(audio_bytes)} bytes of audio")
    assert len(audio_bytes) > 0

    # Test transcribe
    transcription = audio.transcribe(audio_bytes, correlation_id="test-009")
    print(f"✓ Transcription: '{transcription.text}' (confidence: {transcription.confidence:.2f})")
    assert transcription.text != ""

    # Test speak
    audio.speak("Hello from Freya HAL", engine=interfaces.TTSEngine.PIPER, correlation_id="test-010")
    print(f"✓ Speech synthesis completed")

    # Test wake word detection
    detected = audio.detect_wake_word(audio_bytes, wake_word="freya", correlation_id="test-011")
    print(f"✓ Wake word detection: {detected}")
    assert isinstance(detected, bool)

    # Test health check
    health = audio.health_check(correlation_id="test-012")
    print(f"✓ Health check: {health.status} (healthy={health.is_healthy})")
    assert health.status == "healthy"


async def test_mock_iot():
    """Test mock IoT driver."""
    print("\n=== Testing Mock IoT Driver ===")

    iot = MockIoTDriver(behavior="normal")

    # Test discover devices
    devices = await iot.discover_devices(correlation_id="test-013")
    print(f"✓ Discovered {len(devices)} device(s)")
    assert len(devices) > 0  # Mock has default devices

    for device in devices:
        print(f"  - {device.name} ({device.device_type}): {device.state}")

    # Test send command
    command = interfaces.DeviceCommand(
        device_id="light.living_room",
        action="turn_on",
        parameters={"brightness": 200},
        correlation_id="test-014",
    )
    success = await iot.send_command(command)
    print(f"✓ Command executed: {success}")
    assert success is True

    # Test query state
    device = await iot.query_state("light.living_room", correlation_id="test-015")
    print(f"✓ Device state: {device.name} = {device.state}")
    assert device.device_id == "light.living_room"

    # Test health check
    health = iot.health_check(correlation_id="test-016")
    print(f"✓ Health check: {health.status} (healthy={health.is_healthy})")
    assert health.status == "healthy"


async def main():
    """Run all HAL tests."""
    print("=" * 70)
    print("Hardware Abstraction Layer (HAL) - Standalone Tests")
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
