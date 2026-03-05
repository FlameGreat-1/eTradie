from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.cache import RedisCache
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.cot import COTDataSet
from engine.macro.storage.repositories.cot.report import COTRepository

logger = get_logger(__name__)


class COTCollector(BaseCollector):
    collector_name = "cot"
    cache_namespace = "cot"

    async def _do_collect(self) -> COTDataSet:
        report = await self._fetch_with_failover(self._providers)
        positions = report.positions if report else []

        async with self._db.session() as session:
            repo = COTRepository(session)
            rows = [
                {
                    "currency": p.currency.value,
                    "contract_name": p.contract_name,
                    "non_commercial_long": p.non_commercial_long,
                    "non_commercial_short": p.non_commercial_short,
                    "non_commercial_net": p.non_commercial_net,
                    "commercial_long": p.commercial_long,
                    "commercial_short": p.commercial_short,
                    "commercial_net": p.commercial_net,
                    "open_interest": p.open_interest,
                    "report_date": p.report_date,
                }
                for p in positions
            ]
            if rows:
                await repo.bulk_upsert(
                    rows,
                    index_elements=["currency", "report_date"],
                    update_fields=["non_commercial_long", "non_commercial_short", "non_commercial_net",
                                   "commercial_long", "commercial_short", "commercial_net", "open_interest"],
                )

        dataset = COTDataSet(
            latest_positions=positions,
            report_date=report.report_date if report else None,
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace, "latest",
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(positions))
        return dataset
