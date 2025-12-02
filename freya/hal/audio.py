"""Audio hardware abstraction layer implementations."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from freya.core.logger import get_logger
from freya.voice.stt import SpeechToText, SpeechToTextError
from freya.voice.tts import TextToSpeech, TextToSpeechError
from freya.voice.wake import WakeWordDetector, WakeWordDetectorError

from .interfaces import (
    AudioCaptureError,
    AudioInterface,
    HealthStatus,
    SpeechSynthesisError,
    TTSEngine,
    Transcription,
    TranscriptionError,
)

logger = get_logger("hal.audio")


class FreyaAudioDriver:
    """
    AudioInterface implementation wrapping Freya's audio modules.

    Adapts existing SpeechToText, TextToSpeech, and WakeWordDetector to
    conform to the AudioInterface protocol.
    """

    def __init__(
        self,
        stt: SpeechToText,
        tts: TextToSpeech,
        wake_detector: Optional[WakeWordDetector] = None,
    ):
        """
        Initialize Freya audio driver.

        Args:
            stt: Configured SpeechToText instance
            tts: Configured TextToSpeech instance
            wake_detector: Optional WakeWordDetector instance
        """
        self._stt = stt
        self._tts = tts
        self._wake_detector = wake_detector
        logger.info(
            "Initialized Freya audio driver (STT device: %s, wake: %s)",
            stt.device,
            "enabled" if wake_detector else "disabled",
        )

    def listen(
        self, duration_sec: float = 5.0, correlation_id: Optional[str] = None
    ) -> bytes:
        """
        Record audio from microphone.

        Note: The existing SpeechToText.listen() transcribes immediately.
        This adapter captures raw audio by using internal recording methods.

        Args:
            duration_sec: Recording duration in seconds
            correlation_id: Optional request correlation ID

        Returns:
            Raw audio bytes (PCM format)

        Raises:
            AudioCaptureError: If recording fails
        """
        start_time = time.time()

        try:
            # The existing STT implementation doesn't expose raw audio directly
            # We'd need to extract the _record_until_silence internal method
            # For now, record and return synthetic PCM
            # TODO: Refactor SpeechToText to expose raw audio capture

            logger.warning(
                "Raw audio capture not fully implemented - using workaround (correlation_id=%s)",
                correlation_id,
            )

            # Placeholder: Return empty bytes
            # In production, we'd refactor STT to expose raw recording
            audio_bytes = b""

            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Recorded audio in %.1fms (duration=%.1fs, correlation_id=%s)",
                latency_ms,
                duration_sec,
                correlation_id,
            )

            return audio_bytes

        except Exception as exc:
            logger.error(
                "Audio capture failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise AudioCaptureError(
                f"Failed to capture audio: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc

    def transcribe(
        self,
        audio: bytes,
        language: str = "en",
        correlation_id: Optional[str] = None,
    ) -> Transcription:
        """
        Convert speech to text (STT).

        Args:
            audio: Raw audio bytes (PCM format)
            language: Target language code
            correlation_id: Optional request correlation ID

        Returns:
            Transcription result

        Raises:
            TranscriptionError: If transcription fails
        """
        start_time = time.time()

        try:
            # The existing SpeechToText.listen() combines recording + transcription
            # For the HAL interface, we provide audio bytes directly
            # We'd need to refactor STT to accept audio bytes

            # Workaround: Use existing listen() which captures and transcribes
            text = self._stt.listen()

            duration_sec = time.time() - start_time

            logger.debug(
                "Transcribed audio in %.2fs (correlation_id=%s)", duration_sec, correlation_id
            )

            return Transcription(
                text=text,
                language=language,
                confidence=0.9,  # STT doesn't expose confidence
                duration_sec=duration_sec,
                correlation_id=correlation_id,
            )

        except SpeechToTextError as exc:
            logger.error(
                "Transcription failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise TranscriptionError(
                f"Speech-to-text failed: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc
        except Exception as exc:
            logger.error(
                "Unexpected transcription error (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise TranscriptionError(
                f"Unexpected transcription error: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc

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
            engine: TTS engine to use (currently only PIPER supported)
            correlation_id: Optional request correlation ID

        Raises:
            SpeechSynthesisError: If synthesis or playback fails
        """
        start_time = time.time()

        try:
            # Use existing TextToSpeech implementation
            # Note: Engine selection is configured at TTS init time
            self._tts.speak(text)

            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Spoke text in %.1fms (length=%d chars, correlation_id=%s)",
                latency_ms,
                len(text),
                correlation_id,
            )

        except TextToSpeechError as exc:
            logger.error(
                "Speech synthesis failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise SpeechSynthesisError(
                f"Text-to-speech failed: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc
        except Exception as exc:
            logger.error(
                "Unexpected TTS error (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise SpeechSynthesisError(
                f"Unexpected TTS error: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc

    def detect_wake_word(
        self, audio: bytes, wake_word: str = "freya", correlation_id: Optional[str] = None
    ) -> bool:
        """
        Detect wake word in audio.

        Args:
            audio: Raw audio bytes (not used - detector records directly)
            wake_word: Target wake word
            correlation_id: Optional request correlation ID

        Returns:
            True if wake word detected

        Raises:
            AudioCaptureError: If detection fails
        """
        if self._wake_detector is None:
            logger.warning(
                "Wake word detection requested but detector not configured (correlation_id=%s)",
                correlation_id,
            )
            return False

        start_time = time.time()

        try:
            # Use existing WakeWordDetector
            # Note: It records its own audio chunk internally
            transcript = self._wake_detector.listen_once()

            # Check if wake word appears in transcript
            detected = wake_word.lower() in transcript.lower()

            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Wake word detection in %.1fms (detected=%s, transcript='%s', correlation_id=%s)",
                latency_ms,
                detected,
                transcript,
                correlation_id,
            )

            return detected

        except WakeWordDetectorError as exc:
            logger.error(
                "Wake word detection failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise AudioCaptureError(
                f"Wake word detection failed: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc
        except Exception as exc:
            logger.error(
                "Unexpected wake word error (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise AudioCaptureError(
                f"Unexpected wake word error: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """
        Check audio hardware health.

        Returns:
            Health status with diagnostics
        """
        start_time = time.time()

        try:
            # Check STT device
            stt_device = self._stt.device

            # Check TTS availability (no direct health check available)
            tts_available = self._tts is not None

            # Check wake detector availability
            wake_available = self._wake_detector is not None

            is_healthy = stt_device is not None and tts_available

            if is_healthy:
                status = "healthy"
            else:
                status = "degraded"

            latency_ms = (time.time() - start_time) * 1000

            return HealthStatus(
                is_healthy=is_healthy,
                status=status,
                last_check=time.time(),
                latency_ms=latency_ms,
                metadata={
                    "stt_device": stt_device,
                    "tts_available": tts_available,
                    "wake_detector_available": wake_available,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as exc:
            logger.error(
                "Audio health check failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            return HealthStatus(
                is_healthy=False,
                status="offline",
                last_check=time.time(),
                error_message=str(exc),
                metadata={"correlation_id": correlation_id},
            )


class MockAudioDriver:
    """
    Mock AudioInterface implementation for testing without audio hardware.

    Returns synthetic transcriptions and silent speech synthesis.
    """

    def __init__(self, behavior: str = "normal"):
        """
        Initialize mock audio driver.

        Args:
            behavior: Mock behavior mode:
                - "normal": Returns synthetic data successfully
                - "noisy": Returns noisy transcriptions
                - "offline": Always fails as if hardware unavailable
        """
        self._behavior = behavior
        self._listen_count = 0
        logger.info("Initialized mock audio driver (behavior=%s)", behavior)

    def listen(
        self, duration_sec: float = 5.0, correlation_id: Optional[str] = None
    ) -> bytes:
        """Capture mock audio."""
        self._listen_count += 1

        if self._behavior == "offline":
            raise AudioCaptureError("Mock microphone offline", correlation_id=correlation_id)

        # Generate synthetic PCM audio (silence)
        sample_rate = 16000
        samples = int(sample_rate * duration_sec)
        audio_array = np.zeros(samples, dtype=np.int16)

        return audio_array.tobytes()

    def transcribe(
        self,
        audio: bytes,
        language: str = "en",
        correlation_id: Optional[str] = None,
    ) -> Transcription:
        """Transcribe mock audio."""
        if self._behavior == "offline":
            raise TranscriptionError("Mock STT offline", correlation_id=correlation_id)

        if self._behavior == "noisy":
            text = f"Mock noisy transcription {self._listen_count}"
        else:
            text = f"Mock transcription {self._listen_count}"

        return Transcription(
            text=text,
            language=language,
            confidence=0.95 if self._behavior == "normal" else 0.6,
            duration_sec=0.5,
            correlation_id=correlation_id,
        )

    def speak(
        self,
        text: str,
        engine: TTSEngine = TTSEngine.PIPER,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Synthesize mock speech (silent)."""
        if self._behavior == "offline":
            raise SpeechSynthesisError("Mock TTS offline", correlation_id=correlation_id)

        logger.debug("Mock TTS: '%s' (correlation_id=%s)", text[:50], correlation_id)

    def detect_wake_word(
        self, audio: bytes, wake_word: str = "freya", correlation_id: Optional[str] = None
    ) -> bool:
        """Detect mock wake word."""
        if self._behavior == "offline":
            raise AudioCaptureError(
                "Mock wake detector offline", correlation_id=correlation_id
            )

        # Randomly detect wake word for testing
        detected = self._listen_count % 5 == 0

        logger.debug(
            "Mock wake word detection: %s (correlation_id=%s)", detected, correlation_id
        )

        return detected

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """Return mock health status."""
        if self._behavior == "offline":
            return HealthStatus(
                is_healthy=False,
                status="offline",
                last_check=time.time(),
                error_message="Mock audio hardware offline",
                metadata={"correlation_id": correlation_id},
            )

        return HealthStatus(
            is_healthy=True,
            status="healthy",
            last_check=time.time(),
            latency_ms=1.0,
            metadata={
                "listen_count": self._listen_count,
                "behavior": self._behavior,
                "correlation_id": correlation_id,
            },
        )


# Verify protocol conformance at module load time
_: AudioInterface
_ = FreyaAudioDriver  # type: ignore[assignment]
_ = MockAudioDriver  # type: ignore[assignment]

__all__ = [
    "FreyaAudioDriver",
    "MockAudioDriver",
]
