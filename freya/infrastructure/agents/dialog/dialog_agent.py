"""
Refactored Dialog Agent with reduced complexity.

Responsibilities:
- Coordinate LLM conversation flow
- Delegate to specialized services
- Publish events
"""

from __future__ import annotations

from freya.domain.exceptions import AgentMessageError
from freya.domain.interfaces.llm_client import ILLMClient
from freya.domain.interfaces.message_bus import IMessageBus
from freya.domain.services.context_builder import ContextBuilder
from freya.domain.services.model_selector import ModelSelector
from freya.domain.value_objects.event import Event, EventType
from freya.infrastructure.agents.base.base_agent import BaseAgent
from freya.infrastructure.agents.dialog.response_streamer import ResponseStreamer
from freya.shared.logging.decorators import log_async_errors, log_async_performance


class DialogAgent(BaseAgent):
    """
    Dialog agent for LLM conversations.
    
    Subscribes to:
    - dialog.request: Generate LLM response
    - dialog.clear_context: Reset conversation
    
    Publishes:
    - dialog.chunk: Streaming response chunks
    - dialog.complete: Complete response
    - dialog.error: Errors
    """

    def __init__(
        self,
        message_bus: IMessageBus,
        llm_client: ILLMClient,
        context_builder: ContextBuilder,
        model_selector: ModelSelector,
        response_streamer: ResponseStreamer,
    ) -> None:
        """
        Initialize dialog agent.
        
        Args:
            message_bus: Message bus for communication
            llm_client: LLM client for generation
            context_builder: Builds conversation context
            model_selector: Selects appropriate model
            response_streamer: Handles streaming responses
        """
        super().__init__("dialog_agent", message_bus)

        self._llm = llm_client
        self._context_builder = context_builder
        self._model_selector = model_selector
        self._streamer = response_streamer

    def subscribes_to(self) -> list[str]:
        """Event subscriptions."""
        return [
            EventType.DIALOG_REQUEST,
            "dialog.clear_context",
        ]

    @log_async_errors()
    async def _handle_event_internal(self, event: Event) -> None:
        """Route events to appropriate handlers."""
        if event.event_type == EventType.DIALOG_REQUEST:
            await self._handle_dialog_request(event)
        elif event.event_type == "dialog.clear_context":
            await self._handle_clear_context(event)

    @log_async_performance(threshold_ms=5000)
    async def _handle_dialog_request(self, event: Event) -> None:
        """
        Handle dialog request.
        
        Simplified by delegating to specialized services.
        """
        try:
            # Extract request data
            user_text = event.data.get("text", "")
            if not user_text:
                raise AgentMessageError(
                    "Missing 'text' in dialog request",
                    message_type=event.event_type,
                )

            stream = event.data.get("stream", True)
            correlation_id = event.correlation_id

            # Build conversation context
            messages = await self._context_builder.build_context(
                user_text=user_text,
                event_data=event.data,
            )

            # Select appropriate model
            model = await self._model_selector.select_model(
                user_text=user_text,
                messages=messages,
                override_model=event.data.get("model"),
            )

            # Generate response
            if stream:
                await self._generate_streaming_response(
                    messages=messages,
                    model=model,
                    correlation_id=correlation_id,
                )
            else:
                await self._generate_complete_response(
                    messages=messages,
                    model=model,
                    correlation_id=correlation_id,
                )

        except Exception as e:
            self._logger.error(
                "Dialog request failed",
                error=str(e),
                exc_info=e,
            )
            await self.publish_event(
                event_type=EventType.DIALOG_ERROR,
                data={"error": str(e)},
                correlation_id=event.correlation_id,
            )

    async def _generate_streaming_response(
        self,
        messages: list[any],
        model: str,
        correlation_id: str | None,
    ) -> None:
        """Generate streaming response using ResponseStreamer."""
        await self._streamer.stream_response(
            llm_client=self._llm,
            messages=messages,
            model=model,
            correlation_id=correlation_id,
            on_chunk=lambda chunk: self._on_response_chunk(chunk, correlation_id),
            on_complete=lambda response, metadata: self._on_response_complete(
                response, metadata, correlation_id
            ),
        )

    async def _generate_complete_response(
        self,
        messages: list[any],
        model: str,
        correlation_id: str | None,
    ) -> None:
        """Generate complete (non-streaming) response."""
        response = await self._llm.generate(
            messages=messages,
            model=model,
        )

        await self.publish_event(
            event_type=EventType.DIALOG_COMPLETE,
            data={
                "response": response,
                "model": model,
                "streaming": False,
            },
            correlation_id=correlation_id,
        )

    async def _on_response_chunk(
        self,
        chunk: str,
        correlation_id: str | None,
    ) -> None:
        """Handle response chunk."""
        await self.publish_event(
            event_type=EventType.DIALOG_CHUNK,
            data={"chunk": chunk},
            correlation_id=correlation_id,
        )

    async def _on_response_complete(
        self,
        response: str,
        metadata: dict[str, any],
        correlation_id: str | None,
    ) -> None:
        """Handle response completion."""
        await self.publish_event(
            event_type=EventType.DIALOG_COMPLETE,
            data={
                "response": response,
                "streaming": True,
                **metadata,
            },
            correlation_id=correlation_id,
        )

    async def _handle_clear_context(self, event: Event) -> None:
        """Clear conversation context."""
        await self._context_builder.clear_context()
        self._logger.info("Conversation context cleared")
