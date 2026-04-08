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

    async def _do_collect(self, user_id: str) -> EconomicDataSet:
        all_releases = []
        sources = []
        for provider in self._providers:
            try:
                releases = await provider.fetch()
                all_releases.extend(releases)
                sources.append(provider.provider_name)
            except Exception:
                logger.warning(
                    "economic_provider_skipped", provider=provider.provider_name
                )

        # Upsert with deduplication: same user + currency + indicator + time = one row.
        async with self._db.session() as session:
            from engine.macro.storage.repositories.economic.release import (
                EconomicRepository,
            )

            repo = EconomicRepository(session)
            rows = [
                {
                    "user_id": user_id,
                    "currency": release.currency.value,
                    "indicator": release.indicator.value,
                    "indicator_name": release.indicator_name,
                    "actual": release.actual,
                    "forecast": release.forecast,
                    "previous": release.previous,
                    "surprise": release.surprise,
                    "surprise_direction": release.surprise_direction.value,
                    "impact": release.impact.value,
                    "inflation_type": (
                        release.inflation_type.value
                        if release.inflation_type
                        else None
                    ),
                    "source": release.source,
                    "release_time": release.release_time,
                }
                for release in all_releases
            ]
            if rows:
                await repo.bulk_upsert(
                    rows,
                    index_elements=[
                        "user_id", "currency", "indicator", "release_time",
                    ],
                    update_fields=[
                        "actual", "forecast", "previous", "surprise",
                        "surprise_direction", "impact", "inflation_type", "source",
                    ],
                )

        dataset = EconomicDataSet(
            releases=all_releases,
            sources=sources,
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace,
            self._user_cache_key(user_id),
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_releases))
        return dataset
