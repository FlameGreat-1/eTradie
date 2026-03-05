"""FRED (Federal Reserve Economic Data) — US Economic Data backup provider.

Free, official US economic data from the Federal Reserve Bank of St. Louis.
Fetches latest observations for key macro series (CPI, GDP, unemployment,
payrolls, retail sales).  Used as backup when TradingEconomics is unavailable.

API docs: https://fred.stlouisfed.org/docs/api/fred/
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

# FRED series IDs mapped to our EventType + human-readable names.
_FRED_SERIES: list[dict[str, Any]] = [
    {"series_id": "CPIAUCSL", "indicator": EventType.CPI, "name": "Consumer Price Index (US)", "impact": EventImpact.HIGH},
    {"series_id": "GDP", "indicator": EventType.GDP, "name": "Gross Domestic Product (US)", "impact": EventImpact.HIGH},
    {"series_id": "UNRATE", "indicator": EventType.EMPLOYMENT, "name": "Unemployment Rate (US)", "impact": EventImpact.HIGH},
    {"series_id": "PAYEMS", "indicator": EventType.NFP, "name": "Total Nonfarm Payrolls (US)", "impact": EventImpact.HIGH},
    {"series_id": "RSXFS", "indicator": EventType.RETAIL_SALES, "name": "Retail Sales (US)", "impact": EventImpact.MEDIUM},
    {"series_id": "PPIFIS", "indicator": EventType.PPI, "name": "Producer Price Index (US)", "impact": EventImpact.MEDIUM},
    {"series_id": "INDPRO", "indicator": EventType.MANUFACTURING, "name": "Industrial Production Index (US)", "impact": EventImpact.MEDIUM},
]


class FREDEconomicProvider(BaseEconomicDataProvider):
    """Fetch latest US economic indicators from the FRED API.

    Only covers United States data — serves as a backup provider for
    US releases when the primary TradingEconomics provider is unavailable.
    """

    provider_name = "fred"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[EconomicRelease]:
        start = time.monotonic()
        try:
            releases: list[EconomicRelease] = []
            for series_cfg in _FRED_SERIES:
                release = await self._fetch_series(series_cfg)
                if release is not None:
                    releases.append(release)
            self._record_success(time.monotonic() - start)
            return releases
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("fred_fetch_failed", error=str(exc))
            raise

    async def _fetch_series(self, series_cfg: dict[str, Any]) -> EconomicRelease | None:
        """Fetch the two most recent observations for a FRED series.

        We need two observations so we can populate both ``actual``
        (latest) and ``previous`` (prior period).  FRED does not provide
        forecast/consensus values — those fields are left as ``None``.
        """
        try:
            raw = await self._http.get(
                f"{self._base_url}/series/observations",
                provider_name=self.provider_name,
                category=self.category.value,
                params={
                    "series_id": series_cfg["series_id"],
                    "api_key": self._api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": "2",
                },
            )
            observations = raw.get("observations", []) if isinstance(raw, dict) else []
            if not observations:
                return None

            actual = self._parse_float(observations[0].get("value"))
            previous = self._parse_float(observations[1].get("value")) if len(observations) > 1 else None

            date_str = str(observations[0].get("date", ""))
            try:
                release_time = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
            except (ValueError, TypeError):
                release_time = datetime.now(UTC)

            return EconomicRelease(
                currency=Currency.USD,
                indicator=series_cfg["indicator"],
                indicator_name=series_cfg["name"],
                actual=actual,
                forecast=None,
                previous=previous,
                surprise=None,
                surprise_direction=compute_surprise_direction(actual, None),
                impact=series_cfg["impact"],
                release_time=release_time,
                source="fred",
            )
        except Exception:
            logger.warning("fred_series_skipped", series_id=series_cfg["series_id"])
            return None

    @staticmethod
    def _parse_float(val: Any) -> float | None:
        if val is None or val == "" or val == ".":
            return None
        try:
            return float(str(val).replace(",", ""))
        except (ValueError, TypeError):
            return None
