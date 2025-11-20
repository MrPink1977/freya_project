"""
DIALOG AGENT - LLM conversation management with streaming and context.

Handles all LLM interactions with smart model selection and context management.
"""

from __future__ import annotations

import re
import time
from typing import Optional

from freya.agents.base_agent import AgentCapability, BaseAgent
from freya.context import ConversationContext
from freya.core.message_bus import Message, MessageBus, MessagePriority
from freya.exceptions import AgentMessageError
from freya.logger import get_logger
from freya.ollama_client import OllamaClient, OllamaError, OllamaModelNotFoundError
from freya.schemas.messages import DialogRequestPayload
from freya.schemas.validation import validate_message_payload
from freya.utils.confusion_detection import detect_confusion

logger = get_logger("dialog_agent")


class DialogAgent(BaseAgent):
    """
    Agent managing LLM conversations with streaming and context.

    Subscribes to:
    - "dialog.request" - Generate LLM response
    - "dialog.clear_context" - Reset conversation history
    - "dialog.set_model" - Change default model
    - "dialog.inject_context" - Add external context (tool results, memories)

    Publishes to:
    - "dialog.chunk" - Streaming response chunk (for live TTS)
    - "dialog.complete" - Full response with metadata
    - "dialog.error" - LLM errors
    """

    def __init__(
        self,
        agent_id: str,
        bus: MessageBus,
        ollama_client: OllamaClient,
        context_manager: ConversationContext,
        # Model configuration
        default_model: str = "llama3.2:3b",
        reasoning_model: str = "dolphin-mixtral:8x7b",
        code_model: str = "deepseek-coder-v2:16b-lite",
        # Context management
        context_limit: int = 32000,
        transfer_threshold: float = 0.75,
        keep_recent_turns: int = 20,
        # Escalation
        enable_escalation: bool = True,
    ) -> None:
        """
        Initialize dialog agent.

        Args:
            agent_id: Unique agent identifier
            bus: Message bus for communication
            ollama_client: Ollama client for LLM requests
            context_manager: Conversation context manager
            default_model: Fast model for simple queries
            reasoning_model: Powerful model for complex reasoning
            code_model: Specialized model for code tasks
            context_limit: Max tokens before transfer
            transfer_threshold: Transfer to long-term at this % (0.75 = 75%)
            keep_recent_turns: How many recent turns to keep after transfer
            enable_escalation: Auto-retry with better model on confusion
        """
        super().__init__(agent_id, bus)
        self._ollama = ollama_client
        self._context = context_manager

        # Model configuration
        self._models = {
            "default": default_model,
            "reasoning": reasoning_model,
            "code": code_model,
        }
        self._current_model = default_model

        # Context management
        self._context_limit = context_limit
        self._transfer_threshold = transfer_threshold
        self._keep_recent_turns = keep_recent_turns

        # Escalation
        self._enable_escalation = enable_escalation

        # Injected context (tool results, memories)
        self._injected_context: list[str] = []

    async def initialize(self) -> None:
        """Initialize dialog agent."""
        self.logger.info(
            f"DialogAgent initialized: default_model={self._models['default']}, "
            f"context_limit={self._context_limit}, transfer_threshold={self._transfer_threshold}"
        )

    def get_capabilities(self) -> list[AgentCapability]:
        """Return dialog management capabilities."""
        return [
            AgentCapability(
                name="llm_conversation",
                description="Streaming LLM conversation with smart model selection",
                input_topics=[
                    "dialog.request",
                    "dialog.clear_context",
                    "dialog.set_model",
                    "dialog.inject_context",
                ],
                output_topics=["dialog.chunk", "dialog.complete", "dialog.error"],
            )
        ]

    async def process_message(self, message: Message) -> None:
        """
        Process dialog-related messages.

        Args:
            message: Dialog command message
        """
        if message.topic == "dialog.request":
            await self._handle_conversation_request(message)
        elif message.topic == "dialog.clear_context":
            self._clear_context()
        elif message.topic == "dialog.set_model":
            self._set_model(message.payload.get("model", self._models["default"]))
        elif message.topic == "dialog.inject_context":
            self._inject_context(message.payload.get("context", ""))

    async def _handle_conversation_request(self, message: Message) -> None:
        """Handle conversation request with streaming and escalation."""
        # Validate payload
        try:
            payload = validate_message_payload(message.payload, DialogRequestPayload, self.agent_id)
        except AgentMessageError as exc:
            self.logger.error("Invalid dialog request: %s", exc)
            await self.publish(
                topic="dialog.error",
                payload={"error": str(exc), "correlation_id": message.correlation_id},
                correlation_id=message.correlation_id,
            )
            return
        
        # Use validated data
        user_text = payload.text
        override_model = payload.model
        stream = payload.stream

        # Add user message to context
        self._context.add_user_message(user_text)

        # Check context size and transfer if needed
        await self._check_and_transfer_context()

        # Build prompt with injected context
        messages = self._build_prompt()

        # Select model (override or default)
        model = override_model or self._current_model

        start_time = time.time()

        try:
            if stream:
                # Streaming response with live TTS
                response, token_count = await self._generate_streaming(
                    messages, model, message.correlation_id
                )
            else:
                # Non-streaming (fallback)
                response, token_count = await self._generate_non_streaming(messages, model)

            # Check for confusion and escalate if enabled
            if (
                self._enable_escalation
                and self._is_confused(response)
                and model == self._models["default"]
            ):
                self.logger.info(
                    f"Model {model} confused, escalating to {self._models['reasoning']}"
                )

                # Retry with reasoning model
                if stream:
                    response, token_count = await self._generate_streaming(
                        messages, self._models["reasoning"], message.correlation_id
                    )
                else:
                    response, token_count = await self._generate_non_streaming(
                        messages, self._models["reasoning"]
                    )

            # Add assistant response to context
            self._context.add_assistant_message(response)

            # Clear injected context after use
            self._injected_context.clear()

            duration_ms = int((time.time() - start_time) * 1000)

            # Publish complete message
            await self.publish(
                topic="dialog.complete",
                payload={
                    "response": response,
                    "model": model,
                    "tokens": token_count,
                    "duration_ms": duration_ms,
                    "streaming": stream,
                },
                correlation_id=message.correlation_id,
                priority=MessagePriority.HIGH,
            )

            self.logger.info(
                f"Response generated: model={model}, tokens={token_count}, "
                f"duration={duration_ms}ms, streaming={stream}"
            )

        except OllamaModelNotFoundError as exc:
            self.logger.error(f"Model not found: {exc.model}")
            await self.publish_error(
                message,
                exc,
                details={
                    "model": exc.model,
                    "message": "Model not installed. Run `ollama pull {model}`",
                },
            )
        except OllamaError as exc:
            self.logger.exception(f"Ollama error: {exc}")
            await self.publish_error(message, exc)
        except Exception as exc:
            self.logger.exception(f"Unexpected error in conversation: {exc}")
            await self.publish_error(message, exc)

    async def _generate_streaming(
        self, messages: list[dict], model: str, correlation_id: Optional[str]
    ) -> tuple[str, int]:
        """Generate streaming response, publishing chunks."""
        full_response = ""
        buffer = ""
        chunk_count = 0

        try:
            # Stream from Ollama
            for chunk in self._ollama.chat_stream(messages):
                if not chunk:
                    continue

                full_response += chunk
                buffer += chunk
                chunk_count += 1

                # Check for sentence boundaries
                speakable, buffer = self._partition_speakable(buffer)

                for piece in speakable:
                    # Clean markdown for TTS
                    cleaned = self._strip_markdown_for_speech(piece)

                    # Publish chunk for live TTS
                    await self.publish(
                        topic="dialog.chunk",
                        payload={"text": cleaned, "raw": piece},
                        correlation_id=correlation_id,
                        priority=MessagePriority.HIGH,
                    )

            # Flush remaining buffer
            if buffer.strip():
                cleaned = self._strip_markdown_for_speech(buffer)
                await self.publish(
                    topic="dialog.chunk",
                    payload={"text": cleaned, "raw": buffer},
                    correlation_id=correlation_id,
                    priority=MessagePriority.HIGH,
                )

        except Exception as exc:
            self.logger.exception(f"Error during streaming: {exc}")
            raise

        # Estimate token count (rough: 1 token ≈ 4 chars)
        token_count = len(full_response) // 4

        return full_response.strip(), token_count

    async def _generate_non_streaming(self, messages: list[dict], model: str) -> tuple[str, int]:
        """Generate non-streaming response (fallback)."""
        response = self._ollama.chat(messages)
        token_count = len(response) // 4
        return response, token_count

    def _build_prompt(self) -> list[dict]:
        """Build prompt with injected context and conversation history."""
        messages = self._context.as_messages()

        # Inject external context (tool results, memories) before user's last message
        if self._injected_context:
            context_text = "\n\n".join(self._injected_context)

            # Insert before last user message
            if messages and messages[-1]["role"] == "user":
                messages.insert(
                    -1, {"role": "system", "content": f"Relevant context:\n{context_text}"}
                )

        return messages

    async def _check_and_transfer_context(self) -> None:
        """Check context size and transfer old turns to long-term memory if needed."""
        # Estimate current token count
        messages = self._context.as_messages()
        estimated_tokens = sum(len(msg["content"]) // 4 for msg in messages)

        threshold_tokens = int(self._context_limit * self._transfer_threshold)

        if estimated_tokens > threshold_tokens:
            self.logger.info(
                f"Context size {estimated_tokens} exceeds threshold {threshold_tokens}, "
                f"transferring to long-term memory"
            )

            # Get old turns (keep only recent)
            all_turns = list(self._context._messages)
            if len(all_turns) > self._keep_recent_turns:
                old_turns = all_turns[: -self._keep_recent_turns]
                recent_turns = all_turns[-self._keep_recent_turns :]

                # Transfer old turns to MemoryAgent
                for turn in old_turns:
                    await self.publish(
                        topic="memory.store",
                        payload={
                            "content": turn.content,
                            "role": turn.role,
                            "importance": 2,  # Higher importance for conversation
                        },
                        priority=MessagePriority.NORMAL,
                    )

                # Update context with only recent turns
                self._context._messages.clear()
                self._context._messages.extend(recent_turns)

                self.logger.info(
                    f"Transferred {len(old_turns)} turns to long-term memory, "
                    f"kept {len(recent_turns)} recent turns"
                )

    def _is_confused(self, response: str) -> bool:
        """Check if response indicates confusion or uncertainty."""
        is_confused, confidence, category = detect_confusion(response, threshold=0.7)
        if is_confused:
            self.logger.debug(
                f"Confusion detected: confidence={confidence:.2f}, category={category}"
            )
        return is_confused

    def _clear_context(self) -> None:
        """Clear conversation context."""
        self._context._messages.clear()
        self._injected_context.clear()
        self.logger.info("Conversation context cleared")

    def _set_model(self, model: str) -> None:
        """Set current model."""
        self._current_model = model
        self.logger.info(f"Default model changed to: {model}")

    def _inject_context(self, context: str) -> None:
        """Inject external context (tool results, memories)."""
        if context and context.strip():
            self._injected_context.append(context.strip())
            self.logger.debug(f"Injected context: {context[:100]}...")

    def _partition_speakable(self, buffer: str) -> tuple[list[str], str]:
        """Split buffer into speakable chunks at sentence boundaries."""
        pieces: list[str] = []
        working = buffer

        while True:
            split_idx = self._find_sentence_break(working)
            if split_idx is None:
                break

            piece = working[:split_idx].strip()
            if piece:
                pieces.append(piece)
            working = working[split_idx:].lstrip()

        # If buffer is too long without sentence break, force split
        if not pieces and len(working) > 240:
            cutoff = working.rfind(" ")
            if cutoff <= 0:
                cutoff = len(working)
            piece = working[:cutoff].strip()
            if piece:
                pieces.append(piece)
                working = working[cutoff:].lstrip()

        return pieces, working

    def _find_sentence_break(self, text: str) -> Optional[int]:
        """Find next sentence boundary index."""
        newline_idx = text.find("\n")
        if newline_idx >= 0 and newline_idx < 200:
            return newline_idx + 1

        for idx, char in enumerate(text):
            if char in ".!?":
                next_idx = idx + 1
                next_char = text[next_idx] if next_idx < len(text) else ""
                if not next_char or next_char.isspace():
                    return next_idx

        return None

    def _strip_markdown_for_speech(self, text: str) -> str:
        """
        Remove markdown formatting for natural TTS.

        Removes:
        - Bold/italic: **, *, _
        - Code blocks: ```
        - Inline code: `
        - Links: [text](url) -> text
        """
        if not text:
            return text

        # Remove code blocks
        cleaned = re.sub(r"```[\s\S]*?```", "", text)

        # Remove inline code
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

        # Remove bold/italic
        cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
        cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
        cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)

        # Remove markdown links [text](url) -> text
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

        # Remove awkward parentheticals
        cleaned = re.sub(r"\s*\([A-Z][^)]{0,30}\)\s*", " ", cleaned)

        # Clean up spaces
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned.strip()

    async def cleanup(self) -> None:
        """Cleanup dialog agent resources."""
        self.logger.debug("DialogAgent cleanup complete")
