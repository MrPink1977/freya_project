"""
ORCHESTRATION COORDINATOR - Lightweight agent conductor.

Replaces monolithic orchestrator with event-driven agent coordination.
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable, Optional

from freya.agents.base_agent import BaseAgent
from freya.agents.dialog_agent import DialogAgent
from freya.agents.memory_agent import MemoryAgent
from freya.agents.speech_agent import SpeechAgent
from freya.agents.tool_executor_agent import ToolExecutorAgent
from freya.agents.wake_word_agent import WakeWordAgent
from freya.context import ConversationContext
from freya.coordination.audio_channel_manager import AudioChannelManager
from freya.core.message_bus import Message, MessageBus, MessagePriority
from freya.logger import get_logger
from freya.memory import ChromaMemoryStore
from freya.ollama_client import OllamaClient
from freya.stt import SpeechToText
from freya.tools import ToolManager
from freya.tts import TextToSpeech
from freya.wake import WakeWordDetector
import keyboard
from colorama import Fore, Style, init as colorama_init

# Initialize colorama for Windows console colors
colorama_init(autoreset=True)

logger = get_logger("coordinator")


class OrchestrationCoordinator:
    """
    Lightweight coordinator for agent-based architecture.

    Initializes MessageBus and agents, wires event handlers,
    manages lifecycle. Drop-in replacement for Orchestrator.run().
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        context: ConversationContext,
        config,  # Full config object for SpeechAgent
        memory_store: ChromaMemoryStore,
        tool_manager: ToolManager,
        output_fn: Callable[[str], None] = print,
        # Wake word config
        wake_word: str = "Hey, Freya",
        wake_sensitivity: float = 0.75,
        session_window: float = 8.0,
        wake_detector: Optional[WakeWordDetector] = None,
        # Dialog config
        default_model: str = "llama3.2:3b",
        reasoning_model: str = "dolphin-mixtral:8x7b",
        code_model: str = "deepseek-coder-v2:16b-lite",
        enable_escalation: bool = True,
        # Mode config
        interaction_mode: str = "voice",
    ) -> None:
        """
        Initialize orchestration coordinator.

        Args:
            ollama_client: Ollama LLM client
            context: Conversation context manager
            config: Full configuration object
            memory_store: ChromaDB memory store
            tool_manager: Tool registry
            output_fn: Output function for user messages
            wake_word: Wake word phrase
            wake_sensitivity: Wake word detection sensitivity
            session_window: Session window duration (seconds)
            wake_detector: Optional lightweight wake detector
            default_model: Default LLM model
            reasoning_model: Powerful reasoning model
            code_model: Code-specialized model
            enable_escalation: Enable model escalation on confusion
            interaction_mode: "voice" or "text"
        """
        self._output = output_fn
        self._mode = interaction_mode.lower()
        self._config = config

        # Create MessageBus
        self.bus = MessageBus()

        # Create AudioChannelManager
        self._channel_manager = AudioChannelManager(self.bus)

        # Initialize agents
        self._speech_agent = SpeechAgent(
            agent_id="speech",
            message_bus=self.bus,
            config=config,
        )

        self._tool_agent = ToolExecutorAgent(
            agent_id="tool_executor",
            bus=self.bus,
            tool_manager=tool_manager,
        )

        self._memory_agent = MemoryAgent(
            agent_id="memory",
            bus=self.bus,
            memory_store=memory_store,
            auto_extract_facts=True,
        )

        # Create temporary STT for wake word (until we have multi-channel STT)
        from freya.stt import SpeechToText

        _temp_stt = SpeechToText(config.stt)

        self._wake_agent = WakeWordAgent(
            agent_id="wake_word",
            bus=self.bus,
            stt=_temp_stt,
            wake_word=wake_word,
            wake_sensitivity=wake_sensitivity,
            session_window=session_window,
            wake_detector=wake_detector,
            channel_id="pc",  # Default PC channel
        )

        # Create personality engine if enabled
        personality_engine = None
        if hasattr(config, "personality") and config.personality.get("enabled", False):
            try:
                from freya.personality import PersonalityEngine
                
                personality_engine = PersonalityEngine(config.personality)
                logger.info("Personality engine enabled")
            except Exception as exc:
                logger.warning(f"Failed to initialize personality engine: {exc}")

        self._dialog_agent = DialogAgent(
            agent_id="dialog",
            bus=self.bus,
            ollama_client=ollama_client,
            context_manager=context,
            default_model=default_model,
            reasoning_model=reasoning_model,
            code_model=code_model,
            enable_escalation=enable_escalation,
            personality_engine=personality_engine,
        )

        # Agent list for lifecycle management
        self._agents: list[BaseAgent] = [
            self._speech_agent,
            self._tool_agent,
            self._memory_agent,
            self._wake_agent,
            self._dialog_agent,
        ]

        # State
        self._running = False
        self._text_mode_task: Optional[asyncio.Task] = None
        
        # Hotkey state
        self._escape_pressed = False
        self._hotkeys_registered = False
        
        # Response accumulation for colored output
        self._response_buffer = ""
        self._response_started = False

    async def run(self) -> None:
        """Main entry point - start agents and run event loop."""
        try:
            # Start all agents
            await self._start_agents()

            # Subscribe to key events
            await self._subscribe_to_events()
            
            # Register hotkeys
            self._register_hotkeys()

            # Announce startup
            await self._announce_startup()

            # Run appropriate mode
            if self._mode == "voice":
                await self._run_voice_mode()
            else:
                await self._run_text_mode()

        except KeyboardInterrupt:
            self._output("\n[Interrupted] Shutting down Freya. Goodbye!")
        finally:
            self._unregister_hotkeys()
            await self._stop_agents()

    async def _start_agents(self) -> None:
        """Start all agents."""
        logger.info("Starting agents...")

        # Start message bus FIRST
        print("[DEBUG] Coordinator: Starting MessageBus...")
        await self.bus.start()
        print("[DEBUG] Coordinator: MessageBus started")

        # Start channel manager
        await self._channel_manager.start()

        # Start all agents
        for agent in self._agents:
            await agent.start()

        logger.info("All agents started")
        self._running = True

    async def _stop_agents(self) -> None:
        """Stop all agents."""
        logger.info("Stopping agents...")
        self._running = False

        # Stop all agents
        for agent in self._agents:
            await agent.stop()

        # Stop channel manager
        await self._channel_manager.stop()

        # Stop message bus last
        await self.bus.stop()

        logger.info("All agents stopped")

    async def _subscribe_to_events(self) -> None:
        """Subscribe coordinator to key events."""
        # Wake word detected → handle conversation
        self.bus.subscribe("wake.detected", self._handle_wake_detected)

        # Dialog chunk → forward to speech agent
        self.bus.subscribe("dialog.chunk", self._handle_dialog_chunk)

        # Dialog complete → store in memory
        self.bus.subscribe("dialog.complete", self._handle_dialog_complete)

        # Tool result → inject into dialog context
        self.bus.subscribe("tool.result", self._handle_tool_result)

        # Speech transcription → process as user input
        self.bus.subscribe("speech.transcription", self._handle_transcription)

        logger.debug("Coordinator subscribed to events")

    def _register_hotkeys(self) -> None:
        """Register emergency hotkeys for speech control."""
        try:
            # Ctrl+M: Mute/Stop current speech
            keyboard.add_hotkey('ctrl+m', self._on_mute_hotkey)
            
            # Escape: Emergency stop
            keyboard.on_press_key('esc', self._on_escape_press)
            keyboard.on_release_key('esc', self._on_escape_release)
            
            self._hotkeys_registered = True
            logger.info("Hotkeys registered: Ctrl+M (mute), Escape (emergency stop)")
            self._output("[Hotkeys] Ctrl+M=Mute speech, Escape=Emergency stop")
        except Exception as e:
            logger.warning(f"Failed to register hotkeys: {e}")

    def _unregister_hotkeys(self) -> None:
        """Unregister all hotkeys."""
        if self._hotkeys_registered:
            try:
                keyboard.unhook_all()
                self._hotkeys_registered = False
                logger.info("Hotkeys unregistered")
            except Exception as e:
                logger.warning(f"Failed to unregister hotkeys: {e}")

    def _on_mute_hotkey(self) -> None:
        """Handle Ctrl+M hotkey - stop current speech."""
        logger.info("Ctrl+M pressed - muting speech")
        self._output("\n[MUTED] Stopping speech...")
        
        # Cancel speech by publishing stop request
        asyncio.create_task(self.bus.publish(
            topic="speech.stop",
            payload={"channel_id": "pc"},
            sender="coordinator",
            priority=MessagePriority.URGENT,
        ))

    def _on_escape_press(self, event) -> None:
        """Handle Escape key press."""
        if not self._escape_pressed:
            self._escape_pressed = True
            logger.info("Escape pressed - emergency stop initiated")
            self._output("\n[EMERGENCY STOP] Cancelling all speech...")
            
            # Stop speech immediately
            asyncio.create_task(self.bus.publish(
                topic="speech.stop",
                payload={"channel_id": "pc", "force": True},
                sender="coordinator",
                priority=MessagePriority.URGENT,
            ))

    def _on_escape_release(self, event) -> None:
        """Handle Escape key release."""
        self._escape_pressed = False

    def _is_exit_command(self, text: str) -> bool:
        """Check if text contains a natural exit command."""
        text_lower = text.lower().strip()
        
        # Direct exit words
        if text_lower in {"exit", "quit", "goodbye", "bye", "stop"}:
            return True
        
        # Natural language exit phrases
        exit_phrases = [
            "be quiet",
            "zip it",
            "shut up",
            "be silent",
            "stop talking",
            "go away",
            "leave me alone",
            "that's enough",
            "i'm done",
            "we're done",
            "that'll do",
            "silence",
            "hush",
            "shh",
        ]
        
        return any(phrase in text_lower for phrase in exit_phrases)

    def _print_user(self, text: str) -> None:
        """Print user message with cyan color and formatting."""
        print(f"\n{Fore.CYAN}┌─ You:{Style.RESET_ALL}")
        lines = text.split('\n')
        for line in lines:
            print(f"{Fore.CYAN}│ {line}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}└{'─' * 60}{Style.RESET_ALL}")

    def _print_freya(self, text: str) -> None:
        """Print Freya's response with magenta color and formatting."""
        print(f"\n{Fore.MAGENTA}┌─ Freya:{Style.RESET_ALL}")
        lines = text.split('\n')
        for line in lines:
            print(f"{Fore.MAGENTA}│ {line}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}└{'─' * 60}{Style.RESET_ALL}")

    async def _announce_startup(self) -> None:
        """Announce startup and mode."""
        if self._mode == "voice":
            print(f"\n{Fore.GREEN}{'='*70}")
            print(f"{Fore.GREEN}  FREYA - Voice Mode Active{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*70}")
            print(f"{Fore.YELLOW}  • Say 'Hey, Freya' followed by your message")
            print(f"{Fore.YELLOW}  • Natural exit: 'Freya, be quiet' or 'zip it'")
            print(f"{Fore.YELLOW}  • Hotkeys: Ctrl+M (mute), Escape (emergency stop)")
            print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}\n")
            
            # Speak ready prompt via SpeechAgent
            print("[DEBUG] Coordinator: Publishing speech.speak_request...")
            await self.bus.publish(
                topic="speech.speak_request",
                payload={"text": "Freya is ready.", "channel_id": "pc"},
                sender="coordinator",
                priority=MessagePriority.NORMAL,
            )
            print("[DEBUG] Coordinator: Published speech.speak_request")
        else:
            print(f"\n{Fore.GREEN}{'='*70}")
            print(f"{Fore.GREEN}  FREYA - Text Mode Active{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*70}")
            print(f"{Fore.YELLOW}  • Type your message and press Enter")
            print(f"{Fore.YELLOW}  • Exit: type 'exit', 'quit', or 'be quiet'")
            print(f"{Fore.YELLOW}  • Hotkeys: Ctrl+M (mute), Escape (emergency stop)")
            print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}\n")

    async def _run_voice_mode(self) -> None:
        """Run voice interaction mode with wake word detection."""
        # Start wake word listening
        await self.bus.publish(
            topic="wake.start",
            payload={},
            sender="coordinator",
            priority=MessagePriority.HIGH,
        )

        # Keep running until interrupted
        try:
            while self._running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    async def _run_text_mode(self) -> None:
        """Run text interaction mode with stdin input."""
        self._text_mode_task = asyncio.create_task(self._text_input_loop())

        try:
            while self._running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            if self._text_mode_task and not self._text_mode_task.done():
                self._text_mode_task.cancel()

    async def _text_input_loop(self) -> None:
        """Read text input from stdin in background."""
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                # Read input in executor to avoid blocking with colored prompt
                prompt = f"{Fore.CYAN}> {Style.RESET_ALL}"
                user_input = await loop.run_in_executor(None, lambda: input(prompt).strip())

                if not user_input:
                    continue

                # Check for exit (redundant now but kept for direct exit words)
                if user_input.lower() in {"exit", "quit", "goodbye"}:
                    self._print_freya("Goodbye!")
                    self._running = False
                    break

                # Send to dialog agent (will check for natural language exits)
                await self._handle_user_input(user_input)

            except EOFError:
                self._running = False
                break
            except Exception as exc:
                logger.exception(f"Error in text input loop: {exc}")

    async def _handle_wake_detected(self, message: Message) -> None:
        """Handle wake word detection - start conversation flow."""
        transcript = message.payload.get("transcript", "").strip()
        channel_id = message.payload.get("channel_id", "pc")

        if not transcript:
            return

        logger.info(f"Wake detected on {channel_id}: '{transcript}'")

        # Query memory for relevant context
        memories_text = await self._query_relevant_memories(transcript)

        # Inject memories into dialog context
        if memories_text:
            await self.bus.publish(
                topic="dialog.inject_context",
                payload={"context": memories_text},
                sender="coordinator",
                priority=MessagePriority.NORMAL,
            )

        # Send to dialog agent with channel info
        await self._handle_user_input(transcript, channel_id)

    async def _handle_user_input(self, user_text: str, channel_id: str = "pc") -> None:
        """Process user input through dialog agent."""
        # Print user input with color
        self._print_user(user_text)
        
        # Check for natural language exit commands
        if self._is_exit_command(user_text):
            self._print_freya("Okay, shutting down. Goodbye!")
            if self._mode == "voice":
                await self.bus.publish(
                    topic="speech.speak_request",
                    payload={"text": "Okay, shutting down. Goodbye!", "channel_id": channel_id},
                    sender="coordinator",
                    priority=MessagePriority.NORMAL,
                )
                await asyncio.sleep(2)  # Let TTS finish
            self._running = False
            return
        
        # Store user message in memory
        await self.bus.publish(
            topic="memory.store",
            payload={"content": user_text, "role": "user", "importance": 1},
            sender="coordinator",
            priority=MessagePriority.NORMAL,
        )

        # Send to dialog agent with channel context
        await self.bus.publish(
            topic="dialog.request",
            payload={"text": user_text, "stream": True},  # Removed channel_id (not in DialogRequestPayload schema)
            sender="coordinator",
            priority=MessagePriority.HIGH,
        )

    async def _handle_dialog_chunk(self, message: Message) -> None:
        """Handle dialog chunk - forward to speech agent for TTS."""
        text = message.payload.get("text", "")
        channel_id = message.payload.get("channel_id", "pc")

        if not text:
            return

        # Forward to SpeechAgent in voice mode
        if self._mode == "voice":
            # Accumulate for final colored print
            self._response_buffer += text
            
            await self.bus.publish(
                topic="speech.speak_request",
                payload={"text": text, "channel_id": channel_id},
                sender="coordinator",
                priority=MessagePriority.HIGH,
                correlation_id=message.correlation_id,
            )
        else:
            # In text mode, accumulate and print with color
            if not self._response_started:
                # Print header on first chunk
                print(f"{Fore.MAGENTA}┌─ Freya:{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}│ {Style.RESET_ALL}", end="", flush=True)
                self._response_started = True
            
            self._response_buffer += text
            print(f"{Fore.MAGENTA}{text}{Style.RESET_ALL}", end="", flush=True)

    async def _handle_dialog_complete(self, message: Message) -> None:
        """Handle dialog completion - store response in memory."""
        response = message.payload.get("response", "")
        model = message.payload.get("model", "unknown")
        duration_ms = message.payload.get("duration_ms", 0)

        if not response:
            return

        logger.info(f"Dialog complete: model={model}, duration={duration_ms}ms")

        # Print colored output based on mode
        if self._mode == "text":
            # Close the text mode streaming output
            print(f"\n{Fore.MAGENTA}└{'─' * 60}{Style.RESET_ALL}")
            self._response_started = False
        else:
            # Voice mode - print complete response with color
            if self._response_buffer:
                self._print_freya(self._response_buffer)
        
        # Clear response buffer
        self._response_buffer = ""

        # Store assistant response
        await self.bus.publish(
            topic="memory.store",
            payload={"content": response, "role": "assistant", "importance": 1},
            sender="coordinator",
            priority=MessagePriority.NORMAL,
        )

    async def _handle_tool_result(self, message: Message) -> None:
        """Handle tool execution result - inject into dialog context."""
        tool_name = message.payload.get("tool", "unknown")
        result = message.payload.get("result", "")

        if result:
            context_text = f"Tool '{tool_name}' result: {result}"
            await self.bus.publish(
                topic="dialog.inject_context",
                payload={"context": context_text},
                sender="coordinator",
                priority=MessagePriority.NORMAL,
            )

    async def _handle_transcription(self, message: Message) -> None:
        """Handle speech transcription from SpeechAgent."""
        text = message.payload.get("text", "").strip()
        channel_id = message.payload.get("channel_id", "pc")

        if not text:
            return

        logger.info(f"Transcription from {channel_id}: '{text}'")
        await self._handle_user_input(text, channel_id)

    async def _query_relevant_memories(self, query: str, limit: int = 3) -> str:
        """Query memory agent for relevant context."""
        # Create correlation ID for tracking
        correlation_id = f"memory_query_{time.time()}"

        # Container for results
        results_container = {"results": []}

        # Subscribe to results
        async def collect_results(msg: Message):
            if msg.correlation_id == correlation_id:
                results_container["results"] = msg.payload.get("results", [])

        self.bus.subscribe("memory.results", collect_results)

        # Publish query
        await self.bus.publish(
            topic="memory.query",
            payload={"query": query, "limit": limit, "min_score": 0.3},
            sender="coordinator",
            priority=MessagePriority.NORMAL,
            correlation_id=correlation_id,
        )

        # Wait for results (with timeout)
        for _ in range(10):  # 1 second timeout
            if results_container["results"]:
                break
            await asyncio.sleep(0.1)

        # Format memories as context
        memories = results_container["results"]
        if not memories:
            return ""

        context_lines = ["Relevant memories:"]
        for mem in memories:
            content = mem.get("content", "")
            role = mem.get("role", "")
            context_lines.append(f"- [{role}] {content}")

        return "\n".join(context_lines)


def create_coordinator_from_config(config) -> OrchestrationCoordinator:
    """
    Factory function to create coordinator from config.

    This matches the interface of the old orchestrator for easy migration.
    """
    # Import here to avoid circular dependencies
    from freya.config import Settings
    from freya.context import ConversationContext
    from freya.memory import ChromaMemoryStore
    from freya.ollama_client import OllamaClient
    from freya.tools import ToolManager
    from freya.wake import WakeWordDetector

    # Initialize components
    print("[DEBUG] factory: Creating OllamaClient...")
    ollama = OllamaClient(config.ollama)
    print("[DEBUG] factory: Creating ConversationContext...")
    context = ConversationContext(
        system_prompt=config.app.system_prompt,
        max_history=config.app.max_history,
    )

    # Memory
    print("[DEBUG] factory: Creating ChromaMemoryStore...")
    memory_store = ChromaMemoryStore(
        db_path=config.memory.long_term.db_path,
    )
    print("[DEBUG] factory: ChromaMemoryStore created")

    # Tools
    print("[DEBUG] factory: Creating ToolManager...")
    tool_manager = ToolManager()
    print("[DEBUG] factory: ToolManager created")

    # Wake detector (optional)
    wake_detector = None
    if hasattr(config, "wake_detector"):
        try:
            wake_detector = WakeWordDetector(config.wake_detector)
        except Exception as exc:
            logger.warning(f"Failed to initialize wake detector: {exc}")

    return OrchestrationCoordinator(
        ollama_client=ollama,
        context=context,
        config=config,  # Pass full config for SpeechAgent
        memory_store=memory_store,
        tool_manager=tool_manager,
        wake_word=config.app.wake_word,
        wake_sensitivity=config.app.wake_word_sensitivity,
        session_window=config.app.wake_session_seconds,
        wake_detector=wake_detector,
        interaction_mode=config.app.interaction_mode,
    )
