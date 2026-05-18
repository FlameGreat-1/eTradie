"""Shared LLM error classifier for background generators.

The trading-plan and performance-review generators both:

  1. Retry LLM calls on transient failures with exponential backoff.
  2. After every attempt fails, surface a user-safe message to the
     SPA via the gateway's fail callback.

Before this module, each generator carried its own copy of the
transient-detection heuristic and a single hard-coded fail message
("AI service is temporarily unavailable; please try again"). That
message did not help the user diagnose anything: a missing/invalid
key, an exhausted quota, a missing model, and a transient 5xx all
looked identical.

This module concentrates the two policies:

  - is_transient_llm_error(exc)    -> bool
  - classify_llm_failure(exc)      -> ClassifiedFailure

The classifier is provider-agnostic and never imports a provider
SDK at module load time, so a deploy without every SDK installed
still boots. Recognition is by exception class name plus message
substring, which is the same surface both generators already used
inline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassifiedFailure:
    """Outcome of classify_llm_failure().

    code is a stable identifier the gateway can use to route the
    user to remediation copy (e.g. show a 'configure key' CTA on
    auth_invalid). user_message is a short English sentence safe
    to display verbatim to the end user.
    """

    code: str
    user_message: str


# Canonical codes. Kept as module constants so call sites can match
# on them without copy-pasting the strings.
CODE_QUOTA_EXCEEDED = "quota_exceeded"
CODE_RATE_LIMITED = "rate_limited"
CODE_AUTH_INVALID = "auth_invalid"
CODE_MODEL_NOT_FOUND = "model_not_found"
CODE_TIMEOUT = "timeout"
CODE_TRANSIENT = "transient"
CODE_UNKNOWN = "unknown"


def is_transient_llm_error(exc: Optional[BaseException]) -> bool:
    """Return True when the failure is worth retrying.

    Provider SDKs raise their own error types (anthropic.APIError,
    openai.APIStatusError, google.api_core.exceptions.*). We do not
    import any of them — we recognise them by class name and message
    substring so the engine boots cleanly without every SDK
    installed. The classification mirrors what the inline heuristics
    in the two generators were doing before this module landed; the
    two copies have been deleted in favour of this single source of
    truth.
    """
    if exc is None:
        return False
    if isinstance(exc, (httpx.TimeoutException, httpx.HTTPError)):
        return True
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return (
        "timeout" in name
        or "timeout" in msg
        or "rate limit" in msg
        or "ratelimit" in name
        or "429" in msg
        or " 500" in msg
        or " 502" in msg
        or " 503" in msg
        or " 504" in msg
        or "overloaded" in msg
        or "unavailable" in msg
    )


def classify_llm_failure(exc: Optional[BaseException]) -> ClassifiedFailure:
    """Map an LLM-call exception to a (code, user-safe message) tuple.

    The user message is the SAME one the gateway will render in the
    fail banner, so it must be free of provider names, stack traces,
    and any internal ID. Operational details remain on the engine's
    structured logs (where the raw exception is logged alongside
    user_id and trace_id).
    """
    if exc is None:
        return ClassifiedFailure(
            CODE_UNKNOWN,
            "AI service is temporarily unavailable; please try again",
        )

    name = type(exc).__name__.lower()
    msg = str(exc).lower()

    # Quota / credit / insufficient funds. Distinct from rate-limit
    # because the remediation is different (top up the account, not
    # wait a few seconds).
    if (
        "quota" in msg
        or "insufficient_quota" in msg
        or "credit balance" in msg
        or "insufficient funds" in msg
        or "billing" in msg
    ):
        return ClassifiedFailure(
            CODE_QUOTA_EXCEEDED,
            "Your AI provider quota or credit is exhausted; "
            "please top up or switch keys and retry.",
        )

    # Rate-limit. Provider SDKs typically raise a 429.
    if (
        "rate limit" in msg
        or "ratelimit" in name
        or "429" in msg
        or "too many requests" in msg
    ):
        return ClassifiedFailure(
            CODE_RATE_LIMITED,
            "AI provider rate limit reached; please wait a moment and retry.",
        )

    # Authentication failure: invalid key, revoked key, missing key.
    if (
        "invalid api key" in msg
        or "invalid_api_key" in msg
        or "unauthorized" in msg
        or "401" in msg
        or "403" in msg
        or "authentication" in msg
        or "permission denied" in msg
    ):
        return ClassifiedFailure(
            CODE_AUTH_INVALID,
            "AI provider rejected the API key; "
            "please verify your key in Settings and retry.",
        )

    # Model mis-configuration: the configured model does not exist
    # for the active provider/key.
    if (
        "model_not_found" in msg
        or "model not found" in msg
        or "unknown model" in msg
        or "does not exist" in msg and "model" in msg
    ):
        return ClassifiedFailure(
            CODE_MODEL_NOT_FOUND,
            "The configured AI model is not available for this key; "
            "please update the model in Settings and retry.",
        )

    # Timeout (either client-side or provider-side). Surfaced
    # distinctly from generic transient because the user may want
    # to know that the request DID start but did not finish.
    if "timeout" in name or "timeout" in msg or "timed out" in msg:
        return ClassifiedFailure(
            CODE_TIMEOUT,
            "AI provider did not respond in time; please retry.",
        )

    # Any other transient signal.
    if is_transient_llm_error(exc):
        return ClassifiedFailure(
            CODE_TRANSIENT,
            "AI service is temporarily unavailable; please retry shortly.",
        )

    # Catch-all. We deliberately do NOT echo the raw exception text —
    # provider SDKs sometimes embed full request URLs, header dumps,
    # or partial payloads in their error strings.
    return ClassifiedFailure(
        CODE_UNKNOWN,
        "AI service returned an unexpected error; please retry. "
        "If this persists, contact support.",
    )
