"""
Protocol-based interfaces for Freya's hardware abstraction layer.

This module defines structural subtyping interfaces using typing.Protocol,
allowing any class with matching methods to satisfy the interface without
explicit inheritance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import numpy as np


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class Image:
    """Represents a captured image from a camera."""

    data: np.ndarray  # RGB or BGR image data
    timestamp: float
    source: str  # Camera identifier
    width: int
    height: int
    correlation_id: Optional[str] = None


@dataclass
class Face:
    """Represents a detected/recognized face in an image."""

    name: str  # "Unknown" if not recognized
    confidence: float  # 0.0-1.0
    bounding_box: tuple[int, int, int, int]  # (top, right, bottom, left)
    timestamp: float
    correlation_id: Optional[str] = None


@dataclass
class Transcription:
    """Result of speech-to-text transcription."""

    text: str
    language: str
    confidence: float  # 0.0-1.0
    duration_sec: float
    correlation_id: Optional[str] = None


@dataclass
class Memory:
    """A stored memory entry."""

    id: str
    content: str
    memory_type: str  # "conversation", "fact", "event"
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


@dataclass
class SearchResult:
    """A memory search result with relevance score."""

    memory: Memory
    score: float  # Relevance score 0.0-1.0
    distance: float  # Vector distance


@dataclass
class Device:
    """Represents a smart home device."""

    device_id: str
    name: str
    device_type: str  # "light", "switch", "sensor", etc.
    state: str  # "on", "off", "unavailable"
    attributes: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


@dataclass
class DeviceCommand:
    """Command to send to a device."""

    device_id: str
    action: str  # "turn_on", "turn_off", "set_brightness", etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


@dataclass
class HealthStatus:
    """Health status for a module."""

    is_healthy: bool
    status: str  # "healthy", "degraded", "offline"
    last_check: float
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Enums
# ============================================================================


class TTSEngine(str, Enum):
    """Supported text-to-speech engines."""

    PIPER = "piper"
    ELEVENLABS = "elevenlabs"


class DeviceType(str, Enum):
    """Smart home device types."""

    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    CLIMATE = "climate"
    MEDIA_PLAYER = "media_player"
    CAMERA = "camera"
    LOCK = "lock"


class DeviceState(str, Enum):
    """Device states."""

    ON = "on"
    OFF = "off"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


# ============================================================================
# Exceptions
# ============================================================================


class HALError(Exception):
    """Base exception for hardware abstraction layer errors."""

    def __init__(self, message: str, correlation_id: Optional[str] = None, **kwargs):
        super().__init__(message)
        self.correlation_id = correlation_id
        self.metadata = kwargs


class CameraUnavailableError(HALError):
    """Raised when camera cannot be accessed."""


class FaceDetectionError(HALError):
    """Raised when face detection fails."""


class MemoryStoreError(HALError):
    """Raised when memory storage operations fail."""


class AudioCaptureError(HALError):
    """Raised when audio recording fails."""


class TranscriptionError(HALError):
    """Raised when speech-to-text fails."""


class SpeechSynthesisError(HALError):
    """Raised when text-to-speech fails."""


class DeviceConnectionError(HALError):
    """Raised when device connection fails."""


class DeviceCommandError(HALError):
    """Raised when device command fails."""


# ============================================================================
# Vision Interface
# ============================================================================


@runtime_checkable
class VisionInterface(Protocol):
    """
    Protocol for vision/camera modules.

    Performance Budgets:
    - capture(): < 100ms (including hardware latency)
    - detect_faces(): < 500ms for 1080p image
    - health_check(): < 50ms
    """

    def capture(self, correlation_id: Optional[str] = None) -> Image:
        """
        Capture a single frame from the camera.

        Args:
            correlation_id: Optional request correlation ID for tracing

        Returns:
            Image object with RGB/BGR data

        Raises:
            CameraUnavailableError: If camera cannot be accessed
        """
        ...

    def detect_faces(
        self, image: Image, correlation_id: Optional[str] = None
    ) -> List[Face]:
        """
        Detect and identify faces in an image.

        Args:
            image: Image to analyze
            correlation_id: Optional request correlation ID

        Returns:
            List of detected faces (empty if none found)

        Raises:
            FaceDetectionError: If detection fails
        """
        ...

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """
        Check hardware health and connectivity.

        Returns:
            Health status with diagnostics
        """
        ...


# ============================================================================
# Memory Interface
# ============================================================================


@runtime_checkable
class MemoryInterface(Protocol):
    """
    Protocol for memory/storage modules.

    Performance Budgets:
    - store(): < 50ms (async write preferred)
    - retrieve(): < 100ms for 10k memories (HNSW index)
    - health_check(): < 50ms
    """

    async def store(
        self,
        content: str,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Memory:
        """
        Store a memory entry.

        Args:
            content: Memory content text
            memory_type: Type of memory (conversation, fact, event)
            metadata: Optional metadata dictionary
            correlation_id: Optional request correlation ID

        Returns:
            Stored memory object with ID

        Raises:
            MemoryStoreError: If storage fails
        """
        ...

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Semantic search for relevant memories.

        Args:
            query: Search query text
            top_k: Maximum number of results
            memory_type: Optional filter by memory type
            correlation_id: Optional request correlation ID

        Returns:
            List of search results sorted by relevance

        Raises:
            MemoryStoreError: If query fails
        """
        ...

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """
        Check memory store health.

        Returns:
            Health status with diagnostics
        """
        ...


# ============================================================================
# Audio Interface
# ============================================================================


@runtime_checkable
class AudioInterface(Protocol):
    """
    Protocol for audio modules (STT/TTS/wake word).

    Performance Budgets:
    - listen(): < 50ms overhead (plus recording time)
    - transcribe(): < 1s for 5s audio (Whisper tiny on CPU)
    - speak(): < 100ms to first audio (Piper)
    - detect_wake_word(): < 300ms per chunk
    - health_check(): < 50ms
    """

    def listen(
        self, duration_sec: float = 5.0, correlation_id: Optional[str] = None
    ) -> bytes:
        """
        Record audio from microphone.

        Args:
            duration_sec: Recording duration in seconds
            correlation_id: Optional request correlation ID

        Returns:
            Raw audio bytes (PCM format)

        Raises:
            AudioCaptureError: If recording fails
        """
        ...

    def transcribe(
        self,
        audio: bytes,
        language: str = "en",
        correlation_id: Optional[str] = None,
    ) -> Transcription:
        """
        Convert speech to text (STT).

        Args:
            audio: Raw audio bytes
            language: Target language code
            correlation_id: Optional request correlation ID

        Returns:
            Transcription result

        Raises:
            TranscriptionError: If transcription fails
        """
        ...

    def speak(
        self,
        text: str,
        engine: TTSEngine = TTSEngine.PIPER,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Convert text to speech and play (TTS).

        Args:
            text: Text to speak
            engine: TTS engine to use
            correlation_id: Optional request correlation ID

        Raises:
            SpeechSynthesisError: If synthesis or playback fails
        """
        ...

    def detect_wake_word(
        self, audio: bytes, wake_word: str = "freya", correlation_id: Optional[str] = None
    ) -> bool:
        """
        Detect wake word in audio.

        Args:
            audio: Raw audio bytes
            wake_word: Target wake word
            correlation_id: Optional request correlation ID

        Returns:
            True if wake word detected

        Raises:
            AudioCaptureError: If detection fails
        """
        ...

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """
        Check audio hardware health.

        Returns:
            Health status with diagnostics
        """
        ...


# ============================================================================
# IoT Interface
# ============================================================================


@runtime_checkable
class IoTInterface(Protocol):
    """
    Protocol for IoT/smart home modules.

    Performance Budgets:
    - discover_devices(): < 2s (local network scan)
    - send_command(): < 500ms (local network)
    - query_state(): < 300ms
    - health_check(): < 50ms
    """

    async def discover_devices(
        self,
        device_type: Optional[DeviceType] = None,
        correlation_id: Optional[str] = None,
    ) -> List[Device]:
        """
        Discover available smart devices.

        Args:
            device_type: Optional filter by device type
            correlation_id: Optional request correlation ID

        Returns:
            List of discovered devices

        Raises:
            DeviceConnectionError: If discovery fails
        """
        ...

    async def send_command(
        self, command: DeviceCommand, correlation_id: Optional[str] = None
    ) -> bool:
        """
        Send command to a device.

        Args:
            command: Device command to execute
            correlation_id: Optional request correlation ID

        Returns:
            True if command succeeded

        Raises:
            DeviceCommandError: If command fails
        """
        ...

    async def query_state(
        self, device_id: str, correlation_id: Optional[str] = None
    ) -> Device:
        """
        Query current device state.

        Args:
            device_id: Device identifier
            correlation_id: Optional request correlation ID

        Returns:
            Device with current state

        Raises:
            DeviceConnectionError: If query fails
        """
        ...

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """
        Check IoT hub connectivity.

        Returns:
            Health status with diagnostics
        """
        ...


__all__ = [
    # Interfaces
    "VisionInterface",
    "MemoryInterface",
    "AudioInterface",
    "IoTInterface",
    # Data classes
    "Image",
    "Face",
    "Transcription",
    "Memory",
    "SearchResult",
    "Device",
    "DeviceCommand",
    "HealthStatus",
    # Enums
    "TTSEngine",
    "DeviceType",
    "DeviceState",
    # Exceptions
    "HALError",
    "CameraUnavailableError",
    "FaceDetectionError",
    "MemoryStoreError",
    "AudioCaptureError",
    "TranscriptionError",
    "SpeechSynthesisError",
    "DeviceConnectionError",
    "DeviceCommandError",
]
