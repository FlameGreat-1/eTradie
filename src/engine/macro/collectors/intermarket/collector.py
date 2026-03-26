from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.market_data import MarketDataSet
from engine.macro.models.provider.market_data import IntermarketSnapshot
from engine.macro.storage.schemas.intermarket import IntermarketSnapshotRow

logger = get_logger(__name__)


def _merge_snapshots(snapshots: list[IntermarketSnapshot]) -> IntermarketSnapshot | None:
    """Merge multiple IntermarketSnapshot objects into one.

    For each field, the first non-None value encountered wins.
    This allows TwelveData to provide core market data while the
    CommodityProxyProvider fills in niche fields like iron_ore
    and dairy_gdt.
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


class IntermarketCollector(BaseCollector):
    collector_name = "intermarket"
    cache_namespace = "intermarket"

    async def _do_collect(self) -> MarketDataSet:
        # Fetch from all providers concurrently and merge results.
        # This allows TwelveData to provide core data while the
        # CommodityProxyProvider fills iron_ore and dairy_gdt.
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

        if snapshot:
            async with self._db.session() as session:
                row = IntermarketSnapshotRow(
                    gold_price=snapshot.gold_price,
                    silver_price=snapshot.silver_price,
                    oil_price=snapshot.oil_price,
                    iron_ore=snapshot.iron_ore,
                    dairy_gdt=snapshot.dairy_gdt,
                    copper=snapshot.copper,
                    natural_gas=snapshot.natural_gas,
                    us2y_yield=snapshot.us2y_yield,
                    us10y_yield=snapshot.us10y_yield,
                    us30y_yield=snapshot.us30y_yield,
                    dxy_value=snapshot.dxy_value,
                    sp500=snapshot.sp500,
                    vix=snapshot.vix,
                    snapshot_at=snapshot.snapshot_at,
                )
                session.add(row)

        dataset = MarketDataSet(
            snapshots=[snapshot] if snapshot else [],
            latest=snapshot,
            sources=[p.provider_name for p in self._providers],
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace,
            "latest",
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(1 if snapshot else 0)
        return dataset
