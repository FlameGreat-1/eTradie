"""LLM call + gateway callback for the Performance Review feature.

Flow:

  1. GET gateway /internal/performance-review/aggregate
     -> deterministic per-window bundle (read from journal in place).
  2. GET gateway /internal/trading-system/:user_id
     -> user's defined operating framework.
  3. GET gateway /internal/performance-review/prior?period=&before=
     -> the prior ready row's review JSON (optional; used for
        trader-evolution deltas per PLAN.md section 12).
  4. Resolve the user's LLM client via the container's tier-aware
     background loader. The loader returns the user's PERSONAL key
     when one is configured, OR the PLATFORM key only for admin /
     pro_managed users (PLAN rules #2 and #4). Free and pro_byok
     users without a personal key are rejected with a 'configure
     your key' message.
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

from engine.processor.llm.error_classifier import (
    classify_llm_failure,
    is_transient_llm_error,
)
from engine.processor.performance_review.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from engine.shared import metering_client as metering
from engine.shared.exceptions import QuotaExceededError
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
    """Engine-side mirror of src/performancereview/models.go::GenerationRequest.

    role and tier are forwarded by the gateway on the dispatch body
    (HTTP path) or supplied by the cron scheduler from the gateway's
    active-users response (cron path). The generator uses them to
    apply the BYOK-or-managed gate without an independent identity
    lookup. Conservative defaults ('etradie' / 'free') preserve the
    BYOK-only posture for any caller that omits them.
    """

    user_id: str
    period: str               # 'weekly' | 'monthly'
    period_start: datetime    # inclusive
    period_end: datetime      # inclusive
    profile_version: int
    role: str = "etradie"
    tier: str = "free"


class PerformanceReviewGenerator:
    """Stateless service wrapping one full review-generation cycle.

    The Container builds ONE instance and reuses it. The LLM client
    is resolved per request via load_llm_client_for_background under
    the BYOK-or-managed policy: personal key when set, platform key
    only for admin / pro_managed, otherwise a tier-aware rejection.
    """

    def __init__(
        self,
        *,
        container: Any,
        http_client: httpx.AsyncClient,
        gateway_base_url: str,
        management_base_url: str,
        internal_secret: str,
    ) -> None:
        self._container = container
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
            container=container,
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

        # Step 2: trading-system profile + authoritative version (from gateway).
        # The version returned here is the single source of truth and
        # overrides the dispatch payload (which may be 0 on the cron
        # path because the scheduler does not enumerate per-user
        # versions before fanning out).
        profile, profile_version = await self._fetch_profile(req.user_id)
        effective_version = profile_version if profile_version > 0 else req.profile_version

        # Step 3: optional prior review (from gateway).
        prior_review = await self._fetch_prior_review(req)

        user_prompt = build_user_prompt(
            user_id=req.user_id,
            period=req.period,
            period_start=req.period_start.isoformat(),
            period_end=req.period_end.isoformat(),
            profile=profile,
            profile_version=effective_version,
            aggregation=aggregation,
            prior_review=prior_review,
        )

        # Performance-review policy:
        #   - Personal LLM key, if the user has one  -> use it.
        #   - Admin or pro_managed with no personal key -> platform key.
        #   - Everyone else with no personal key     -> hard reject
        #     with a 'configure your key' CTA. This preserves the
        #     BYOK requirement for free / pro_byok users (rule #2 in
        #     PRACTICE.md) while letting admins and managed users run
        #     reviews on the platform key (rule #4).
        dynamic_client, dynamic_config = await self._container.load_llm_client_for_background(
            req.user_id,
            role=req.role,
            tier=req.tier,
            allow_platform_fallback=True,
        )
        if dynamic_client is None or dynamic_config is None:
            raise PerformanceReviewGenerationError(
                "You must configure your own LLM API Key in Settings to generate Performance Reviews."
            )

        model_name = dynamic_config.model_name
        max_output_tokens = max(1, dynamic_config.max_output_tokens)

        try:
            # Metering reserve (Pro Managed / admin only). Identical
            # contract to the analysis path: estimated_input is a
            # conservative byte-length / 4 approximation, the commit()
            # call below corrects to the real token counts.
            #
            # If metering is disabled (METERING_ENABLED=false or no
            # gateway URL configured) reserve() returns '' and the call
            # proceeds without any quota check.
            estimated_input = max(0, len(user_prompt.encode("utf-8")) // 4)
            trace_id_metering = f"performance-review:{req.user_id}:{req.period}"
            try:
                reservation_id = await metering.reserve(
                    user_id=req.user_id,
                    provider=str(dynamic_client.PROVIDER),
                    model=model_name,
                    estimated_input_tokens=estimated_input,
                    max_output_tokens=max_output_tokens,
                    trace_id=trace_id_metering,
                )
            except QuotaExceededError as exc:
                logger.info(
                    "performance_review_quota_exceeded",
                    extra={
                        "user_id": req.user_id,
                        "period": req.period,
                        "dimension": exc.dimension,
                        "limit": exc.limit,
                        "used": exc.used,
                        "retry_after": exc.retry_after,
                    },
                )
                raise PerformanceReviewGenerationError(
                    f"LLM quota reached for your tier ({exc.dimension}); "
                    f"resets in {exc.retry_after} seconds"
                )
    
            # Bounded retry loop for the LLM call. Shared transient
            # classifier with trading_plan so the heuristic stays in
            # one place. Every error path either retries (keeping the
            # reservation alive) or refunds and re-raises so the held
            # debit is released within its TTL.
            response = None
            last_exc: Optional[Exception] = None
            for attempt in range(_LLM_MAX_ATTEMPTS):
                try:
                    response = await dynamic_client.call(
                        system_prompt=SYSTEM_PROMPT,
                        user_message=user_prompt,
                        trace_id=f"performance-review:{req.user_id}:{req.period}:{attempt}",
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                transient = is_transient_llm_error(last_exc)
                logger.warning(
                    "performance_review_llm_attempt_failed",
                    extra={
                        "user_id": req.user_id,
                        "period": req.period,
                        "attempt": attempt + 1,
                        "max_attempts": _LLM_MAX_ATTEMPTS,
                        "transient": transient,
                        # Include the raw exception text so an operator
                        # grepping for "performance_review_llm" sees
                        # exactly what the provider returned, not just
                        # the Python class name. Symmetric with the
                        # trading-plan generator's logging.
                        "error": str(last_exc),
                        "error_type": type(last_exc).__name__,
                    },
                )
                if not transient or attempt == _LLM_MAX_ATTEMPTS - 1:
                    break
                await asyncio.sleep(_LLM_BACKOFF_S[attempt])
            if response is None:
                # Every attempt failed. Refund the provisional debit so the
                # user's quota is not permanently consumed for a call that
                # never completed. Best-effort: the janitor reaps the
                # reservation after its TTL if the refund itself fails.
                await metering.refund(reservation_id=reservation_id)
                failure = classify_llm_failure(last_exc)
                logger.warning(
                    "performance_review_llm_failed",
                    extra={
                        "user_id": req.user_id,
                        "period": req.period,
                        # Raw exception text on the final failure too:
                        # this is the single line we will reach for
                        # when a user reports the unknown-bucket
                        # message and we need to diagnose. Symmetric
                        # with trading_plan_llm_call_failed.
                        "error": str(last_exc) if last_exc else "unknown",
                        "error_type": type(last_exc).__name__ if last_exc else "unknown",
                        "failure_code": failure.code,
                    },
                )
                raise PerformanceReviewGenerationError(failure.user_message)

            # Commit the real token counts. The over-reservation on the
            # output side (max_output - actual_output) is returned to the
            # user's quota. Commit is best-effort; a transient failure does
            # not roll back the completed LLM call.
            await metering.commit(
                reservation_id=reservation_id,
                actual_input_tokens=response.input_tokens,
                actual_output_tokens=response.output_tokens,
            )
    
            parsed = self._parse_response(response.text)
            review = self._shape_review(
                parsed=parsed,
                req=req,
                aggregation=aggregation,
                profile_version=effective_version,
            )
            review["generation_started_at"] = generation_started_at
            return review
        finally:
            # Lifecycle note: the LLM client is owned by
            # Container._user_background_llm (the per-user cache on
            # the container). We DO NOT close it here — closing
            # would tear down a connection pool that other in-flight
            # or subsequent requests for the same user need to reuse,
            # which is the entire point of the cache. The cache
            # invalidates and closes the client when the user mutates
            # their LLM connection (every route in llm_connections.py
            # calls invalidate_user_background_llm()), when the
            # platform key rotates (invalidate_all_background_llm()),
            # or when the process exits (Container.shutdown()).
            pass

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

    async def _fetch_profile(self, user_id: str) -> tuple[dict[str, Any], int]:
        """Fetch the user's trading-system profile from the gateway's
        internal endpoint.

        Wire contract (matches src/tradingsystem/handlers.go::handleInternalGet):

          Request:
            POST {gateway}/internal/trading-system/get
            Headers:
              X-Internal-Auth: <shared secret>
              X-User-Id:       <user_id>     (also in body, body wins)
            Body:
              {"user_id": "<user_id>"}

          Response (200, JSON):
            {
              "user_id":     "...",
              "status":      "none" | "skipped" | "active",
              "version":     <int>,
              "profile":     {...}  | null,
              "has_profile": <bool>,
              "updated_at":  "<RFC3339>"
            }

        Returns the (profile, version) tuple. Raises a user-safe error
        when the profile is missing or the trading system is not yet
        active so the gateway can surface the right CTA to the SPA.
        """
        url = f"{self._base_url}/internal/trading-system/get"
        body = {"user_id": user_id}
        try:
            resp = await self._http.post(
                url,
                json=body,
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

        # The gateway returns status='none' with profile=null when the
        # user has never built (or has reset) their trading system.
        # That is a precondition failure, not a transport error.
        status = str(data.get("status") or "").lower()
        profile = data.get("profile")
        if status != "active" or not isinstance(profile, dict) or not profile:
            raise PerformanceReviewGenerationError(
                "build your trading system before requesting a review"
            )

        # The version is authoritative: the cron dispatch path passes 0
        # because it does not enumerate per-user versions. Reading the
        # value here lets the review audit trail correlate to the
        # exact framework version the LLM observed.
        try:
            version = int(data.get("version") or 0)
        except (TypeError, ValueError):
            version = 0
        return profile, version

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
        profile_version: int,
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
            "profile_version": int(profile_version),
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
