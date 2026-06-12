"""Exponential backoff + jitter retry logic for LLM API calls.

Classifies errors as retryable (genuinely transient: network glitches,
5xx infra blips, connect/read timeouts) vs non-retryable (auth, invalid
request, content filtering, rate-limit, quota-exhausted, provider
overload).

Rate-limit (429), provider-overload (503 / 529), and quota-exhausted
are deliberately NOT retried inside the same process() call. Those
failure modes do not recover in the seconds an exponential-backoff
retry waits -- provider Retry-After windows on these are typically
minutes. Retrying inside the same call hammers the same rate-limited
endpoint with the same heavy prompt, doubles or triples the token
spend, and blows the user-facing trigger latency budget. The correct
recovery path is the gateway-level cycle retry (or the next scheduled
cycle, or a manual user retrigger) once the rate-limit window has
reset.

Provider-agnostic: reads the active provider from config for metrics.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from engine.processor.config import ProcessorConfig
from engine.processor.llm.errors import (
    LLMError,
    LLMRateLimitedError,
    LLMTransientError,
)
from engine.shared.exceptions import ProcessorError
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import LLM_ERRORS_TOTAL

logger = get_logger(__name__)

T = TypeVar("T")

# Genuinely transient infra failures. 429 (rate-limit), 503 (overload),
# 529 (Anthropic overload) are deliberately excluded -- see module
# docstring.
_RETRYABLE_STATUS_CODES = {500, 502, 504}

_NON_RETRYABLE_ERROR_TYPES = {
    "AuthenticationError",
    "PermissionDeniedError",
    "BadRequestError",
    "NotFoundError",
    # RateLimitError is non-retryable inside the same call. The retry
    # loop cannot resolve a rate-limit; only wall-clock progress can.
    "RateLimitError",
}


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception is retryable.

    Typed-error path first: the providers translate their SDK
    exceptions to ``LLMRateLimitedError`` / ``LLMTransientError``
    inside the provider modules.

      * ``LLMRateLimitedError`` -- NOT retryable. Rate limits and
        quota exhaustion do not recover in the seconds an
        exponential-backoff retry waits.
      * ``LLMTransientError`` -- retryable. Each provider's
        ``_translate_provider_error`` only buckets genuine transient
        signals (timeout / connection / 5xx) into this class.

    Legacy fallback (string-based class-name + status_code probe) is
    retained for callers that bypass the typed translation.
    """
    if isinstance(exc, LLMRateLimitedError):
        return False
    if isinstance(exc, LLMTransientError):
        return True

    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True

    error_type = type(exc).__name__

    if error_type in _NON_RETRYABLE_ERROR_TYPES:
        return False

    if hasattr(exc, "status_code"):
        return exc.status_code in _RETRYABLE_STATUS_CODES

    # String-based fallback for transient network/timeout issues.
    # Note: an explicit "rate limit" / "429" / "resource_exhausted"
    # substring is matched FIRST and excluded so a provider whose SDK
    # class name does not appear in _NON_RETRYABLE_ERROR_TYPES still
    # falls into the non-retryable bucket.
    msg = str(exc).lower()
    if (
        "rate limit" in msg
        or "ratelimit" in msg
        or "429" in msg
        or "resource_exhausted" in msg
        or "insufficient_quota" in msg
        or "overloaded" in msg
        or "503" in msg
        or "529" in msg
    ):
        return False
    if "timeout" in msg or "connection" in msg:
        return True

    return error_type in ("InternalServerError", "APIConnectionError", "APITimeoutError")


def _compute_delay(attempt: int, config: ProcessorConfig) -> float:
    """Compute delay with exponential backoff + full jitter."""
    exp_delay = config.retry_backoff_base_seconds * (2**attempt)
    capped = min(exp_delay, config.retry_backoff_max_seconds)
    return random.uniform(0, capped)  # noqa: S311


async def retry_llm_call[T](
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
        config: Processor configuration with retry policy and provider.
        trace_id: Distributed trace ID for correlation.
        **kwargs: Keyword arguments for fn.

    Returns:
        The result of fn.

    Raises:
        ProcessorError: After all retries exhausted or on non-retryable error.
    """
    provider = config.llm_provider
    last_exc: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await fn(*args, **kwargs)

        except Exception as exc:
            last_exc = exc
            error_type = type(exc).__name__

            LLM_ERRORS_TOTAL.labels(
                provider=provider,
                model=config.model_name,
                error_type=error_type,
            ).inc()

            if not _is_retryable(exc):
                logger.error(
                    "llm_non_retryable_error",
                    extra={
                        "provider": provider,
                        "error_type": error_type,
                        "error": str(exc),
                        "attempt": attempt + 1,
                        "trace_id": trace_id,
                    },
                )
                # Preserve typed LLMError subclasses so the FastAPI router
                # in src/engine/routers/internal.py can match the specific
                # exception class (LLMRateLimitedError /
                # LLMSafetyFilterError / LLMTruncatedError /
                # LLMSchemaViolationError) and return 422 with a stable
                # `code` instead of a generic 500. Wrapping in
                # ProcessorError(...) from exc puts the typed error on
                # __cause__ but changes the raised type, breaking the
                # router's isinstance-based dispatch.
                if isinstance(exc, LLMError):
                    raise
                raise ProcessorError(
                    f"Non-retryable LLM error ({provider}): {error_type}: {exc}",
                    details={
                        "provider": provider,
                        "error_type": error_type,
                        "attempt": attempt + 1,
                    },
                ) from exc

            if attempt >= config.max_retries:
                break

            delay = _compute_delay(attempt, config)

            logger.warning(
                "llm_retryable_error",
                extra={
                    "provider": provider,
                    "error_type": error_type,
                    "error": str(exc),
                    "attempt": attempt + 1,
                    "max_retries": config.max_retries,
                    "retry_delay_seconds": round(delay, 2),
                    "trace_id": trace_id,
                },
            )

            await asyncio.sleep(delay)

    # Retry budget exhausted on a retryable error. If the last
    # exception was a typed LLMError (e.g. LLMTransientError after the
    # retry budget was used up), re-raise it so the router's
    # isinstance-based 422 mapping still fires. Only fall through to
    # the generic ProcessorError wrap for truly untyped exceptions.
    if isinstance(last_exc, LLMError):
        raise last_exc
    raise ProcessorError(
        f"LLM call failed after {config.max_retries + 1} attempts ({provider}): {last_exc}",
        details={
            "provider": provider,
            "error_type": type(last_exc).__name__ if last_exc else "unknown",
            "total_attempts": config.max_retries + 1,
        },
    )
