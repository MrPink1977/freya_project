"""
Circuit breaker pattern implementation for fault tolerance.

Prevents cascading failures by monitoring service health and failing fast
when a service is unhealthy.
"""

import asyncio
import time
from collections import deque
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Any, TypeVar, ParamSpec
import logging

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"      # Failure threshold exceeded, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation with three states:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, all requests fail fast
    - HALF_OPEN: Testing recovery, limited requests allowed
    
    Args:
        failure_threshold: Percentage of failures (0.0-1.0) to trigger OPEN state
        recovery_timeout: Seconds to wait before transitioning to HALF_OPEN
        window_size: Number of recent requests to track for failure rate
        name: Name for logging
    """
    
    def __init__(
        self,
        failure_threshold: float = 0.5,
        recovery_timeout: float = 60.0,
        window_size: int = 10,
        name: str = "circuit_breaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window_size = window_size
        self.name = name
        
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._recent_results: deque[bool] = deque(maxlen=window_size)
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if not self._recent_results:
            return 0.0
        failures = sum(1 for result in self._recent_results if not result)
        return failures / len(self._recent_results)
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._state != CircuitBreakerState.OPEN:
            return False
        if self._last_failure_time is None:
            return False
        return (time.time() - self._last_failure_time) >= self.recovery_timeout
    
    async def _record_success(self) -> None:
        """Record successful request."""
        async with self._lock:
            self._success_count += 1
            self._recent_results.append(True)
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                # Success in HALF_OPEN state means service recovered
                self._state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED")
    
    async def _record_failure(self) -> None:
        """Record failed request."""
        async with self._lock:
            self._failure_count += 1
            self._recent_results.append(False)
            self._last_failure_time = time.time()
            
            # Check if we should open the circuit
            if self._state == CircuitBreakerState.CLOSED:
                if len(self._recent_results) >= self.window_size:
                    if self.failure_rate >= self.failure_threshold:
                        self._state = CircuitBreakerState.OPEN
                        logger.warning(
                            f"Circuit breaker '{self.name}' OPENED "
                            f"(failure rate: {self.failure_rate:.1%})"
                        )
            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Failure in HALF_OPEN means service still unhealthy
                self._state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' returned to OPEN")
    
    async def call(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result from function
            
        Raises:
            CircuitBreakerError: If circuit is OPEN
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            async with self._lock:
                self._state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")
        
        # Fail fast if circuit is OPEN
        if self._state == CircuitBreakerState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN "
                f"(failure rate: {self.failure_rate:.1%})"
            )
        
        # Execute function and track result
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._recent_results.clear()
        self._last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")


def circuit_breaker(
    failure_threshold: float = 0.5,
    recovery_timeout: float = 60.0,
    window_size: int = 10,
    name: Optional[str] = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to wrap function with circuit breaker.
    
    Args:
        failure_threshold: Percentage of failures to trigger OPEN state
        recovery_timeout: Seconds before attempting recovery
        window_size: Number of requests to track
        name: Circuit breaker name (defaults to function name)
    
    Example:
        @circuit_breaker(failure_threshold=0.5, recovery_timeout=60)
        async def call_external_service():
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        breaker_name = name or func.__name__
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            window_size=window_size,
            name=breaker_name
        )
        
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # For sync functions, we need to run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(breaker.call(func, *args, **kwargs))
        
        # Store breaker instance for testing/monitoring
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        wrapper._circuit_breaker = breaker  # type: ignore
        return wrapper
    
    return decorator
