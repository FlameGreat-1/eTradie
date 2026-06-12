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
        or "timed out" in msg
        or "deadline_exceeded" in msg
        or "deadline exceeded" in msg
        or "rate limit" in msg
        or "ratelimit" in name
        or "429" in msg
        or "resource_exhausted" in msg
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
    # 'billing' is deliberately NOT a predicate here: it appears in
    # routine support references (e.g. 'contact support at
    # billing@anthropic.com') that have nothing to do with quota
    # exhaustion. The four predicates below cover every realistic
    # quota-error message from anthropic, openai, gemini, and
    # openai-compatible self-hosted endpoints.
    if (
        "quota" in msg
        or "insufficient_quota" in msg
        or "credit balance" in msg
        or "insufficient funds" in msg
        # Gemini's google-genai SDK surfaces hard quota exhaustion as
        # a 429 RESOURCE_EXHAUSTED status. We special-case it before
        # the rate-limit bucket so the user gets the 'top up' CTA
        # rather than the 'wait a moment' CTA \u2014 the two have very
        # different remediations and conflating them sends the user
        # in circles.
        or "resource_exhausted" in msg
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
    # We deliberately do NOT match the bare three-digit substrings
    # '401' or '403' — they appear in arbitrary error bodies (request
    # payloads that contain those digits as data) and would misroute
    # non-auth errors into the 'check your key' branch. The named-
    # status predicates already cover every realistic provider auth
    # error from anthropic, openai, gemini, and openai-compatible
    # self-hosted endpoints.
    if (
        "invalid api key" in msg
        or "invalid_api_key" in msg
        or "unauthorized" in msg
        or "authentication" in msg
        or "permission denied" in msg
        # Gemini-specific phrasings the predicates above miss:
        # 'API key not valid. Please pass a valid API key.' and
        # '403 PERMISSION_DENIED' (lowercased to 'permission_denied'
        # \u2014 underscore form rather than the space-separated form
        # Anthropic/OpenAI use).
        or "api key not valid" in msg
        or "api_key_invalid" in msg
        or "permission_denied" in msg
    ):
        return ClassifiedFailure(
            CODE_AUTH_INVALID,
            "AI provider rejected the API key; "
            "please verify your key in Settings and retry.",
        )

    # Model mis-configuration: the configured model does not exist
    # for the active provider/key.
    # The 'does not exist' clause is parenthesised explicitly because
    # Python's and-binds-tighter-than-or precedence gave the correct
    # semantic only by accident; an editor inserting a new clause
    # could silently break it. Parenthesising the conjunction makes
    # the intent unambiguous and future-edit safe.
    if (
        "model_not_found" in msg
        or "model not found" in msg
        or "unknown model" in msg
        or ("does not exist" in msg and "model" in msg)
        # Gemini's google-genai SDK surfaces a missing-model error as
        # '404 NOT_FOUND. models/gemini-XXX is not found ...'. The
        # 'is not found' + 'model' conjunction is the precise predicate
        # \u2014 'not found' alone would over-match (any 404 for any
        # resource type).
        or ("is not found" in msg and "model" in msg)
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
