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


class InvestingComProvider(BaseEconomicDataProvider):
    provider_name = "investing_com"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[EconomicRelease]:
        start = time.monotonic()
        try:
            headers = {
                "X-RapidAPI-Key": self._api_key,
                "X-RapidAPI-Host": "investing-cryptocurrency-markets.p.rapidapi.com",
            }
            raw = await self._http.get(
                f"{self._base_url}/economic-calendar",
                provider_name=self.provider_name,
                category=self.category.value,
                headers=headers,
            )
            events = raw if isinstance(raw, list) else raw.get("data", []) if isinstance(raw, dict) else []
            releases = [r for r in (self._parse_event(e) for e in events) if r is not None]
            self._record_success(time.monotonic() - start)
            return releases
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("investing_com_fetch_failed", error=str(exc))
            raise

    def _parse_event(self, raw: dict[str, Any]) -> EconomicRelease | None:
        country = str(raw.get("country", "")).upper()[:3]
        try:
            currency = Currency(country)
        except ValueError:
            return None

        actual = self._safe_float(raw.get("actual"))
        forecast = self._safe_float(raw.get("forecast"))
        previous = self._safe_float(raw.get("previous"))
        surprise = (actual - forecast) if actual is not None and forecast is not None else None

        try:
            release_time = datetime.fromisoformat(str(raw.get("date", ""))).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            release_time = datetime.now(UTC)

        return EconomicRelease(
            currency=currency,
            indicator=EventType.OTHER,
            indicator_name=str(raw.get("event", "")),
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=surprise,
            surprise_direction=compute_surprise_direction(actual, forecast),
            impact=EventImpact.MEDIUM,
            release_time=release_time,
            source="investing_com",
        )

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None or val == "":
            return None
        try:
            return float(str(val).replace("%", "").replace(",", ""))
        except (ValueError, TypeError):
            return None
