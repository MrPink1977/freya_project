"""Rate limiting utility using token bucket algorithm."""

from __future__ import annotations

import asyncio
import time
from typing import Optional


class RateLimitError(RuntimeError):
    """Raised when rate limit is exceeded."""


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for async operations.

    The token bucket algorithm allows bursts while maintaining
    an average rate limit over time.
    """

    def __init__(
        self,
        rate: float,
        burst: int = 1,
        time_window: float = 60.0,
    ):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum requests per time window
            burst: Maximum burst size (tokens available immediately)
            time_window: Time window in seconds (default: 60 seconds)
        """
        self.rate = rate
        self.burst = burst
        self.time_window = time_window
        self.tokens_per_second = rate / time_window

        self._tokens = float(burst)  # Start with full burst
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: Optional[float] = None) -> None:
        """
        Acquire a token, waiting if necessary.

        Args:
            timeout: Maximum time to wait in seconds (None = no timeout)

        Raises:
            RateLimitError: If timeout expires before token available
        """
        start_time = time.monotonic()

        async with self._lock:
            while True:
                # Refill tokens based on time elapsed
                now = time.monotonic()
                elapsed = now - self._last_update
                self._tokens = min(self.burst, self._tokens + elapsed * self.tokens_per_second)
                self._last_update = now

                # Check if we have a token available
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                # Calculate wait time for next token
                wait_time = (1.0 - self._tokens) / self.tokens_per_second

                # Check timeout
                if timeout is not None:
                    elapsed_total = time.monotonic() - start_time
                    if elapsed_total + wait_time > timeout:
                        raise RateLimitError(
                            f"Rate limit exceeded: timeout after {elapsed_total:.2f}s"
                        )

                # Wait for next token
                await asyncio.sleep(wait_time)

    def get_stats(self) -> dict[str, float]:
        """
        Get current rate limiter statistics.

        Returns:
            Dictionary with tokens, rate, and burst info
        """
        return {
            "available_tokens": self._tokens,
            "rate": self.rate,
            "burst": self.burst,
            "time_window": self.time_window,
        }


__all__ = ["TokenBucketRateLimiter", "RateLimitError"]
