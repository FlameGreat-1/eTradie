from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.market_data import MarketDataSet
from engine.macro.storage.schemas.dxy import DXYSnapshotRow

logger = get_logger(__name__)


class DXYCollector(BaseCollector):
    collector_name = "dxy"
    cache_namespace = "dxy"

    async def _do_collect(self) -> MarketDataSet:
        snapshot = await self._fetch_with_failover(self._providers)

        if snapshot and snapshot.dxy_value is not None:
            async with self._db.session() as session:
                row = DXYSnapshotRow(
                    value=snapshot.dxy_value,
                    analyzed_at=snapshot.snapshot_at,
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
