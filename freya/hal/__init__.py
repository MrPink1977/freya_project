"""
Hardware Abstraction Layer for Freya.

This module provides Protocol-based interfaces and wrapper implementations
for all hardware-dependent modules (Vision, Memory, Audio, IoT).

The HAL enables:
- Testability via mock implementations
- Swappable drivers without code changes
- Consistent correlation ID tracking
- Health monitoring across all modules
"""

from .interfaces import (
    AudioInterface,
    VisionInterface,
    MemoryInterface,
    IoTInterface,
    # Data classes
    Image,
    Face,
    Transcription,
    Memory,
    SearchResult,
    Device,
    DeviceCommand,
    # Enums
    TTSEngine,
    DeviceType,
    DeviceState,
    # Exceptions
    CameraUnavailableError,
    FaceDetectionError,
    MemoryStoreError,
    AudioCaptureError,
    TranscriptionError,
    SpeechSynthesisError,
    DeviceConnectionError,
    DeviceCommandError,
)
from .factory import ModuleFactory, create_vision, create_memory, create_audio, create_iot

__all__ = [
    # Interfaces
    "AudioInterface",
    "VisionInterface",
    "MemoryInterface",
    "IoTInterface",
    # Data classes
    "Image",
    "Face",
    "Transcription",
    "Memory",
    "SearchResult",
    "Device",
    "DeviceCommand",
    # Enums
    "TTSEngine",
    "DeviceType",
    "DeviceState",
    # Exceptions
    "CameraUnavailableError",
    "FaceDetectionError",
    "MemoryStoreError",
    "AudioCaptureError",
    "TranscriptionError",
    "SpeechSynthesisError",
    "DeviceConnectionError",
    "DeviceCommandError",
    # Factory
    "ModuleFactory",
    "create_vision",
    "create_memory",
    "create_audio",
    "create_iot",
]
