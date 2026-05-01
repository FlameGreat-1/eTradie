"""Investing.com RSS — Economic Calendar provider (FREE).

Parses the Investing.com economic calendar RSS feed to extract upcoming
and recent economic events with impact levels, currencies, and
actual/forecast/previous values when available.

Covers all major forex currencies: USD, EUR, GBP, JPY, CHF, AUD, CAD, NZD.
Zero cost, no API key required.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact
from engine.shared.rss import RSSParser
from engine.shared.rss.parser import RSSEntry
from engine.macro.models.provider.calendar import CalendarEvent
from engine.macro.providers.calendar.base import BaseCalendarProvider

logger = get_logger(__name__)

# Map country/region names found in RSS titles to Currency enum.
_CURRENCY_KEYWORDS: dict[str, Currency] = {
    "usd": Currency.USD,
    "united states": Currency.USD,
    "u.s.": Currency.USD,
    "us ": Currency.USD,
    "eur": Currency.EUR,
    "euro zone": Currency.EUR,
    "eurozone": Currency.EUR,
    "euro area": Currency.EUR,
    "gbp": Currency.GBP,
    "united kingdom": Currency.GBP,
    "uk ": Currency.GBP,
    "british": Currency.GBP,
    "jpy": Currency.JPY,
    "japan": Currency.JPY,
    "chf": Currency.CHF,
    "switzerland": Currency.CHF,
    "swiss": Currency.CHF,
    "aud": Currency.AUD,
    "australia": Currency.AUD,
    "australian": Currency.AUD,
    "cad": Currency.CAD,
    "canada": Currency.CAD,
    "canadian": Currency.CAD,
    "nzd": Currency.NZD,
    "new zealand": Currency.NZD,
}

_HIGH_IMPACT_KEYWORDS = frozenset(
    {
        "interest rate",
        "rate decision",
        "nfp",
        "non-farm",
        "nonfarm",
        "cpi",
        "inflation",
        "gdp",
        "employment change",
        "unemployment",
        "fomc",
        "ecb",
        "boe",
        "boj",
        "rba",
        "boc",
        "snb",
        "monetary policy",
        "retail sales",
        "pmi",
    }
)

_MEDIUM_IMPACT_KEYWORDS = frozenset(
    {
        "trade balance",
        "consumer confidence",
        "business confidence",
        "housing",
        "building permits",
        "industrial production",
        "manufacturing",
        "ppi",
        "producer price",
        "current account",
    }
)

# Removed regexes for actual/forecast/previous as they are no longer collected.


class InvestingRSSCalendarProvider(BaseCalendarProvider):
    """Fetch economic calendar events from Investing.com RSS feed."""

    provider_name = "investing_rss_calendar"

    def __init__(self, rss_parser: RSSParser, *, feed_url: str) -> None:
        super().__init__()
        self._rss = rss_parser
        self._feed_url = feed_url

    async def fetch(self) -> list[CalendarEvent]:
        start = time.monotonic()
        try:
            entries = await self._rss.fetch_and_parse(
                self._feed_url,
                provider_name=self.provider_name,
                category=self.category.value,
            )
            events = [
                e
                for e in (self._parse_entry(entry) for entry in entries)
                if e is not None
            ]
            self._record_success(time.monotonic() - start)
            return events
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("investing_rss_calendar_fetch_failed", error=str(exc))
            raise

    def _parse_entry(self, entry: RSSEntry) -> CalendarEvent | None:
        full_text = f"{entry.title} {entry.summary}".lower()

        currency = self._detect_currency(full_text)
        if currency is None:
            return None

        return CalendarEvent(
            event_name=entry.title.strip(),
            currency=currency,
            event_time=entry.published_at or datetime.now(UTC),
            impact=self._detect_impact(full_text),
            source="investing.com",
        )

    @staticmethod
    def _detect_currency(text: str) -> Currency | None:
        for keyword, currency in _CURRENCY_KEYWORDS.items():
            if keyword in text:
                return currency
        return None

    @staticmethod
    def _detect_impact(text: str) -> EventImpact:
        for keyword in _HIGH_IMPACT_KEYWORDS:
            if keyword in text:
                return EventImpact.HIGH
        for keyword in _MEDIUM_IMPACT_KEYWORDS:
            if keyword in text:
                return EventImpact.MEDIUM
        return EventImpact.LOW
