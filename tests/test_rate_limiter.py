"""Tests for rate limiter utility."""

from __future__ import annotations

import asyncio
import time

import pytest

from freya.utils.rate_limiter import RateLimitError, TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    """Test token bucket rate limiting."""

    @pytest.mark.asyncio
    async def test_allows_burst_requests(self):
        """Rate limiter allows burst of requests."""
        limiter = TokenBucketRateLimiter(rate=10, burst=3, time_window=60.0)

        # Should allow 3 requests immediately (burst)
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

        # 4th request should wait (rate is 10/60 = 0.167 per second, ~6 seconds per token)
        start = time.monotonic()
        await limiter.acquire(timeout=10.0)
        elapsed = time.monotonic() - start

        assert elapsed > 5.0  # Had to wait about 6 seconds

    @pytest.mark.asyncio
    async def test_enforces_rate_limit(self):
        """Rate limiter enforces requests per time window."""
        limiter = TokenBucketRateLimiter(rate=2, burst=1, time_window=1.0)

        # First request immediate
        await limiter.acquire()

        # Second request should wait ~0.5 seconds
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        assert 0.4 < elapsed < 0.7  # Approximately 0.5 seconds

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """Rate limiter raises RateLimitError on timeout."""
        limiter = TokenBucketRateLimiter(rate=1, burst=1, time_window=10.0)

        # Use up the burst
        await limiter.acquire()

        # Next request should timeout (needs 10 seconds, timeout is 0.1)
        with pytest.raises(RateLimitError, match="timeout"):
            await limiter.acquire(timeout=0.1)

    @pytest.mark.asyncio
    async def test_tokens_refill_over_time(self):
        """Tokens refill at specified rate."""
        limiter = TokenBucketRateLimiter(rate=10, burst=2, time_window=1.0)

        # Use burst
        await limiter.acquire()
        await limiter.acquire()

        # Wait for tokens to refill
        await asyncio.sleep(0.3)  # Should refill ~3 tokens

        # Should be able to get 2 more without much wait
        start = time.monotonic()
        await limiter.acquire()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        assert elapsed < 0.2  # Should be fast

    @pytest.mark.asyncio
    async def test_stats_return_correct_info(self):
        """get_stats returns limiter configuration."""
        limiter = TokenBucketRateLimiter(rate=5, burst=2, time_window=30.0)

        stats = limiter.get_stats()
        assert stats["rate"] == 5
        assert stats["burst"] == 2
        assert stats["time_window"] == 30.0
        assert "available_tokens" in stats

    @pytest.mark.asyncio
    async def test_concurrent_requests_queued(self):
        """Concurrent requests are queued properly."""
        limiter = TokenBucketRateLimiter(rate=5, burst=1, time_window=1.0)

        async def make_request():
            await limiter.acquire(timeout=2.0)
            return True

        # Launch 3 concurrent requests
        start = time.monotonic()
        results = await asyncio.gather(
            make_request(), make_request(), make_request()
        )
        elapsed = time.monotonic() - start

        assert all(results)
        assert elapsed > 0.3  # Multiple requests had to wait

    @pytest.mark.asyncio
    async def test_no_timeout_waits_indefinitely(self):
        """No timeout means wait indefinitely for token."""
        limiter = TokenBucketRateLimiter(rate=2, burst=1, time_window=1.0)

        await limiter.acquire()  # Use burst

        # This should wait ~0.5 seconds without timeout
        start = time.monotonic()
        await limiter.acquire(timeout=None)
        elapsed = time.monotonic() - start

        assert 0.4 < elapsed < 0.7
