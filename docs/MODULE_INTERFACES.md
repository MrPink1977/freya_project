# Module Interface Specifications - Freya v0.4.0

**Version**: 1.0
**Date**: 2025-12-02
**Status**: Design Specification
**Purpose**: Define strict contracts for Vision, Memory, Audio, and IoT modules

---

## Overview

This document defines the interface contracts for Freya's core modules. These interfaces enable:
- **Modularity**: Swap implementations without changing application code
- **Testability**: Mock implementations for hardware-independent testing
- **Scalability**: Add new implementations (better algorithms, new hardware)
- **Maintainability**: Clear boundaries between modules

### Design Principles

1. **Contract-First Design**: Define interfaces before implementations
2. **Protocol Over ABC**: Use `typing.Protocol` for structural subtyping (more flexible)
3. **Fail-Fast**: Validate inputs early, provide clear error messages
4. **Performance Budgets**: Define acceptable latency for each operation
5. **Health Monitoring**: All implementations report health status
6. **Correlation Tracking**: All operations can be traced through the system

---

## 1. Vision Module Interface

**Purpose**: Camera capture, facial recognition, object detection, scene description

### 1.1 Core Interface

```python
from typing import Protocol, Generator, Optional, List, runtime_checkable
from dataclasses import dataclass
from enum import Enum
import numpy as np

@dataclass
class Image:
    """Standardized image representation."""
    data: np.ndarray  # HWC format, RGB
    timestamp: float
    source: str  # Camera ID
    width: int
    height: int
    correlation_id: Optional[str] = None

@dataclass
class Face:
    """Detected face with identification."""
    name: Optional[str]  # None if unknown
    confidence: float  # 0.0 - 1.0
    bounding_box: tuple[int, int, int, int]  # (x, y, w, h)
    encoding: Optional[np.ndarray] = None

@dataclass
class SceneDescription:
    """AI-generated scene description."""
    description: str
    objects: List[str]
    confidence: float
    processing_time_ms: float

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

@runtime_checkable
class VisionInterface(Protocol):
    """
    Vision module interface for camera and image processing.

    All methods must be thread-safe.
    All methods accept optional correlation_id for request tracing.
    """

    def capture(self, correlation_id: Optional[str] = None) -> Image:
        """
        Capture a single frame from the camera.

        Performance Budget: < 100ms (including hardware latency)

        Args:
            correlation_id: Request tracking ID

        Returns:
            Image with populated metadata

        Raises:
            CameraUnavailableError: Camera disconnected or busy
            CaptureTimeoutError: Capture exceeded timeout
        """
        ...

    def detect_faces(
        self,
        image: Image,
        correlation_id: Optional[str] = None
    ) -> List[Face]:
        """
        Detect and identify faces in an image.

        Performance Budget: < 500ms for 1080p image

        Args:
            image: Image to process
            correlation_id: Request tracking ID

        Returns:
            List of detected faces (empty if none found)

        Raises:
            ProcessingError: Face detection failed
        """
        ...

    def describe_scene(
        self,
        image: Image,
        correlation_id: Optional[str] = None
    ) -> SceneDescription:
        """
        Generate AI description of scene contents.

        Performance Budget: < 2000ms (may use LLM)

        Args:
            image: Image to analyze
            correlation_id: Request tracking ID

        Returns:
            Scene description with confidence

        Raises:
            ProcessingError: Description generation failed
        """
        ...

    def stream_rtsp(
        self,
        duration_sec: Optional[float] = None,
        correlation_id: Optional[str] = None
    ) -> Generator[Image, None, None]:
        """
        Stream frames from RTSP camera.

        Performance Budget: Target 15-30 FPS depending on network

        Args:
            duration_sec: Stream duration (None = infinite)
            correlation_id: Request tracking ID

        Yields:
            Image frames as they arrive

        Raises:
            StreamError: Connection lost or stream corrupted
        """
        ...

    def get_health(self) -> tuple[HealthStatus, str]:
        """
        Report module health status.

        Performance Budget: < 10ms (no heavy operations)

        Returns:
            (status, message) tuple
        """
        ...

    def close(self) -> None:
        """
        Release hardware resources gracefully.

        Must be idempotent (safe to call multiple times).
        """
        ...
```

### 1.2 Implementations

#### 1.2.1 Real Hardware Implementation

```python
class ReolinkCameraDriver(VisionInterface):
    """Production implementation for Reolink cameras."""

    def __init__(self, config: CameraConfig):
        self.ip = config.ip
        self.port = config.rtsp_port
        self.username = config.username
        self.password = config.password
        self._connection = None
        self._face_recognizer = FaceRecognizer(config.faces_directory)

    # Implement all protocol methods...
```

#### 1.2.2 Mock Implementation

```python
class MockCameraDriver(VisionInterface):
    """Test implementation with configurable behavior."""

    def __init__(self, behavior: str = "normal"):
        self.behavior = behavior  # normal, flaky, offline
        self._frame_count = 0

    def capture(self, correlation_id: Optional[str] = None) -> Image:
        if self.behavior == "offline":
            raise CameraUnavailableError("Mock camera offline")
        elif self.behavior == "flaky" and self._frame_count % 3 == 0:
            raise CaptureTimeoutError("Mock timeout")

        # Return synthetic image
        return Image(
            data=np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
            timestamp=time.time(),
            source="mock_camera",
            width=640,
            height=480,
            correlation_id=correlation_id
        )
```

### 1.3 Configuration

```yaml
vision:
  driver: "reolink"  # or "mock" for testing

  # Real hardware config
  camera:
    ip: "192.168.0.22"
    rtsp_port: 554
    username: "admin"
    password: "${REOLINK_CAM_PASS}"

  # Facial recognition
  faces_directory: "data/faces"
  recognition_threshold: 0.6

  # Performance tuning
  capture_timeout_ms: 100
  stream_fps: 15
  processing_threads: 2

  # Mock behavior (when driver=mock)
  mock_behavior: "normal"  # normal, flaky, offline
```

### 1.4 Error Handling Strategy

**Custom Exceptions**:
```python
class VisionError(Exception):
    """Base exception for vision module."""
    pass

class CameraUnavailableError(VisionError):
    """Camera is disconnected, busy, or powered off."""
    pass

class CaptureTimeoutError(VisionError):
    """Frame capture exceeded timeout."""
    pass

class ProcessingError(VisionError):
    """Image processing failed (detection, recognition, description)."""
    pass

class StreamError(VisionError):
    """RTSP stream connection lost or corrupted."""
    pass
```

**Error Recovery**:
- Transient errors (timeout): Retry with exponential backoff (3 attempts)
- Permanent errors (unavailable): Mark health as DEGRADED, continue without vision
- Stream errors: Attempt reconnection, fallback to single captures

### 1.5 Performance Budgets

| Operation | Budget | Rationale |
|-----------|--------|-----------|
| `capture()` | < 100ms | Real-time feel, 10 FPS minimum |
| `detect_faces()` | < 500ms | Acceptable for non-realtime |
| `describe_scene()` | < 2000ms | May use LLM, user expects delay |
| `stream_rtsp()` | 15-30 FPS | Network dependent, adaptive |
| `get_health()` | < 10ms | Called frequently, must be fast |

---

## 2. Memory Module Interface

**Purpose**: Vector storage, semantic search, fact extraction, context management

### 2.1 Core Interface

```python
from typing import Protocol, List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Memory:
    """Single memory entry."""
    id: str
    content: str
    timestamp: datetime
    memory_type: str  # "conversation", "fact", "observation"
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    correlation_id: Optional[str] = None

@dataclass
class SearchResult:
    """Memory search result with relevance."""
    memory: Memory
    relevance_score: float  # 0.0 - 1.0
    distance: float  # Vector distance

@runtime_checkable
class MemoryInterface(Protocol):
    """
    Memory module interface for storage and retrieval.

    All methods must be thread-safe.
    Implementations should use connection pooling for performance.
    """

    def store(
        self,
        content: str,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Memory:
        """
        Store a memory entry.

        Performance Budget: < 50ms (async write preferred)

        Args:
            content: Text content to store
            memory_type: Type classification
            metadata: Additional structured data
            correlation_id: Request tracking ID

        Returns:
            Stored memory with generated ID

        Raises:
            StorageError: Database write failed
        """
        ...

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Semantic search for relevant memories.

        Performance Budget: < 100ms for 10k memories (HNSW index)

        Args:
            query: Search query text
            top_k: Number of results to return
            memory_type: Filter by type (None = all types)
            correlation_id: Request tracking ID

        Returns:
            Ranked list of relevant memories

        Raises:
            SearchError: Search operation failed
        """
        ...

    def extract_facts(
        self,
        conversation: List[str],
        correlation_id: Optional[str] = None
    ) -> List[Memory]:
        """
        Extract factual statements from conversation.

        Performance Budget: < 1000ms (may use LLM)

        Args:
            conversation: List of conversation turns
            correlation_id: Request tracking ID

        Returns:
            Extracted facts as memory entries

        Raises:
            ExtractionError: Fact extraction failed
        """
        ...

    def consolidate(
        self,
        threshold: float = 0.75,
        correlation_id: Optional[str] = None
    ) -> int:
        """
        Merge similar memories and archive old conversations.

        Performance Budget: < 5000ms (background operation)

        Args:
            threshold: Similarity threshold for merging
            correlation_id: Request tracking ID

        Returns:
            Number of memories consolidated

        Raises:
            ConsolidationError: Consolidation failed
        """
        ...

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory storage statistics.

        Performance Budget: < 20ms

        Returns:
            Dictionary with: total_memories, storage_size_mb, index_size
        """
        ...

    def get_health(self) -> tuple[HealthStatus, str]:
        """
        Report module health status.

        Performance Budget: < 10ms

        Returns:
            (status, message) tuple
        """
        ...
```

### 2.2 Implementations

#### 2.2.1 ChromaDB Implementation

```python
class ChromaMemoryStore(MemoryInterface):
    """Production implementation using ChromaDB."""

    def __init__(self, config: MemoryConfig):
        self.persist_directory = config.persist_directory
        self.collection_name = config.collection_name
        self._client = chromadb.Client(
            Settings(persist_directory=self.persist_directory)
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self._embedding_function = SentenceTransformerEmbeddingFunction()

    # Implement all protocol methods...
```

#### 2.2.2 Mock Implementation

```python
class MockMemoryStore(MemoryInterface):
    """In-memory implementation for testing."""

    def __init__(self):
        self._memories: Dict[str, Memory] = {}
        self._index = 0

    def store(
        self,
        content: str,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Memory:
        memory = Memory(
            id=f"mock_{self._index}",
            content=content,
            timestamp=datetime.now(),
            memory_type=memory_type,
            metadata=metadata or {},
            correlation_id=correlation_id
        )
        self._memories[memory.id] = memory
        self._index += 1
        return memory

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> List[SearchResult]:
        # Simple keyword matching for mock
        results = []
        for memory in self._memories.values():
            if memory_type and memory.memory_type != memory_type:
                continue
            # Simple relevance: word overlap
            query_words = set(query.lower().split())
            content_words = set(memory.content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                results.append(SearchResult(
                    memory=memory,
                    relevance_score=overlap / len(query_words),
                    distance=1.0 - (overlap / len(query_words))
                ))
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]
```

### 2.3 Configuration

```yaml
memory:
  driver: "chroma"  # or "mock" for testing

  # ChromaDB config
  persist_directory: "data/chroma_db"
  collection_name: "freya_memories"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

  # Performance tuning
  max_memories: 10000
  consolidation_threshold: 0.75
  auto_consolidate: true

  # Search parameters
  default_top_k: 5
  relevance_threshold: 0.3
```

### 2.4 Error Handling Strategy

```python
class MemoryError(Exception):
    """Base exception for memory module."""
    pass

class StorageError(MemoryError):
    """Database write operation failed."""
    pass

class SearchError(MemoryError):
    """Search operation failed (index corrupt, timeout, etc)."""
    pass

class ExtractionError(MemoryError):
    """Fact extraction from conversation failed."""
    pass

class ConsolidationError(MemoryError):
    """Memory consolidation process failed."""
    pass
```

**Error Recovery**:
- Write failures: Retry with backoff, fallback to in-memory cache
- Search failures: Return empty results, log error, continue
- Extraction failures: Skip fact extraction, store raw conversation
- Consolidation failures: Log error, continue (non-critical operation)

### 2.5 Performance Budgets

| Operation | Budget | Rationale |
|-----------|--------|-----------|
| `store()` | < 50ms | Must not block conversation flow |
| `retrieve()` | < 100ms | Real-time search for context injection |
| `extract_facts()` | < 1000ms | Background operation, LLM involved |
| `consolidate()` | < 5000ms | Background maintenance task |
| `get_stats()` | < 20ms | Monitoring should be lightweight |
| `get_health()` | < 10ms | Called frequently |

---

## 3. Audio Module Interface

**Purpose**: Speech-to-text, text-to-speech, wake word detection, audio device management

### 3.1 Core Interface

```python
from typing import Protocol, Optional, List, Callable, Generator
from dataclasses import dataclass
from enum import Enum

@dataclass
class AudioConfig:
    """Audio device configuration."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    device_index: Optional[int] = None

@dataclass
class Transcription:
    """Speech-to-text result."""
    text: str
    confidence: float  # 0.0 - 1.0
    language: str
    processing_time_ms: float
    correlation_id: Optional[str] = None

@dataclass
class WakeWordEvent:
    """Wake word detection event."""
    detected: bool
    confidence: float
    timestamp: float
    audio_snippet: Optional[bytes] = None

class TTSEngine(Enum):
    PIPER = "piper"
    ELEVENLABS = "elevenlabs"

@runtime_checkable
class AudioInterface(Protocol):
    """
    Audio module interface for voice interaction.

    All audio operations must handle device errors gracefully.
    """

    def listen(
        self,
        duration_sec: float = 5.0,
        correlation_id: Optional[str] = None
    ) -> bytes:
        """
        Record audio from microphone.

        Performance Budget: Real-time (duration + 50ms overhead)

        Args:
            duration_sec: Recording duration
            correlation_id: Request tracking ID

        Returns:
            Raw audio bytes (WAV format)

        Raises:
            MicrophoneUnavailableError: Microphone disconnected or in use
            RecordingError: Audio capture failed
        """
        ...

    def transcribe(
        self,
        audio: bytes,
        language: str = "en",
        correlation_id: Optional[str] = None
    ) -> Transcription:
        """
        Convert speech to text (STT).

        Performance Budget: < 500ms for 5 sec audio (Faster Whisper)

        Args:
            audio: Raw audio bytes
            language: Language code
            correlation_id: Request tracking ID

        Returns:
            Transcription with confidence score

        Raises:
            TranscriptionError: STT processing failed
        """
        ...

    def speak(
        self,
        text: str,
        engine: TTSEngine = TTSEngine.PIPER,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Convert text to speech and play (TTS).

        Performance Budget: < 200ms latency + playback time

        Args:
            text: Text to speak
            engine: TTS engine to use
            correlation_id: Request tracking ID

        Raises:
            SpeakerUnavailableError: Speaker disconnected
            SynthesisError: TTS generation failed
        """
        ...

    def detect_wake_word(
        self,
        callback: Callable[[WakeWordEvent], None],
        wake_word: str = "hey freya",
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Start background wake word detection.

        Performance Budget: < 10ms per audio chunk (real-time)

        Args:
            callback: Function called when wake word detected
            wake_word: Wake phrase to detect
            correlation_id: Request tracking ID

        Raises:
            DetectionError: Wake word detection failed to start
        """
        ...

    def stop_wake_word_detection(self) -> None:
        """
        Stop wake word detection.

        Must be idempotent (safe to call multiple times).
        """
        ...

    def list_devices(self) -> Dict[str, List[str]]:
        """
        List available audio devices.

        Performance Budget: < 50ms

        Returns:
            Dictionary with 'input' and 'output' device lists
        """
        ...

    def get_health(self) -> tuple[HealthStatus, str]:
        """
        Report module health status.

        Performance Budget: < 10ms

        Returns:
            (status, message) tuple
        """
        ...
```

### 3.2 Implementations

#### 3.2.1 Real Hardware Implementation

```python
class FasterWhisperSTT(AudioInterface):
    """Production implementation using Faster Whisper + Piper/ElevenLabs."""

    def __init__(self, config: AudioConfig):
        self.config = config
        self._stt_model = WhisperModel(
            model_size_or_path="base",
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
        self._piper = PiperTTS(config.piper_model_path)
        self._elevenlabs = ElevenLabsTTS(config.elevenlabs_api_key)
        self._wake_detector = WakeWordDetector(config.wake_model)
        self._audio_stream = None

    # Implement all protocol methods...
```

#### 3.2.2 Mock Implementation

```python
class MockAudioDriver(AudioInterface):
    """Mock implementation for testing without hardware."""

    def __init__(self, behavior: str = "normal"):
        self.behavior = behavior
        self._recordings: List[bytes] = []
        self._wake_callback: Optional[Callable] = None

    def listen(
        self,
        duration_sec: float = 5.0,
        correlation_id: Optional[str] = None
    ) -> bytes:
        if self.behavior == "offline":
            raise MicrophoneUnavailableError("Mock microphone offline")

        # Return synthetic audio (silence)
        sample_rate = 16000
        samples = int(duration_sec * sample_rate)
        audio = np.zeros(samples, dtype=np.int16)
        return audio.tobytes()

    def transcribe(
        self,
        audio: bytes,
        language: str = "en",
        correlation_id: Optional[str] = None
    ) -> Transcription:
        # Return mock transcription
        return Transcription(
            text="Mock transcription text",
            confidence=0.95,
            language=language,
            processing_time_ms=50,
            correlation_id=correlation_id
        )
```

### 3.3 Configuration

```yaml
audio:
  driver: "faster_whisper"  # or "mock" for testing

  # Microphone
  input_device: 0  # Device index (null = default)
  sample_rate: 16000
  channels: 1

  # Speech-to-Text
  stt_model: "base"  # whisper model size
  stt_device: "cuda"  # cuda or cpu
  stt_language: "en"

  # Text-to-Speech
  default_engine: "piper"  # or "elevenlabs"
  piper_model: "voices/en_GB-southern_english_female-low.onnx"
  elevenlabs_api_key: "${ELEVENLABS_API_KEY}"
  elevenlabs_voice_id: "${ELEVENLABS_VOICE_ID}"

  # Wake Word
  wake_word: "hey freya"
  wake_threshold: 0.7
  wake_model: "base"

  # Mock behavior
  mock_behavior: "normal"  # normal, offline
```

### 3.4 Error Handling Strategy

```python
class AudioError(Exception):
    """Base exception for audio module."""
    pass

class MicrophoneUnavailableError(AudioError):
    """Microphone is disconnected or in use by another process."""
    pass

class SpeakerUnavailableError(AudioError):
    """Speaker/audio output is unavailable."""
    pass

class RecordingError(AudioError):
    """Audio recording failed (buffer overflow, driver error)."""
    pass

class TranscriptionError(AudioError):
    """Speech-to-text processing failed."""
    pass

class SynthesisError(AudioError):
    """Text-to-speech generation failed."""
    pass

class DetectionError(AudioError):
    """Wake word detection failed to start or crashed."""
    pass
```

**Error Recovery**:
- Microphone unavailable: Fallback to text mode, notify user
- Speaker unavailable: Log warning, continue without audio output
- Transcription errors: Retry once, then return error to user
- Wake word crashes: Restart detection, limit to 3 restarts/hour

### 3.5 Performance Budgets

| Operation | Budget | Rationale |
|-----------|--------|-----------|
| `listen()` | Real-time + 50ms | Direct hardware passthrough |
| `transcribe()` | < 500ms | Faster Whisper on GPU |
| `speak()` | < 200ms latency | Streaming TTS preferred |
| `detect_wake_word()` | < 10ms/chunk | Must not miss audio frames |
| `list_devices()` | < 50ms | System query, cached |
| `get_health()` | < 10ms | No heavy operations |

---

## 4. IoT Module Interface

**Purpose**: Home Assistant integration, smart device control, sensor monitoring

### 4.1 Core Interface

```python
from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class DeviceType(Enum):
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    CAMERA = "camera"
    LOCK = "lock"
    CLIMATE = "climate"

@dataclass
class Device:
    """Smart device representation."""
    entity_id: str
    name: str
    device_type: DeviceType
    state: Any  # on/off for switches, temperature for sensors, etc
    attributes: Dict[str, Any]
    last_updated: datetime

@dataclass
class DeviceCommand:
    """Command to send to a device."""
    entity_id: str
    command: str  # "turn_on", "turn_off", "set_temperature", etc
    parameters: Optional[Dict[str, Any]] = None

@runtime_checkable
class IoTInterface(Protocol):
    """
    IoT module interface for smart home integration.

    All operations should handle network failures gracefully.
    """

    def discover_devices(
        self,
        device_type: Optional[DeviceType] = None,
        correlation_id: Optional[str] = None
    ) -> List[Device]:
        """
        Discover available smart devices.

        Performance Budget: < 1000ms (network dependent)

        Args:
            device_type: Filter by type (None = all types)
            correlation_id: Request tracking ID

        Returns:
            List of discovered devices

        Raises:
            DiscoveryError: Device discovery failed
        """
        ...

    def send_command(
        self,
        command: DeviceCommand,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Send command to a device.

        Performance Budget: < 500ms (network + device response)

        Args:
            command: Command to execute
            correlation_id: Request tracking ID

        Returns:
            True if command succeeded

        Raises:
            CommandError: Command execution failed
            DeviceNotFoundError: Entity ID not found
        """
        ...

    def get_state(
        self,
        entity_id: str,
        correlation_id: Optional[str] = None
    ) -> Device:
        """
        Query current state of a device.

        Performance Budget: < 200ms (cached where possible)

        Args:
            entity_id: Device entity ID
            correlation_id: Request tracking ID

        Returns:
            Device with current state

        Raises:
            DeviceNotFoundError: Entity ID not found
            StateQueryError: State query failed
        """
        ...

    def subscribe_events(
        self,
        callback: Callable[[Device], None],
        entity_ids: Optional[List[str]] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Subscribe to device state change events.

        Performance Budget: < 100ms to establish connection

        Args:
            callback: Function called on state changes
            entity_ids: Filter by entity IDs (None = all devices)
            correlation_id: Request tracking ID

        Raises:
            SubscriptionError: Event subscription failed
        """
        ...

    def unsubscribe_events(self) -> None:
        """
        Unsubscribe from device events.

        Must be idempotent.
        """
        ...

    def get_health(self) -> tuple[HealthStatus, str]:
        """
        Report module health status.

        Performance Budget: < 10ms

        Returns:
            (status, message) tuple
        """
        ...
```

### 4.2 Implementations

#### 4.2.1 Home Assistant Implementation

```python
class HomeAssistantClient(IoTInterface):
    """Production implementation for Home Assistant."""

    def __init__(self, config: IoTConfig):
        self.url = config.ha_url
        self.token = config.ha_token
        self._session = aiohttp.ClientSession()
        self._ws_connection = None
        self._device_cache: Dict[str, Device] = {}
        self._cache_ttl = 30  # seconds

    # Implement all protocol methods...
```

#### 4.2.2 Mock Implementation

```python
class MockIoTDriver(IoTInterface):
    """Mock IoT implementation for testing."""

    def __init__(self):
        self._devices: Dict[str, Device] = {
            "light.living_room": Device(
                entity_id="light.living_room",
                name="Living Room Light",
                device_type=DeviceType.LIGHT,
                state="off",
                attributes={"brightness": 0},
                last_updated=datetime.now()
            ),
            "sensor.temperature": Device(
                entity_id="sensor.temperature",
                name="Temperature Sensor",
                device_type=DeviceType.SENSOR,
                state=22.5,
                attributes={"unit": "°C"},
                last_updated=datetime.now()
            )
        }

    def discover_devices(
        self,
        device_type: Optional[DeviceType] = None,
        correlation_id: Optional[str] = None
    ) -> List[Device]:
        devices = list(self._devices.values())
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
        return devices

    def send_command(
        self,
        command: DeviceCommand,
        correlation_id: Optional[str] = None
    ) -> bool:
        if command.entity_id not in self._devices:
            raise DeviceNotFoundError(f"Device {command.entity_id} not found")

        device = self._devices[command.entity_id]
        if command.command == "turn_on":
            device.state = "on"
        elif command.command == "turn_off":
            device.state = "off"
        device.last_updated = datetime.now()
        return True
```

### 4.3 Configuration

```yaml
iot:
  driver: "home_assistant"  # or "mock" for testing

  # Home Assistant config
  ha_url: "http://homeassistant.local:8123"
  ha_token: "${HA_TOKEN}"
  auto_discover: true

  # Performance tuning
  command_timeout_ms: 500
  state_cache_ttl_sec: 30
  reconnect_attempts: 3

  # Device filtering
  include_entity_patterns:
    - "light.*"
    - "switch.*"
    - "sensor.temperature"
```

### 4.4 Error Handling Strategy

```python
class IoTError(Exception):
    """Base exception for IoT module."""
    pass

class DiscoveryError(IoTError):
    """Device discovery failed (network error, auth failure)."""
    pass

class DeviceNotFoundError(IoTError):
    """Requested device entity ID not found."""
    pass

class CommandError(IoTError):
    """Command execution failed (device offline, invalid command)."""
    pass

class StateQueryError(IoTError):
    """State query failed (network error, timeout)."""
    pass

class SubscriptionError(IoTError):
    """Event subscription failed (WebSocket connection error)."""
    pass
```

**Error Recovery**:
- Discovery failures: Retry with backoff, return cached devices
- Command failures: Retry once, report error to user
- State queries: Return cached state, mark as stale
- Subscription failures: Attempt reconnect (3 attempts), fallback to polling

### 4.5 Performance Budgets

| Operation | Budget | Rationale |
|-----------|--------|-----------|
| `discover_devices()` | < 1000ms | Network request, one-time cost |
| `send_command()` | < 500ms | User expects immediate response |
| `get_state()` | < 200ms | Cached when possible |
| `subscribe_events()` | < 100ms | WebSocket connection |
| `get_health()` | < 10ms | Frequent monitoring |

---

## 5. Cross-Cutting Concerns

### 5.1 Correlation ID Tracking

All interface methods accept `correlation_id` for request tracing:

```python
import uuid

# Generate at request entry point
correlation_id = str(uuid.uuid4())

# Pass through all operations
image = vision.capture(correlation_id=correlation_id)
faces = vision.detect_faces(image, correlation_id=correlation_id)
memory.store(f"Detected {len(faces)} faces", correlation_id=correlation_id)

# Logs will include correlation_id for tracing
# [2025-12-02 14:32:15.234] [Vision] [INFO] [abc-123] Captured image
# [2025-12-02 14:32:15.567] [Vision] [INFO] [abc-123] Detected 2 faces
# [2025-12-02 14:32:15.789] [Memory] [INFO] [abc-123] Stored memory
```

### 5.2 Health Monitoring

All modules must implement `get_health()`:

```python
# Health check example
from freya.core.health_monitor import HealthMonitor

monitor = HealthMonitor()

@monitor.check("vision")
async def check_vision():
    status, message = vision_module.get_health()
    return status, message

# Aggregate health
overall_health = monitor.get_overall_health()
# Returns: (HEALTHY | DEGRADED | UNAVAILABLE, component_details)
```

### 5.3 Configuration Management

Use Pydantic for type-safe configuration:

```python
from pydantic import BaseModel, Field

class VisionConfig(BaseModel):
    driver: str = Field("reolink", description="Driver name")
    camera_ip: str = Field(..., description="Camera IP address")
    rtsp_port: int = Field(554, description="RTSP port")
    faces_directory: Path = Field("data/faces", description="Known faces directory")

    # Validation
    @validator("camera_ip")
    def validate_ip(cls, v):
        # IP validation logic
        return v
```

### 5.4 Factory Pattern

Centralized driver instantiation:

```python
from typing import Type, Dict, Any

class ModuleFactory:
    """Factory for creating module instances."""

    _vision_drivers: Dict[str, Type[VisionInterface]] = {
        "reolink": ReolinkCameraDriver,
        "mock": MockCameraDriver,
    }

    _memory_drivers: Dict[str, Type[MemoryInterface]] = {
        "chroma": ChromaMemoryStore,
        "mock": MockMemoryStore,
    }

    # ... other modules

    @classmethod
    def create_vision(cls, config: VisionConfig) -> VisionInterface:
        """Create vision module instance."""
        driver_class = cls._vision_drivers.get(config.driver)
        if not driver_class:
            raise ValueError(f"Unknown vision driver: {config.driver}")
        return driver_class(config)

    @classmethod
    def create_memory(cls, config: MemoryConfig) -> MemoryInterface:
        """Create memory module instance."""
        driver_class = cls._memory_drivers.get(config.driver)
        if not driver_class:
            raise ValueError(f"Unknown memory driver: {config.driver}")
        return driver_class(config)
```

### 5.5 Testing Strategy

#### Unit Tests (Mock Implementations)

```python
import pytest

def test_vision_capture():
    vision = MockCameraDriver(behavior="normal")
    image = vision.capture()
    assert image.width == 640
    assert image.height == 480

def test_vision_offline():
    vision = MockCameraDriver(behavior="offline")
    with pytest.raises(CameraUnavailableError):
        vision.capture()
```

#### Integration Tests (Real Hardware)

```python
@pytest.mark.integration
@pytest.mark.requires_hardware("camera")
def test_real_camera_capture():
    config = VisionConfig(driver="reolink", camera_ip="192.168.0.22")
    vision = ModuleFactory.create_vision(config)

    image = vision.capture()
    assert image.width > 0
    assert image.height > 0
```

#### Contract Tests

```python
from typing import get_args

def test_vision_interface_compliance():
    """Verify all implementations satisfy the interface."""
    for driver_name, driver_class in ModuleFactory._vision_drivers.items():
        instance = driver_class(MockConfig())

        # Check protocol compliance
        assert isinstance(instance, VisionInterface)

        # Verify all methods exist
        assert hasattr(instance, 'capture')
        assert hasattr(instance, 'detect_faces')
        assert hasattr(instance, 'describe_scene')
        assert hasattr(instance, 'stream_rtsp')
        assert hasattr(instance, 'get_health')
        assert hasattr(instance, 'close')
```

---

## 6. Migration Path

### 6.1 Current State → Interface Adoption

**Phase 1: Create Interfaces** (this document) ✅
- Define protocols for all modules
- Document contracts and performance budgets

**Phase 2: Wrapper Implementations** (1-2 days)
- Wrap existing code in interface implementations
- No behavior changes, just conforming to contracts
- Example:
  ```python
  class ExistingFacialRecognitionWrapper(VisionInterface):
      def __init__(self, config):
          self.legacy_impl = ExistingFacialRecognition(config)

      def detect_faces(self, image, correlation_id=None):
          # Adapt legacy interface to new contract
          faces = self.legacy_impl.recognize_faces(image.data)
          return [Face(name=f.name, confidence=f.conf, ...) for f in faces]
  ```

**Phase 3: Mock Implementations** (1 day)
- Create mock versions of all interfaces
- Enable hardware-independent testing

**Phase 4: Factory Integration** (1 day)
- Update main.py to use ModuleFactory
- Add config-driven driver selection
- Validate with integration tests

**Phase 5: Refactor Existing Code** (2-3 days)
- Update agents to use interfaces instead of concrete classes
- Add correlation_id propagation
- Improve error handling

### 6.2 Validation Checklist

Before Phase 3 is considered complete:

- [ ] All 4 interfaces defined with Protocol
- [ ] Performance budgets documented for each operation
- [ ] Error types defined for each module
- [ ] Mock implementations created for all interfaces
- [ ] Factory pattern implemented
- [ ] Configuration schemas defined (Pydantic models)
- [ ] Health monitoring integrated
- [ ] Correlation ID support added
- [ ] Contract tests written
- [ ] Migration path documented

---

## 7. Future Enhancements

### 7.1 Hardware-in-the-Loop (HIL) Testing

Connect to hardware simulators (QEMU, Renode) for realistic testing without physical devices.

### 7.2 Performance Monitoring

Add instrumentation to track:
- Operation latencies (histograms)
- Error rates by type
- Health status transitions

### 7.3 Circuit Breaker Pattern

Prevent cascade failures when hardware is degraded:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def capture_with_protection(self, correlation_id=None):
    return self.vision.capture(correlation_id)
```

### 7.4 Capability Discovery

Allow implementations to declare capabilities:
```python
class VisionInterface(Protocol):
    def get_capabilities(self) -> Set[str]:
        """Return set of supported features: {'face_detection', 'rtsp_streaming', ...}"""
        ...
```

---

## Conclusion

This module interface specification provides:
- ✅ Clear contracts for all major modules
- ✅ Testability through mock implementations
- ✅ Performance transparency via budgets
- ✅ Error handling strategy
- ✅ Migration path from existing code

**Next Steps**:
1. Review and approve this specification
2. Implement mock versions of all interfaces
3. Create ModuleFactory for driver selection
4. Begin migration of existing code to use interfaces

**Status**: Ready for implementation (Phase 3, Item #7 complete)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Author**: Claude (AI Assistant)
**Review Status**: Draft - Awaiting approval
