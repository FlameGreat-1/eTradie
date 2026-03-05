from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.economic import EconomicDataSet
from engine.macro.storage.schemas.economic import EconomicReleaseRow

logger = get_logger(__name__)


class EconomicDataCollector(BaseCollector):
    collector_name = "economic_data"
    cache_namespace = "economic"

    async def _do_collect(self) -> EconomicDataSet:
        all_releases = []
        sources = []
        for provider in self._providers:
            try:
                releases = await provider.fetch()
                all_releases.extend(releases)
                sources.append(provider.provider_name)
            except Exception:
                logger.warning("economic_provider_skipped", provider=provider.provider_name)

        async with self._db.session() as session:
            for release in all_releases:
                row = EconomicReleaseRow(
                    currency=release.currency.value,
                    indicator=release.indicator.value,
                    indicator_name=release.indicator_name,
                    actual=release.actual,
                    forecast=release.forecast,
                    previous=release.previous,
                    surprise=release.surprise,
                    surprise_direction=release.surprise_direction.value,
                    impact=release.impact.value,
                    source=release.source,
                    release_time=release.release_time,
                )
                session.add(row)

        dataset = EconomicDataSet(
            releases=all_releases,
            sources=sources,
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace, "latest",
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_releases))
        return dataset
