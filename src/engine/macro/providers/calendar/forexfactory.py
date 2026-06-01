"""Forex Factory economic-calendar provider (FREE, scheduled future times).

Consumes Forex Factory's official machine-readable weekly calendar JSON, served
from their faireconomy CDN (no API key, no scraping of the JS-rendered site):

  https://nfs.faireconomy.media/ff_calendar_thisweek.json

Unlike a news RSS feed, every entry carries the event's SCHEDULED time, which
is what the gateway news-blackout guard needs (it locks out trades only when a
high-impact event is within `lockoutMinutes` in the FUTURE). The previous
Investing.com RSS source supplied the article PUBLISH time (always in the
past), so the guard could never fire; this provider fixes that at the source.

Feed entry shape:
  {"title": "Non-Farm Employment Change", "country": "USD",
   "date": "2026-06-05T08:30:00-04:00", "impact": "High",
   "forecast": "95K", "previous": "115K"}
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

# Forex Factory impact label -> EventImpact. "Holiday" is deliberately mapped
# to LOW: a market holiday is not a high-impact data spike and must never trip
# the HIGH-impact news lockout. Anything unrecognised defaults to LOW.
_IMPACT_MAP: dict[str, EventImpact] = {
    "high": EventImpact.HIGH,
    "medium": EventImpact.MEDIUM,
    "low": EventImpact.LOW,
    "holiday": EventImpact.LOW,
}

# Currency codes the system trades. Feed entries for any other code (e.g. CNY)
# are skipped -- they carry no fiat-calendar exposure for our pairs.
_SUPPORTED_CURRENCIES: frozenset[str] = frozenset(
    {
        Currency.USD.value,
        Currency.EUR.value,
        Currency.GBP.value,
        Currency.JPY.value,
        Currency.CHF.value,
        Currency.AUD.value,
        Currency.CAD.value,
        Currency.NZD.value,
    }
)


class ForexFactoryCalendarProvider(BaseCalendarProvider):
    """Fetch the Forex Factory weekly economic calendar JSON."""

    provider_name = "forexfactory_calendar"

    def __init__(self, http_client: HttpClient, *, feed_url: str) -> None:
        super().__init__()
        self._http = http_client
        self._feed_url = feed_url

    async def fetch(self) -> list[CalendarEvent]:
        start = time.monotonic()
        try:
            raw = await self._http.get(
                self._feed_url,
                provider_name=self.provider_name,
                category=self.category.value,
            )
            rows = self._coerce_rows(raw)

            events: list[CalendarEvent] = []
            for row in rows:
                event = self._parse_row(row)
                if event is not None:
                    events.append(event)

            if not events:
                logger.warning(
                    "forexfactory_calendar_no_events",
                    extra={"rows": len(rows)},
                )

            self._record_success(time.monotonic() - start)
            return events
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "forexfactory_calendar_fetch_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            raise

    @staticmethod
    def _coerce_rows(raw: Any) -> list[dict[str, Any]]:
        """The HTTP client may return a parsed list/dict or a JSON string."""
        if isinstance(raw, list):
            return [r for r in raw if isinstance(r, dict)]
        if isinstance(raw, str):
            import json

            try:
                parsed = json.loads(raw)
            except (ValueError, TypeError):
                return []
            if isinstance(parsed, list):
                return [r for r in parsed if isinstance(r, dict)]
        return []

    def _parse_row(self, row: dict[str, Any]) -> CalendarEvent | None:
        country = str(row.get("country", "")).strip().upper()
        if country not in _SUPPORTED_CURRENCIES:
            return None
        try:
            currency = Currency(country)
        except ValueError:
            return None

        title = str(row.get("title", "")).strip()
        if not title:
            return None

        event_time = self._parse_dt(row.get("date"))
        if event_time is None:
            return None

        impact = _IMPACT_MAP.get(
            str(row.get("impact", "")).strip().lower(), EventImpact.LOW
        )

        return CalendarEvent(
            event_name=title,
            currency=currency,
            event_time=event_time,
            impact=impact,
            forecast=str(row.get("forecast", "") or "").strip(),
            previous=str(row.get("previous", "") or "").strip(),
            actual=str(row.get("actual", "") or "").strip(),
            source="forexfactory",
        )

    @staticmethod
    def _parse_dt(value: Any) -> datetime | None:
        """Parse the ISO-8601 timestamp (with tz offset) and return UTC.

        Forex Factory emits e.g. "2026-06-05T08:30:00-04:00". We normalise to
        UTC so the value matches the gateway guard's RFC3339/UTC expectation
        and so the durable snapshot is timezone-unambiguous.
        """
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
