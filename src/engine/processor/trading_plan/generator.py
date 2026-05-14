"""LLM call + gateway callback for Trading Plan generation.

Flow:

  1. Build the prompt from the saved Trading System profile and the
     account balance the gateway resolved (broker or fallback).
  2. Call the PLATFORM LLM client (NOT the user's BYOK client). The
     trading plan is always generated with the platform key because
     most users are still onboarding when this fires.
  3. Parse the JSON response. Reject anything that does not match
     the six-section shape PRACTICE.md specifies.
  4. POST the parsed plan to the gateway's internal callback. On
     any failure, POST to /internal/trading-plan/fail so the gateway
     row flips to status='failed' and the SPA can show a retry CTA.

The generator is fully self-contained: it does not own its HTTP
client or LLM client, so unit tests can swap both with fakes.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from engine.processor.llm.client import LLMClient
from engine.processor.trading_plan.prompt import (
    JOURNAL_SEED_ROWS,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from engine.shared.logging import get_logger

logger = get_logger(__name__)

_INTERNAL_AUTH_HEADER = "X-Internal-Auth"
_INTERNAL_USER_ID_HEADER = "X-User-Id"
_CALLBACK_TIMEOUT_S = 5.0

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
    """Engine-side mirror of src/tradingplan/models.go::GenerationRequest."""

    user_id: str
    balance: float
    balance_currency: str
    balance_source: str  # 'broker' | 'fallback'
    profile_version: int
    profile: dict[str, Any]


class TradingPlanGenerator:
    """Stateless service wrapping a single LLM call + gateway callback.

    The Container builds ONE instance and reuses it. The LLM client
    is the platform's (Container.processor_llm_client), guaranteeing
    the call uses the platform key even when the requesting user is
    BYOK.
    """

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        http_client: httpx.AsyncClient,
        gateway_base_url: str,
        internal_secret: str,
    ) -> None:
        self._llm = llm_client
        self._http = http_client
        self._base_url = gateway_base_url.rstrip("/")
        self._secret = internal_secret

    @classmethod
    def from_container(cls, container: Any) -> Optional["TradingPlanGenerator"]:
        """Build a generator using the Container's wired LLM and HTTP
        clients. Returns None when the gateway URL or shared secret
        is missing (local dev / tests); callers MUST handle the None
        case by responding 503 to the dispatch request.
        """
        base_url = (
            os.environ.get("ENGINE_GATEWAY_URL")
            or os.environ.get("GATEWAY_HTTP_URL")
            or ""
        ).strip()
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
            llm_client=container.processor_llm_client,
            http_client=client,
            gateway_base_url=base_url,
            internal_secret=secret,
        )

    async def aclose(self) -> None:
        """Close the dedicated callback HTTP client. Safe to re-call."""
        try:
            await self._http.aclose()
        except Exception:
            pass

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
            raise TradingPlanGenerationError(
                "trading system profile is missing"
            )

        user_prompt = build_user_prompt(
            profile=req.profile,
            balance=req.balance,
            balance_currency=req.balance_currency,
            balance_source=req.balance_source,
        )

        try:
            response = await self._llm.call(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_prompt,
                trace_id=f"trading-plan:{req.user_id}",
            )
        except Exception as exc:
            # LLM provider error envelopes can carry sensitive
            # information (account IDs, internal routing hints); we
            # log full detail server-side and surface a generic
            # message to the user.
            logger.warning(
                "trading_plan_llm_call_failed",
                extra={
                    "user_id": req.user_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise TradingPlanGenerationError(
                "AI service is temporarily unavailable; please try again"
            )

        parsed = self._parse_response(response.text)
        plan = self._shape_plan(
            parsed=parsed,
            balance=req.balance,
            balance_currency=req.balance_currency,
            balance_source=req.balance_source,
            profile_version=req.profile_version,
        )
        return plan

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
            raise TradingPlanGenerationError(
                "AI response was not valid JSON"
            )
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            raise TradingPlanGenerationError(
                "AI response was not valid JSON"
            )
        if not isinstance(data, dict):
            raise TradingPlanGenerationError(
                "AI response was not a JSON object"
            )
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
                raise TradingPlanGenerationError(
                    f"AI response is missing the '{name}' section"
                )
            return v

        def _require_list(value: Any, name: str) -> list[Any]:
            if not isinstance(value, list):
                raise TradingPlanGenerationError(
                    f"AI response section '{name}' is malformed"
                )
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
            raise TradingPlanGenerationError(
                "AI response section 'journal' is malformed"
            )

        def _journal_row(src: Any) -> dict[str, str]:
            if not isinstance(src, dict):
                src = {}
            # The 25 columns mirror src/tradingplan/models.go::JournalRow
            # field-for-field. Every cell defaults to an empty string
            # so a sparse LLM response still produces a structurally
            # valid row the gateway validator accepts.
            return {
                "date":                 str(src.get("date", "")),
                "session":              str(src.get("session", "")),
                "pair":                 str(src.get("pair", "")),
                "direction":            str(src.get("direction", "")),
                "style":                str(src.get("style", "")),
                "setup_type":           str(src.get("setup_type", "")),
                "htf_bias":             str(src.get("htf_bias", "")),
                "entry":                str(src.get("entry", "")),
                "stop_loss":            str(src.get("stop_loss", "")),
                "take_profit":          str(src.get("take_profit", "")),
                "risk_percent":         str(src.get("risk_percent", "")),
                "position_size":        str(src.get("position_size", "")),
                "exit":                 str(src.get("exit", "")),
                "rr_planned":           str(src.get("rr_planned", "")),
                "rr_achieved":          str(src.get("rr_achieved", "")),
                "pnl":                  str(src.get("pnl", "")),
                "outcome":              str(src.get("outcome", "")),
                "rule_followed":        str(src.get("rule_followed", "")),
                "emotion_before_trade": str(src.get("emotion_before_trade", "")),
                "emotion_after_trade":  str(src.get("emotion_after_trade", "")),
                "trade_quality":        str(src.get("trade_quality", "")),
                "mistake_category":     str(src.get("mistake_category", "")),
                "news_present":         str(src.get("news_present", "")),
                "screenshot_link":      str(src.get("screenshot_link", "")),
                "notes":                str(src.get("notes", "")),
            }

        journal: list[dict[str, str]] = [
            _journal_row(r) for r in raw_journal[:JOURNAL_SEED_ROWS]
        ]
        while len(journal) < JOURNAL_SEED_ROWS:
            journal.append(_journal_row({}))

        scorecard_items: list[dict[str, str]] = []
        for it in score_items:
            if not isinstance(it, dict):
                continue
            metric = str(it.get("metric", "")).strip()
            if not metric:
                continue
            scorecard_items.append({
                "metric": metric,
                "score": str(it.get("score", "")),
            })

        plan: dict[str, Any] = {
            "trader_profile": {
                "headline": str(trader.get("headline", "")).strip(),
                "bullets": [str(b).strip() for b in bullets if str(b).strip()],
            },
            "account": {
                "starting_balance":      str(account.get("starting_balance", "")),
                "max_daily_risk":        str(account.get("max_daily_risk", "")),
                "max_weekly_drawdown":   str(account.get("max_weekly_drawdown", "")),
                "preferred_rr":          str(account.get("preferred_rr", "")),
                "max_trades_per_day":    str(account.get("max_trades_per_day", "")),
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
        url = f"{self._base_url}/internal/trading-plan/callback"
        try:
            resp = await self._http.post(
                url,
                json={"user_id": user_id, "plan": plan},
                headers={
                    _INTERNAL_AUTH_HEADER: self._secret,
                    _INTERNAL_USER_ID_HEADER: user_id,
                },
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.error(
                "trading_plan_callback_post_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )
            return

        if resp.status_code != 200:
            logger.error(
                "trading_plan_callback_rejected",
                extra={
                    "user_id": user_id,
                    "status": resp.status_code,
                    "body_preview": resp.text[:300],
                },
            )
            await self._post_fail(
                user_id,
                "AI produced an invalid plan structure; please regenerate",
            )
            return

        logger.info(
            "trading_plan_callback_persisted",
            extra={"user_id": user_id},
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
