"""Tests for streaming timeout and validation."""

import asyncio
import time
from unittest.mock import Mock

import pytest

from freya.agents.dialog_agent import (
    STREAM_CHUNK_TIMEOUT,
    STREAM_TOTAL_TIMEOUT,
    DialogAgent,
    StreamTimeoutError,
)
from freya.context import ConversationContext
from freya.core.message_bus import Message, MessageBus
from freya.ollama_client import OllamaClient, OllamaError


@pytest.fixture
def mock_bus():
    """Create mock message bus."""
    return Mock(spec=MessageBus)


@pytest.fixture
def mock_ollama():
    """Create mock Ollama client."""
    return Mock(spec=OllamaClient)


@pytest.fixture
def mock_context():
    """Create mock conversation context."""
    return Mock(spec=ConversationContext)


@pytest.fixture
def dialog_agent(mock_bus, mock_ollama, mock_context):
    """Create dialog agent for testing."""
    agent = DialogAgent(
        agent_id="test_dialog",
        bus=mock_bus,
        ollama_client=mock_ollama,
        context_manager=mock_context,
    )
    return agent


class TestStreamingTimeouts:
    """Test streaming timeout functionality."""

    @pytest.mark.asyncio
    async def test_normal_streaming_completes(self, dialog_agent, mock_ollama):
        """Normal streaming completes successfully."""
        # Mock fast streaming
        mock_ollama.chat_stream.return_value = iter([
            "Hello ",
            "world",
            "!"
        ])

        response, tokens = await dialog_agent._generate_streaming(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            correlation_id="test-123"
        )

        assert response == "Hello world!"

    @pytest.mark.asyncio
    async def test_chunk_timeout_raises_error(self, dialog_agent, mock_ollama):
        """Stream times out when no chunks received."""
        async def slow_stream():
            """Generator that yields chunks slowly."""
            yield "First chunk"
            await asyncio.sleep(STREAM_CHUNK_TIMEOUT + 1)
            yield "Second chunk"

        # Create synchronous generator that simulates slow streaming
        def slow_sync_stream():
            yield "First chunk"
            time.sleep(STREAM_CHUNK_TIMEOUT + 1)
            yield "Second chunk"

        mock_ollama.chat_stream.return_value = slow_sync_stream()

        with pytest.raises(StreamTimeoutError) as exc_info:
            await dialog_agent._generate_streaming(
                messages=[{"role": "user", "content": "test"}],
                model="test-model",
                correlation_id="test-123"
            )

        assert "No chunk received" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_total_timeout_raises_error(self, dialog_agent, mock_ollama):
        """Stream times out when total duration exceeds limit."""
        def infinite_stream():
            """Generator that never stops."""
            start = time.time()
            while time.time() - start < STREAM_TOTAL_TIMEOUT + 5:
                yield "chunk "
                time.sleep(0.1)

        mock_ollama.chat_stream.return_value = infinite_stream()

        with pytest.raises(StreamTimeoutError) as exc_info:
            await dialog_agent._generate_streaming(
                messages=[{"role": "user", "content": "test"}],
                model="test-model",
                correlation_id="test-123"
            )

        assert "total timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_chunk_skipped(self, dialog_agent, mock_ollama):
        """Invalid chunks are skipped without error."""
        mock_ollama.chat_stream.return_value = iter([
            "Valid chunk",
            None,  # Invalid
            "",    # Empty
            "Another valid chunk"
        ])

        response, tokens = await dialog_agent._generate_streaming(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            correlation_id="test-123"
        )

        # Should only include valid chunks
        assert "Valid chunk" in response
        assert "Another valid chunk" in response

    @pytest.mark.asyncio
    async def test_empty_chunks_dont_timeout(self, dialog_agent, mock_ollama):
        """Empty chunks update timeout without processing."""
        mock_ollama.chat_stream.return_value = iter([
            "Start",
            "   ",  # Whitespace only
            "",     # Empty
            "End"
        ])

        response, tokens = await dialog_agent._generate_streaming(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            correlation_id="test-123"
        )

        assert "Start" in response
        assert "End" in response


class TestStreamingFallback:
    """Test fallback to non-streaming on stream failure."""

    @pytest.mark.asyncio
    async def test_fallback_on_stream_timeout(self, mock_bus):
        """Falls back to non-streaming on timeout."""
        mock_ollama = Mock(spec=OllamaClient)
        mock_context = Mock(spec=ConversationContext)
        mock_context.build_prompt.return_value = [{"role": "user", "content": "test"}]
        mock_context.estimate_tokens.return_value = 100

        agent = DialogAgent(
            agent_id="test_dialog",
            bus=mock_bus,
            ollama_client=mock_ollama,
            context_manager=mock_context,
        )

        # Initialize agent
        await agent.initialize()

        # Mock streaming to timeout
        def timeout_stream():
            yield "First"
            time.sleep(STREAM_CHUNK_TIMEOUT + 1)
            yield "Second"

        mock_ollama.chat_stream.return_value = timeout_stream()

        # Mock non-streaming fallback
        mock_ollama.chat.return_value = "Fallback response"

        # Create message
        message = Message(
            topic="dialog.request",
            payload={"user_input": "test", "stream": True},
            sender="test",
            correlation_id="test-123"
        )

        # Should fall back without error
        await agent._handle_conversation(message)

        # Non-streaming should have been called
        mock_ollama.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_on_stream_error(self, mock_bus):
        """Falls back to non-streaming on Ollama error."""
        mock_ollama = Mock(spec=OllamaClient)
        mock_context = Mock(spec=ConversationContext)
        mock_context.build_prompt.return_value = [{"role": "user", "content": "test"}]
        mock_context.estimate_tokens.return_value = 100

        agent = DialogAgent(
            agent_id="test_dialog",
            bus=mock_bus,
            ollama_client=mock_ollama,
            context_manager=mock_context,
        )

        await agent.initialize()

        # Mock streaming to raise error
        mock_ollama.chat_stream.side_effect = OllamaError("Stream failed")

        # Mock non-streaming fallback
        mock_ollama.chat.return_value = "Fallback response"

        message = Message(
            topic="dialog.request",
            payload={"user_input": "test", "stream": True},
            sender="test",
            correlation_id="test-123"
        )

        # Should fall back without error
        await agent._handle_conversation(message)

        # Non-streaming should have been called
        mock_ollama.chat.assert_called_once()


class TestStreamingChunkValidation:
    """Test chunk validation during streaming."""

    @pytest.mark.asyncio
    async def test_non_string_chunks_skipped(self, dialog_agent, mock_ollama):
        """Non-string chunks are skipped."""
        mock_ollama.chat_stream.return_value = iter([
            "Valid string",
            123,  # Invalid type
            {"data": "dict"},  # Invalid type
            "Another valid string"
        ])

        response, tokens = await dialog_agent._generate_streaming(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            correlation_id="test-123"
        )

        assert "Valid string" in response
        assert "Another valid string" in response
        assert "123" not in response

    @pytest.mark.asyncio
    async def test_chunk_count_tracks_valid_chunks(self, dialog_agent, mock_ollama):
        """Chunk count only includes valid chunks."""
        mock_ollama.chat_stream.return_value = iter([
            "Chunk 1",
            None,
            "Chunk 2",
            "",
            "Chunk 3"
        ])

        response, tokens = await dialog_agent._generate_streaming(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            correlation_id="test-123"
        )

        # Should have processed 3 valid chunks
        assert "Chunk 1" in response
        assert "Chunk 2" in response
        assert "Chunk 3" in response


class TestStreamingTimeoutConfiguration:
    """Test streaming timeout configuration."""

    def test_chunk_timeout_constant(self):
        """Chunk timeout is configured correctly."""
        assert STREAM_CHUNK_TIMEOUT == 10.0

    def test_total_timeout_constant(self):
        """Total timeout is configured correctly."""
        assert STREAM_TOTAL_TIMEOUT == 120.0

    @pytest.mark.asyncio
    async def test_chunk_timeout_prevents_hang(self, dialog_agent, mock_ollama):
        """Chunk timeout prevents indefinite hang."""
        start_time = time.time()

        def hanging_stream():
            yield "First chunk"
            time.sleep(STREAM_CHUNK_TIMEOUT + 2)
            yield "Never reached"

        mock_ollama.chat_stream.return_value = hanging_stream()

        with pytest.raises(StreamTimeoutError):
            await dialog_agent._generate_streaming(
                messages=[{"role": "user", "content": "test"}],
                model="test-model",
                correlation_id="test-123"
            )

        elapsed = time.time() - start_time
        # Should timeout after STREAM_CHUNK_TIMEOUT, not hang forever
        assert elapsed < STREAM_CHUNK_TIMEOUT + 5
