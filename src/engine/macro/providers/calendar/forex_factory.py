from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact
from engine.macro.models.provider.calendar import CalendarEvent
from engine.macro.providers.calendar.base import BaseCalendarProvider

logger = get_logger(__name__)

_IMPACT_MAP = {"High": EventImpact.HIGH, "Medium": EventImpact.MEDIUM, "Low": EventImpact.LOW}


class ForexFactoryCalendarProvider(BaseCalendarProvider):
    provider_name = "forex_factory_calendar"

    def __init__(self, http_client: HttpClient, *, base_url: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url

    async def fetch(self) -> list[CalendarEvent]:
        start = time.monotonic()
        try:
            raw = await self._http.get(
                self._base_url,
                provider_name=self.provider_name,
                category=self.category.value,
            )
            events = [e for e in (self._parse(r) for r in (raw if isinstance(raw, list) else [])) if e is not None]
            self._record_success(time.monotonic() - start)
            return events
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("ff_calendar_fetch_failed", error=str(exc))
            raise

    def _parse(self, raw: dict[str, Any]) -> CalendarEvent | None:
        country = str(raw.get("country", "")).upper()[:3]
        try:
            currency = Currency(country)
        except ValueError:
            return None
        try:
            event_time = datetime.fromisoformat(str(raw.get("date", ""))).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            event_time = datetime.now(UTC)

        return CalendarEvent(
            event_name=str(raw.get("title", "")),
            currency=currency,
            impact=_IMPACT_MAP.get(raw.get("impact", ""), EventImpact.LOW),
            event_time=event_time,
            actual=str(raw.get("actual", "")),
            forecast=str(raw.get("forecast", "")),
            previous=str(raw.get("previous", "")),
            source="forex_factory",
        )
