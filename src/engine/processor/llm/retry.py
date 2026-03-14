"""Exponential backoff + jitter retry logic for LLM API calls.

Classifies errors as retryable (transient network, rate limit,
server errors) vs non-retryable (auth, invalid request, content
filtering). Respects retry budgets and max delay caps.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Awaitable, Callable, TypeVar

from engine.shared.exceptions import ProcessorError
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import LLM_ERRORS_TOTAL
from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLM_PROVIDER, PROCESSOR_NAME

logger = get_logger(__name__)

T = TypeVar("T")

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 529}

_NON_RETRYABLE_ERROR_TYPES = {
    "AuthenticationError",
    "PermissionDeniedError",
    "BadRequestError",
    "NotFoundError",
}


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception is retryable."""
    error_type = type(exc).__name__

    if error_type in _NON_RETRYABLE_ERROR_TYPES:
        return False

    if hasattr(exc, "status_code"):
        return exc.status_code in _RETRYABLE_STATUS_CODES

    if "timeout" in str(exc).lower() or "connection" in str(exc).lower():
        return True

    if error_type in ("RateLimitError", "InternalServerError", "APIConnectionError", "APITimeoutError"):
        return True

    return False


def _compute_delay(attempt: int, config: ProcessorConfig) -> float:
    """Compute delay with exponential backoff + full jitter."""
    exp_delay = config.retry_backoff_base_seconds * (2 ** attempt)
    capped = min(exp_delay, config.retry_backoff_max_seconds)
    return random.uniform(0, capped)  # noqa: S311


async def retry_llm_call(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    config: ProcessorConfig,
    trace_id: str | None = None,
    **kwargs: Any,
) -> T:
    """Execute an async LLM call with retry on transient failures.

    Args:
        fn: Async callable to execute.
        *args: Positional arguments for fn.
        config: Processor configuration with retry policy.
        trace_id: Distributed trace ID for correlation.
        **kwargs: Keyword arguments for fn.

    Returns:
        The result of fn.

    Raises:
        ProcessorError: After all retries exhausted or on non-retryable error.
    """
    last_exc: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await fn(*args, **kwargs)

        except Exception as exc:
            last_exc = exc
            error_type = type(exc).__name__

            LLM_ERRORS_TOTAL.labels(
                provider=LLM_PROVIDER,
                model=config.model_name,
                error_type=error_type,
            ).inc()

            if not _is_retryable(exc):
                logger.error(
                    "llm_non_retryable_error",
                    extra={
                        "error_type": error_type,
                        "error": str(exc),
                        "attempt": attempt + 1,
                        "trace_id": trace_id,
                    },
                )
                raise ProcessorError(
                    f"Non-retryable LLM error: {error_type}: {exc}",
                    details={"error_type": error_type, "attempt": attempt + 1},
                ) from exc

            if attempt >= config.max_retries:
                break

            delay = _compute_delay(attempt, config)

            logger.warning(
                "llm_retryable_error",
                extra={
                    "error_type": error_type,
                    "error": str(exc),
                    "attempt": attempt + 1,
                    "max_retries": config.max_retries,
                    "retry_delay_seconds": round(delay, 2),
                    "trace_id": trace_id,
                },
            )

            await asyncio.sleep(delay)

    raise ProcessorError(
        f"LLM call failed after {config.max_retries + 1} attempts: {last_exc}",
        details={
            "error_type": type(last_exc).__name__ if last_exc else "unknown",
            "total_attempts": config.max_retries + 1,
        },
    )
