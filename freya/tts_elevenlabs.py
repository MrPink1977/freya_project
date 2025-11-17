"""Text-to-speech using ElevenLabs API for high-quality voice synthesis."""

from __future__ import annotations

import io
import threading
from typing import Optional

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
except ImportError as exc:
    ElevenLabs = None  # type: ignore[assignment,misc]
    VoiceSettings = None  # type: ignore[assignment,misc]
    _ELEVENLABS_ERROR = exc
else:
    _ELEVENLABS_ERROR = None

try:
    import pyaudio
except ImportError as exc:
    pyaudio = None  # type: ignore[assignment]
    _PYAUDIO_ERROR = exc
else:
    _PYAUDIO_ERROR = None

from .logger import get_logger

logger = get_logger("tts.elevenlabs")


class TextToSpeechError(RuntimeError):
    """Raised when synthesising or playing speech fails."""


class ElevenLabsTTS:
    """Convert text responses into spoken audio output using ElevenLabs API."""

    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel - default voice
        model_id: str = "eleven_turbo_v2_5",  # Fastest, lowest latency
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ) -> None:
        """Initialize ElevenLabs TTS.

        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use (default: Rachel)
            model_id: Model to use (turbo_v2_5 for speed, multilingual_v2 for quality)
            stability: Voice stability (0-1, higher = more stable/consistent)
            similarity_boost: Voice similarity (0-1, higher = more similar to original)
            style: Style exaggeration (0-1, higher = more expressive)
            use_speaker_boost: Enable speaker boost for clarity
        """
        if _ELEVENLABS_ERROR is not None:
            raise TextToSpeechError(
                "ElevenLabs dependency missing: elevenlabs (pip install elevenlabs)"
            ) from _ELEVENLABS_ERROR
        if _PYAUDIO_ERROR is not None:
            raise TextToSpeechError(
                "Audio playback dependency missing: pyaudio (pip install pyaudio)"
            ) from _PYAUDIO_ERROR

        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self._stop_speech = threading.Event()

        # Initialize ElevenLabs client
        self._client = ElevenLabs(api_key=api_key)

        # Voice settings for optimal quality
        self._voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
        )

        logger.info(
            "Initialized ElevenLabs TTS with voice_id=%s, model=%s",
            voice_id,
            model_id,
        )

    def speak(self, text: str) -> None:
        """Synthesize and play the provided text using ElevenLabs.

        Args:
            text: Text to convert to speech
        """
        if not text or not text.strip():
            logger.debug("No text provided for speech output")
            return

        # Clear stop flag at start of new speech
        self._stop_speech.clear()

        trimmed = text.strip()
        logger.info("Speaking response: %s", trimmed[:1000])

        try:
            # Generate audio stream from ElevenLabs
            audio_stream = self._client.generate(
                text=trimmed,
                voice=self._voice_id,
                model=self._model_id,
                voice_settings=self._voice_settings,
                stream=True,  # Enable streaming for lower latency
            )

            # Stream and play audio
            self._play_audio_stream(audio_stream)

        except Exception as exc:
            logger.exception("Failed to synthesize or play speech: %s", exc)
            raise TextToSpeechError("Failed to synthesize speech with ElevenLabs") from exc

    def stop_speaking(self) -> None:
        """Signal the TTS to stop current playback."""
        self._stop_speech.set()
        logger.debug("Stop speech signal set")

    def preload_phrase(self, text: str) -> None:
        """Preload a phrase (no-op for ElevenLabs streaming).

        ElevenLabs uses streaming API, so preloading isn't as beneficial.
        This method is kept for interface compatibility.
        """
        logger.debug("Preload requested for '%s' (no-op for streaming API)", text[:50])

    def _play_audio_stream(self, audio_stream) -> None:
        """Play audio stream from ElevenLabs.

        Args:
            audio_stream: Generator yielding audio chunks
        """
        try:
            # Initialize PyAudio
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=22050,  # ElevenLabs default sample rate
                output=True,
            )

            try:
                # Stream audio chunks
                for chunk in audio_stream:
                    if self._stop_speech.is_set():
                        logger.debug("Stop signal received, halting playback")
                        break

                    if chunk:
                        stream.write(chunk)

            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()

        except Exception as exc:
            logger.exception("Failed to play audio stream: %s", exc)
            raise TextToSpeechError("Failed to play audio") from exc


# Popular ElevenLabs voice IDs for easy reference
VOICE_IDS = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",  # Calm, clear (default)
    "domi": "AZnzlk1XvdvUeBnXmlld",  # Strong, confident
    "bella": "EXAVITQu4vr4xnSDxMaL",  # Soft, warm
    "antoni": "ErXwobaYiN019PkySvjV",  # Well-rounded male
    "elli": "MF3mGyEYCl7XYWbV9V6O",  # Emotional, expressive
    "josh": "TxGEqnHWrfWFTfGW9XjX",  # Deep, authoritative male
    "arnold": "VR6AewLTigWG4xSOukaG",  # Crisp, professional male
    "adam": "pNInz6obpgDQGcFmaJgB",  # Deep, narrator male
    "sam": "yoZ06aMxZJJ28mfd3POQ",  # Raspy, dynamic male
}


__all__ = ["ElevenLabsTTS", "TextToSpeechError", "VOICE_IDS"]
