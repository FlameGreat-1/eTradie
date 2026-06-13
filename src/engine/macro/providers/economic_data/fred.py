"""FRED (Federal Reserve Economic Data) -- US Economic Data backup provider.

Free, official US economic data from the Federal Reserve Bank of St. Louis.
Fetches latest observations for key macro series (CPI, GDP, unemployment,
payrolls, retail sales).  Used as backup when TradingEconomics is unavailable.

API docs: https://fred.stlouisfed.org/docs/api/fred/
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.macro.models.provider.economic import EconomicRelease
from engine.macro.providers.economic_data.base import BaseEconomicDataProvider
from engine.shared.http import HttpClient
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Each entry is the FRED series id and the LLM-facing display name.
# Other classification metadata (impact, inflation type, indicator
# enum) was removed in the 2026-05 EconomicRelease cleanup; nothing
# downstream consumed it.
_FRED_SERIES: list[dict[str, Any]] = [
    {"series_id": "CPIAUCSL", "name": "Consumer Price Index (US)"},
    {"series_id": "CPILFESL", "name": "Core CPI ex Food & Energy (US)"},
    {"series_id": "PCEPI", "name": "PCE Price Index (US)"},
    {"series_id": "PCEPILFE", "name": "Core PCE ex Food & Energy (US)"},
    {"series_id": "GDP", "name": "Gross Domestic Product (US)"},
    {"series_id": "UNRATE", "name": "Unemployment Rate (US)"},
    {"series_id": "PAYEMS", "name": "Total Nonfarm Payrolls (US)"},
    {"series_id": "RSXFS", "name": "Retail Sales (US)"},
    {"series_id": "PPIFIS", "name": "Producer Price Index (US)"},
    {"series_id": "INDPRO", "name": "Industrial Production Index (US)"},
]


class FREDEconomicProvider(BaseEconomicDataProvider):
    """Fetch latest US economic indicators from the FRED API.

    Only covers United States data. Serves as a backup provider for
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

        if not self._api_key:
            logger.warning(
                "fred_api_key_missing",
                extra={"action": "skipping FRED provider - no API key configured"},
            )
            return []

        try:
            releases: list[EconomicRelease] = []
            for series_cfg in _FRED_SERIES:
                series_releases = await self._fetch_series(series_cfg)
                releases.extend(series_releases)

            if not releases:
                logger.warning(
                    "fred_no_releases_fetched",
                    extra={
                        "series_attempted": len(_FRED_SERIES),
                        "api_key_present": bool(self._api_key),
                    },
                )

            self._record_success(time.monotonic() - start)
            return releases
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "fred_fetch_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            raise

    async def _fetch_series(self, series_cfg: dict[str, Any]) -> list[EconomicRelease]:
        """Fetch the most recent observations for a FRED series.

        We fetch 6 observations (~3 months for monthly data) so the
        LLM has enough historical context to identify trends, not
        just a single latest + previous pair.
        """
        series_id = series_cfg["series_id"]
        try:
            raw = await self._http.get(
                f"{self._base_url}/series/observations",
                provider_name=self.provider_name,
                category=self.category.value,
                params={
                    "series_id": series_id,
                    "api_key": self._api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": "6",
                },
            )
            observations = raw.get("observations", []) if isinstance(raw, dict) else []
            if not observations:
                logger.debug(
                    "fred_series_no_observations",
                    extra={"series_id": series_id},
                )
                return []

            releases: list[EconomicRelease] = []
            for i, obs in enumerate(observations):
                actual = self._parse_float(obs.get("value"))
                if actual is None:
                    continue

                previous = self._parse_float(observations[i + 1].get("value")) if i + 1 < len(observations) else None

                date_str = str(obs.get("date", ""))
                try:
                    release_time = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
                except (ValueError, TypeError):
                    release_time = datetime.now(UTC)

                releases.append(
                    EconomicRelease(
                        indicator_name=series_cfg["name"],
                        actual=actual,
                        previous=previous,
                        release_time=release_time,
                    )
                )

            return releases
        except Exception as exc:
            logger.warning(
                "fred_series_skipped",
                extra={
                    "series_id": series_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return []

    @staticmethod
    def _parse_float(val: Any) -> float | None:
        if val is None or val in {"", "."}:
            return None
        try:
            return float(str(val).replace(",", ""))
        except (ValueError, TypeError):
            return None
