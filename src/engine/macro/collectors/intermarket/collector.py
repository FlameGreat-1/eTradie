from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.market_data import MarketDataSet
from engine.macro.models.provider.market_data import IntermarketSnapshot
from engine.macro.storage.repositories.intermarket.snapshot import IntermarketRepository
from engine.shared.logging import get_logger

logger = get_logger(__name__)


def _merge_snapshots(
    snapshots: list[IntermarketSnapshot],
) -> IntermarketSnapshot | None:
    """Merge multiple IntermarketSnapshot objects into one.

    For each field, the first non-None value encountered wins. This lets the
    FRED intermarket provider supply DXY/yields/VIX/S&P/oil/gas/iron-ore/copper
    while the Yahoo metals provider fills gold and silver, producing one
    complete snapshot.
    """
    if not snapshots:
        return None

    merged_data: dict[str, object] = {
        "dxy_value": None,
        "dxy_momentum": None,
        "gold_price": None,
        "silver_price": None,
        "oil_price": None,
        "iron_ore": None,
        "dairy_gdt": None,
        "copper": None,
        "natural_gas": None,
        "us2y_yield": None,
        "us10y_yield": None,
        "us30y_yield": None,
        "sp500": None,
        "vix": None,
    }

    sources: list[str] = []
    latest_time = datetime.now(UTC)

    for snap in snapshots:
        for field in merged_data:
            if merged_data[field] is None:
                val = getattr(snap, field, None)
                if val is not None:
                    merged_data[field] = val
        if snap.source and snap.source not in sources:
            sources.append(snap.source)
        latest_time = snap.snapshot_at

    return IntermarketSnapshot(
        dxy_value=merged_data["dxy_value"],
        dxy_momentum=merged_data["dxy_momentum"],
        gold_price=merged_data["gold_price"],
        silver_price=merged_data["silver_price"],
        oil_price=merged_data["oil_price"],
        iron_ore=merged_data["iron_ore"],
        dairy_gdt=merged_data["dairy_gdt"],
        copper=merged_data["copper"],
        natural_gas=merged_data["natural_gas"],
        us2y_yield=merged_data["us2y_yield"],
        us10y_yield=merged_data["us10y_yield"],
        us30y_yield=merged_data["us30y_yield"],
        sp500=merged_data["sp500"],
        vix=merged_data["vix"],
        snapshot_at=latest_time,
        source="+".join(sources) if sources else "",
    )


def _compute_correlation_signals(
    snapshot: IntermarketSnapshot,
) -> dict[str, Any]:
    """Compute cross-asset correlation signals from intermarket data.

    Identifies key relationships:
    - Gold/USD inverse correlation (gold up + DXY down = risk-off)
    - Yield curve slope (2Y vs 10Y spread, inversion = recession risk)
    - VIX risk signal (elevated VIX = fear/risk-off)
    - Commodity currency proxies (iron_ore for AUD, dairy for NZD)
    """
    signals: dict[str, Any] = {
        "gold_usd_inverse": None,
        "yield_curve_slope_bps": None,
        "yield_curve_inverted": None,
        "vix_regime": None,
        "iron_ore_aud_signal": None,
        "dairy_nzd_signal": None,
    }

    # Gold/USD inverse: if both available, check if they're moving
    # in opposite directions (gold up = USD weakness signal)
    if snapshot.gold_price is not None and snapshot.dxy_value is not None:
        signals["gold_usd_inverse"] = {
            "gold_price": snapshot.gold_price,
            "dxy_value": snapshot.dxy_value,
        }

    # Yield curve slope: 10Y - 2Y spread in basis points
    if snapshot.us2y_yield is not None and snapshot.us10y_yield is not None:
        spread_bps = round((snapshot.us10y_yield - snapshot.us2y_yield) * 100, 1)
        signals["yield_curve_slope_bps"] = spread_bps
        signals["yield_curve_inverted"] = spread_bps < 0

    # VIX regime classification
    if snapshot.vix is not None:
        if snapshot.vix > 30:
            signals["vix_regime"] = "EXTREME_FEAR"
        elif snapshot.vix > 20:
            signals["vix_regime"] = "ELEVATED"
        elif snapshot.vix < 15:
            signals["vix_regime"] = "COMPLACENT"
        else:
            signals["vix_regime"] = "NORMAL"

    # Iron ore as AUD proxy (Australia's top export)
    if snapshot.iron_ore is not None:
        if snapshot.iron_ore > 120:
            signals["iron_ore_aud_signal"] = "SUPPORTIVE"
        elif snapshot.iron_ore < 80:
            signals["iron_ore_aud_signal"] = "HEADWIND"
        else:
            signals["iron_ore_aud_signal"] = "NEUTRAL"

    # Dairy GDT as NZD proxy (New Zealand's top export)
    if snapshot.dairy_gdt is not None:
        if snapshot.dairy_gdt > 1200:
            signals["dairy_nzd_signal"] = "SUPPORTIVE"
        elif snapshot.dairy_gdt < 900:
            signals["dairy_nzd_signal"] = "HEADWIND"
        else:
            signals["dairy_nzd_signal"] = "NEUTRAL"

    return signals


def _compute_trend_signals(
    current: IntermarketSnapshot,
    previous: IntermarketSnapshot | None,
) -> dict[str, Any]:
    """Direction + change for the fields whose TRAJECTORY is a real risk signal.

    Only VIX, the US 10Y yield, and gold are trended: rising VIX / falling
    yields / rallying gold all signal risk-off, which the LLM should see as a
    direction, not just a level. DXY already has full trend in its own
    collector; S&P/oil/silver/gas and the monthly iron-ore/copper are omitted.

    Returns an empty dict when there is no previous snapshot (first cycle) or a
    field is missing on either side. Thresholds keep ordinary noise STABLE.
    """
    if previous is None:
        return {}

    out: dict[str, Any] = {}

    if current.vix is not None and previous.vix is not None:
        change = round(current.vix - previous.vix, 2)
        out["vix_change"] = change
        if change >= 1.0:
            out["vix_trend"] = "RISING"
        elif change <= -1.0:
            out["vix_trend"] = "FALLING"
        else:
            out["vix_trend"] = "STABLE"

    if current.us10y_yield is not None and previous.us10y_yield is not None:
        change_bps = round((current.us10y_yield - previous.us10y_yield) * 100, 1)
        out["us10y_change_bps"] = change_bps
        if change_bps >= 5.0:
            out["us10y_trend"] = "RISING"
        elif change_bps <= -5.0:
            out["us10y_trend"] = "FALLING"
        else:
            out["us10y_trend"] = "STABLE"

    if current.gold_price is not None and previous.gold_price is not None and previous.gold_price != 0:
        pct = round(
            (current.gold_price - previous.gold_price) / previous.gold_price * 100,
            2,
        )
        out["gold_change_pct"] = pct
        if pct >= 2.0:
            out["gold_trend"] = "RISING"
        elif pct <= -2.0:
            out["gold_trend"] = "FALLING"
        else:
            out["gold_trend"] = "STABLE"

    return out


class IntermarketCollector(BaseCollector):
    """Collect intermarket data from multiple providers and merge.

    Computes cross-asset correlation signals and persists via
    IntermarketRepository.upsert_snapshot() with deduplication on
    (snapshot_at) to prevent unbounded row growth.
    """

    collector_name = "intermarket"
    cache_namespace = "intermarket"
    cache_model = MarketDataSet

    async def _do_collect(self) -> MarketDataSet:
        # Fetch from all providers and merge results.
        # TwelveData provides core data; CommodityProxyProvider
        # fills iron_ore and dairy_gdt.
        snapshots: list[IntermarketSnapshot] = []
        for provider in self._providers:
            try:
                snap = await provider.fetch()
                if snap is not None:
                    snapshots.append(snap)
            except Exception:
                logger.warning(
                    "intermarket_provider_skipped",
                    provider=provider.provider_name,
                )

        snapshot = _merge_snapshots(snapshots)

        correlation_signals: dict[str, Any] | None = None
        if snapshot:
            correlation_signals = _compute_correlation_signals(snapshot)

            async with self._db.session() as session:
                repo = IntermarketRepository(session)
                # Read the prior snapshot BEFORE upserting the new one so the
                # trend comparison uses the previous cycle's values. Best-effort:
                # a read failure simply omits trends (no prior -> empty).
                try:
                    previous = await repo.get_latest()
                except Exception:
                    previous = None
                trend_signals = _compute_trend_signals(snapshot, previous)
                if trend_signals:
                    correlation_signals.update(trend_signals)
                await repo.upsert_snapshot(
                    snapshot_data={
                        "gold_price": snapshot.gold_price,
                        "silver_price": snapshot.silver_price,
                        "oil_price": snapshot.oil_price,
                        "iron_ore": snapshot.iron_ore,
                        "dairy_gdt": snapshot.dairy_gdt,
                        "copper": snapshot.copper,
                        "natural_gas": snapshot.natural_gas,
                        "us2y_yield": snapshot.us2y_yield,
                        "us10y_yield": snapshot.us10y_yield,
                        "us30y_yield": snapshot.us30y_yield,
                        "dxy_value": snapshot.dxy_value,
                        "sp500": snapshot.sp500,
                        "vix": snapshot.vix,
                        "correlation_signals_json": correlation_signals,
                        "snapshot_at": snapshot.snapshot_at,
                    },
                )

        dataset = MarketDataSet(
            snapshots=[snapshot] if snapshot else [],
            latest=snapshot,
            sources=[p.provider_name for p in self._providers],
            correlation_signals=correlation_signals,
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

    def _empty_dataset(self) -> MarketDataSet:
        return MarketDataSet(snapshots=[], latest=None, sources=[], collected_at=datetime.now(UTC))
