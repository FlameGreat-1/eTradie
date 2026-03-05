from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.models.collector.cot import COTDataSet
from engine.macro.collectors.base import BaseCollector

logger = get_logger(__name__)


class COTCollector(BaseCollector):
    collector_name = "cot"
    cache_namespace = "cot"

    async def _do_collect(self) -> COTDataSet:
        report = await self._fetch_with_failover(self._providers)
        dataset = COTDataSet(
            latest_positions=report.positions if report else [],
            report_date=report.report_date if report else None,
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace, "latest",
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(dataset.latest_positions))
        return dataset
