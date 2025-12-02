"""Factory functions for creating HAL module instances."""

from __future__ import annotations

from typing import Dict, Literal, Type

from freya.core.config import (
    FaceRecognitionConfig,
    SpeechToTextConfig,
    TextToSpeechConfig,
    WakeDetectorConfig,
)
from freya.core.logger import get_logger
from freya.memory.memory_store import ChromaMemoryStore
from freya.vision.facial_recognition import FacialRecognition
from freya.voice.stt import SpeechToText
from freya.voice.tts import TextToSpeech
from freya.voice.wake import WakeWordDetector

from .audio import FreyaAudioDriver, MockAudioDriver
from .interfaces import AudioInterface, IoTInterface, MemoryInterface, VisionInterface
from .iot import HomeAssistantDriver, MockIoTDriver
from .memory import ChromaMemoryDriver, MockMemoryDriver
from .vision import MockCameraDriver, ReolinkCameraDriver

logger = get_logger("hal.factory")


# ============================================================================
# Module Factory
# ============================================================================


class ModuleFactory:
    """
    Factory for creating HAL module instances.

    Provides centralized driver registration and instantiation with
    automatic driver selection based on configuration.
    """

    # Driver registries
    _vision_drivers: Dict[str, Type[VisionInterface]] = {
        "reolink": ReolinkCameraDriver,
        "mock": MockCameraDriver,
    }

    _memory_drivers: Dict[str, Type[MemoryInterface]] = {
        "chroma": ChromaMemoryDriver,
        "mock": MockMemoryDriver,
    }

    _audio_drivers: Dict[str, Type[AudioInterface]] = {
        "freya": FreyaAudioDriver,
        "mock": MockAudioDriver,
    }

    _iot_drivers: Dict[str, Type[IoTInterface]] = {
        "homeassistant": HomeAssistantDriver,
        "mock": MockIoTDriver,
    }

    @classmethod
    def register_vision_driver(cls, name: str, driver_class: Type[VisionInterface]) -> None:
        """Register a custom vision driver."""
        cls._vision_drivers[name] = driver_class
        logger.info("Registered vision driver: %s", name)

    @classmethod
    def register_memory_driver(cls, name: str, driver_class: Type[MemoryInterface]) -> None:
        """Register a custom memory driver."""
        cls._memory_drivers[name] = driver_class
        logger.info("Registered memory driver: %s", name)

    @classmethod
    def register_audio_driver(cls, name: str, driver_class: Type[AudioInterface]) -> None:
        """Register a custom audio driver."""
        cls._audio_drivers[name] = driver_class
        logger.info("Registered audio driver: %s", name)

    @classmethod
    def register_iot_driver(cls, name: str, driver_class: Type[IoTInterface]) -> None:
        """Register a custom IoT driver."""
        cls._iot_drivers[name] = driver_class
        logger.info("Registered IoT driver: %s", name)

    @classmethod
    def create_vision(
        cls,
        driver: Literal["reolink", "mock"] = "reolink",
        face_config: FaceRecognitionConfig | None = None,
        **kwargs,
    ) -> VisionInterface:
        """
        Create vision module instance.

        Args:
            driver: Driver name ("reolink" or "mock")
            face_config: Optional FaceRecognitionConfig for real drivers
            **kwargs: Additional driver-specific arguments

        Returns:
            Vision module instance

        Raises:
            ValueError: If driver not found
        """
        driver_class = cls._vision_drivers.get(driver)
        if not driver_class:
            raise ValueError(
                f"Unknown vision driver: {driver}. "
                f"Available: {list(cls._vision_drivers.keys())}"
            )

        if driver == "mock":
            behavior = kwargs.get("behavior", "normal")
            instance = MockCameraDriver(behavior=behavior)
        elif driver == "reolink":
            if face_config is None:
                raise ValueError("face_config required for reolink driver")
            facial_recognition = FacialRecognition(face_config)
            rtsp_handler = kwargs.get("rtsp_handler")
            instance = ReolinkCameraDriver(
                facial_recognition=facial_recognition,
                rtsp_handler=rtsp_handler,
            )
        else:
            # Generic instantiation
            instance = driver_class(**kwargs)  # type: ignore

        logger.info("Created vision module: %s", driver)
        return instance

    @classmethod
    def create_memory(
        cls,
        driver: Literal["chroma", "mock"] = "chroma",
        db_path: str | None = None,
        **kwargs,
    ) -> MemoryInterface:
        """
        Create memory module instance.

        Args:
            driver: Driver name ("chroma" or "mock")
            db_path: Database path (required for chroma driver)
            **kwargs: Additional driver-specific arguments

        Returns:
            Memory module instance

        Raises:
            ValueError: If driver not found
        """
        driver_class = cls._memory_drivers.get(driver)
        if not driver_class:
            raise ValueError(
                f"Unknown memory driver: {driver}. "
                f"Available: {list(cls._memory_drivers.keys())}"
            )

        if driver == "mock":
            behavior = kwargs.get("behavior", "normal")
            instance = MockMemoryDriver(behavior=behavior)
        elif driver == "chroma":
            if db_path is None:
                raise ValueError("db_path required for chroma driver")
            memory_store = ChromaMemoryStore(db_path=db_path)
            instance = ChromaMemoryDriver(memory_store=memory_store)
        else:
            # Generic instantiation
            instance = driver_class(**kwargs)  # type: ignore

        logger.info("Created memory module: %s", driver)
        return instance

    @classmethod
    def create_audio(
        cls,
        driver: Literal["freya", "mock"] = "freya",
        stt_config: SpeechToTextConfig | None = None,
        tts_config: TextToSpeechConfig | None = None,
        wake_config: WakeDetectorConfig | None = None,
        **kwargs,
    ) -> AudioInterface:
        """
        Create audio module instance.

        Args:
            driver: Driver name ("freya" or "mock")
            stt_config: SpeechToTextConfig (required for freya driver)
            tts_config: TextToSpeechConfig (required for freya driver)
            wake_config: Optional WakeDetectorConfig
            **kwargs: Additional driver-specific arguments

        Returns:
            Audio module instance

        Raises:
            ValueError: If driver not found
        """
        driver_class = cls._audio_drivers.get(driver)
        if not driver_class:
            raise ValueError(
                f"Unknown audio driver: {driver}. "
                f"Available: {list(cls._audio_drivers.keys())}"
            )

        if driver == "mock":
            behavior = kwargs.get("behavior", "normal")
            instance = MockAudioDriver(behavior=behavior)
        elif driver == "freya":
            if stt_config is None or tts_config is None:
                raise ValueError("stt_config and tts_config required for freya driver")

            stt = SpeechToText(stt_config)
            tts = TextToSpeech(tts_config)
            wake_detector = WakeWordDetector(wake_config) if wake_config else None

            instance = FreyaAudioDriver(stt=stt, tts=tts, wake_detector=wake_detector)
        else:
            # Generic instantiation
            instance = driver_class(**kwargs)  # type: ignore

        logger.info("Created audio module: %s", driver)
        return instance

    @classmethod
    def create_iot(
        cls,
        driver: Literal["homeassistant", "mock"] = "homeassistant",
        base_url: str | None = None,
        access_token: str | None = None,
        **kwargs,
    ) -> IoTInterface:
        """
        Create IoT module instance.

        Args:
            driver: Driver name ("homeassistant" or "mock")
            base_url: Home Assistant URL (required for homeassistant driver)
            access_token: Access token (required for homeassistant driver)
            **kwargs: Additional driver-specific arguments

        Returns:
            IoT module instance

        Raises:
            ValueError: If driver not found
        """
        driver_class = cls._iot_drivers.get(driver)
        if not driver_class:
            raise ValueError(
                f"Unknown IoT driver: {driver}. "
                f"Available: {list(cls._iot_drivers.keys())}"
            )

        if driver == "mock":
            behavior = kwargs.get("behavior", "normal")
            instance = MockIoTDriver(behavior=behavior)
        elif driver == "homeassistant":
            if base_url is None or access_token is None:
                raise ValueError("base_url and access_token required for homeassistant driver")
            instance = HomeAssistantDriver(base_url=base_url, access_token=access_token)
        else:
            # Generic instantiation
            instance = driver_class(**kwargs)  # type: ignore

        logger.info("Created IoT module: %s", driver)
        return instance


# ============================================================================
# Convenience Functions
# ============================================================================


def create_vision(
    driver: Literal["reolink", "mock"] = "reolink",
    face_config: FaceRecognitionConfig | None = None,
    **kwargs,
) -> VisionInterface:
    """
    Create vision module instance (convenience wrapper).

    Args:
        driver: Driver name ("reolink" or "mock")
        face_config: Optional FaceRecognitionConfig for real drivers
        **kwargs: Additional driver-specific arguments

    Returns:
        Vision module instance
    """
    return ModuleFactory.create_vision(driver=driver, face_config=face_config, **kwargs)


def create_memory(
    driver: Literal["chroma", "mock"] = "chroma",
    db_path: str | None = None,
    **kwargs,
) -> MemoryInterface:
    """
    Create memory module instance (convenience wrapper).

    Args:
        driver: Driver name ("chroma" or "mock")
        db_path: Database path (required for chroma driver)
        **kwargs: Additional driver-specific arguments

    Returns:
        Memory module instance
    """
    return ModuleFactory.create_memory(driver=driver, db_path=db_path, **kwargs)


def create_audio(
    driver: Literal["freya", "mock"] = "freya",
    stt_config: SpeechToTextConfig | None = None,
    tts_config: TextToSpeechConfig | None = None,
    wake_config: WakeDetectorConfig | None = None,
    **kwargs,
) -> AudioInterface:
    """
    Create audio module instance (convenience wrapper).

    Args:
        driver: Driver name ("freya" or "mock")
        stt_config: SpeechToTextConfig (required for freya driver)
        tts_config: TextToSpeechConfig (required for freya driver)
        wake_config: Optional WakeDetectorConfig
        **kwargs: Additional driver-specific arguments

    Returns:
        Audio module instance
    """
    return ModuleFactory.create_audio(
        driver=driver,
        stt_config=stt_config,
        tts_config=tts_config,
        wake_config=wake_config,
        **kwargs,
    )


def create_iot(
    driver: Literal["homeassistant", "mock"] = "homeassistant",
    base_url: str | None = None,
    access_token: str | None = None,
    **kwargs,
) -> IoTInterface:
    """
    Create IoT module instance (convenience wrapper).

    Args:
        driver: Driver name ("homeassistant" or "mock")
        base_url: Home Assistant URL (required for homeassistant driver)
        access_token: Access token (required for homeassistant driver)
        **kwargs: Additional driver-specific arguments

    Returns:
        IoT module instance
    """
    return ModuleFactory.create_iot(
        driver=driver,
        base_url=base_url,
        access_token=access_token,
        **kwargs,
    )


__all__ = [
    "ModuleFactory",
    "create_vision",
    "create_memory",
    "create_audio",
    "create_iot",
]
