"""RTSP stream handler for Reolink IP cameras.

This module provides audio and video extraction from Reolink cameras via RTSP
streams. Audio is extracted as 16kHz mono PCM for compatibility with Freya's
STT pipeline, and video frames can be captured for facial recognition.
"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Callable, Optional

import numpy as np

from .logger import get_logger
from .multi_channel_coordinator import ChannelConfig

logger = get_logger("rtsp_stream")


@dataclass
class AudioChunk:
    """A chunk of audio data from an RTSP stream."""

    data: bytes
    sample_rate: int
    channels: int
    timestamp: float


@dataclass
class VideoFrame:
    """A video frame from an RTSP stream."""

    frame: np.ndarray  # BGR format
    timestamp: float


class RTSPStreamHandler:
    """Handles RTSP stream from a Reolink camera with audio/video extraction.

    Uses ffmpeg subprocess to demux RTSP stream into separate audio and video.
    Audio is converted to 16kHz mono PCM s16le for STT compatibility.
    """

    def __init__(
        self,
        config: ChannelConfig,
        *,
        audio_callback: Optional[Callable[[AudioChunk], None]] = None,
        video_callback: Optional[Callable[[VideoFrame], None]] = None,
        audio_chunk_duration: float = 1.0,
    ) -> None:
        """Initialize the RTSP stream handler.

        Args:
            config: Channel configuration with RTSP connection details
            audio_callback: Optional callback for audio chunks
            video_callback: Optional callback for video frames
            audio_chunk_duration: Duration of audio chunks in seconds (default 1.0)
        """
        self._config = config
        self._audio_callback = audio_callback
        self._video_callback = video_callback
        self._audio_chunk_duration = audio_chunk_duration

        self._running = False
        self._audio_thread: Optional[threading.Thread] = None
        self._video_thread: Optional[threading.Thread] = None
        self._audio_process: Optional[subprocess.Popen] = None
        self._video_process: Optional[subprocess.Popen] = None

        self._sample_rate = 16000  # Target sample rate for STT
        self._channels = 1  # Mono audio

        logger.info(
            "Initialized RTSP handler for channel '%s' at %s:%s",
            config.channel_id,
            config.ip,
            config.rtsp_port,
        )

    def start(self) -> None:
        """Start streaming from the RTSP source."""
        if self._running:
            logger.warning("RTSP handler already running for '%s'", self._config.channel_id)
            return

        self._running = True

        # Start audio extraction if callback is provided
        if self._audio_callback:
            self._audio_thread = threading.Thread(
                target=self._audio_loop,
                name=f"rtsp-audio-{self._config.channel_id}",
                daemon=True,
            )
            self._audio_thread.start()
            logger.info("Started audio extraction for '%s'", self._config.channel_id)

        # Start video extraction if callback is provided
        if self._video_callback:
            self._video_thread = threading.Thread(
                target=self._video_loop,
                name=f"rtsp-video-{self._config.channel_id}",
                daemon=True,
            )
            self._video_thread.start()
            logger.info("Started video extraction for '%s'", self._config.channel_id)

    def stop(self) -> None:
        """Stop streaming and clean up resources."""
        if not self._running:
            return

        logger.info("Stopping RTSP handler for '%s'", self._config.channel_id)
        self._running = False

        # Terminate ffmpeg processes
        if self._audio_process:
            self._audio_process.terminate()
            try:
                self._audio_process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._audio_process.kill()
            self._audio_process = None

        if self._video_process:
            self._video_process.terminate()
            try:
                self._video_process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._video_process.kill()
            self._video_process = None

        # Wait for threads to finish
        if self._audio_thread and self._audio_thread.is_alive():
            self._audio_thread.join(timeout=3.0)
        if self._video_thread and self._video_thread.is_alive():
            self._video_thread.join(timeout=3.0)

        logger.info("RTSP handler stopped for '%s'", self._config.channel_id)

    def _build_rtsp_url(self) -> str:
        """Build the RTSP URL from configuration."""
        return (
            f"rtsp://{self._config.username}:{self._config.password}"
            f"@{self._config.ip}:{self._config.rtsp_port}/h264Preview_01_main"
        )

    def _audio_loop(self) -> None:
        """Audio extraction loop using ffmpeg subprocess."""
        rtsp_url = self._build_rtsp_url()
        chunk_size = int(self._sample_rate * self._audio_chunk_duration * 2)  # 2 bytes per sample

        while self._running:
            try:
                # Start ffmpeg process for audio extraction
                cmd = [
                    "ffmpeg",
                    "-rtsp_transport",
                    "tcp",
                    "-i",
                    rtsp_url,
                    "-vn",  # No video
                    "-acodec",
                    "pcm_s16le",  # 16-bit PCM
                    "-ar",
                    str(self._sample_rate),  # 16kHz sample rate
                    "-ac",
                    str(self._channels),  # Mono
                    "-f",
                    "s16le",  # Raw PCM format
                    "pipe:1",  # Output to stdout
                ]

                self._audio_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=chunk_size,
                )

                logger.info("Audio extraction started for '%s'", self._config.channel_id)

                # Read audio chunks from ffmpeg stdout
                while self._running:
                    if not self._audio_process or not self._audio_process.stdout:
                        break

                    data = self._audio_process.stdout.read(chunk_size)
                    if not data:
                        logger.warning("Audio stream ended for '%s', reconnecting...", self._config.channel_id)
                        break

                    chunk = AudioChunk(
                        data=data,
                        sample_rate=self._sample_rate,
                        channels=self._channels,
                        timestamp=time.time(),
                    )

                    if self._audio_callback:
                        self._audio_callback(chunk)

            except Exception as exc:
                logger.error("Audio extraction error for '%s': %s", self._config.channel_id, exc)

            finally:
                if self._audio_process:
                    self._audio_process.terminate()
                    self._audio_process = None

            # Reconnect delay
            if self._running:
                logger.info("Reconnecting audio stream for '%s' in 3s...", self._config.channel_id)
                time.sleep(3.0)

    def _video_loop(self) -> None:
        """Video extraction loop using opencv."""
        try:
            import cv2
        except ImportError:
            logger.error("opencv-python not available, video extraction disabled")
            return

        rtsp_url = self._build_rtsp_url()

        while self._running:
            cap = None
            try:
                # Open RTSP stream with opencv
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffering for lower latency

                if not cap.isOpened():
                    logger.warning("Failed to open video stream for '%s', retrying...", self._config.channel_id)
                    time.sleep(3.0)
                    continue

                logger.info("Video extraction started for '%s'", self._config.channel_id)

                # Read frames
                while self._running:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("Video frame read failed for '%s', reconnecting...", self._config.channel_id)
                        break

                    video_frame = VideoFrame(frame=frame, timestamp=time.time())

                    if self._video_callback:
                        self._video_callback(video_frame)

                    # Limit frame rate to ~5fps for facial recognition (no need for full 30fps)
                    time.sleep(0.2)

            except Exception as exc:
                logger.error("Video extraction error for '%s': %s", self._config.channel_id, exc)

            finally:
                if cap:
                    cap.release()

            # Reconnect delay
            if self._running:
                logger.info("Reconnecting video stream for '%s' in 3s...", self._config.channel_id)
                time.sleep(3.0)

    def __enter__(self) -> RTSPStreamHandler:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.stop()


__all__ = ["AudioChunk", "RTSPStreamHandler", "VideoFrame"]
