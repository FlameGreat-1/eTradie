from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.calendar import CalendarDataSet

logger = get_logger(__name__)


class CalendarCollector(BaseCollector):
    collector_name = "calendar"
    cache_namespace = "calendar"
    cache_model = CalendarDataSet

    async def _do_collect(self) -> CalendarDataSet:
        all_events = []
        sources = []
        for provider in self._providers:
            try:
                events = await provider.fetch()
                all_events.extend(events)
                sources.append(provider.provider_name)
            except Exception:
                logger.warning(
                    "calendar_provider_skipped", provider=provider.provider_name
                )

        # Upsert with deduplication: event + currency + time = one row.
        async with self._db.session() as session:
            from engine.macro.storage.repositories.calendar.event import (
                CalendarRepository,
            )

            repo = CalendarRepository(session)
            rows = [
                {
                    "event_name": event.event_name,
                    "currency": event.currency.value,
                    "event_time": event.event_time,
                    "impact": event.impact.value,
                    "source": event.source,
                }
                for event in all_events
            ]
            if rows:
                await repo.bulk_upsert(
                    rows,
                    index_elements=["event_name", "currency", "event_time"],
                    update_fields=["source", "impact"],
                )

        dataset = CalendarDataSet(
            events=all_events,
            sources=sources,
            collected_at=datetime.now(UTC),
        )

        await self._cache.set(
            self.cache_namespace,
            self._cache_key(),
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_events))
        return dataset


    async def _read_from_db(self):
        return None

    def _empty_dataset(self):
        return CalendarDataSet(events=[], sources=[], collected_at=datetime.now(UTC))
