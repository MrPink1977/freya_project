"""
Freya Web GUI Integration Layer

Bridges the FastAPI web interface with Freya's event-driven agent architecture.
"""

from __future__ import annotations

import asyncio
from typing import Optional
import logging

from freya.config import load_settings, Settings
from freya.infrastructure.messaging.message_bus import MessageBus
from freya.infrastructure.agents.dialog.dialog_agent import DialogAgent
from freya.domain.services.context_builder import ContextBuilder
from freya.domain.services.model_selector import ModelSelector
from freya.infrastructure.agents.dialog.response_streamer import ResponseStreamer
from freya.infrastructure.llm.ollama_client import OllamaClient
from freya.domain.value_objects.event import Event, EventType

logger = logging.getLogger(__name__)


class FreyaIntegration:
    """
    Integration layer between web GUI and Freya core.

    Manages the lifecycle of Freya's components and provides
    a simplified interface for the web GUI.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the integration layer."""
        self.config: Optional[Settings] = None
        self.message_bus: Optional[MessageBus] = None
        self.dialog_agent: Optional[DialogAgent] = None
        self.llm_client: Optional[OllamaClient] = None

        self._config_path = config_path
        self._response_callbacks: list[callable] = []
        self._running = False

    async def initialize(self) -> bool:
        """
        Initialize Freya components.

        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing Freya integration...")

            # Load configuration
            self.config = load_settings(self._config_path)
            logger.info(f"Configuration loaded: {self.config.ollama.model}")

            # Create message bus
            self.message_bus = MessageBus()
            await self.message_bus.start()
            logger.info("MessageBus started")

            # Subscribe to dialog events for web GUI
            await self.message_bus.subscribe(
                EventType.DIALOG_CHUNK,
                self._handle_dialog_chunk,
                subscriber_id="web_gui"
            )
            await self.message_bus.subscribe(
                EventType.DIALOG_COMPLETE,
                self._handle_dialog_complete,
                subscriber_id="web_gui"
            )
            await self.message_bus.subscribe(
                EventType.DIALOG_ERROR,
                self._handle_dialog_error,
                subscriber_id="web_gui"
            )

            # Create LLM client
            self.llm_client = OllamaClient(
                host=self.config.ollama.host,
                model=self.config.ollama.model,
                temperature=self.config.ollama.options.get("temperature", 0.7),
            )
            logger.info(f"LLM client created: {self.config.ollama.host}")

            # Create dialog agent components
            context_builder = ContextBuilder(
                max_history=self.config.app.max_history,
                system_prompt=self.config.app.system_prompt,
            )

            model_selector = ModelSelector(
                primary_model=self.config.ollama.model,
            )

            response_streamer = ResponseStreamer(
                message_bus=self.message_bus,
            )

            # Create and start dialog agent
            self.dialog_agent = DialogAgent(
                message_bus=self.message_bus,
                llm_client=self.llm_client,
                context_builder=context_builder,
                model_selector=model_selector,
                response_streamer=response_streamer,
            )

            await self.dialog_agent.start()
            logger.info("DialogAgent started")

            self._running = True
            logger.info("Freya integration initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Freya integration: {e}", exc_info=True)
            return False

    async def shutdown(self) -> None:
        """Shutdown Freya components."""
        logger.info("Shutting down Freya integration...")

        self._running = False

        if self.dialog_agent:
            await self.dialog_agent.stop()
            logger.info("DialogAgent stopped")

        if self.message_bus:
            await self.message_bus.stop()
            logger.info("MessageBus stopped")

        logger.info("Freya integration shutdown complete")

    async def send_message(self, user_message: str, user_id: str = "web_user") -> None:
        """
        Send a message to Freya's dialog system.

        Args:
            user_message: The user's message
            user_id: User identifier
        """
        if not self._running:
            raise RuntimeError("Freya integration not initialized")

        logger.info(f"Sending message from {user_id}: {user_message}")

        # Create and publish dialog request event
        event = Event(
            event_type=EventType.DIALOG_REQUEST,
            data={
                "message": user_message,
                "user_id": user_id,
            },
        )

        await self.message_bus.publish(event)

    def register_response_callback(self, callback: callable) -> None:
        """
        Register a callback for dialog responses.

        Callback signature: async def callback(response_type: str, data: dict)
        Where response_type is: "chunk", "complete", or "error"
        """
        self._response_callbacks.append(callback)

    async def _handle_dialog_chunk(self, event: Event) -> None:
        """Handle streaming response chunks."""
        chunk = event.data.get("chunk", "")

        for callback in self._response_callbacks:
            try:
                await callback("chunk", {"chunk": chunk})
            except Exception as e:
                logger.error(f"Error in response callback: {e}")

    async def _handle_dialog_complete(self, event: Event) -> None:
        """Handle complete dialog response."""
        response = event.data.get("response", "")

        logger.info(f"Dialog complete: {len(response)} characters")

        for callback in self._response_callbacks:
            try:
                await callback("complete", {"response": response})
            except Exception as e:
                logger.error(f"Error in response callback: {e}")

    async def _handle_dialog_error(self, event: Event) -> None:
        """Handle dialog errors."""
        error = event.data.get("error", "Unknown error")

        logger.error(f"Dialog error: {error}")

        for callback in self._response_callbacks:
            try:
                await callback("error", {"error": str(error)})
            except Exception as e:
                logger.error(f"Error in response callback: {e}")

    @property
    def is_running(self) -> bool:
        """Check if integration is running."""
        return self._running

    @property
    def status(self) -> dict:
        """Get status information."""
        return {
            "running": self._running,
            "message_bus": self.message_bus is not None,
            "dialog_agent": self.dialog_agent is not None,
            "llm_client": self.llm_client is not None,
            "model": self.config.ollama.model if self.config else None,
        }
