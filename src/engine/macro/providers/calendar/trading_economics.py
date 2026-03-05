"""TradingEconomics.com — Economic Calendar provider.

Institutional-grade economic calendar covering ~1600 events/month across 150+
countries.  Returns real-time actuals, consensus forecasts, and previous values
with impact levels (1=Low, 2=Medium, 3=High).

API docs: https://docs.tradingeconomics.com/economic_calendar/snapshot
"""

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

# TradingEconomics uses Importance: 1=Low, 2=Medium, 3=High
_IMPORTANCE_MAP: dict[int, EventImpact] = {
    3: EventImpact.HIGH,
    2: EventImpact.MEDIUM,
    1: EventImpact.LOW,
}

# Map TradingEconomics country names → Currency enum values.
# Only currencies we trade are mapped; others are silently skipped.
_COUNTRY_CURRENCY_MAP: dict[str, Currency] = {
    "United States": Currency.USD,
    "Euro Area": Currency.EUR,
    "United Kingdom": Currency.GBP,
    "Japan": Currency.JPY,
    "Switzerland": Currency.CHF,
    "Australia": Currency.AUD,
    "Canada": Currency.CAD,
    "New Zealand": Currency.NZD,
}


class TradingEconomicsCalendarProvider(BaseCalendarProvider):
    """Fetch upcoming/recent economic events from TradingEconomics calendar API."""

    provider_name = "tradingeconomics_calendar"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[CalendarEvent]:
        start = time.monotonic()
        try:
            raw = await self._http.get(
                f"{self._base_url}/calendar",
                provider_name=self.provider_name,
                category=self.category.value,
                params={"c": self._api_key, "f": "json"},
            )
            if not isinstance(raw, list):
                raw = []
            events = [e for e in (self._parse(r) for r in raw) if e is not None]
            self._record_success(time.monotonic() - start)
            return events
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("te_calendar_fetch_failed", error=str(exc))
            raise

    def _parse(self, raw: dict[str, Any]) -> CalendarEvent | None:
        country = str(raw.get("Country", ""))
        currency = _COUNTRY_CURRENCY_MAP.get(country)
        if currency is None:
            return None

        importance = raw.get("Importance", 1)
        try:
            importance_int = int(importance)
        except (ValueError, TypeError):
            importance_int = 1
        impact = _IMPORTANCE_MAP.get(importance_int, EventImpact.LOW)

        date_str = str(raw.get("Date", ""))
        try:
            event_time = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            event_time = datetime.now(UTC)

        return CalendarEvent(
            event_name=str(raw.get("Event", "")),
            currency=currency,
            impact=impact,
            event_time=event_time,
            actual=str(raw.get("Actual", "")),
            forecast=str(raw.get("Forecast", "")),
            previous=str(raw.get("Previous", "")),
            source="tradingeconomics",
        )
