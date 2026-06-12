"""LLM call + gateway callback for Trading Plan generation.

Flow:

  1. Build the prompt from the saved Trading System profile and the
     account balance the gateway resolved (broker or fallback).
  2. Resolve the user's LLM client via the container's tier-aware
     background loader. The loader returns:
       - the user's PERSONAL key when they have one configured, OR
       - the PLATFORM key (DB row first, env-var fallback) when the
         user has no personal key.
     For trading-plan every user is eligible for the platform key,
     so brand-new users can still generate a plan during onboarding.
  3. Parse the JSON response. Reject anything that does not match
     the six-section shape PRACTICE.md specifies.
  4. POST the parsed plan to the gateway's internal callback. On
     any failure, POST to /internal/trading-plan/fail so the gateway
     row flips to status='failed' and the SPA can show a retry CTA.

The generator is fully self-contained: it does not own its HTTP
client or LLM client, so unit tests can swap both with fakes.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC
from typing import Any

import httpx

from engine.processor.llm.error_classifier import (
    classify_llm_failure,
    is_transient_llm_error,
)
from engine.processor.trading_plan.prompt import (
    JOURNAL_SEED_ROWS,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from engine.shared import metering_client as metering
from engine.shared.exceptions import QuotaExceededError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

_INTERNAL_AUTH_HEADER = "X-Internal-Auth"
_INTERNAL_USER_ID_HEADER = "X-User-Id"

# Per-attempt timeout. The callback path is gateway-internal traffic
# (Redis-adjacent infra, sub-millisecond RTT in steady state) so 10s
# is generous headroom for warm-up jitter without dragging the user's
# end-to-end wait if the gateway is genuinely down.
_CALLBACK_TIMEOUT_S = 10.0

# Retry policy for the gateway callback. Exponential backoff caps
# the total wait at ~3.5s across three attempts; after that we
# escalate to _post_fail so the row flips to 'failed' instead of
# being stranded in 'generating'.
_CALLBACK_MAX_ATTEMPTS = 3
_CALLBACK_BACKOFF_S = (0.5, 1.0, 2.0)

# Retry policy for the LLM call inside _generate. We retry on
# transient httpx transport errors and httpx.HTTPStatusError when
# the provider returned a 5xx. Non-transient errors (auth, bad
# request) fail fast.
_LLM_MAX_ATTEMPTS = 3
_LLM_BACKOFF_S = (1.0, 2.0)

# Regex used to strip a stray JSON fence the model occasionally
# wraps the response in (despite the prompt's instruction). We do
# NOT use it to extract a sub-object; we use it only to remove the
# fence delimiters and trim the surrounding whitespace.
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class TradingPlanGenerationError(Exception):
    """Raised when the LLM call or response parsing fails.

    The Message attribute is user-safe: stack traces, internal IDs,
    and provider-specific error envelopes are never propagated.
    """

    def __init__(self, user_safe_message: str) -> None:
        super().__init__(user_safe_message)
        self.user_safe_message = user_safe_message


@dataclass(frozen=True)
class GenerationRequest:
    """Engine-side mirror of src/tradingplan/models.go::GenerationRequest.

    role and tier are forwarded by the gateway on the dispatch body so
    the engine can honor the platform-key fallback policy without an
    independent identity lookup. The router applies conservative
    defaults ('etradie' / 'free') when the gateway omits them on a
    deploy-skew window, which keeps BYOK behaviour for any caller
    that did not yet update.
    """

    user_id: str
    balance: float
    balance_currency: str
    balance_source: str  # 'broker' | 'fallback'
    profile_version: int
    profile: dict[str, Any]
    role: str = "etradie"
    tier: str = "free"


class TradingPlanGenerator:
    """Stateless service wrapping a single LLM call + gateway callback.

    The Container builds ONE instance and reuses it. The LLM client
    is resolved per request via load_llm_client_for_background, so a
    user with a personal key uses their own key and a user without
    one falls back to the platform key (PLAN rule #3).
    """

    def __init__(
        self,
        *,
        container: Any,
        http_client: httpx.AsyncClient,
        gateway_base_url: str,
        internal_secret: str,
    ) -> None:
        self._container = container
        self._http = http_client
        self._base_url = gateway_base_url.rstrip("/")
        self._secret = internal_secret

    @classmethod
    def from_container(cls, container: Any) -> TradingPlanGenerator | None:
        """Build a generator using the Container's wired LLM and HTTP
        clients. Returns None when the gateway URL or shared secret
        is missing (local dev / tests); callers MUST handle the None
        case by responding 503 to the dispatch request.
        """
        base_url = (os.environ.get("ENGINE_GATEWAY_URL") or os.environ.get("GATEWAY_HTTP_URL") or "").strip()
        secret = (
            os.environ.get("ENGINE_INTERNAL_SHARED_SECRET")
            or os.environ.get("GATEWAY_ENGINE_INTERNAL_SHARED_SECRET")
            or ""
        ).strip()
        if not base_url or not secret:
            logger.info(
                "trading_plan_generator_disabled",
                extra={
                    "base_url_set": bool(base_url),
                    "secret_set": bool(secret),
                },
            )
            return None
        # httpx.AsyncClient is owned by the Container.http_client wrapper.
        # We need a raw AsyncClient to call the gateway directly with
        # internal headers, so we lazily build a dedicated one here.
        # It is closed in shutdown via aclose() below.
        client = httpx.AsyncClient(
            timeout=_CALLBACK_TIMEOUT_S,
            headers={"Content-Type": "application/json"},
        )
        return cls(
            container=container,
            http_client=client,
            gateway_base_url=base_url,
            internal_secret=secret,
        )

    async def aclose(self) -> None:
        """Close the dedicated callback HTTP client. Safe to re-call."""
        with contextlib.suppress(Exception):
            await self._http.aclose()

    # -- Public entry point -------------------------------------------------

    async def run(self, req: GenerationRequest) -> None:
        """Generate a plan for `req` and post it back to the gateway.

        Never raises: every failure path culminates in a fail callback
        that flips the gateway row to status='failed' with a user-safe
        message the SPA can render.
        """
        try:
            plan = await self._generate(req)
        except TradingPlanGenerationError as exc:
            logger.warning(
                "trading_plan_generation_failed",
                extra={
                    "user_id": req.user_id,
                    "reason": exc.user_safe_message,
                },
            )
            await self._post_fail(req.user_id, exc.user_safe_message)
            return
        except Exception as exc:
            logger.exception(
                "trading_plan_generation_unexpected_error",
                extra={"user_id": req.user_id, "error_type": type(exc).__name__},
            )
            await self._post_fail(
                req.user_id,
                "plan generation failed unexpectedly; please try again",
            )
            return

        await self._post_callback(req.user_id, plan)

    # -- Internals -----------------------------------------------------------

    async def _generate(self, req: GenerationRequest) -> dict[str, Any]:
        if not req.user_id:
            raise TradingPlanGenerationError("missing user_id")
        if not isinstance(req.profile, dict) or not req.profile:
            raise TradingPlanGenerationError("trading system profile is missing")

        # Stamp the LLM-call start time so the gateway can record
        # TradingPlanLLMCallDuration accurately on the callback. The
        # gateway falls back to skipping the metric if this field is
        # missing, so deploys mid-flight stay backward-compatible.
        from datetime import datetime

        generation_started_at = datetime.now(UTC).isoformat()

        user_prompt = build_user_prompt(
            profile=req.profile,
            balance=req.balance,
            balance_currency=req.balance_currency,
            balance_source=req.balance_source,
        )

        # Resolve the LLM client via the tier-aware background loader.
        # Trading-plan policy (rule #3 in PRACTICE.md): every user can
        # use the platform key when they have no personal key, so we
        # pass allow_platform_fallback=True. The loader still reads
        # the platform DB row first (hot-reloadable via the dashboard)
        # and falls back to env-var config only when no DB row exists.
        llm_client, dynamic_config = await self._container.load_llm_client_for_background(
            req.user_id,
            role=req.role,
            tier=req.tier,
            allow_platform_fallback=True,
        )
        if llm_client is None or dynamic_config is None:
            # In practice this should not happen for trading-plan
            # because allow_platform_fallback=True grants every user
            # the platform key. We still handle it as a clean failure
            # so a misconfigured deploy (no platform row, no env
            # platform key) surfaces a real message instead of
            # NoneType-attribute crashes downstream.
            raise TradingPlanGenerationError("AI service is not configured on the platform; please contact support.")

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
            trace_id_metering = f"trading-plan:{req.user_id}"
            try:
                reservation_id = await metering.reserve(
                    user_id=req.user_id,
                    provider=str(llm_client.PROVIDER),
                    model=model_name,
                    estimated_input_tokens=estimated_input,
                    max_output_tokens=max_output_tokens,
                    trace_id=trace_id_metering,
                )
            except QuotaExceededError as exc:
                logger.info(
                    "trading_plan_quota_exceeded",
                    extra={
                        "user_id": req.user_id,
                        "dimension": exc.dimension,
                        "limit": exc.limit,
                        "used": exc.used,
                        "retry_after": exc.retry_after,
                    },
                )
                raise TradingPlanGenerationError(
                    f"LLM quota reached for your tier ({exc.dimension}); resets in {exc.retry_after} seconds"
                )

            # Bounded retry loop for the LLM call. Transient transport
            # errors and provider 5xx responses get one or two retries
            # with exponential backoff; non-transient errors (auth, bad
            # request, malformed prompt) raise on the first attempt so
            # we do not waste time or tokens. Every error path refunds
            # the held reservation before re-raising so dangling
            # reservations are never left for the janitor.
            response = None
            last_exc: Exception | None = None
            for attempt in range(_LLM_MAX_ATTEMPTS):
                try:
                    # use_structured_output=False is required here.
                    # The Trading Plan response schema is defined by
                    # SYSTEM_PROMPT (trader_profile / account / journal /
                    # weekly_review / scorecard / objectives) and
                    # validated against the gateway's tradingplan.Plan
                    # Go struct on callback. The shared LLM client
                    # defaults to enforcing AnalysisOutput's schema
                    # (the analysis processor's wire shape); leaving
                    # the default in place would force the provider's
                    # API grammar to coerce every plan response into
                    # an AnalysisOutput object, after which
                    # _shape_plan()._require_dict("trader_profile")
                    # would always fail with "AI response is missing
                    # the 'trader_profile' section".
                    response = await llm_client.call(
                        system_prompt=SYSTEM_PROMPT,
                        user_message=user_prompt,
                        trace_id=f"trading-plan:{req.user_id}:{attempt}",
                        use_structured_output=False,
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                transient = is_transient_llm_error(last_exc)
                logger.warning(
                    "trading_plan_llm_call_attempt_failed",
                    extra={
                        "user_id": req.user_id,
                        "attempt": attempt + 1,
                        "max_attempts": _LLM_MAX_ATTEMPTS,
                        "transient": transient,
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
                    "trading_plan_llm_call_failed",
                    extra={
                        "user_id": req.user_id,
                        "error": str(last_exc) if last_exc else "unknown",
                        "error_type": (type(last_exc).__name__ if last_exc else "unknown"),
                        "failure_code": failure.code,
                    },
                )
                raise TradingPlanGenerationError(failure.user_message)

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
            plan = self._shape_plan(
                parsed=parsed,
                balance=req.balance,
                balance_currency=req.balance_currency,
                balance_source=req.balance_source,
                profile_version=req.profile_version,
            )
            plan["generation_started_at"] = generation_started_at
            return plan
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

    @staticmethod
    def _parse_response(raw: str) -> dict[str, Any]:
        """Decode the LLM response into a dict.

        Tolerates a stray ```json fence wrapper. Rejects anything
        that is not a single JSON object.
        """
        text = (raw or "").strip()
        if not text:
            raise TradingPlanGenerationError("AI returned an empty response")
        text = _FENCE_RE.sub("", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise TradingPlanGenerationError("AI response was not valid JSON")
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            raise TradingPlanGenerationError("AI response was not valid JSON")
        if not isinstance(data, dict):
            raise TradingPlanGenerationError("AI response was not a JSON object")
        return data

    @staticmethod
    def _shape_plan(
        *,
        parsed: dict[str, Any],
        balance: float,
        balance_currency: str,
        balance_source: str,
        profile_version: int,
    ) -> dict[str, Any]:
        """Project the LLM payload into the wire shape the gateway
        validator expects. Tolerant of small omissions: missing
        sections are filled with the safe default; structural
        mismatches raise so the engine can mark the row 'failed'.
        """

        def _require_dict(name: str) -> dict[str, Any]:
            v = parsed.get(name)
            if not isinstance(v, dict):
                raise TradingPlanGenerationError(f"AI response is missing the '{name}' section")
            return v

        def _require_list(value: Any, name: str) -> list[Any]:
            if not isinstance(value, list):
                raise TradingPlanGenerationError(f"AI response section '{name}' is malformed")
            return value

        trader = _require_dict("trader_profile")
        account = _require_dict("account")
        weekly = _require_dict("weekly_review")
        scorecard = _require_dict("scorecard")
        objectives = _require_dict("objectives")

        bullets = _require_list(trader.get("bullets", []), "trader_profile.bullets")
        prompts = _require_list(weekly.get("prompts", []), "weekly_review.prompts")
        score_items = _require_list(scorecard.get("items", []), "scorecard.items")
        obj_items = _require_list(objectives.get("items", []), "objectives.items")

        raw_journal = parsed.get("journal", [])
        if not isinstance(raw_journal, list):
            raise TradingPlanGenerationError("AI response section 'journal' is malformed")

        def _journal_row(src: Any) -> dict[str, str]:
            if not isinstance(src, dict):
                src = {}
            # The 25 columns mirror src/tradingplan/models.go::JournalRow
            # field-for-field. Every cell defaults to an empty string
            # so a sparse LLM response still produces a structurally
            # valid row the gateway validator accepts.
            return {
                "date": str(src.get("date", "")),
                "session": str(src.get("session", "")),
                "pair": str(src.get("pair", "")),
                "direction": str(src.get("direction", "")),
                "style": str(src.get("style", "")),
                "setup_type": str(src.get("setup_type", "")),
                "htf_bias": str(src.get("htf_bias", "")),
                "entry": str(src.get("entry", "")),
                "stop_loss": str(src.get("stop_loss", "")),
                "take_profit": str(src.get("take_profit", "")),
                "risk_percent": str(src.get("risk_percent", "")),
                "position_size": str(src.get("position_size", "")),
                "exit": str(src.get("exit", "")),
                "rr_planned": str(src.get("rr_planned", "")),
                "rr_achieved": str(src.get("rr_achieved", "")),
                "pnl": str(src.get("pnl", "")),
                "outcome": str(src.get("outcome", "")),
                "rule_followed": str(src.get("rule_followed", "")),
                "emotion_before_trade": str(src.get("emotion_before_trade", "")),
                "emotion_after_trade": str(src.get("emotion_after_trade", "")),
                "trade_quality": str(src.get("trade_quality", "")),
                "mistake_category": str(src.get("mistake_category", "")),
                "news_present": str(src.get("news_present", "")),
                "screenshot_link": str(src.get("screenshot_link", "")),
                "notes": str(src.get("notes", "")),
            }

        journal: list[dict[str, str]] = [_journal_row(r) for r in raw_journal[:JOURNAL_SEED_ROWS]]
        while len(journal) < JOURNAL_SEED_ROWS:
            journal.append(_journal_row({}))

        scorecard_items: list[dict[str, str]] = []
        for it in score_items:
            if not isinstance(it, dict):
                continue
            metric = str(it.get("metric", "")).strip()
            if not metric:
                continue
            scorecard_items.append(
                {
                    "metric": metric,
                    "score": str(it.get("score", "")),
                }
            )

        plan: dict[str, Any] = {
            "trader_profile": {
                "headline": str(trader.get("headline", "")).strip(),
                "bullets": [str(b).strip() for b in bullets if str(b).strip()],
            },
            "account": {
                "starting_balance": str(account.get("starting_balance", "")),
                "max_daily_risk": str(account.get("max_daily_risk", "")),
                "max_weekly_drawdown": str(account.get("max_weekly_drawdown", "")),
                "preferred_rr": str(account.get("preferred_rr", "")),
                "max_trades_per_day": str(account.get("max_trades_per_day", "")),
                "trading_days_per_week": str(account.get("trading_days_per_week", "")),
            },
            "journal": journal,
            "weekly_review": {
                "prompts": [str(p).strip() for p in prompts if str(p).strip()],
            },
            "scorecard": {
                "items": scorecard_items,
            },
            "objectives": {
                "items": [str(o).strip() for o in obj_items if str(o).strip()],
            },
            "profile_summary": str(parsed.get("profile_summary", "")).strip(),
            "profile_version": int(profile_version),
            "balance_used": float(balance),
            "balance_currency": balance_currency or "USD",
            "balance_source_kind": balance_source or "fallback",
            "generated_by": "Exoper AI",
            # generated_at is set by the gateway store on Save().
        }
        return plan

    # -- Gateway HTTP --------------------------------------------------------

    async def _post_callback(self, user_id: str, plan: dict[str, Any]) -> None:
        """POST the generated plan to the gateway callback with bounded retries.

        Retry policy:
          * Transport errors (timeout, network) — retry up to
            _CALLBACK_MAX_ATTEMPTS with exponential backoff.
          * 5xx responses — retried under the same policy.
          * 4xx responses other than 422 — fail fast and mark
            the gateway row failed (these indicate a contract bug).
          * 422 response — fail fast and mark failed (the gateway's
            validator rejected the LLM payload; a retry will not fix
            it).
          * 200 — success.

        If every retry exhausts we call _post_fail so the gateway
        row transitions out of 'generating' and the SPA's polling
        terminates.
        """
        url = f"{self._base_url}/internal/trading-plan/callback"
        headers = {
            _INTERNAL_AUTH_HEADER: self._secret,
            _INTERNAL_USER_ID_HEADER: user_id,
        }

        last_status: int | None = None
        last_body_preview: str = ""
        for attempt in range(_CALLBACK_MAX_ATTEMPTS):
            try:
                resp = await self._http.post(
                    url,
                    json={"user_id": user_id, "plan": plan},
                    headers=headers,
                )
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                logger.warning(
                    "trading_plan_callback_attempt_failed_transport",
                    extra={
                        "user_id": user_id,
                        "attempt": attempt + 1,
                        "max_attempts": _CALLBACK_MAX_ATTEMPTS,
                        "error": str(exc),
                    },
                )
                if attempt < _CALLBACK_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_CALLBACK_BACKOFF_S[attempt])
                    continue
                # Exhausted retries on transport errors. The gateway
                # row is still 'generating'; escalate to _post_fail.
                await self._post_fail(
                    user_id,
                    "could not deliver plan to the gateway; please regenerate",
                )
                return

            last_status = resp.status_code
            last_body_preview = resp.text[:300]

            if resp.status_code == 200:
                logger.info(
                    "trading_plan_callback_persisted",
                    extra={"user_id": user_id, "attempt": attempt + 1},
                )
                return

            # 422 — validator rejection; retry will not fix it.
            if resp.status_code == 422:
                logger.error(
                    "trading_plan_callback_rejected_validation",
                    extra={
                        "user_id": user_id,
                        "body_preview": last_body_preview,
                    },
                )
                await self._post_fail(
                    user_id,
                    "AI produced an invalid plan structure; please regenerate",
                )
                return

            # 5xx — transient on the gateway side, retry.
            if 500 <= resp.status_code < 600:
                logger.warning(
                    "trading_plan_callback_attempt_failed_5xx",
                    extra={
                        "user_id": user_id,
                        "attempt": attempt + 1,
                        "max_attempts": _CALLBACK_MAX_ATTEMPTS,
                        "status": resp.status_code,
                        "body_preview": last_body_preview,
                    },
                )
                if attempt < _CALLBACK_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_CALLBACK_BACKOFF_S[attempt])
                    continue
                # Exhausted retries on 5xx.
                await self._post_fail(
                    user_id,
                    "gateway is temporarily unavailable; please regenerate",
                )
                return

            # Other 4xx — contract bug; do not retry, escalate.
            logger.error(
                "trading_plan_callback_rejected_unexpected",
                extra={
                    "user_id": user_id,
                    "status": resp.status_code,
                    "body_preview": last_body_preview,
                },
            )
            await self._post_fail(
                user_id,
                "plan delivery rejected; please contact support",
            )
            return

        # Should be unreachable (loop above always returns), but the
        # belt-and-braces escalation guards against a future refactor.
        logger.error(
            "trading_plan_callback_loop_exited_unexpectedly",
            extra={
                "user_id": user_id,
                "last_status": last_status,
                "last_body_preview": last_body_preview,
            },
        )
        await self._post_fail(
            user_id,
            "plan delivery failed; please regenerate",
        )

    async def _post_fail(self, user_id: str, message: str) -> None:
        url = f"{self._base_url}/internal/trading-plan/fail"
        try:
            await self._http.post(
                url,
                json={"user_id": user_id, "message": message},
                headers={
                    _INTERNAL_AUTH_HEADER: self._secret,
                    _INTERNAL_USER_ID_HEADER: user_id,
                },
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.error(
                "trading_plan_fail_post_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )
