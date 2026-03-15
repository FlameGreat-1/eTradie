"""Post-processor guard checks.

These are hard rejection rules that run AFTER the Processor LLM
has made its decision. The LLM decides trade validity using
TA + Macro + RAG context. Guards are the final safety net that
enforce non-negotiable operational rules before execution.

Guards do NOT decide trade validity - the processor does.
Guards BLOCK execution when hard safety rules are violated.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Optional

from engine.shared.logging import get_logger
from engine.shared.models.events import NEWS_LOCKOUT_MINUTES
from gateway.constants import GuardRule, GuardVerdict
from gateway.context.models import (
    GuardCheckResult,
    GuardEvaluationResult,
    MacroResult,
    ProcessorOutput,
    TASymbolResult,
)
from gateway.observability.metrics import GATEWAY_GUARD_DURATION, GATEWAY_GUARD_REJECTIONS

logger = get_logger(__name__)


class GuardEvaluator:
    """Evaluates all post-processor guard rules.

    Each guard is a pure check that returns PASS, REJECT, or WARN.
    The evaluator aggregates all results and determines the overall verdict.
    """

    def evaluate(
        self,
        *,
        processor_output: ProcessorOutput,
        ta_result: TASymbolResult,
        macro_result: MacroResult,
        trace_id: Optional[str] = None,
    ) -> GuardEvaluationResult:
        """Run all guard checks and return aggregated result."""
        start = time.monotonic()

        checks: list[GuardCheckResult] = [
            self._check_news_proximity(macro_result),
            self._check_session_restriction(ta_result),
            self._check_counter_trend(processor_output, ta_result),
            self._check_weekend_gap_risk(),
            self._check_low_liquidity_hours(),
        ]

        blocking: list[str] = []
        overall = GuardVerdict.PASS

        for check in checks:
            if check.verdict == GuardVerdict.REJECT:
                overall = GuardVerdict.REJECT
                blocking.append(check.rule.value)
                GATEWAY_GUARD_REJECTIONS.labels(rule=check.rule.value).inc()
            elif check.verdict == GuardVerdict.WARN and overall != GuardVerdict.REJECT:
                overall = GuardVerdict.WARN

        elapsed = time.monotonic() - start
        GATEWAY_GUARD_DURATION.observe(elapsed)

        result = GuardEvaluationResult(
            checks=checks,
            overall_verdict=overall,
            blocking_rules=blocking,
        )

        logger.info(
            "guard_evaluation_completed",
            extra={
                "overall_verdict": overall.value,
                "blocking_rules": blocking,
                "checks_total": len(checks),
                "duration_ms": round(elapsed * 1000, 1),
                "trace_id": trace_id,
            },
        )

        return result

    @staticmethod
    def _check_news_proximity(macro: MacroResult) -> GuardCheckResult:
        """MR-REJECT-001: No entries within NEWS_LOCKOUT_MINUTES of high-impact news."""
        calendar = macro.calendar
        if not calendar:
            return GuardCheckResult(
                rule=GuardRule.NEWS_PROXIMITY,
                verdict=GuardVerdict.PASS,
                reason="No calendar data available",
            )

        events = calendar.get("events", [])
        now = datetime.now(UTC)

        for event in events:
            impact = event.get("impact", "").upper()
            if impact != "HIGH":
                continue

            event_time_str = event.get("event_time")
            if not event_time_str:
                continue

            try:
                if isinstance(event_time_str, str):
                    event_time = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
                else:
                    event_time = event_time_str

                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=UTC)

                minutes_until = (event_time - now).total_seconds() / 60

                if 0 <= minutes_until <= NEWS_LOCKOUT_MINUTES:
                    return GuardCheckResult(
                        rule=GuardRule.NEWS_PROXIMITY,
                        verdict=GuardVerdict.REJECT,
                        reason=(
                            f"High-impact event '{event.get('event_name', 'unknown')}' "
                            f"in {int(minutes_until)} minutes (lockout: {NEWS_LOCKOUT_MINUTES}min)"
                        ),
                        metadata={"event_name": event.get("event_name"), "minutes_until": minutes_until},
                    )
            except (ValueError, TypeError):
                continue

        return GuardCheckResult(
            rule=GuardRule.NEWS_PROXIMITY,
            verdict=GuardVerdict.PASS,
            reason="No high-impact events within lockout window",
        )

    @staticmethod
    def _check_session_restriction(ta: TASymbolResult) -> GuardCheckResult:
        """MR-REJECT-002: No entries during restricted sessions (Asian for most pairs)."""
        now = datetime.now(UTC)
        hour = now.hour

        is_asian = 0 <= hour < 7

        if not is_asian:
            return GuardCheckResult(
                rule=GuardRule.SESSION_RESTRICTION,
                verdict=GuardVerdict.PASS,
                reason=f"Current hour {hour} UTC is outside Asian session",
            )

        symbol = ta.symbol.upper()
        is_jpy_pair = "JPY" in symbol
        is_aud_pair = "AUD" in symbol
        is_nzd_pair = "NZD" in symbol

        if is_jpy_pair or is_aud_pair or is_nzd_pair:
            return GuardCheckResult(
                rule=GuardRule.SESSION_RESTRICTION,
                verdict=GuardVerdict.PASS,
                reason=f"{symbol} is active during Asian session",
            )

        return GuardCheckResult(
            rule=GuardRule.SESSION_RESTRICTION,
            verdict=GuardVerdict.REJECT,
            reason=f"Asian session restriction: {symbol} should not be traded 00:00-07:00 UTC",
            metadata={"hour_utc": hour, "symbol": symbol},
        )

    @staticmethod
    def _check_counter_trend(
        processor: ProcessorOutput,
        ta: TASymbolResult,
    ) -> GuardCheckResult:
        """MR-REJECT-006: Counter-trend without HTF CHoCH = NO SETUP.

        If the processor approved a trade that goes against the HTF trend
        and there is no HTF CHoCH in the snapshot, reject it.
        """
        if not processor.trade_valid:
            return GuardCheckResult(
                rule=GuardRule.COUNTER_TREND_NO_CHOCH,
                verdict=GuardVerdict.PASS,
                reason="Trade not valid, guard not applicable",
            )

        snapshot = ta.snapshot or {}
        trend = snapshot.get("trend_direction", "NEUTRAL")
        direction = (processor.direction or "").upper()

        is_counter = (
            (trend == "BULLISH" and direction in ("SHORT", "BEARISH", "SELL"))
            or (trend == "BEARISH" and direction in ("LONG", "BULLISH", "BUY"))
        )

        if not is_counter:
            return GuardCheckResult(
                rule=GuardRule.COUNTER_TREND_NO_CHOCH,
                verdict=GuardVerdict.PASS,
                reason="Trade aligns with HTF trend",
            )

        choch_events = snapshot.get("choch_events", {})
        choch_count = choch_events.get("count", 0) if isinstance(choch_events, dict) else 0

        if choch_count > 0:
            return GuardCheckResult(
                rule=GuardRule.COUNTER_TREND_NO_CHOCH,
                verdict=GuardVerdict.WARN,
                reason="Counter-trend trade with CHoCH detected - proceed with caution",
                metadata={"choch_count": choch_count},
            )

        htf = ta.htf_timeframe or "HTF"
        return GuardCheckResult(
            rule=GuardRule.COUNTER_TREND_NO_CHOCH,
            verdict=GuardVerdict.REJECT,
            reason=f"Counter-trend trade without {htf} CHoCH - rejected per MR-REJECT-006",
            metadata={"trend": trend, "direction": direction},
        )

    @staticmethod
    def _check_weekend_gap_risk() -> GuardCheckResult:
        """MR-REJECT-008: No new entries close to market close on Friday."""
        now = datetime.now(UTC)

        if now.weekday() == 4 and now.hour >= 20:
            return GuardCheckResult(
                rule=GuardRule.WEEKEND_GAP_RISK,
                verdict=GuardVerdict.REJECT,
                reason="Friday after 20:00 UTC - weekend gap risk",
                metadata={"day": "Friday", "hour": now.hour},
            )

        if now.weekday() in (5, 6):
            return GuardCheckResult(
                rule=GuardRule.WEEKEND_GAP_RISK,
                verdict=GuardVerdict.REJECT,
                reason="Weekend - market closed",
                metadata={"day": now.strftime("%A")},
            )

        return GuardCheckResult(
            rule=GuardRule.WEEKEND_GAP_RISK,
            verdict=GuardVerdict.PASS,
            reason="Not in weekend gap risk window",
        )

    @staticmethod
    def _check_low_liquidity_hours() -> GuardCheckResult:
        """MR-REJECT-009: Warn during known low-liquidity hours."""
        now = datetime.now(UTC)
        hour = now.hour

        if 21 <= hour or hour < 1:
            return GuardCheckResult(
                rule=GuardRule.LOW_LIQUIDITY_HOURS,
                verdict=GuardVerdict.WARN,
                reason=f"Low liquidity period: {hour}:00 UTC",
                metadata={"hour_utc": hour},
            )

        return GuardCheckResult(
            rule=GuardRule.LOW_LIQUIDITY_HOURS,
            verdict=GuardVerdict.PASS,
            reason=f"Normal liquidity hours: {hour}:00 UTC",
        )
