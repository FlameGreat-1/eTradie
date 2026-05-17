"""LLM call + gateway callback for the Performance Review feature.

Flow:

  1. GET gateway /internal/performance-review/aggregate
     -> deterministic per-window bundle (read from journal in place).
  2. GET gateway /internal/trading-system/:user_id
     -> user's defined operating framework.
  3. GET gateway /internal/performance-review/prior?period=&before=
     -> the prior ready row's review JSON (optional; used for
        trader-evolution deltas per PLAN.md section 12).
  4. Build the prompt, call the PLATFORM LLM client.
  5. Parse + shape into the 14-section wire schema.
  6. POST gateway /internal/performance-review/callback. On any
     failure POST /internal/performance-review/fail so the gateway
     row flips to status='failed' with a user-safe message.

The generator is self-contained: it does not own its HTTP client or
LLM client, so unit tests can swap both with fakes. Mirrors the
trading_plan generator exactly.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from engine.processor.llm.client import LLMClient
from engine.processor.performance_review.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from engine.shared.logging import get_logger

logger = get_logger(__name__)

_INTERNAL_AUTH_HEADER = "X-Internal-Auth"
_INTERNAL_USER_ID_HEADER = "X-User-Id"

# Per-attempt timeout for gateway calls. The aggregator queries are
# read-only against a single table with an index on user_id + closed_at,
# so 10s is generous headroom for warm-up jitter.
_HTTP_TIMEOUT_S = 10.0

# Retry policy for the gateway callback. Same as trading_plan.
_CALLBACK_MAX_ATTEMPTS = 3
_CALLBACK_BACKOFF_S = (0.5, 1.0, 2.0)

# Retry policy for the LLM call.
_LLM_MAX_ATTEMPTS = 3
_LLM_BACKOFF_S = (1.0, 2.0)

# Regex used to strip a stray JSON fence the model occasionally
# wraps the response in.
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class PerformanceReviewGenerationError(Exception):
    """Raised when the LLM call or response parsing fails.

    The message attribute is user-safe: stack traces, internal IDs,
    and provider-specific error envelopes are never propagated.
    """

    def __init__(self, user_safe_message: str) -> None:
        super().__init__(user_safe_message)
        self.user_safe_message = user_safe_message


@dataclass(frozen=True)
class GenerationRequest:
    """Engine-side mirror of src/performancereview/models.go::GenerationRequest."""

    user_id: str
    period: str               # 'weekly' | 'monthly'
    period_start: datetime    # inclusive
    period_end: datetime      # inclusive
    profile_version: int


class PerformanceReviewGenerator:
    """Stateless service wrapping one full review-generation cycle.

    The Container builds ONE instance and reuses it. The LLM client
    is the platform's (Container.processor_llm_client), guaranteeing
    the call uses the platform key.
    """

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        http_client: httpx.AsyncClient,
        gateway_base_url: str,
        management_base_url: str,
        internal_secret: str,
    ) -> None:
        self._llm = llm_client
        self._http = http_client
        self._base_url = gateway_base_url.rstrip("/")
        self._management_url = management_base_url.rstrip("/")
        self._secret = internal_secret

    @classmethod
    def from_container(cls, container: Any) -> Optional["PerformanceReviewGenerator"]:
        """Build a generator using the Container's wired LLM client.

        Returns None when the gateway URL, management URL, or shared
        secret is missing (local dev / tests); callers MUST handle
        the None case by responding 503 to the dispatch request.
        """
        base_url = (
            os.environ.get("ENGINE_GATEWAY_URL")
            or os.environ.get("GATEWAY_HTTP_URL")
            or ""
        ).strip()
        management_url = (
            os.environ.get("ENGINE_MANAGEMENT_HTTP_URL")
            or os.environ.get("MANAGEMENT_HTTP_URL")
            or ""
        ).strip()
        secret = (
            os.environ.get("ENGINE_INTERNAL_SHARED_SECRET")
            or os.environ.get("GATEWAY_ENGINE_INTERNAL_SHARED_SECRET")
            or ""
        ).strip()
        if not base_url or not management_url or not secret:
            logger.info(
                "performance_review_generator_disabled",
                extra={
                    "gateway_url_set": bool(base_url),
                    "management_url_set": bool(management_url),
                    "secret_set": bool(secret),
                },
            )
            return None
        client = httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT_S,
            headers={"Content-Type": "application/json"},
        )
        return cls(
            llm_client=container.processor_llm_client,
            http_client=client,
            gateway_base_url=base_url,
            management_base_url=management_url,
            internal_secret=secret,
        )

    async def aclose(self) -> None:
        """Close the dedicated HTTP client. Safe to re-call."""
        try:
            await self._http.aclose()
        except Exception:
            pass

    # -- Public entry point ----------------------------------------------

    async def run(self, req: GenerationRequest) -> None:
        """Generate the review for `req` and post it back to the gateway.

        Never raises: every failure path culminates in a fail callback
        that flips the gateway row to status='failed' with a user-safe
        message the SPA can render.
        """
        try:
            review = await self._generate(req)
        except PerformanceReviewGenerationError as exc:
            logger.warning(
                "performance_review_generation_failed",
                extra={
                    "user_id": req.user_id,
                    "period": req.period,
                    "reason": exc.user_safe_message,
                },
            )
            await self._post_fail(req, exc.user_safe_message)
            return
        except Exception as exc:
            logger.exception(
                "performance_review_generation_unexpected_error",
                extra={
                    "user_id": req.user_id,
                    "period": req.period,
                    "error_type": type(exc).__name__,
                },
            )
            await self._post_fail(
                req,
                "review generation failed unexpectedly; please try again",
            )
            return

        await self._post_callback(req, review)

    # -- Internals -------------------------------------------------------

    async def _generate(self, req: GenerationRequest) -> dict[str, Any]:
        if not req.user_id:
            raise PerformanceReviewGenerationError("missing user_id")
        if req.period not in ("weekly", "monthly"):
            raise PerformanceReviewGenerationError("invalid period")

        generation_started_at = datetime.now(timezone.utc).isoformat()

        # Step 1: aggregator bundle (from management).
        aggregation = await self._fetch_aggregation(req)

        # Step 2: trading-system profile (from gateway).
        profile = await self._fetch_profile(req.user_id)

        # Step 3: optional prior review (from gateway).
        prior_review = await self._fetch_prior_review(req)

        user_prompt = build_user_prompt(
            user_id=req.user_id,
            period=req.period,
            period_start=req.period_start.isoformat(),
            period_end=req.period_end.isoformat(),
            profile=profile,
            profile_version=req.profile_version,
            aggregation=aggregation,
            prior_review=prior_review,
        )

        # Bounded retry loop for the LLM call. Same transient
        # classification as trading_plan.
        response = None
        last_exc: Optional[Exception] = None
        for attempt in range(_LLM_MAX_ATTEMPTS):
            try:
                response = await self._llm.call(
                    system_prompt=SYSTEM_PROMPT,
                    user_message=user_prompt,
                    trace_id=f"performance-review:{req.user_id}:{req.period}:{attempt}",
                )
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                name = type(exc).__name__.lower()
                msg = str(exc).lower()
                is_transient = (
                    isinstance(exc, (httpx.TimeoutException, httpx.HTTPError))
                    or "timeout" in name
                    or "timeout" in msg
                    or "rate limit" in msg
                    or "ratelimit" in name
                    or " 429" in msg
                    or " 500" in msg
                    or " 502" in msg
                    or " 503" in msg
                    or " 504" in msg
                )
                logger.warning(
                    "performance_review_llm_attempt_failed",
                    extra={
                        "user_id": req.user_id,
                        "period": req.period,
                        "attempt": attempt + 1,
                        "max_attempts": _LLM_MAX_ATTEMPTS,
                        "transient": is_transient,
                        "error_type": type(exc).__name__,
                    },
                )
                if not is_transient or attempt == _LLM_MAX_ATTEMPTS - 1:
                    break
                await asyncio.sleep(_LLM_BACKOFF_S[attempt])
        if response is None:
            logger.warning(
                "performance_review_llm_failed",
                extra={
                    "user_id": req.user_id,
                    "period": req.period,
                    "error_type": type(last_exc).__name__ if last_exc else "unknown",
                },
            )
            raise PerformanceReviewGenerationError(
                "AI service is temporarily unavailable; please try again"
            )

        parsed = self._parse_response(response.text)
        review = self._shape_review(
            parsed=parsed,
            req=req,
            aggregation=aggregation,
        )
        review["generation_started_at"] = generation_started_at
        return review

    # -- Inbound HTTP (gateway + management) -----------------------------

    async def _fetch_aggregation(self, req: GenerationRequest) -> dict[str, Any]:
        url = f"{self._management_url}/internal/performance-review/aggregate"
        body = {
            "user_id": req.user_id,
            "period": req.period,
            "period_start": req.period_start.isoformat(),
            "period_end": req.period_end.isoformat(),
        }
        try:
            resp = await self._http.post(
                url,
                json=body,
                headers={
                    _INTERNAL_AUTH_HEADER: self._secret,
                    _INTERNAL_USER_ID_HEADER: req.user_id,
                },
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning(
                "performance_review_aggregate_transport_error",
                extra={"user_id": req.user_id, "error": str(exc)},
            )
            raise PerformanceReviewGenerationError(
                "could not load trading history; please try again"
            )
        if resp.status_code != 200:
            logger.warning(
                "performance_review_aggregate_non_200",
                extra={
                    "user_id": req.user_id,
                    "status": resp.status_code,
                    "body_preview": resp.text[:300],
                },
            )
            raise PerformanceReviewGenerationError(
                "could not load trading history; please try again"
            )
        try:
            data = resp.json()
        except Exception:
            raise PerformanceReviewGenerationError(
                "trading history response was not valid JSON"
            )
        if not isinstance(data, dict):
            raise PerformanceReviewGenerationError(
                "trading history response had an unexpected shape"
            )
        return data

    async def _fetch_profile(self, user_id: str) -> dict[str, Any]:
        """Fetch the user's trading-system profile from the gateway's
        internal endpoint. The gateway exposes
        /internal/trading-system/:user_id under the same shared-secret
        HMAC the engine uses for the other /internal/* calls.
        """
        url = f"{self._base_url}/internal/trading-system/{user_id}"
        try:
            resp = await self._http.get(
                url,
                headers={
                    _INTERNAL_AUTH_HEADER: self._secret,
                    _INTERNAL_USER_ID_HEADER: user_id,
                },
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning(
                "performance_review_profile_transport_error",
                extra={"user_id": user_id, "error": str(exc)},
            )
            raise PerformanceReviewGenerationError(
                "could not load your trading system; please try again"
            )
        if resp.status_code == 404:
            raise PerformanceReviewGenerationError(
                "build your trading system before requesting a review"
            )
        if resp.status_code != 200:
            logger.warning(
                "performance_review_profile_non_200",
                extra={
                    "user_id": user_id,
                    "status": resp.status_code,
                    "body_preview": resp.text[:300],
                },
            )
            raise PerformanceReviewGenerationError(
                "could not load your trading system; please try again"
            )
        try:
            data = resp.json()
        except Exception:
            raise PerformanceReviewGenerationError(
                "trading-system response was not valid JSON"
            )
        if not isinstance(data, dict):
            raise PerformanceReviewGenerationError(
                "trading-system response had an unexpected shape"
            )
        # The gateway returns the full record; the LLM only needs
        # the profile sub-document. Tolerate either shape.
        profile = data.get("profile") if "profile" in data else data
        if not isinstance(profile, dict) or not profile:
            raise PerformanceReviewGenerationError(
                "trading-system profile is empty; complete the builder first"
            )
        return profile

    async def _fetch_prior_review(
        self,
        req: GenerationRequest,
    ) -> dict[str, Any] | None:
        """Fetch the most recent ready review strictly before the
        current window. Returns None when no prior review exists;
        the prompt forces trader_evolution.items to be empty in that
        case. Tolerant of 404 / 503 — a missing prior review is not
        a hard failure.
        """
        url = (
            f"{self._base_url}/internal/performance-review/prior"
            f"?user_id={req.user_id}&period={req.period}"
            f"&before={req.period_start.isoformat()}"
        )
        try:
            resp = await self._http.get(
                url,
                headers={
                    _INTERNAL_AUTH_HEADER: self._secret,
                    _INTERNAL_USER_ID_HEADER: req.user_id,
                },
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.info(
                "performance_review_prior_lookup_failed",
                extra={"user_id": req.user_id, "error": str(exc)},
            )
            return None
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            logger.info(
                "performance_review_prior_non_200",
                extra={
                    "user_id": req.user_id,
                    "status": resp.status_code,
                },
            )
            return None
        try:
            data = resp.json()
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        return data.get("review") if "review" in data else None

    # -- Parsing + shaping ----------------------------------------------

    @staticmethod
    def _parse_response(raw: str) -> dict[str, Any]:
        text = (raw or "").strip()
        if not text:
            raise PerformanceReviewGenerationError("AI returned an empty response")
        text = _FENCE_RE.sub("", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise PerformanceReviewGenerationError("AI response was not valid JSON")
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            raise PerformanceReviewGenerationError("AI response was not valid JSON")
        if not isinstance(data, dict):
            raise PerformanceReviewGenerationError("AI response was not a JSON object")
        return data

    @staticmethod
    def _shape_review(
        *,
        parsed: dict[str, Any],
        req: GenerationRequest,
        aggregation: dict[str, Any],
    ) -> dict[str, Any]:
        """Project the LLM payload into the wire shape the gateway
        validator expects.

        Tolerant of small omissions: missing sections are filled with
        empty structures so the gateway validator's mandatory-field
        checks have a chance to fire with field-level errors instead
        of generic decode errors.
        """
        def _dict(name: str) -> dict[str, Any]:
            v = parsed.get(name)
            return v if isinstance(v, dict) else {}

        def _list(value: Any) -> list[Any]:
            return value if isinstance(value, list) else []

        exec_summary = _dict("executive_summary")
        metrics = _dict("performance_metrics")
        behavioral = _dict("behavioral_analysis")
        adherence = _dict("system_adherence")
        emotional = _dict("emotional_intelligence")
        setups = _dict("setup_quality")
        sessions = _dict("session_analysis")
        risk = _dict("risk_analysis")
        improvements = _dict("improvement_recommendations")
        next_focus = _dict("next_focus")
        confidence = _dict("confidence_report")
        evolution = _dict("trader_evolution")
        alignment = _dict("system_alignment")
        warnings = _dict("psychological_warnings")

        # Confidence is stamped by the aggregator and must NOT be
        # changed by the LLM. We overwrite whatever the model emitted
        # with the deterministic band; the validator then checks the
        # written value. This is the single source of truth that
        # prevents fake precision.
        agg_conf = aggregation.get("confidence") if isinstance(aggregation, dict) else None
        if isinstance(agg_conf, dict):
            confidence = {
                "band": str(agg_conf.get("band", "insufficient")),
                "sample_size": int(agg_conf.get("sample_size", 0) or 0),
                "note": str(
                    confidence.get("note")
                    or agg_conf.get("note")
                    or ""
                ),
            }

        review: dict[str, Any] = {
            "executive_summary": {
                "headline": str(exec_summary.get("headline", "")),
                "narrative": str(exec_summary.get("narrative", "")),
            },
            "performance_metrics": {
                "total_trades": str(metrics.get("total_trades", "")),
                "win_rate": str(metrics.get("win_rate", "")),
                "avg_rr": str(metrics.get("avg_rr", "")),
                "net_pnl": str(metrics.get("net_pnl", "")),
                "best_session": str(metrics.get("best_session", "")),
                "worst_session": str(metrics.get("worst_session", "")),
                "most_profitable_setup": str(metrics.get("most_profitable_setup", "")),
                "worst_behavior": str(metrics.get("worst_behavior", "")),
            },
            "behavioral_analysis": {
                "patterns": [str(p) for p in _list(behavioral.get("patterns"))],
            },
            "system_adherence": {
                "items": [
                    {
                        "rule": str(it.get("rule", "")),
                        "compliance": str(it.get("compliance", "")),
                    }
                    for it in _list(adherence.get("items"))
                    if isinstance(it, dict)
                ],
            },
            "emotional_intelligence": {
                "narrative": str(emotional.get("narrative", "")),
            },
            "setup_quality": {
                "items": [
                    {
                        "setup": str(it.get("setup", "")),
                        "win_rate": str(it.get("win_rate", "")),
                        "avg_rr": str(it.get("avg_rr", "")),
                    }
                    for it in _list(setups.get("items"))
                    if isinstance(it, dict)
                ],
            },
            "session_analysis": {
                "items": [
                    {
                        "session": str(it.get("session", "")),
                        "performance": str(it.get("performance", "")),
                    }
                    for it in _list(sessions.get("items"))
                    if isinstance(it, dict)
                ],
            },
            "risk_analysis": {
                "narrative": str(risk.get("narrative", "")),
            },
            "improvement_recommendations": {
                "items": [str(p) for p in _list(improvements.get("items"))],
            },
            "next_focus": {
                "items": [str(p) for p in _list(next_focus.get("items"))],
            },
            "confidence_report": confidence,
            "trader_evolution": {
                "items": [
                    {
                        "metric": str(it.get("metric", "")),
                        "direction": str(it.get("direction", "stable")).lower(),
                        "delta": str(it.get("delta", "")),
                    }
                    for it in _list(evolution.get("items"))
                    if isinstance(it, dict)
                ],
            },
            "system_alignment": {
                "narrative": str(alignment.get("narrative", "")),
                "gaps": [str(g) for g in _list(alignment.get("gaps"))],
            },
            "psychological_warnings": {
                "items": [
                    {
                        "signal": str(it.get("signal", "")),
                        "severity": str(it.get("severity", "info")).lower(),
                        "explanation": str(it.get("explanation", "")),
                    }
                    for it in _list(warnings.get("items"))
                    if isinstance(it, dict)
                ],
            },
            "period": req.period,
            "period_start": req.period_start.isoformat(),
            "period_end": req.period_end.isoformat(),
            "generated_by": "Exoper AI",
            "profile_version": int(req.profile_version),
        }
        return review

    # -- Gateway HTTP (callback / fail) ---------------------------------

    async def _post_callback(
        self,
        req: GenerationRequest,
        review: dict[str, Any],
    ) -> None:
        url = f"{self._base_url}/internal/performance-review/callback"
        headers = {
            _INTERNAL_AUTH_HEADER: self._secret,
            _INTERNAL_USER_ID_HEADER: req.user_id,
        }
        last_status: Optional[int] = None
        last_body_preview: str = ""
        for attempt in range(_CALLBACK_MAX_ATTEMPTS):
            try:
                resp = await self._http.post(
                    url,
                    json={"user_id": req.user_id, "review": review},
                    headers=headers,
                )
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                logger.warning(
                    "performance_review_callback_transport_error",
                    extra={
                        "user_id": req.user_id,
                        "period": req.period,
                        "attempt": attempt + 1,
                        "error": str(exc),
                    },
                )
                if attempt < _CALLBACK_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_CALLBACK_BACKOFF_S[attempt])
                    continue
                await self._post_fail(
                    req,
                    "could not deliver review to the gateway; please regenerate",
                )
                return
            last_status = resp.status_code
            last_body_preview = resp.text[:300]
            if resp.status_code == 200:
                logger.info(
                    "performance_review_callback_persisted",
                    extra={
                        "user_id": req.user_id,
                        "period": req.period,
                        "attempt": attempt + 1,
                    },
                )
                return
            if resp.status_code == 422:
                logger.error(
                    "performance_review_callback_rejected_validation",
                    extra={
                        "user_id": req.user_id,
                        "period": req.period,
                        "body_preview": last_body_preview,
                    },
                )
                await self._post_fail(
                    req,
                    "AI produced an invalid review structure; please regenerate",
                )
                return
            if 500 <= resp.status_code < 600:
                logger.warning(
                    "performance_review_callback_5xx",
                    extra={
                        "user_id": req.user_id,
                        "period": req.period,
                        "attempt": attempt + 1,
                        "status": resp.status_code,
                    },
                )
                if attempt < _CALLBACK_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_CALLBACK_BACKOFF_S[attempt])
                    continue
                await self._post_fail(
                    req,
                    "gateway is temporarily unavailable; please regenerate",
                )
                return
            logger.error(
                "performance_review_callback_rejected_unexpected",
                extra={
                    "user_id": req.user_id,
                    "period": req.period,
                    "status": resp.status_code,
                    "body_preview": last_body_preview,
                },
            )
            await self._post_fail(
                req,
                "review delivery rejected; please contact support",
            )
            return
        logger.error(
            "performance_review_callback_loop_exited_unexpectedly",
            extra={
                "user_id": req.user_id,
                "period": req.period,
                "last_status": last_status,
                "last_body_preview": last_body_preview,
            },
        )
        await self._post_fail(req, "review delivery failed; please regenerate")

    async def _post_fail(self, req: GenerationRequest, message: str) -> None:
        url = f"{self._base_url}/internal/performance-review/fail"
        try:
            await self._http.post(
                url,
                json={
                    "user_id": req.user_id,
                    "period": req.period,
                    "period_start": req.period_start.isoformat(),
                    "message": message,
                },
                headers={
                    _INTERNAL_AUTH_HEADER: self._secret,
                    _INTERNAL_USER_ID_HEADER: req.user_id,
                },
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.error(
                "performance_review_fail_post_failed",
                extra={
                    "user_id": req.user_id,
                    "period": req.period,
                    "error": str(exc),
                },
            )
