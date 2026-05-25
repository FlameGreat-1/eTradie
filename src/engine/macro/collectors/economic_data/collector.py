from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.economic import EconomicDataSet

logger = get_logger(__name__)


class EconomicDataCollector(BaseCollector):
    collector_name = "economic_data"
    cache_namespace = "economic"
    cache_model = EconomicDataSet

    async def _do_collect(self) -> EconomicDataSet:
        all_releases = []
        sources = []
        provider_errors: dict[str, str] = {}

        for provider in self._providers:
            try:
                releases = await provider.fetch()
                if releases:
                    all_releases.extend(releases)
                    sources.append(provider.provider_name)
                    logger.info(
                        "economic_provider_success",
                        extra={
                            "provider": provider.provider_name,
                            "releases_count": len(releases),
                        },
                    )
                else:
                    logger.warning(
                        "economic_provider_empty",
                        extra={"provider": provider.provider_name},
                    )
            except Exception as exc:
                provider_errors[provider.provider_name] = str(exc)
                logger.warning(
                    "economic_provider_skipped",
                    extra={
                        "provider": provider.provider_name,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )

        if provider_errors and not all_releases:
            logger.error(
                "economic_all_providers_failed",
                extra={"errors": provider_errors},
            )

        # Persist to DB, but don't let DB errors kill the entire collector.
        # The collected data is still valuable for the current analysis cycle
        # even if we can't persist it for historical queries.
        if all_releases:
            unique_map = {
                (r.indicator_name, r.release_time): r for r in all_releases
            }
            all_releases = list(unique_map.values())
            try:
                async with self._db.session() as session:
                    from engine.macro.storage.repositories.economic.release import (
                        EconomicReleaseRepository,
                    )

                    repo = EconomicReleaseRepository(session)
                    rows = [
                        {
                            "indicator_name": release.indicator_name,
                            "actual": release.actual,
                            "previous": release.previous,
                            "release_time": release.release_time,
                        }
                        for release in all_releases
                    ]
                    await repo.bulk_upsert(
                        rows,
                        index_elements=[
                            "indicator_name",
                            "release_time",
                        ],
                        update_fields=[
                            "actual",
                            "previous",
                        ],
                    )
            except Exception as exc:
                logger.error(
                    "economic_db_upsert_failed",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "releases_count": len(all_releases),
                    },
                )
                # Continue - return the data even if DB persistence failed.

        dataset = EconomicDataSet(
            releases=all_releases,
            sources=sources,
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace,
            self._cache_key(),
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_releases))
        return dataset


    async def _read_from_db(self):
        return None

    def _empty_dataset(self):
        return EconomicDataSet(releases=[], sources=[], collected_at=datetime.now(UTC))
