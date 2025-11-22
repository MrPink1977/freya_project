"""Response streamer for handling LLM streaming responses."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from freya.domain.exceptions import TimeoutError
from freya.domain.interfaces.llm_client import ILLMClient
from freya.domain.value_objects.message import Message
from freya.shared.logging.decorators import log_async_performance
from freya.shared.logging.logger import get_logger

logger = get_logger(__name__)

OnChunkCallback = Callable[[str], Awaitable[None]]
OnCompleteCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class ResponseStreamer:
    """
    Handles streaming LLM responses.
    
    Responsibilities:
    - Stream response chunks
    - Track performance metrics
    - Handle timeouts
    - Invoke callbacks
    """

    def __init__(
        self,
        chunk_timeout: float = 10.0,
        total_timeout: float = 120.0,
    ) -> None:
        """
        Initialize response streamer.
        
        Args:
            chunk_timeout: Max seconds between chunks
            total_timeout: Max total streaming duration
        """
        self._chunk_timeout = chunk_timeout
        self._total_timeout = total_timeout

    @log_async_performance(threshold_ms=10000)
    async def stream_response(
        self,
        llm_client: ILLMClient,
        messages: list[Message],
        model: str,
        correlation_id: str | None,
        on_chunk: OnChunkCallback,
        on_complete: OnCompleteCallback,
    ) -> None:
        """
        Stream LLM response with callbacks.
        
        Args:
            llm_client: LLM client
            messages: Conversation messages
            model: Model to use
            correlation_id: Correlation ID for tracking
            on_chunk: Callback for each chunk
            on_complete: Callback when complete
            
        Raises:
            TimeoutError: If streaming times out
        """
        full_response = ""
        chunk_count = 0
        start_time = time.perf_counter()
        last_chunk_time = start_time

        try:
            # Stream from LLM
            async for chunk in llm_client.generate_stream(messages, model=model):
                current_time = time.perf_counter()

                # Check total timeout
                if current_time - start_time > self._total_timeout:
                    raise TimeoutError(
                        f"Streaming exceeded total timeout",
                        timeout_seconds=self._total_timeout,
                    )

                # Check chunk timeout
                if current_time - last_chunk_time > self._chunk_timeout:
                    raise TimeoutError(
                        f"No chunk received within timeout",
                        timeout_seconds=self._chunk_timeout,
                    )

                # Process chunk
                if chunk:
                    full_response += chunk
                    chunk_count += 1
                    last_chunk_time = current_time

                    # Invoke chunk callback
                    await on_chunk(chunk)

            # Calculate metrics
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            tokens = len(full_response.split())  # Rough estimate

            metadata = {
                "model": model,
                "tokens": tokens,
                "chunks": chunk_count,
                "duration_ms": duration_ms,
            }

            logger.info(
                "Streaming complete",
                **metadata,
                correlation_id=correlation_id,
            )

            # Invoke completion callback
            await on_complete(full_response, metadata)

        except TimeoutError:
            logger.error(
                "Streaming timeout",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
                chunk_count=chunk_count,
            )
            raise

        except Exception as e:
            logger.error(
                "Streaming error",
                error=str(e),
                chunk_count=chunk_count,
                exc_info=e,
            )
            raise
