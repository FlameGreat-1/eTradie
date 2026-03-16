from __future__ import annotations

from datetime import UTC, datetime, timedelta

from engine.shared.logging import get_logger
from engine.shared.models.events import DXYMomentum
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.market_data import MarketDataSet
from engine.macro.storage.repositories.dxy.snapshot import DXYRepository
from engine.macro.storage.schemas.dxy import DXYSnapshotRow

logger = get_logger(__name__)


def _compute_momentum(current: float, previous: float | None) -> DXYMomentum:
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


class DXYCollector(BaseCollector):
    collector_name = "dxy"
    cache_namespace = "dxy"

    async def _do_collect(self) -> MarketDataSet:
        snapshot = await self._fetch_with_failover(self._providers)

        momentum = DXYMomentum.FLAT
        if snapshot and snapshot.dxy_value is not None:
            async with self._db.session() as session:
                repo = DXYRepository(session)
                prev = await repo.get_latest()
                prev_value = prev.value if prev else None
                momentum = _compute_momentum(snapshot.dxy_value, prev_value)

                row = DXYSnapshotRow(
                    value=snapshot.dxy_value,
                    momentum=momentum.value,
                    analyzed_at=snapshot.snapshot_at,
                )
                session.add(row)

            snapshot = snapshot.model_copy(update={"dxy_momentum": momentum})

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
