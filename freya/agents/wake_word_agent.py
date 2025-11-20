"""
WAKE WORD AGENT - Always-listening background wake word detection.

Runs independently, detects "Hey, Freya" and publishes transcript to MessageBus.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from freya.agents.base_agent import AgentCapability, BaseAgent
from freya.core.message_bus import Message, MessageBus, MessagePriority
from freya.logger import get_logger
from freya.stt import SpeechToText
from freya.wake import WakeWordDetector
from freya.wake_word_matcher import WakeWordMatcher


class WakeWordAgent(BaseAgent):
    """
    Agent that continuously listens for wake word in background.

    Subscribes to:
    - "wake.start" - Start listening
    - "wake.stop" - Stop listening
    - "wake.set_window" - Update session window

    Publishes to:
    - "wake.detected" - Wake word detected with transcript
    - "wake.timeout" - Session window expired
    - "wake.listening" - Status update
    """

    def __init__(
        self,
        agent_id: str,
        bus: MessageBus,
        stt: SpeechToText,
        wake_word: str = "Hey, Freya",
        wake_sensitivity: float = 0.75,
        session_window: float = 8.0,
        wake_detector: Optional[WakeWordDetector] = None,
        channel_id: str = "pc",
    ) -> None:
        """
        Initialize wake word agent.

        Args:
            agent_id: Unique agent identifier
            bus: Message bus for communication
            stt: Speech-to-text engine
            wake_word: Wake word phrase
            wake_sensitivity: Detection sensitivity (0-1)
            session_window: Seconds to keep session active after wake
            wake_detector: Optional lightweight wake detector (Whisper tiny)
            channel_id: Audio channel this agent listens on (pc, doorbell, etc.)
        """
        super().__init__(agent_id, bus)
        self._stt = stt
        self._wake_detector = wake_detector
        self._wake_matcher = WakeWordMatcher(
            wake_word=wake_word,
            sensitivity=wake_sensitivity,
            token_offset_limit=2,
        )
        self._session_window = max(0.0, session_window)
        self._session_active_until = 0.0
        self._channel_id = channel_id

        # State management
        self._listening = False
        self._listen_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize wake word agent."""
        self.logger.info(
            f"WakeWordAgent initialized: wake_word='{self._wake_matcher.wake_word_display}', "
            f"session_window={self._session_window}s, channel={self._channel_id}"
        )

    def get_capabilities(self) -> list[AgentCapability]:
        """Return wake word detection capabilities."""
        return [
            AgentCapability(
                name="wake_detection",
                description="Background wake word detection with session management",
                input_topics=["wake.start", "wake.stop", "wake.set_window"],
                output_topics=["wake.detected", "wake.timeout", "wake.listening"],
            )
        ]

    async def process_message(self, message: Message) -> None:
        """
        Process wake word control messages.

        Args:
            message: Control message
        """
        if message.topic == "wake.start":
            await self._start_listening()
        elif message.topic == "wake.stop":
            await self._stop_listening()
        elif message.topic == "wake.set_window":
            window = message.payload.get("window", self._session_window)
            self._session_window = max(0.0, float(window))
            self.logger.debug(f"Session window updated: {self._session_window}s")

    async def _start_listening(self) -> None:
        """Start background listening task."""
        if self._listening:
            self.logger.debug("Already listening")
            return

        self._listening = True
        self._listen_task = self.create_task(self._listen_loop())

        await self.publish(
            topic="wake.listening",
            payload={"listening": True, "wake_word": self._wake_matcher.wake_word_display},
            priority=MessagePriority.NORMAL,
        )

        self.logger.info("Started wake word listening")

    async def _stop_listening(self) -> None:
        """Stop background listening task."""
        if not self._listening:
            return

        self._listening = False

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        await self.publish(
            topic="wake.listening",
            payload={"listening": False},
            priority=MessagePriority.NORMAL,
        )

        self.logger.info("Stopped wake word listening")

    async def _listen_loop(self) -> None:
        """
        Main listening loop - runs in background.

        Continuously listens for wake word and processes audio.
        """
        self.logger.debug("Wake word listen loop started")

        while self._listening:
            try:
                # Check if session is still active
                now = time.time()
                if self._session_active_until > 0 and now < self._session_active_until:
                    # Session active - listen for continuation
                    await self._listen_for_continuation()
                else:
                    # Session expired or not started - listen for wake word
                    if self._session_active_until > 0:
                        # Session just expired
                        await self.publish(
                            topic="wake.timeout",
                            payload={"message": "Session window expired"},
                            priority=MessagePriority.LOW,
                        )
                        self._session_active_until = 0.0

                    await self._listen_for_wake_word()

            except asyncio.CancelledError:
                self.logger.debug("Listen loop cancelled")
                break
            except Exception as exc:
                self.logger.exception(f"Error in listen loop: {exc}")
                await asyncio.sleep(0.5)  # Brief pause before retry

        self.logger.debug("Wake word listen loop stopped")

    async def _listen_for_wake_word(self) -> None:
        """Listen for wake word using STT."""
        try:
            # Use STT to get full transcript
            transcript = await asyncio.to_thread(self._stt.listen)
            if not transcript or not transcript.strip():
                return

            # Check for wake word with fuzzy matching
            detected, remainder = self._wake_matcher.find_wake_word(transcript)

            if detected:
                self.logger.info(f"Wake word detected! Remainder: '{remainder}'")

                # Start session window
                self._session_active_until = time.time() + self._session_window

                # Publish wake detection event
                await self.publish(
                    topic="wake.detected",
                    payload={
                        "transcript": remainder.strip(),
                        "full_transcript": transcript,
                        "confidence": 0.9,  # TODO: Get from wake detector
                        "session_expires": self._session_active_until,
                        "channel_id": self._channel_id,
                    },
                    priority=MessagePriority.HIGH,
                )

        except Exception as exc:
            self.logger.exception(f"Error detecting wake word: {exc}")

    async def _listen_for_continuation(self) -> None:
        """
        Listen for continuation within session window.

        When session is active, doesn't require wake word.
        """
        try:
            # Listen with shorter timeout (session window aware)
            remaining = self._session_active_until - time.time()
            if remaining <= 0:
                return

            # Listen for input (no wake word needed)
            transcript = await asyncio.to_thread(self._stt.listen)
            if not transcript or not transcript.strip():
                return

            # Check if user said exit/quit
            lowered = transcript.lower().strip()
            if lowered in {"exit", "quit", "stop", "goodbye"}:
                self._session_active_until = 0.0
                await self.publish(
                    topic="wake.exit",
                    payload={"message": "User requested exit"},
                    priority=MessagePriority.HIGH,
                )
                return

            # Publish continuation (within session window)
            self.logger.info(f"Session continuation: '{transcript}'")

            await self.publish(
                topic="wake.detected",
                payload={
                    "transcript": transcript.strip(),
                    "full_transcript": transcript,
                    "confidence": 1.0,
                    "continuation": True,
                    "session_expires": self._session_active_until,
                    "channel_id": self._channel_id,
                },
                priority=MessagePriority.HIGH,
            )

        except Exception as exc:
            self.logger.exception(f"Error in continuation listening: {exc}")

    async def cleanup(self) -> None:
        """Cleanup wake word agent resources."""
        await self._stop_listening()
        self.logger.debug("WakeWordAgent cleanup complete")
