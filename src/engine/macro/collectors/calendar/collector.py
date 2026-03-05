from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.calendar import CalendarDataSet
from engine.macro.storage.schemas.calendar import CalendarEventRow

logger = get_logger(__name__)


class CalendarCollector(BaseCollector):
    collector_name = "calendar"
    cache_namespace = "calendar"

    async def _do_collect(self) -> CalendarDataSet:
        all_events = []
        sources = []
        for provider in self._providers:
            try:
                events = await provider.fetch()
                all_events.extend(events)
                sources.append(provider.provider_name)
            except Exception:
                logger.warning("calendar_provider_skipped", provider=provider.provider_name)

        async with self._db.session() as session:
            for event in all_events:
                row = CalendarEventRow(
                    event_name=event.event_name,
                    currency=event.currency.value,
                    impact=event.impact.value,
                    event_time=event.event_time,
                    actual=event.actual,
                    forecast=event.forecast,
                    previous=event.previous,
                    source=event.source,
                )
                session.add(row)

        dataset = CalendarDataSet(
            events=all_events,
            sources=sources,
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace, "latest",
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_events))
        return dataset
