"""
Logging decorators for automatic function/method logging.

Provides decorators for:
- Automatic entry/exit logging
- Performance tracking
- Error logging
- Async function support
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar, cast

from freya.shared.logging.logger import get_logger

F = TypeVar("F", bound=Callable[..., Any])


def log_call(logger_name: str | None = None) -> Callable[[F], F]:
    """
    Decorator to log function calls with arguments and return values.
    
    Args:
        logger_name: Optional logger name (defaults to function's module)
        
    Example:
        @log_call()
        def process_data(data: str) -> int:
            return len(data)
    """

    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__
            logger.debug(
                f"Calling {func_name}",
                function=func_name,
                args=str(args)[:100],  # Limit arg length
                kwargs=str(kwargs)[:100],
            )

            try:
                result = func(*args, **kwargs)
                logger.debug(
                    f"{func_name} completed",
                    function=func_name,
                    result=str(result)[:100],
                )
                return result
            except Exception as e:
                logger.error(
                    f"{func_name} failed",
                    function=func_name,
                    error=str(e),
                    exc_info=e,
                )
                raise

        return cast(F, wrapper)

    return decorator


def log_async_call(logger_name: str | None = None) -> Callable[[F], F]:
    """
    Decorator to log async function calls.
    
    Args:
        logger_name: Optional logger name (defaults to function's module)
        
    Example:
        @log_async_call()
        async def fetch_data(url: str) -> dict:
            ...
    """

    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__
            logger.debug(
                f"Calling async {func_name}",
                function=func_name,
                args=str(args)[:100],
                kwargs=str(kwargs)[:100],
            )

            try:
                result = await func(*args, **kwargs)
                logger.debug(
                    f"Async {func_name} completed",
                    function=func_name,
                    result=str(result)[:100],
                )
                return result
            except Exception as e:
                logger.error(
                    f"Async {func_name} failed",
                    function=func_name,
                    error=str(e),
                    exc_info=e,
                )
                raise

        return cast(F, wrapper)

    return decorator


def log_performance(
    logger_name: str | None = None,
    threshold_ms: float = 1000.0,
) -> Callable[[F], F]:
    """
    Decorator to log function performance.
    
    Logs warning if execution time exceeds threshold.
    
    Args:
        logger_name: Optional logger name
        threshold_ms: Warning threshold in milliseconds
        
    Example:
        @log_performance(threshold_ms=500)
        def slow_operation() -> None:
            time.sleep(1)
    """

    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if duration_ms > threshold_ms:
                    logger.warning(
                        f"{func_name} exceeded performance threshold",
                        function=func_name,
                        duration_ms=round(duration_ms, 2),
                        threshold_ms=threshold_ms,
                    )
                else:
                    logger.debug(
                        f"{func_name} performance",
                        function=func_name,
                        duration_ms=round(duration_ms, 2),
                    )

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"{func_name} failed after {duration_ms:.2f}ms",
                    function=func_name,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                    exc_info=e,
                )
                raise

        return cast(F, wrapper)

    return decorator


def log_async_performance(
    logger_name: str | None = None,
    threshold_ms: float = 1000.0,
) -> Callable[[F], F]:
    """
    Decorator to log async function performance.
    
    Args:
        logger_name: Optional logger name
        threshold_ms: Warning threshold in milliseconds
        
    Example:
        @log_async_performance(threshold_ms=500)
        async def slow_async_operation() -> None:
            await asyncio.sleep(1)
    """

    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Async {func_name} exceeded performance threshold",
                        function=func_name,
                        duration_ms=round(duration_ms, 2),
                        threshold_ms=threshold_ms,
                    )
                else:
                    logger.debug(
                        f"Async {func_name} performance",
                        function=func_name,
                        duration_ms=round(duration_ms, 2),
                    )

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Async {func_name} failed after {duration_ms:.2f}ms",
                    function=func_name,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                    exc_info=e,
                )
                raise

        return cast(F, wrapper)

    return decorator


def log_errors(logger_name: str | None = None) -> Callable[[F], F]:
    """
    Decorator to automatically log errors.
    
    Args:
        logger_name: Optional logger name
        
    Example:
        @log_errors()
        def risky_operation() -> None:
            raise ValueError("Something went wrong")
    """

    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}",
                    function=func.__name__,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=e,
                )
                raise

        return cast(F, wrapper)

    return decorator


def log_async_errors(logger_name: str | None = None) -> Callable[[F], F]:
    """
    Decorator to automatically log errors in async functions.
    
    Args:
        logger_name: Optional logger name
    """

    def decorator(func: F) -> F:
        logger = get_logger(logger_name or func.__module__)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in async {func.__name__}",
                    function=func.__name__,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=e,
                )
                raise

        return cast(F, wrapper)

    return decorator
