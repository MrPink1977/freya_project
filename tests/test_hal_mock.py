"""Direct HAL mock tests (bypassing package __init__)."""

import asyncio
import importlib.util
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def import_module_from_path(module_name: str, file_path: Path):
    """Import a module directly from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Manually import HAL modules bypassing freya/__init__.py
print("Importing HAL modules directly...")

try:
    # Import dependencies first (they don't have problematic imports)
    import numpy as np

    # Import logger without full freya package
    logger_path = project_root / "freya" / "core" / "logger.py"
    logger_module = import_module_from_path("freya.core.logger", logger_path)

    # Import interfaces
    interfaces_path = project_root / "freya" / "hal" / "interfaces.py"
    interfaces = import_module_from_path("freya.hal.interfaces", interfaces_path)

    # Import mock implementations
    vision_path = project_root / "freya" / "hal" / "vision.py"
    vision_module = import_module_from_path("freya.hal.vision", vision_path)

    memory_path = project_root / "freya" / "hal" / "memory.py"
    memory_module = import_module_from_path("freya.hal.memory", memory_path)

    audio_path = project_root / "freya" / "hal" / "audio.py"
    audio_module = import_module_from_path("freya.hal.audio", audio_path)

    iot_path = project_root / "freya" / "hal" / "iot.py"
    iot_module = import_module_from_path("freya.hal.iot", iot_path)

    print("✓ All HAL modules imported successfully")

except Exception as exc:
    print(f"❌ Failed to import HAL modules: {exc}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def test_mock_vision():
    """Test mock vision driver."""
    print("\n=== Testing Mock Vision Driver ===")

    MockCameraDriver = vision_module.MockCameraDriver
    vision = MockCameraDriver(behavior="normal")

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

    MockMemoryDriver = memory_module.MockMemoryDriver
    memory = MockMemoryDriver(behavior="normal")

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

    MockAudioDriver = audio_module.MockAudioDriver
    audio = MockAudioDriver(behavior="normal")

    # Test listen
    audio_bytes = audio.listen(duration_sec=2.0, correlation_id="test-008")
    print(f"✓ Captured {len(audio_bytes)} bytes of audio")

    # Test transcribe
    transcription = audio.transcribe(audio_bytes, correlation_id="test-009")
    print(f"✓ Transcription: '{transcription.text}' (confidence: {transcription.confidence:.2f})")

    # Test speak
    audio.speak("Hello from Freya HAL", engine=interfaces.TTSEngine.PIPER, correlation_id="test-010")
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

    MockIoTDriver = iot_module.MockIoTDriver
    iot = MockIoTDriver(behavior="normal")

    # Test discover devices
    devices = await iot.discover_devices(correlation_id="test-013")
    print(f"✓ Discovered {len(devices)} device(s)")
    for device in devices:
        print(f"  - {device.name} ({device.device_type}): {device.state}")

    # Test send command
    DeviceCommand = interfaces.DeviceCommand
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
    print("Hardware Abstraction Layer (HAL) - Mock Tests")
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
        print("✅ All HAL mock tests passed!")
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
