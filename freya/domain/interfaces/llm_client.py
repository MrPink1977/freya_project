"""LLM client interface protocol."""

from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from freya.domain.value_objects.message import Message


@runtime_checkable
class ILLMClient(Protocol):
    """
    Interface for LLM clients.
    
    Supports both streaming and non-streaming responses.
    """

    async def generate(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate a response (non-streaming).
        
        Args:
            messages: Conversation history
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
            
        Raises:
            ServiceUnavailableError: If LLM service is unavailable
            NetworkError: If network request fails
        """
        ...

    async def generate_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response.
        
        Args:
            messages: Conversation history
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            Response chunks as they are generated
            
        Raises:
            ServiceUnavailableError: If LLM service is unavailable
            NetworkError: If network request fails
        """
        ...

    async def list_models(self) -> list[str]:
        """
        List available models.
        
        Returns:
            List of model names
        """
        ...

    async def is_available(self) -> bool:
        """
        Check if LLM service is available.
        
        Returns:
            True if service is reachable
        """
        ...
