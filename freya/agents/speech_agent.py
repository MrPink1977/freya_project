"""Speech Agent: Coordinates STT and TTS with multi-channel support."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from freya.core.config import Settings
from ..core.message_bus import Message, MessageBus
from freya.core.logger import get_logger
from freya.voice.stt import SpeechToText
from freya.voice.tts import TextToSpeech
from .base_agent import BaseAgent

logger = get_logger("speech_agent")


class TTSEngine(str, Enum):
    """Available TTS engines."""

    PIPER = "piper"
    ELEVENLABS = "elevenlabs"


@dataclass
class AudioChannel:
    """Represents an audio input/output channel."""

    channel_id: str
    name: str
    stt_device: Optional[int] = None  # Microphone device index
    tts_device: Optional[int] = None  # Speaker device index
    is_active: bool = True
    is_muted: bool = False


class SpeechAgent(BaseAgent):
    """
    Coordinates speech-to-text and text-to-speech operations.

    Features:
    - Multi-channel audio support (PC, Reolink camera, etc.)
    - Dynamic TTS engine switching (Piper/ElevenLabs)
    - Channel-aware STT/TTS routing
    - Mutex control for channel isolation

    Subscribes to:
    - speech.listen_request: Request to start listening on a channel
    - speech.speak_request: Request to speak on a channel
    - speech.change_engine: Switch TTS engine
    - dialog.chunk: Stream TTS output in real-time

    Publishes:
    - speech.transcription: STT result with channel_id
    - speech.speech_started: TTS playback started
    - speech.speech_complete: TTS playback finished
    - speech.error: STT/TTS errors
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        config: Settings,
    ):
        super().__init__(agent_id, message_bus)
        self.config = config

        # Initialize STT/TTS
        self.stt: Optional[SpeechToText] = None
        self.tts: Optional[TextToSpeech] = None
        self.current_engine = TTSEngine(config.tts.engine)

        # Channel management
        self.channels: dict[str, AudioChannel] = {}
        self._active_channel: Optional[str] = None  # Currently speaking/listening channel
        self._channel_lock = asyncio.Lock()

        # Streaming TTS buffer
        self._tts_buffer: list[str] = []
        self._tts_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Initialize STT/TTS and register default channels."""
        print("[DEBUG] SpeechAgent: start() called")
        await super().start()

        # Initialize STT
        print("[DEBUG] SpeechAgent: Initializing STT...")
        from freya.voice.stt import SpeechToText

        self.stt = SpeechToText(self.config.stt)
        print("[DEBUG] SpeechAgent: STT initialized")
        logger.info(
            "STT initialized: model=%s, device=%s", self.config.stt.model, self.config.stt.device
        )

        # Initialize TTS
        print(f"[DEBUG] SpeechAgent: Initializing TTS engine={self.current_engine}...")
        await self._initialize_tts(self.current_engine)
        print("[DEBUG] SpeechAgent: TTS initialized")

        # Register default PC channel
        self.channels["pc"] = AudioChannel(
            channel_id="pc",
            name="PC Audio",
            stt_device=None,  # Default mic
            tts_device=None,  # Default speakers
        )
        logger.info("Registered default PC audio channel")

        # Subscribe to events
        print("[DEBUG] SpeechAgent: Subscribing to speech.speak_request...")
        self.bus.subscribe("speech.speak_request", self._handle_speak_request)
        self.bus.subscribe("speech.listen_request", self._handle_listen_request)
        self.bus.subscribe("speech.change_engine", self._handle_change_engine)
        self.bus.subscribe("dialog.chunk", self._handle_dialog_chunk)
        self.bus.subscribe("speech.mute_channel", self._handle_mute_channel)
        self.bus.subscribe("speech.unmute_channel", self._handle_unmute_channel)
        self.bus.subscribe("speech.stop", self._handle_stop_speech)
        print("[DEBUG] SpeechAgent: Subscribed to all topics")

        logger.info("SpeechAgent started")

    async def initialize(self) -> None:
        """Initialize speech agent (called by BaseAgent)."""
        pass  # Initialization done in start()

    def get_capabilities(self) -> list:
        """Return speech agent capabilities."""
        from .base_agent import AgentCapability

        return [
            AgentCapability(
                name="speech_to_text",
                description="Multi-channel speech-to-text conversion",
                input_topics=["speech.listen_request"],
                output_topics=["speech.transcription"],
            ),
            AgentCapability(
                name="text_to_speech",
                description="Multi-channel text-to-speech with engine switching",
                input_topics=["speech.speak_request", "dialog.chunk"],
                output_topics=["speech.speech_started", "speech.speech_complete"],
            ),
        ]

    async def process_message(self, message: Message) -> None:
        """Process incoming messages (handled by subscriptions)."""
        pass  # All processing done via subscriptions

    async def stop(self) -> None:
        """Clean up STT/TTS resources."""
        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()

        if self.tts and hasattr(self.tts, "close"):
            self.tts.close()

        await super().stop()
        logger.info("SpeechAgent stopped")

    async def _initialize_tts(self, engine: TTSEngine) -> None:
        """Initialize or switch TTS engine."""
        if self.tts and hasattr(self.tts, "close"):
            self.tts.close()

        if engine == TTSEngine.PIPER:
            from freya.voice.tts import TextToSpeech

            self.tts = TextToSpeech(self.config.tts)
            logger.info("TTS initialized: engine=Piper, voice=%s", self.config.tts.voice_path)
        elif engine == TTSEngine.ELEVENLABS:
            from freya.voice.tts_elevenlabs import ElevenLabsTTS

            self.tts = ElevenLabsTTS(
                api_key=self.config.tts.elevenlabs.api_key,
                voice_id=self.config.tts.elevenlabs.voice_id,
                model_id=self.config.tts.elevenlabs.model,
            )
            logger.info(
                "TTS initialized: engine=ElevenLabs, voice=%s, model=%s",
                self.config.tts.elevenlabs.voice_id,
                self.config.tts.elevenlabs.model,
            )

        self.current_engine = engine

    async def _handle_listen_request(self, message: Message) -> None:
        """Handle request to listen on a channel."""
        channel_id = message.payload.get("channel_id", "pc")
        timeout = message.payload.get("timeout", 30.0)

        if channel_id not in self.channels:
            await self.publish_error(
                f"Unknown channel: {channel_id}",
                correlation_id=message.correlation_id,
            )
            return

        channel = self.channels[channel_id]
        if not channel.is_active or channel.is_muted:
            await self.publish_error(
                f"Channel {channel_id} is not available (active={channel.is_active}, muted={channel.is_muted})",
                correlation_id=message.correlation_id,
            )
            return

        # Acquire channel lock
        async with self._channel_lock:
            self._active_channel = channel_id

            try:
                # Run STT in executor (blocking operation)
                loop = asyncio.get_event_loop()
                transcription = await loop.run_in_executor(
                    None,
                    self.stt.transcribe_from_mic,
                    timeout,
                )

                if transcription:
                    await self.publish(
                        "speech.transcription",
                        {
                            "text": transcription,
                            "channel_id": channel_id,
                        },
                        correlation_id=message.correlation_id,
                    )
                    logger.info("Transcription from %s: %s", channel_id, transcription)

            except Exception as e:
                logger.error("STT error on channel %s: %s", channel_id, e)
                await self.publish_error(
                    f"STT failed on {channel_id}: {e}",
                    correlation_id=message.correlation_id,
                )
            finally:
                self._active_channel = None

    async def _handle_speak_request(self, message: Message) -> None:
        """Handle request to speak on a channel."""
        text = message.payload.get("text", "")
        channel_id = message.payload.get("channel_id", "pc")

        print(f"[DEBUG] SpeechAgent received speak request: '{text}' on '{channel_id}'")

        if not text:
            return

        if channel_id not in self.channels:
            await self.publish_error(
                f"Unknown channel: {channel_id}",
                correlation_id=message.correlation_id,
            )
            return

        channel = self.channels[channel_id]
        if not channel.is_active or channel.is_muted:
            logger.debug("Skipping TTS on muted/inactive channel %s", channel_id)
            return

        # Acquire channel lock
        async with self._channel_lock:
            self._active_channel = channel_id

            try:
                await self.publish(
                    "speech.speech_started",
                    {"channel_id": channel_id, "text": text},
                    correlation_id=message.correlation_id,
                )

                # Run TTS in executor (blocking operation)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.tts.speak,
                    text,
                )

                await self.publish(
                    "speech.speech_complete",
                    {"channel_id": channel_id},
                    correlation_id=message.correlation_id,
                )
                logger.info("TTS complete on %s: %s", channel_id, text[:50])

            except Exception as e:
                logger.error("TTS error on channel %s: %s", channel_id, e)
                await self.publish_error(
                    f"TTS failed on {channel_id}: {e}",
                    correlation_id=message.correlation_id,
                )
            finally:
                self._active_channel = None

    async def _handle_change_engine(self, message: Message) -> None:
        """Handle request to change TTS engine."""
        engine_name = message.payload.get("engine", "piper")

        try:
            engine = TTSEngine(engine_name)
            await self._initialize_tts(engine)

            await self.publish(
                "speech.engine_changed",
                {"engine": engine.value},
                correlation_id=message.correlation_id,
            )
            logger.info("TTS engine changed to: %s", engine.value)

        except ValueError:
            await self.publish_error(
                f"Invalid TTS engine: {engine_name}",
                correlation_id=message.correlation_id,
            )

    async def _handle_dialog_chunk(self, message: Message) -> None:
        """Handle streaming dialog chunks for real-time TTS."""
        chunk = message.payload.get("chunk", "")
        channel_id = message.payload.get("channel_id", "pc")
        _is_final = message.payload.get("is_final", False)  # noqa: F841

        if chunk:
            self._tts_buffer.append(chunk)

        # Start streaming TTS task if not already running
        if not self._tts_task or self._tts_task.done():
            self._tts_task = asyncio.create_task(
                self._stream_tts(channel_id, message.correlation_id)
            )

    async def _stream_tts(self, channel_id: str, correlation_id: Optional[str]) -> None:
        """Stream TTS output as chunks arrive."""
        # Wait a bit to accumulate chunks
        await asyncio.sleep(0.1)

        if not self._tts_buffer:
            return

        # Combine buffer and speak
        text = "".join(self._tts_buffer)
        self._tts_buffer.clear()

        await self._handle_speak_request(
            Message(
                topic="speech.speak_request",
                payload={"text": text, "channel_id": channel_id},
                correlation_id=correlation_id,
            )
        )

    async def register_channel(
        self,
        channel_id: str,
        name: str,
        stt_device: Optional[int] = None,
        tts_device: Optional[int] = None,
    ) -> None:
        """Register a new audio channel."""
        self.channels[channel_id] = AudioChannel(
            channel_id=channel_id,
            name=name,
            stt_device=stt_device,
            tts_device=tts_device,
        )
        logger.info("Registered audio channel: %s (%s)", channel_id, name)

    async def mute_channel(self, channel_id: str) -> None:
        """Mute a channel (no audio in/out)."""
        if channel_id in self.channels:
            self.channels[channel_id].is_muted = True
            logger.info("Muted channel: %s", channel_id)

    async def unmute_channel(self, channel_id: str) -> None:
        """Unmute a channel."""
        if channel_id in self.channels:
            self.channels[channel_id].is_muted = False
            logger.info("Unmuted channel: %s", channel_id)

    async def _handle_mute_channel(self, message: Message) -> None:
        """Handle mute channel event from AudioChannelManager."""
        channel_id = message.payload.get("channel_id", "")
        if channel_id:
            await self.mute_channel(channel_id)

    async def _handle_unmute_channel(self, message: Message) -> None:
        """Handle unmute channel event from AudioChannelManager."""
        channel_id = message.payload.get("channel_id", "")
        if channel_id:
            await self.unmute_channel(channel_id)

    async def _handle_stop_speech(self, message: Message) -> None:
        """Handle emergency stop of current speech."""
        channel_id = message.payload.get("channel_id", "pc")
        force = message.payload.get("force", False)
        
        logger.info(f"Stop speech requested for channel {channel_id} (force={force})")
        
        # Stop TTS playback immediately
        if self.tts and hasattr(self.tts, "stop_speaking"):
            self.tts.stop_speaking()
            logger.debug("TTS stop signal sent")
        
        # Cancel TTS task if running
        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()
            logger.debug("TTS task cancelled")
        
        # Clear buffer
        self._tts_buffer.clear()
        
        # Release channel lock if held
        if self._active_channel == channel_id:
            self._active_channel = None
        
        # Notify speech stopped
        await self.publish(
            "speech.speech_stopped",
            {"channel_id": channel_id, "forced": force},
            priority=MessagePriority.URGENT,
        )

    def get_active_channel(self) -> Optional[str]:
        """Get the currently active channel."""
        return self._active_channel
