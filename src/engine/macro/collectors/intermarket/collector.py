from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.market_data import MarketDataSet
from engine.macro.storage.schemas.intermarket import IntermarketSnapshotRow

logger = get_logger(__name__)


class IntermarketCollector(BaseCollector):
    collector_name = "intermarket"
    cache_namespace = "intermarket"

    async def _do_collect(self) -> MarketDataSet:
        snapshot = await self._fetch_with_failover(self._providers)

        if snapshot:
            async with self._db.session() as session:
                row = IntermarketSnapshotRow(
                    gold_price=snapshot.gold_price,
                    silver_price=snapshot.silver_price,
                    oil_price=snapshot.oil_price,
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
            self.cache_namespace, "latest",
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(1 if snapshot else 0)
        return dataset
