"""Multi-channel audio coordinator for Freya.

This module manages multiple audio input channels (system microphone and Reolink
cameras) and arbitrates which channel owns the active conversation at any time.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

from .logger import get_logger
from .multi_channel_coordinator import ChannelConfig, ChannelType
from .rtsp_stream import AudioChunk, RTSPStreamHandler, VideoFrame

logger = get_logger("coordinator")


class ChannelState(str, Enum):
    """State of an audio channel."""

    IDLE = "idle"  # Listening for wake word
    ACTIVE = "active"  # Owns the conversation
    DISABLED = "disabled"  # Offline or disabled


@dataclass
class ChannelStatus:
    """Runtime status of a channel."""

    channel_id: str
    state: ChannelState = ChannelState.IDLE
    last_wake_time: Optional[float] = None
    error_count: int = 0
    rtsp_handler: Optional[RTSPStreamHandler] = None


@dataclass
class AudioEvent:
    """Audio event from a channel."""

    channel_id: str
    audio_data: bytes
    sample_rate: int
    timestamp: float


@dataclass
class WakeEvent:
    """Wake word detection event from a channel."""

    channel_id: str
    transcript: str
    confidence: float
    timestamp: float


class MultiChannelCoordinator:
    """Coordinates multiple audio input channels and manages conversation ownership.

    Implements the architecture described in docs/multi_channel_overview.md:
    - Each channel runs wake word detection independently
    - First channel to detect wake word acquires conversation lock
    - Other channels continue listening but ignore wake words during conversation
    - Lock is released when conversation ends
    """

    def __init__(
        self,
        channels: List[ChannelConfig],
        *,
        wake_callback: Optional[Callable[[WakeEvent], None]] = None,
        audio_callback: Optional[Callable[[AudioEvent], None]] = None,
        video_callback: Optional[Callable[[str, VideoFrame], None]] = None,
        conversation_timeout: float = 30.0,
    ) -> None:
        """Initialize the multi-channel coordinator.

        Args:
            channels: List of channel configurations
            wake_callback: Callback when wake word is detected
            audio_callback: Callback for audio data from active channel
            video_callback: Callback for video frames (channel_id, frame)
            conversation_timeout: Auto-release lock after this many seconds of inactivity
        """
        self._channels = {ch.channel_id: ch for ch in channels if ch.enabled}
        self._wake_callback = wake_callback
        self._audio_callback = audio_callback
        self._video_callback = video_callback
        self._conversation_timeout = conversation_timeout

        self._channel_status: Dict[str, ChannelStatus] = {}
        self._conversation_lock = threading.Lock()
        self._active_channel: Optional[str] = None
        self._last_activity: float = 0.0
        self._running = False

        # Audio buffers for each channel
        self._audio_buffers: Dict[str, queue.Queue] = {}

        logger.info("Initialized coordinator with %d channel(s)", len(self._channels))
        for channel_id, config in self._channels.items():
            logger.info("  - %s (%s)", channel_id, config.channel_type.value)

    def start(self) -> None:
        """Start all enabled channels."""
        if self._running:
            logger.warning("Coordinator already running")
            return

        self._running = True

        for channel_id, config in self._channels.items():
            try:
                self._start_channel(channel_id, config)
            except Exception as exc:
                logger.error("Failed to start channel '%s': %s", channel_id, exc)
                self._channel_status[channel_id] = ChannelStatus(
                    channel_id=channel_id,
                    state=ChannelState.DISABLED,
                    error_count=1,
                )

        # Start timeout monitor thread
        timeout_thread = threading.Thread(
            target=self._timeout_monitor,
            name="channel-timeout-monitor",
            daemon=True,
        )
        timeout_thread.start()

        logger.info("Coordinator started")

    def stop(self) -> None:
        """Stop all channels and cleanup."""
        if not self._running:
            return

        logger.info("Stopping coordinator...")
        self._running = False

        # Stop all RTSP handlers
        for status in self._channel_status.values():
            if status.rtsp_handler:
                status.rtsp_handler.stop()

        logger.info("Coordinator stopped")

    def acquire_conversation(self, channel_id: str) -> bool:
        """Attempt to acquire the conversation lock for a channel.

        Args:
            channel_id: ID of the channel requesting the lock

        Returns:
            True if lock was acquired, False otherwise
        """
        with self._conversation_lock:
            # Already active
            if self._active_channel == channel_id:
                self._last_activity = time.time()
                return True

            # Another channel is active
            if self._active_channel is not None:
                logger.debug(
                    "Channel '%s' cannot acquire lock, '%s' is active",
                    channel_id,
                    self._active_channel,
                )
                return False

            # Acquire lock
            self._active_channel = channel_id
            self._last_activity = time.time()

            if channel_id in self._channel_status:
                self._channel_status[channel_id].state = ChannelState.ACTIVE
                self._channel_status[channel_id].last_wake_time = time.time()

            logger.info("Channel '%s' acquired conversation lock", channel_id)
            return True

    def release_conversation(self, channel_id: Optional[str] = None) -> None:
        """Release the conversation lock.

        Args:
            channel_id: Optional channel ID to verify ownership before release
        """
        with self._conversation_lock:
            # Verify ownership if channel_id provided
            if channel_id and self._active_channel != channel_id:
                logger.warning(
                    "Channel '%s' cannot release lock owned by '%s'",
                    channel_id,
                    self._active_channel,
                )
                return

            if self._active_channel:
                logger.info("Channel '%s' released conversation lock", self._active_channel)

                # Reset channel state to idle
                if self._active_channel in self._channel_status:
                    self._channel_status[self._active_channel].state = ChannelState.IDLE

            self._active_channel = None
            self._last_activity = 0.0

    def get_active_channel(self) -> Optional[str]:
        """Get the currently active channel ID."""
        with self._conversation_lock:
            return self._active_channel

    def is_channel_active(self, channel_id: str) -> bool:
        """Check if a specific channel is active."""
        with self._conversation_lock:
            return self._active_channel == channel_id

    def get_channel_status(self, channel_id: str) -> Optional[ChannelStatus]:
        """Get the status of a specific channel."""
        return self._channel_status.get(channel_id)

    def _start_channel(self, channel_id: str, config: ChannelConfig) -> None:
        """Start a single channel based on its type."""
        if config.channel_type == ChannelType.SYSTEM:
            # System microphone - will be handled by existing audio capture
            self._channel_status[channel_id] = ChannelStatus(
                channel_id=channel_id,
                state=ChannelState.IDLE,
            )
            self._audio_buffers[channel_id] = queue.Queue(maxsize=10)
            logger.info("System channel '%s' initialized", channel_id)

        elif config.channel_type == ChannelType.REOLINK:
            # Reolink camera via RTSP
            def audio_callback(chunk):
                return self._on_audio_chunk(channel_id, chunk)

            def video_callback(frame):
                if self._video_callback:
                    return self._on_video_frame(channel_id, frame)
                return None

            rtsp_handler = RTSPStreamHandler(
                config,
                audio_callback=audio_callback,
                video_callback=video_callback,
                audio_chunk_duration=1.0,
            )
            rtsp_handler.start()

            self._channel_status[channel_id] = ChannelStatus(
                channel_id=channel_id,
                state=ChannelState.IDLE,
                rtsp_handler=rtsp_handler,
            )
            self._audio_buffers[channel_id] = queue.Queue(maxsize=10)
            logger.info("Reolink channel '%s' started", channel_id)

    def _on_audio_chunk(self, channel_id: str, chunk: AudioChunk) -> None:
        """Handle audio chunk from a channel."""
        # Add to buffer for wake word detection
        if channel_id in self._audio_buffers:
            try:
                self._audio_buffers[channel_id].put_nowait(
                    AudioEvent(
                        channel_id=channel_id,
                        audio_data=chunk.data,
                        sample_rate=chunk.sample_rate,
                        timestamp=chunk.timestamp,
                    )
                )
            except queue.Full:
                # Drop oldest chunk
                try:
                    self._audio_buffers[channel_id].get_nowait()
                    self._audio_buffers[channel_id].put_nowait(
                        AudioEvent(
                            channel_id=channel_id,
                            audio_data=chunk.data,
                            sample_rate=chunk.sample_rate,
                            timestamp=chunk.timestamp,
                        )
                    )
                except queue.Empty:
                    pass

        # Forward to audio callback if this is the active channel
        if self.is_channel_active(channel_id) and self._audio_callback:
            self._audio_callback(
                AudioEvent(
                    channel_id=channel_id,
                    audio_data=chunk.data,
                    sample_rate=chunk.sample_rate,
                    timestamp=chunk.timestamp,
                )
            )

    def _on_video_frame(self, channel_id: str, frame: VideoFrame) -> None:
        """Handle video frame from a channel."""
        if self._video_callback:
            self._video_callback(channel_id, frame)

    def _timeout_monitor(self) -> None:
        """Monitor conversation timeout and auto-release lock."""
        while self._running:
            time.sleep(1.0)

            with self._conversation_lock:
                if self._active_channel and self._last_activity > 0:
                    elapsed = time.time() - self._last_activity
                    if elapsed > self._conversation_timeout:
                        logger.info(
                            "Conversation timeout after %.1fs, releasing lock from '%s'",
                            elapsed,
                            self._active_channel,
                        )
                        self.release_conversation()

    def get_audio_event(self, channel_id: str, timeout: float = 0.1) -> Optional[AudioEvent]:
        """Get the next audio event from a channel's buffer.

        Args:
            channel_id: Channel to get audio from
            timeout: Max time to wait in seconds

        Returns:
            AudioEvent or None if timeout/empty
        """
        if channel_id not in self._audio_buffers:
            return None

        try:
            return self._audio_buffers[channel_id].get(timeout=timeout)
        except queue.Empty:
            return None

    def __enter__(self) -> MultiChannelCoordinator:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.stop()


__all__ = ["AudioEvent", "ChannelState", "ChannelStatus", "MultiChannelCoordinator", "WakeEvent"]
