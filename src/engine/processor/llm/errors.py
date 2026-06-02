"""Typed LLM failure modes.

Every LLM-call failure inside the processor is mapped to one of the
classes below before it reaches the FastAPI route. The classes are
subclasses of the existing ``ProcessorError`` so any caller that
currently catches ``ProcessorError`` keeps working unchanged. New
callers that want fine-grained handling can match the specific
subclass directly.

The distinction matters because the gateway's orchestrator currently
logs every 500 from ``/internal/processor/process`` as a
PIPELINE_ERROR. Truncation and schema violations are not
pipeline-level events; they are per-symbol analysis failures. The
router translates these typed errors to per-symbol unavailable
results so one symbol's bad LLM output never aborts a multi-symbol
cycle.
"""

from __future__ import annotations

from typing import Any

from engine.shared.exceptions import ProcessorError


class LLMError(ProcessorError):
    """Base for every typed LLM failure.

    Subclassing ``ProcessorError`` preserves the existing
    ``except ProcessorError`` paths in ``service.py``,
    ``trading_plan``, and ``performance_review`` without change. New
    code can match the more specific subclass.
    """

    pass


class LLMTruncatedError(LLMError):
    """The provider stopped generating before the response completed.

    Carries the provider's ``finish_reason`` and the reported output
    token count so the operator can decide whether to raise
    ``reasoning_budget_tokens``, raise ``max_output_tokens``, or
    switch to a non-thinking model.
    """

    def __init__(
        self,
        message: str,
        *,
        finish_reason: str,
        output_tokens: int = 0,
        max_output_tokens: int = 0,
        response_length: int = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged: dict[str, Any] = {
            "finish_reason": finish_reason,
            "output_tokens": output_tokens,
            "max_output_tokens": max_output_tokens,
            "response_length": response_length,
        }
        if details:
            merged.update(details)
        super().__init__(message, details=merged)
        self.finish_reason = finish_reason
        self.output_tokens = output_tokens
        self.max_output_tokens = max_output_tokens
        self.response_length = response_length


class LLMSchemaViolationError(LLMError):
    """The wire response did not validate against ``AnalysisOutput``.

    Should be rare after Phase 2: provider-native structured output
    masks invalid tokens at the decoder so the wire response is
    already schema-valid. The fallback path (providers without
    structured-output support) can still raise this.
    """

    def __init__(
        self,
        message: str,
        *,
        validation_errors: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged: dict[str, Any] = {"validation_errors": validation_errors or []}
        if details:
            merged.update(details)
        super().__init__(message, details=merged)
        self.validation_errors = validation_errors or []


class LLMSafetyFilterError(LLMError):
    """Provider blocked the response on a safety / policy filter.

    Not retryable. Surfaces a distinct code so the operator can see
    safety blocks separately from quota / transient noise on
    Prometheus.
    """

    pass


class LLMRateLimitedError(LLMError):
    """Provider returned a 429 / RESOURCE_EXHAUSTED.

    Distinct from ``QuotaExceededError`` which is raised by our own
    metering layer for tier-based caps. ``LLMRateLimitedError`` comes
    from the upstream provider (Anthropic / OpenAI / Gemini /
    self-hosted).
    """

    pass


class LLMTransientError(LLMError):
    """5xx, timeout, or transient network failure from the provider.

    The retry layer already classifies and retries these. This class
    exists so callers above the retry layer can still distinguish a
    transient failure ("the call never completed") from a structured
    failure ("the call completed but produced unusable output").
    """

    pass


class LLMDuplicateSuppressedError(LLMError):
    """This analysis call is a duplicate and was deliberately not run.

    Raised by the idempotency guard when an identical call (same
    user_id + symbol + prompt_hash) is already in flight or just
    completed, and this caller therefore must NOT issue its own LLM
    call. It is not a failure of the analysis -- the authoritative
    result is being produced by the in-flight owner. The router maps it
    to HTTP 409 with code "llm_duplicate_suppressed"; it is never
    retried.
    """

    pass


