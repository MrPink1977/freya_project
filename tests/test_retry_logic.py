"""Tests for retry logic with exponential backoff."""

from unittest.mock import Mock, patch

import pytest
from requests import HTTPError, Response

from freya.config import OllamaConfig
from freya.ollama_client import OllamaClient, OllamaModelNotFoundError
from freya.tools.web_search import WebSearchError, search_web_async


class TestOllamaClientRetry:
    """Test retry logic in Ollama client."""

    def test_retry_on_connection_error(self):
        """Retry on connection errors."""
        config = OllamaConfig(host="http://localhost:11434", model="test-model", options={})
        client = OllamaClient(config)

        with patch.object(client._session, 'post') as mock_post:
            # Fail twice, then succeed
            mock_response = Mock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {"content": "success"}
            }

            mock_post.side_effect = [
                ConnectionError("Connection refused"),
                ConnectionError("Connection refused"),
                mock_response
            ]

            result = client.chat([{"role": "user", "content": "test"}])
            assert result == "success"
            assert mock_post.call_count == 3

    def test_no_retry_on_model_not_found(self):
        """Don't retry when model is not found."""
        config = OllamaConfig(host="http://localhost:11434", model="nonexistent", options={})
        client = OllamaClient(config)

        with patch.object(client._session, 'post') as mock_post:
            mock_response = Mock(spec=Response)
            mock_response.status_code = 404
            mock_response.json.return_value = {
                "error": "model not found"
            }
            mock_response.text = "model not found"
            mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
            mock_post.return_value = mock_response

            with patch.object(client, '_model_missing', return_value=True):
                with pytest.raises(OllamaModelNotFoundError):
                    client.chat([{"role": "user", "content": "test"}])

                # Should only try once, no retries
                assert mock_post.call_count == 1

    def test_no_retry_on_4xx_errors(self):
        """Don't retry on 4xx client errors (except 429)."""
        config = OllamaConfig(host="http://localhost:11434", model="test-model", options={})
        client = OllamaClient(config)

        with patch.object(client._session, 'post') as mock_post:
            mock_response = Mock(spec=Response)
            mock_response.status_code = 400
            mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
            mock_post.return_value = mock_response

            with pytest.raises(HTTPError):
                client.chat([{"role": "user", "content": "test"}])

            # Should only try once
            assert mock_post.call_count == 1

    def test_retry_exhausted_raises_exception(self):
        """Raise exception after max retries exhausted."""
        config = OllamaConfig(host="http://localhost:11434", model="test-model", options={})
        client = OllamaClient(config)

        with patch.object(client._session, 'post') as mock_post:
            mock_post.side_effect = ConnectionError("Connection refused")

            with pytest.raises(ConnectionError):
                client.chat([{"role": "user", "content": "test"}])

            # Should try 3 times
            assert mock_post.call_count == 3

    def test_successful_first_attempt_no_retry(self):
        """Successful first attempt doesn't trigger retry."""
        config = OllamaConfig(host="http://localhost:11434", model="test-model", options={})
        client = OllamaClient(config)

        with patch.object(client._session, 'post') as mock_post:
            mock_response = Mock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {"content": "success"}
            }
            mock_post.return_value = mock_response

            result = client.chat([{"role": "user", "content": "test"}])
            assert result == "success"
            assert mock_post.call_count == 1


class TestWebSearchRetry:
    """Test retry logic in web search."""

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self):
        """Retry on connection errors in web search."""
        with patch('freya.tools.web_search.DDGS') as mock_ddgs_class:
            mock_ddgs = Mock()
            mock_ddgs_class.return_value = mock_ddgs

            # Fail once, then succeed
            mock_ddgs.text.side_effect = [
                ConnectionError("Connection failed"),
                [{"title": "Result", "body": "Description", "href": "http://example.com"}]
            ]

            result = await search_web_async("test query", use_cache=False)
            assert "Result" in result
            assert mock_ddgs.text.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Retry on timeout errors."""
        with patch('freya.tools.web_search.DDGS') as mock_ddgs_class:
            mock_ddgs = Mock()
            mock_ddgs_class.return_value = mock_ddgs

            # Fail with timeout, then succeed
            mock_ddgs.text.side_effect = [
                TimeoutError("Request timed out"),
                [{"title": "Result", "body": "Description", "href": "http://example.com"}]
            ]

            result = await search_web_async("test query", use_cache=False)
            assert "Result" in result
            assert mock_ddgs.text.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self):
        """Raise WebSearchError after retries exhausted."""
        with patch('freya.tools.web_search.DDGS') as mock_ddgs_class:
            mock_ddgs = Mock()
            mock_ddgs_class.return_value = mock_ddgs

            # Always fail
            mock_ddgs.text.side_effect = ConnectionError("Connection failed")

            with pytest.raises(WebSearchError):
                await search_web_async("test query", use_cache=False)

            # Should try 2 times (initial + 1 retry)
            assert mock_ddgs.text.call_count == 2

    @pytest.mark.asyncio
    async def test_successful_first_attempt_no_retry(self):
        """Successful first attempt doesn't trigger retry."""
        with patch('freya.tools.web_search.DDGS') as mock_ddgs_class:
            mock_ddgs = Mock()
            mock_ddgs_class.return_value = mock_ddgs
            mock_ddgs.text.return_value = [
                {"title": "Result", "body": "Description", "href": "http://example.com"}
            ]

            result = await search_web_async("test query", use_cache=False)
            assert "Result" in result
            assert mock_ddgs.text.call_count == 1


class TestRetryBackoffTiming:
    """Test exponential backoff timing."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_increases_wait_time(self):
        """Verify exponential backoff increases wait time between retries."""
        import time

        with patch('freya.tools.web_search.DDGS') as mock_ddgs_class:
            mock_ddgs = Mock()
            mock_ddgs_class.return_value = mock_ddgs

            # Track timing of calls
            call_times = []

            def track_call(*args, **kwargs):
                call_times.append(time.time())
                raise ConnectionError("Connection failed")

            mock_ddgs.text.side_effect = track_call

            try:
                await search_web_async("test query", use_cache=False)
            except WebSearchError:
                pass

            # Should have 2 calls (initial + 1 retry)
            assert len(call_times) == 2

            # Second call should be at least 2 seconds later (exponential backoff)
            time_diff = call_times[1] - call_times[0]
            assert time_diff >= 1.8  # Allow some margin for timing

    def test_ollama_backoff_timing(self):
        """Verify Ollama client exponential backoff timing."""
        import time

        config = OllamaConfig(host="http://localhost:11434", model="test-model")
        client = OllamaClient(config)

        call_times = []

        def track_call(*args, **kwargs):
            call_times.append(time.time())
            raise ConnectionError("Connection refused")

        with patch.object(client._session, 'post', side_effect=track_call):
            try:
                client.chat([{"role": "user", "content": "test"}])
            except ConnectionError:
                pass

        # Should have 3 calls (initial + 2 retries)
        assert len(call_times) == 3

        # First retry should be ~1s later, second retry ~2s after that
        first_gap = call_times[1] - call_times[0]
        second_gap = call_times[2] - call_times[1]

        assert first_gap >= 0.8  # ~1s with margin
        assert second_gap >= 1.8  # ~2s with margin
