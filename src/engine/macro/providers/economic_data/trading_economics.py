"""TradingEconomics.com — Economic Releases provider.

Uses the same calendar endpoint but focuses on extracting economic release data
with actual/forecast/previous values and computing surprise direction.  This is
the institutional-grade replacement for Forex Factory and Investing.com
economic data feeds.

API docs: https://docs.tradingeconomics.com/economic_calendar/snapshot
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact, EventType
from engine.macro.models.provider.economic import EconomicRelease
from engine.macro.providers.economic_data.base import (
    BaseEconomicDataProvider,
    compute_surprise_direction,
)

logger = get_logger(__name__)

# TradingEconomics Importance: 1=Low, 2=Medium, 3=High
_IMPORTANCE_MAP: dict[int, EventImpact] = {
    3: EventImpact.HIGH,
    2: EventImpact.MEDIUM,
    1: EventImpact.LOW,
}

# Map TE Category field → EventType enum.
# TE uses human-readable category names; we match on substrings.
_CATEGORY_MAP: dict[str, EventType] = {
    "Interest Rate": EventType.RATE_DECISION,
    "Inflation Rate": EventType.CPI,
    "CPI": EventType.CPI,
    "Consumer Price": EventType.CPI,
    "PPI": EventType.PPI,
    "Producer Price": EventType.PPI,
    "Non Farm Payrolls": EventType.NFP,
    "Nonfarm Payrolls": EventType.NFP,
    "GDP": EventType.GDP,
    "Gross Domestic Product": EventType.GDP,
    "GDP Growth Rate": EventType.GDP,
    "PMI": EventType.PMI,
    "Manufacturing PMI": EventType.PMI,
    "Services PMI": EventType.PMI,
    "Retail Sales": EventType.RETAIL_SALES,
    "Employment": EventType.EMPLOYMENT,
    "Unemployment Rate": EventType.EMPLOYMENT,
    "Unemployment": EventType.EMPLOYMENT,
    "Trade Balance": EventType.TRADE_BALANCE,
    "Consumer Confidence": EventType.CONSUMER_CONFIDENCE,
    "Housing": EventType.HOUSING,
    "Building Permits": EventType.HOUSING,
    "Manufacturing": EventType.MANUFACTURING,
    "Industrial Production": EventType.MANUFACTURING,
}

# Map TradingEconomics country names → Currency enum values.
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


class TradingEconomicsEconomicProvider(BaseEconomicDataProvider):
    """Fetch economic releases with actuals/forecasts from TradingEconomics."""

    provider_name = "tradingeconomics"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[EconomicRelease]:
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
            releases = [r for r in (self._parse_event(e) for e in raw) if r is not None]
            self._record_success(time.monotonic() - start)
            return releases
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("te_economic_fetch_failed", error=str(exc))
            raise

    def _parse_event(self, raw: dict[str, Any]) -> EconomicRelease | None:
        country = str(raw.get("Country", ""))
        currency = _COUNTRY_CURRENCY_MAP.get(country)
        if currency is None:
            return None

        category = str(raw.get("Category", ""))
        event_name = str(raw.get("Event", ""))
        indicator = self._classify_indicator(category, event_name)

        importance = raw.get("Importance", 1)
        try:
            importance_int = int(importance)
        except (ValueError, TypeError):
            importance_int = 1
        impact = _IMPORTANCE_MAP.get(importance_int, EventImpact.LOW)

        actual = self._parse_float(raw.get("Actual"))
        forecast = self._parse_float(raw.get("Forecast"))
        previous = self._parse_float(raw.get("Previous"))
        surprise = (actual - forecast) if actual is not None and forecast is not None else None

        date_str = str(raw.get("Date", ""))
        try:
            release_time = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            release_time = datetime.now(UTC)

        return EconomicRelease(
            currency=currency,
            indicator=indicator,
            indicator_name=event_name,
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=surprise,
            surprise_direction=compute_surprise_direction(actual, forecast),
            impact=impact,
            release_time=release_time,
            source="tradingeconomics",
        )

    @staticmethod
    def _classify_indicator(category: str, event_name: str) -> EventType:
        """Match TE Category or Event name to our EventType enum."""
        combined = f"{category} {event_name}"
        for keyword, event_type in _CATEGORY_MAP.items():
            if keyword.lower() in combined.lower():
                return event_type
        return EventType.OTHER

    @staticmethod
    def _parse_float(val: Any) -> float | None:
        if val is None or val == "":
            return None
        try:
            cleaned = str(val).replace("%", "").replace(",", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
