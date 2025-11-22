"""
Conversation Manager - Handles wake word detection and conversation flow.

Implements two-stage wake system:
1. Lightweight wake word detector (always running, 20MB CPU)
2. Whisper STT (loaded after wake, unloaded after conversation timeout)

Conversation flow:
- Wake detected → Load Whisper tiny (200ms)
- Background load Whisper small (500ms)
- Listen for speech with 8-second timeout
- Keep Whisper loaded during active conversation
- Unload after conversation ends
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, List
import numpy as np

from freya.shared.logging.logger import get_logger
from freya.shared.logging.decorators import log_performance
from freya.domain.exceptions import SpeechError
from freya.infrastructure.models.model_manager import ModelManager, ModelType


logger = get_logger(__name__)


class ConversationState(Enum):
    """Current state of the conversation."""
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"


@dataclass
class SpeechSegment:
    """A segment of transcribed speech."""
    text: str
    confidence: float
    start_time: float
    end_time: float
    is_final: bool = True


class ConversationManager:
    """
    Manages conversation flow with wake word detection and speech recognition.
    
    Features:
    - Multi-phrase wake word detection ("Freya", "Hey Freya", "Yo Freya")
    - Two-stage Whisper loading (tiny → small)
    - 8-second conversation timeout
    - Automatic resource cleanup
    - Silence detection
    
    Resource usage:
    - Idle: 20MB CPU (wake word detector only)
    - Active: +2.5GB GPU (Whisper tiny + small)
    """
    
    def __init__(
        self,
        model_manager: ModelManager,
        wake_phrases: List[str] = None,
        conversation_timeout: float = 8.0,
        silence_threshold: float = 2.0,
        on_wake: Optional[Callable] = None,
        on_speech: Optional[Callable[[str], None]] = None,
        on_timeout: Optional[Callable] = None,
    ):
        """
        Initialize conversation manager.
        
        Args:
            model_manager: Model manager for loading STT models
            wake_phrases: List of wake phrases (default: ["freya", "hey freya", "yo freya"])
            conversation_timeout: Seconds of silence before ending conversation
            silence_threshold: Seconds of silence to detect end of utterance
            on_wake: Callback when wake word detected
            on_speech: Callback when speech transcribed
            on_timeout: Callback when conversation times out
        """
        self.model_manager = model_manager
        self.wake_phrases = wake_phrases or ["freya", "hey freya", "yo freya"]
        self.conversation_timeout = conversation_timeout
        self.silence_threshold = silence_threshold
        
        self.on_wake = on_wake
        self.on_speech = on_speech
        self.on_timeout = on_timeout
        
        self._state = ConversationState.IDLE
        self._wake_detector = None
        self._whisper_tiny = None
        self._whisper_small = None
        self._last_speech_time = None
        self._conversation_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            "ConversationManager initialized",
            extra={
                "wake_phrases": self.wake_phrases,
                "timeout": conversation_timeout
            }
        )
    
    async def start(self):
        """Start the conversation manager and wake word detection."""
        if self._running:
            logger.warning("ConversationManager already running")
            return
        
        logger.info("Starting ConversationManager...")
        self._running = True
        
        # Initialize wake word detector
        try:
            await self._initialize_wake_detector()
            logger.info("Wake word detector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize wake word detector: {e}")
            raise
        
        # Start listening loop
        self._conversation_task = asyncio.create_task(self._listen_loop())
        
        logger.info("ConversationManager started - listening for wake word")
    
    async def stop(self):
        """Stop the conversation manager and clean up resources."""
        logger.info("Stopping ConversationManager...")
        self._running = False
        
        # Cancel listening task
        if self._conversation_task:
            self._conversation_task.cancel()
            try:
                await self._conversation_task
            except asyncio.CancelledError:
                pass
        
        # Clean up wake detector
        if self._wake_detector:
            await self._cleanup_wake_detector()
        
        # Unload STT models
        await self._unload_whisper()
        
        logger.info("ConversationManager stopped")
    
    async def _initialize_wake_detector(self):
        """Initialize the wake word detector."""
        try:
            # Try OpenWakeWord first (easier custom phrases)
            from openwakeword.model import Model as OpenWakeWordModel
            
            self._wake_detector = OpenWakeWordModel()
            
            # Add custom wake phrases
            for phrase in self.wake_phrases:
                # OpenWakeWord expects phrases in specific format
                # For now, use built-in models or train custom ones
                logger.info(f"Wake phrase registered: {phrase}")
            
            logger.info("Using OpenWakeWord for wake detection")
            
        except ImportError:
            # Fallback to Porcupine
            try:
                import pvporcupine
                
                # Note: Porcupine requires access key
                # For production, get key from config
                self._wake_detector = pvporcupine.create(
                    keywords=["jarvis"],  # Use built-in keyword for now
                    # For custom keywords, need to train and provide paths:
                    # keyword_paths=["path/to/freya.ppn"]
                )
                
                logger.info("Using Porcupine for wake detection")
                
            except Exception as e:
                logger.error(f"Failed to initialize wake detector: {e}")
                # Fallback: Simple audio-based detection
                self._wake_detector = None
                logger.warning("Using fallback wake detection (less accurate)")
    
    async def _cleanup_wake_detector(self):
        """Clean up wake detector resources."""
        if self._wake_detector:
            try:
                if hasattr(self._wake_detector, 'delete'):
                    self._wake_detector.delete()
                del self._wake_detector
                self._wake_detector = None
            except Exception as e:
                logger.warning(f"Error cleaning up wake detector: {e}")
    
    async def _listen_loop(self):
        """Main listening loop for wake word detection."""
        while self._running:
            try:
                # Wait for wake word
                if await self._detect_wake_word():
                    logger.info("Wake word detected!")
                    self._state = ConversationState.WAKE_DETECTED
                    
                    # Trigger callback
                    if self.on_wake:
                        try:
                            await self.on_wake()
                        except Exception as e:
                            logger.error(f"Error in wake callback: {e}")
                    
                    # Start conversation
                    await self._handle_conversation()
                
                # Small delay to avoid busy loop
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(1.0)  # Back off on error
    
    async def _detect_wake_word(self) -> bool:
        """
        Detect wake word in audio stream.
        
        Returns:
            True if wake word detected, False otherwise
        """
        # This is a placeholder implementation
        # In production, integrate with actual microphone input
        
        if self._wake_detector is None:
            # Fallback: simulate wake detection for testing
            # In production, this should read from microphone
            await asyncio.sleep(0.1)
            return False
        
        try:
            # Read audio chunk from microphone
            # audio_chunk = await self._read_microphone()
            
            # For now, return False (no wake detected)
            # In production, pass audio to wake detector
            # result = self._wake_detector.process(audio_chunk)
            # return result >= 0  # Porcupine returns keyword index or -1
            
            await asyncio.sleep(0.1)
            return False
            
        except Exception as e:
            logger.error(f"Error detecting wake word: {e}")
            return False
    
    @log_performance
    async def _handle_conversation(self):
        """Handle active conversation after wake word detected."""
        logger.info("Starting conversation...")
        self._state = ConversationState.LISTENING
        self._last_speech_time = time.time()
        
        try:
            # Load Whisper models
            await self._load_whisper()
            
            # Conversation loop
            while self._running:
                # Check for timeout
                idle_time = time.time() - self._last_speech_time
                if idle_time > self.conversation_timeout:
                    logger.info(f"Conversation timeout after {idle_time:.1f}s")
                    if self.on_timeout:
                        try:
                            await self.on_timeout()
                        except Exception as e:
                            logger.error(f"Error in timeout callback: {e}")
                    break
                
                # Listen for speech
                speech = await self._listen_for_speech()
                
                if speech:
                    logger.info(f"Speech detected: {speech.text[:50]}...")
                    self._last_speech_time = time.time()
                    
                    # Trigger callback
                    if self.on_speech:
                        try:
                            await self.on_speech(speech.text)
                        except Exception as e:
                            logger.error(f"Error in speech callback: {e}")
                
                # Small delay
                await asyncio.sleep(0.1)
        
        finally:
            # Clean up
            await self._unload_whisper()
            self._state = ConversationState.IDLE
            logger.info("Conversation ended")
    
    async def _load_whisper(self):
        """Load Whisper STT models (tiny first, then small)."""
        logger.info("Loading Whisper models...")
        
        # Load tiny model immediately (fast, ~200ms)
        try:
            self._whisper_tiny = await self.model_manager.get_model(ModelType.STT_TINY)
            logger.info("Whisper tiny loaded - ready for immediate transcription")
        except Exception as e:
            logger.error(f"Failed to load Whisper tiny: {e}")
            raise SpeechError("Failed to load speech recognition") from e
        
        # Load small model in background (better accuracy, ~500ms)
        async def load_small():
            try:
                self._whisper_small = await self.model_manager.get_model(ModelType.STT_SMALL)
                logger.info("Whisper small loaded - high accuracy available")
            except Exception as e:
                logger.warning(f"Failed to load Whisper small: {e}")
                # Continue with tiny only
        
        asyncio.create_task(load_small())
    
    async def _unload_whisper(self):
        """Unload Whisper models (handled by ModelManager cache)."""
        # Models will be unloaded by ModelManager after cache TTL
        self._whisper_tiny = None
        self._whisper_small = None
        logger.debug("Whisper models marked for unload")
    
    async def _listen_for_speech(self) -> Optional[SpeechSegment]:
        """
        Listen for speech and transcribe.
        
        Returns:
            Transcribed speech segment, or None if no speech detected
        """
        # This is a placeholder implementation
        # In production, integrate with actual microphone input
        
        try:
            # Read audio from microphone until silence
            # audio_buffer = await self._record_until_silence()
            
            # For now, return None (no speech)
            # In production, transcribe with Whisper
            # if audio_buffer:
            #     model = self._whisper_small or self._whisper_tiny
            #     result = await model.transcribe(audio_buffer)
            #     return SpeechSegment(
            #         text=result['text'],
            #         confidence=result.get('confidence', 1.0),
            #         start_time=time.time(),
            #         end_time=time.time(),
            #     )
            
            await asyncio.sleep(0.1)
            return None
            
        except Exception as e:
            logger.error(f"Error transcribing speech: {e}")
            return None
    
    async def _record_until_silence(self) -> Optional[np.ndarray]:
        """
        Record audio until silence detected.
        
        Returns:
            Audio buffer as numpy array, or None if no audio
        """
        # Placeholder for microphone integration
        # In production, implement actual audio recording with silence detection
        pass
    
    def get_state(self) -> ConversationState:
        """Get current conversation state."""
        return self._state
    
    def is_active(self) -> bool:
        """Check if conversation is currently active."""
        return self._state in [
            ConversationState.LISTENING,
            ConversationState.PROCESSING,
            ConversationState.RESPONDING
        ]
    
    def get_status(self) -> dict:
        """Get current status information."""
        return {
            "state": self._state.value,
            "running": self._running,
            "whisper_loaded": self._whisper_tiny is not None or self._whisper_small is not None,
            "last_speech_time": self._last_speech_time,
            "idle_seconds": time.time() - self._last_speech_time if self._last_speech_time else None,
        }
