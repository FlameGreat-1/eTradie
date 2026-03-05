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

_IMPACT_MAP = {"High": EventImpact.HIGH, "Medium": EventImpact.MEDIUM, "Low": EventImpact.LOW}

_INDICATOR_MAP: dict[str, EventType] = {
    "CPI": EventType.CPI,
    "PPI": EventType.PPI,
    "Non-Farm": EventType.NFP,
    "NFP": EventType.NFP,
    "GDP": EventType.GDP,
    "PMI": EventType.PMI,
    "Retail Sales": EventType.RETAIL_SALES,
    "Employment": EventType.EMPLOYMENT,
    "Unemployment": EventType.EMPLOYMENT,
}


class ForexFactoryProvider(BaseEconomicDataProvider):
    provider_name = "forex_factory"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str = "") -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url
        self._api_key = api_key

    async def fetch(self) -> list[EconomicRelease]:
        start = time.monotonic()
        try:
            raw = await self._http.get(
                self._base_url,
                provider_name=self.provider_name,
                category=self.category.value,
            )
            if not isinstance(raw, list):
                raw = []
            releases = [r for r in (self._parse_event(e) for e in raw) if r is not None]
            self._record_success(time.monotonic() - start)
            return releases
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("forex_factory_fetch_failed", error=str(exc))
            raise

    def _parse_event(self, raw: dict[str, Any]) -> EconomicRelease | None:
        title = raw.get("title", "")
        country = raw.get("country", "").upper()
        try:
            currency = Currency(country)
        except ValueError:
            return None

        impact = _IMPACT_MAP.get(raw.get("impact", ""), EventImpact.LOW)
        indicator = self._classify_indicator(title)

        actual = self._parse_float(raw.get("actual"))
        forecast = self._parse_float(raw.get("forecast"))
        previous = self._parse_float(raw.get("previous"))
        surprise = (actual - forecast) if actual is not None and forecast is not None else None

        date_str = raw.get("date", "")
        try:
            release_time = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            release_time = datetime.now(UTC)

        return EconomicRelease(
            currency=currency,
            indicator=indicator,
            indicator_name=title,
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=surprise,
            surprise_direction=compute_surprise_direction(actual, forecast),
            impact=impact,
            release_time=release_time,
            source="forex_factory",
        )

    @staticmethod
    def _classify_indicator(title: str) -> EventType:
        for keyword, event_type in _INDICATOR_MAP.items():
            if keyword.lower() in title.lower():
                return event_type
        return EventType.OTHER

    @staticmethod
    def _parse_float(val: Any) -> float | None:
        if val is None or val == "":
            return None
        try:
            cleaned = str(val).replace("%", "").replace("K", "e3").replace("M", "e6").replace("B", "e9")
            return float(cleaned)
        except (ValueError, TypeError):
            return None
