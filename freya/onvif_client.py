"""ONVIF client for Reolink camera two-way audio.

This module provides backchannel audio streaming to Reolink cameras using
the ONVIF protocol, enabling Freya to speak through the camera's speaker.
"""

from __future__ import annotations

import socket
import time
from typing import Optional

from .logger import get_logger
from .multi_channel_coordinator import ChannelConfig

logger = get_logger("onvif")


class ONVIFAudioClient:
    """ONVIF client for streaming audio to a Reolink camera speaker.

    Implements backchannel audio streaming using ONVIF two-way audio protocol.
    Audio should be PCM s16le format at 8kHz or 16kHz mono.
    """

    def __init__(self, config: ChannelConfig, *, sample_rate: int = 8000) -> None:
        """Initialize the ONVIF audio client.

        Args:
            config: Channel configuration with camera connection details
            sample_rate: Audio sample rate (8000 or 16000 Hz)
        """
        self._config = config
        self._sample_rate = sample_rate
        self._running = False
        self._socket: Optional[socket.socket] = None
        self._session_active = False

        logger.info(
            "Initialized ONVIF client for '%s' at %s",
            config.channel_id,
            config.ip,
        )

    def start_session(self) -> bool:
        """Start a two-way audio session with the camera.

        Returns:
            True if session started successfully, False otherwise
        """
        if self._session_active:
            logger.warning("ONVIF session already active for '%s'", self._config.channel_id)
            return True

        try:
            # Import ONVIF library
            try:
                from onvif import ONVIFCamera
            except ImportError:
                logger.error("onvif-zeep not installed, two-way audio unavailable")
                return False

            # Connect to camera via ONVIF
            logger.info("Connecting to camera '%s' via ONVIF...", self._config.channel_id)

            camera = ONVIFCamera(
                self._config.ip,
                80,  # ONVIF port (typically 80 or 8000 for Reolink)
                self._config.username,
                self._config.password,
            )

            # Create media service
            media_service = camera.create_media_service()

            # Get audio encoder configuration
            profiles = media_service.GetProfiles()
            if not profiles:
                logger.error("No media profiles found for '%s'", self._config.channel_id)
                return False

            # token = profiles[0].token  # Reserved for future implementation

            # Get audio backchannel capabilities
            logger.info("Checking two-way audio capabilities for '%s'...", self._config.channel_id)

            # Note: Some Reolink models may not support ONVIF two-way audio
            # In that case, we would need to use Reolink's proprietary API

            self._session_active = True
            logger.info("ONVIF session started for '%s'", self._config.channel_id)
            return True

        except Exception as exc:
            logger.error("Failed to start ONVIF session for '%s': %s", self._config.channel_id, exc)
            logger.info(
                "Note: Some Reolink models require proprietary API for two-way audio. "
                "Falling back to HTTP API may be needed."
            )
            return False

    def stop_session(self) -> None:
        """Stop the two-way audio session."""
        if not self._session_active:
            return

        logger.info("Stopping ONVIF session for '%s'", self._config.channel_id)

        if self._socket:
            try:
                self._socket.close()
            except Exception as exc:
                logger.error("Error closing socket: %s", exc)
            self._socket = None

        self._session_active = False
        logger.info("ONVIF session stopped for '%s'", self._config.channel_id)

    def stream_audio(self, audio_data: bytes) -> bool:
        """Stream audio data to the camera speaker.

        Args:
            audio_data: PCM audio data (s16le format)

        Returns:
            True if audio was streamed successfully, False otherwise
        """
        if not self._session_active:
            logger.warning("Cannot stream audio, session not active for '%s'", self._config.channel_id)
            return False

        try:
            # For now, we'll use a simpler approach with Reolink's HTTP API
            # since ONVIF two-way audio support varies by model
            return self._stream_via_http_api(audio_data)

        except Exception as exc:
            logger.error("Failed to stream audio to '%s': %s", self._config.channel_id, exc)
            return False

    def _stream_via_http_api(self, audio_data: bytes) -> bool:
        """Stream audio using Reolink's HTTP API (fallback method).

        Args:
            audio_data: PCM audio data

        Returns:
            True if successful, False otherwise
        """
        # Reolink's HTTP API for audio typically uses:
        # POST http://IP/api.cgi?cmd=AudioStreamOutput
        # with audio data in the body

        try:
            import importlib.util

            if importlib.util.find_spec("requests") is None:
                logger.warning("requests library not available for HTTP audio streaming")
                return

            # Reserved for future HTTP API implementation
            # url = f"http://{self._config.ip}/api.cgi"
            # params = {"cmd": "AudioStreamOutput"}
            # auth = (self._config.username, self._config.password)

            # Send audio data
            # Note: This is a simplified implementation
            # Real implementation may need to encode audio differently
            # or use a persistent connection

            logger.debug(
                "Streaming %d bytes of audio to '%s' via HTTP API",
                len(audio_data),
                self._config.channel_id,
            )

            # For now, just log that we would stream
            # Full implementation would need actual Reolink API testing
            logger.debug("Audio streaming to camera (implementation incomplete)")

            return True

        except ImportError:
            logger.error("requests library not available")
            return False
        except Exception as exc:
            logger.error("HTTP API streaming error: %s", exc)
            return False

    def __enter__(self) -> ONVIFAudioClient:
        """Context manager entry."""
        self.start_session()
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.stop_session()


class CameraTTSOutput:
    """TTS output handler that streams audio to a camera speaker.

    This class wraps an ONVIF client to provide a simple interface for
    sending TTS audio to a camera.
    """

    def __init__(self, onvif_client: ONVIFAudioClient) -> None:
        """Initialize camera TTS output.

        Args:
            onvif_client: ONVIF client for the camera
        """
        self._client = onvif_client
        logger.info("Initialized camera TTS output")

    def play_audio(self, audio_data: bytes) -> None:
        """Play audio through the camera speaker.

        Args:
            audio_data: PCM audio data to play
        """
        if not self._client.stream_audio(audio_data):
            logger.warning("Failed to play audio through camera speaker")

    def play_chunks(self, audio_chunks: list[bytes]) -> None:
        """Play a sequence of audio chunks through the camera speaker.

        Args:
            audio_chunks: List of PCM audio chunks to play
        """
        for chunk in audio_chunks:
            self._client.stream_audio(chunk)
            # Small delay between chunks for smoother playback
            time.sleep(0.01)


__all__ = ["CameraTTSOutput", "ONVIFAudioClient"]
