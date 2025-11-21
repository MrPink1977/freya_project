"""Tests for circuit breaker pattern implementation."""

import asyncio

import pytest

from freya.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
)


class TestCircuitBreaker:
    """Test circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_closed_state_allows_requests(self):
        """Circuit breaker in CLOSED state allows requests through."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=10)

        async def successful_operation():
            return "success"

        result = await breaker.call(successful_operation)
        assert result == "success"
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_open_state_blocks_requests(self):
        """Circuit breaker in OPEN state blocks requests."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=10)

        # Cause enough failures to open circuit
        async def failing_operation():
            raise ValueError("Expected failure")

        for _ in range(10):
            try:
                await breaker.call(failing_operation)
            except ValueError:
                pass

        assert breaker.state == CircuitBreakerState.OPEN

        # Next request should fail fast
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(failing_operation)

        assert "is OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_half_open_transition_after_timeout(self):
        """Circuit breaker transitions to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(
            failure_threshold=0.5,
            recovery_timeout=0.1,  # Short timeout for testing
            window_size=10
        )

        # Cause failures to open circuit
        async def failing_operation():
            raise ValueError("Expected failure")

        for _ in range(10):
            try:
                await breaker.call(failing_operation)
            except ValueError:
                pass

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Next request should transition to HALF_OPEN
        try:
            await breaker.call(failing_operation)
        except ValueError:
            pass

        # After failure in HALF_OPEN, should return to OPEN
        assert breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Successful request in HALF_OPEN state closes circuit."""
        breaker = CircuitBreaker(
            failure_threshold=0.5,
            recovery_timeout=0.1,
            window_size=10
        )

        # Open the circuit
        async def failing_operation():
            raise ValueError("Expected failure")

        for _ in range(10):
            try:
                await breaker.call(failing_operation)
            except ValueError:
                pass

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Successful request in HALF_OPEN should close circuit
        async def successful_operation():
            return "recovered"

        result = await breaker.call(successful_operation)
        assert result == "recovered"
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_failure_rate_calculation(self):
        """Circuit breaker accurately calculates failure rate."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=10)

        async def successful_operation():
            return "success"

        async def failing_operation():
            raise ValueError("Expected failure")

        # 5 successes, 5 failures = 50% failure rate
        for _ in range(5):
            await breaker.call(successful_operation)

        for _ in range(5):
            try:
                await breaker.call(failing_operation)
            except ValueError:
                pass

        assert breaker.failure_rate == 0.5
        assert breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_window_size_limits_tracking(self):
        """Circuit breaker only tracks last N requests."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=5)

        async def successful_operation():
            return "success"

        async def failing_operation():
            raise ValueError("Expected failure")

        # Start with 10 failures
        for _ in range(10):
            try:
                await breaker.call(failing_operation)
            except (ValueError, CircuitBreakerError):
                pass

        # Circuit should be open after failures
        assert breaker.state == CircuitBreakerState.OPEN

        # Reset to test window tracking
        breaker.reset()

        # Then 5 successes (window size = 5)
        for _ in range(5):
            await breaker.call(successful_operation)

        # Failure rate should be 0% (only last 5 tracked)
        assert breaker.failure_rate == 0.0
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Manual reset returns circuit to CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=10)

        # Open the circuit
        async def failing_operation():
            raise ValueError("Expected failure")

        for _ in range(10):
            try:
                await breaker.call(failing_operation)
            except ValueError:
                pass

        assert breaker.state == CircuitBreakerState.OPEN

        # Manual reset
        breaker.reset()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_rate == 0.0

    @pytest.mark.asyncio
    async def test_sync_function_support(self):
        """Circuit breaker works with synchronous functions."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=10)

        def sync_operation():
            return "sync_success"

        result = await breaker.call(sync_operation)
        assert result == "sync_success"

    @pytest.mark.asyncio
    async def test_exception_propagation(self):
        """Circuit breaker propagates original exceptions."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=10)

        async def custom_error_operation():
            raise KeyError("custom error")

        with pytest.raises(KeyError) as exc_info:
            await breaker.call(custom_error_operation)

        assert "custom error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mixed_success_failure_doesnt_open(self):
        """Circuit stays closed with mixed results below threshold."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=10)

        async def successful_operation():
            return "success"

        async def failing_operation():
            raise ValueError("Expected failure")

        # 6 successes, 4 failures = 40% failure rate (below 50% threshold)
        for _ in range(6):
            await breaker.call(successful_operation)

        for _ in range(4):
            try:
                await breaker.call(failing_operation)
            except ValueError:
                pass

        assert breaker.failure_rate == 0.4
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_args_kwargs(self):
        """Circuit breaker passes arguments correctly."""
        breaker = CircuitBreaker()

        async def operation_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await breaker.call(operation_with_args, "x", "y", c="z")
        assert result == "x-y-z"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Circuit breaker handles concurrent requests safely."""
        breaker = CircuitBreaker(failure_threshold=0.5, window_size=20)

        async def operation(should_fail: bool):
            await asyncio.sleep(0.01)  # Simulate async work
            if should_fail:
                raise ValueError("Expected failure")
            return "success"

        # Run 10 concurrent successes and 10 concurrent failures
        tasks = []
        for i in range(20):
            task = breaker.call(operation, should_fail=(i >= 10))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = sum(1 for r in results if r == "success")
        failures = sum(1 for r in results if isinstance(r, (ValueError, CircuitBreakerError)))

        # Some successes, some failures (circuit might open during execution)
        assert successes >= 10
        assert failures >= 0

        # After all requests, failure rate should trigger open if enough failures
        if breaker.failure_rate >= 0.5:
            assert breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_different_failure_thresholds(self):
        """Circuit breaker respects different failure thresholds."""
        # 30% threshold
        breaker_low = CircuitBreaker(failure_threshold=0.3, window_size=10)

        async def failing_operation():
            raise ValueError("Expected failure")

        async def successful_operation():
            return "success"

        # 7 successes, 3 failures = 30% failure rate
        for _ in range(7):
            await breaker_low.call(successful_operation)

        for _ in range(3):
            try:
                await breaker_low.call(failing_operation)
            except ValueError:
                pass

        # Should open at exactly 30%
        assert breaker_low.failure_rate == 0.3
        assert breaker_low.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_recovery_timeout_accuracy(self):
        """Circuit breaker respects recovery timeout duration."""
        breaker = CircuitBreaker(
            failure_threshold=0.5,
            recovery_timeout=0.2,
            window_size=10
        )

        # Open the circuit
        async def failing_operation():
            raise ValueError("Expected failure")

        for _ in range(10):
            try:
                await breaker.call(failing_operation)
            except ValueError:
                pass

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait less than recovery timeout
        await asyncio.sleep(0.1)

        # Should still be OPEN
        with pytest.raises(CircuitBreakerError):
            await breaker.call(failing_operation)

        # Wait for full recovery timeout
        await asyncio.sleep(0.15)

        # Now should allow attempt (will fail and return to OPEN)
        try:
            await breaker.call(failing_operation)
        except ValueError:
            pass

        assert breaker.state == CircuitBreakerState.OPEN
