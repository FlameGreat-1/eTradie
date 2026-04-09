from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from engine.shared.logging import get_logger
from engine.shared.models.events import DXYMomentum, MacroBias, TrendDirection
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.market_data import MarketDataSet
from engine.macro.storage.repositories.dxy.snapshot import DXYRepository

logger = get_logger(__name__)


def _compute_momentum(current: float, previous: float | None) -> DXYMomentum:
    """Compute DXY momentum from current vs previous value."""
    if previous is None or previous == 0:
        return DXYMomentum.FLAT
    pct_change = ((current - previous) / previous) * 100.0
    if pct_change >= 1.0:
        return DXYMomentum.STRONG_UP
    if pct_change >= 0.3:
        return DXYMomentum.UP
    if pct_change <= -1.0:
        return DXYMomentum.STRONG_DOWN
    if pct_change <= -0.3:
        return DXYMomentum.DOWN
    return DXYMomentum.FLAT


def _compute_trend(
    current: float,
    history: list[float],
) -> TrendDirection:
    """Compute trend direction from recent DXY values.

    Uses a simple comparison: if the current value is above the
    average of recent history, trend is UP. Below = DOWN.
    Requires at least 3 data points for a meaningful trend.
    """
    if len(history) < 2:
        return TrendDirection.SIDEWAYS

    avg = sum(history) / len(history)
    diff_pct = ((current - avg) / avg) * 100.0 if avg != 0 else 0.0

    if diff_pct > 0.15:
        return TrendDirection.UP
    if diff_pct < -0.15:
        return TrendDirection.DOWN
    return TrendDirection.SIDEWAYS


def _compute_key_levels(
    current: float,
    history: list[float],
) -> dict[str, Any]:
    """Identify support and resistance levels from recent DXY history.

    Finds local minima (support) and maxima (resistance) from the
    historical values. Returns the nearest support below current
    price and nearest resistance above.
    """
    if len(history) < 3:
        return {"support": None, "resistance": None, "levels": []}

    # Find local extremes (simple peak/trough detection)
    supports: list[float] = []
    resistances: list[float] = []

    for i in range(1, len(history) - 1):
        if history[i] <= history[i - 1] and history[i] <= history[i + 1]:
            supports.append(history[i])
        if history[i] >= history[i - 1] and history[i] >= history[i + 1]:
            resistances.append(history[i])

    # Also consider the overall min/max as key levels
    supports.append(min(history))
    resistances.append(max(history))

    # Deduplicate and sort
    supports = sorted(set(supports))
    resistances = sorted(set(resistances))

    # Nearest support below current, nearest resistance above current
    nearest_support = max(
        (s for s in supports if s < current), default=None
    )
    nearest_resistance = min(
        (r for r in resistances if r > current), default=None
    )

    return {
        "support": nearest_support,
        "resistance": nearest_resistance,
        "levels": sorted(set(supports + resistances)),
    }


def _detect_divergence(
    momentum: DXYMomentum,
    trend: TrendDirection,
) -> dict[str, Any]:
    """Detect divergence between DXY momentum and trend.

    Divergence occurs when short-term momentum disagrees with the
    broader trend direction. This is a potential reversal signal.
    """
    momentum_bullish = momentum in (DXYMomentum.UP, DXYMomentum.STRONG_UP)
    momentum_bearish = momentum in (DXYMomentum.DOWN, DXYMomentum.STRONG_DOWN)
    trend_up = trend == TrendDirection.UP
    trend_down = trend == TrendDirection.DOWN

    divergence_detected = (
        (momentum_bullish and trend_down)
        or (momentum_bearish and trend_up)
    )

    signal_type = "NONE"
    if momentum_bearish and trend_up:
        signal_type = "BEARISH_DIVERGENCE"
    elif momentum_bullish and trend_down:
        signal_type = "BULLISH_DIVERGENCE"

    return {
        "divergence_detected": divergence_detected,
        "signal_type": signal_type,
        "momentum": momentum.value,
        "trend": trend.value,
    }


def _compute_bias(
    momentum: DXYMomentum,
    trend: TrendDirection,
) -> MacroBias:
    """Derive overall DXY bias from momentum and trend.

    Both momentum and trend must agree for a directional bias.
    If they disagree or are neutral, bias is NEUTRAL.
    """
    momentum_bullish = momentum in (DXYMomentum.UP, DXYMomentum.STRONG_UP)
    momentum_bearish = momentum in (DXYMomentum.DOWN, DXYMomentum.STRONG_DOWN)

    if momentum_bullish and trend in (TrendDirection.UP, TrendDirection.SIDEWAYS):
        return MacroBias.BULLISH
    if momentum_bearish and trend in (TrendDirection.DOWN, TrendDirection.SIDEWAYS):
        return MacroBias.BEARISH
    if trend == TrendDirection.UP and momentum == DXYMomentum.FLAT:
        return MacroBias.BULLISH
    if trend == TrendDirection.DOWN and momentum == DXYMomentum.FLAT:
        return MacroBias.BEARISH
    return MacroBias.NEUTRAL


class DXYCollector(BaseCollector):
    """Collect DXY (US Dollar Index) snapshots with full analysis.

    Computes momentum, trend direction, key support/resistance levels,
    divergence signals, and overall bias. Persists via
    DXYRepository.upsert_snapshot() with deduplication on
    (user_id, analyzed_at) to prevent unbounded row growth.
    """

    collector_name = "dxy"
    cache_namespace = "dxy"

    async def _do_collect(self) -> MarketDataSet:
        snapshot = await self._fetch_with_failover(self._providers)

        momentum = DXYMomentum.FLAT
        if snapshot and snapshot.dxy_value is not None:
            async with self._db.session() as session:
                repo = DXYRepository(session)

                # Get previous snapshot for momentum calculation
                prev = await repo.get_latest()
                prev_value = prev.value if prev else None
                momentum = _compute_momentum(snapshot.dxy_value, prev_value)

                # Get recent history for trend and key level analysis
                recent_rows = await repo.get_recent_values(limit=20)
                history_values = [
                    row.value for row in reversed(recent_rows)
                ]

                trend = _compute_trend(snapshot.dxy_value, history_values)
                key_levels = _compute_key_levels(
                    snapshot.dxy_value, history_values,
                )
                divergence = _detect_divergence(momentum, trend)
                bias = _compute_bias(momentum, trend)

                await repo.upsert_snapshot(
                    value=snapshot.dxy_value,
                    trend_direction=trend.value,
                    momentum=momentum.value,
                    key_levels_json=key_levels,
                    divergence_signals_json=divergence,
                    bias=bias.value,
                    analyzed_at=snapshot.snapshot_at,
                )

            snapshot = snapshot.model_copy(update={"dxy_momentum": momentum})

        dataset = MarketDataSet(
            snapshots=[snapshot] if snapshot else [],
            latest=snapshot,
            sources=[p.provider_name for p in self._providers],
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace,
            self._cache_key(),
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(1 if snapshot else 0)
        return dataset
