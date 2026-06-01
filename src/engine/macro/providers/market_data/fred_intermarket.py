"""FRED-backed intermarket / market-data provider.

Replaces the TwelveData provider (whose USDX/US02Y/SPX/VIX/CL... tickers never
returned data on the configured plan) and the HTML commodity-proxy scraper
(fragile regex, no reliable output). Uses the same FRED API + parse shape the
central-bank rate providers already use successfully.

Series fetched (all free daily series on the St. Louis Fed API):
  - DTWEXBGS  Broad trade-weighted US Dollar Index (USD strength proxy)
  - DGS2 / DGS10 / DGS30  US Treasury constant-maturity yields (2/10/30y)
  - VIXCLS    CBOE Volatility Index (VIX)
  - SP500     S&P 500 index
  - DCOILWTICO  WTI crude oil spot price

Fields the snapshot also supports but FRED does not reliably serve here
(gold, silver, copper, natural gas, iron ore, dairy) are left None -- they are
nullable on IntermarketSnapshot and will be wired from a verified source later
rather than guessed.

Note on DXY: DTWEXBGS is the BROAD trade-weighted dollar index (~119 scale),
not the ICE "DXY" futures contract (~104 scale). They track the same thing
(USD strength); the DXY collector computes momentum/trend/bias from RELATIVE
change, so direction is correct regardless of the absolute scale.

FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.macro.models.provider.market_data import IntermarketSnapshot
from engine.macro.providers.market_data.base import BaseMarketDataProvider

logger = get_logger(__name__)

# snapshot field -> FRED series id. All operator-verified to return real values.
#
# Daily series: DTWEXBGS, DGS2/10/30, VIXCLS, SP500, DCOILWTICO, DHHNGSP.
# Monthly IMF series (slower cadence, fine for macro context): PIORECRUSDM
# (iron ore, $/tonne), PCOPPUSDM (copper, $/tonne).
#
# Gold and silver come from the Yahoo metals provider (FRED has no usable
# series for them). Dairy has no verified source and is left None (never
# guessed). IR14260 was rejected as a "gold" source: it returns ~271, which is
# NOT a gold price.
_SERIES: dict[str, str] = {
    "dxy_value": "DTWEXBGS",
    "us2y_yield": "DGS2",
    "us10y_yield": "DGS10",
    "us30y_yield": "DGS30",
    "vix": "VIXCLS",
    "sp500": "SP500",
    "oil_price": "DCOILWTICO",
    "natural_gas": "DHHNGSP",
    "iron_ore": "PIORECRUSDM",
    "copper": "PCOPPUSDM",
}


class FREDIntermarketProvider(BaseMarketDataProvider):
    """Fetch intermarket data points from the FRED API.

    Each field is fetched as the latest non-missing observation of its FRED
    series. A per-series failure is isolated (logged, left None) so one bad
    series never empties the whole snapshot. A missing API key yields an
    all-None snapshot (non-fatal), matching the rate providers' behaviour.
    """

    provider_name = "fred_intermarket"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> IntermarketSnapshot:
        start = time.monotonic()

        if not self._api_key:
            logger.warning(
                "fred_intermarket_api_key_missing",
                extra={"action": "skipping - no FRED API key configured"},
            )
            self._record_success(time.monotonic() - start)
            return IntermarketSnapshot(
                snapshot_at=datetime.now(UTC), source=self.provider_name
            )

        try:
            values: dict[str, float | None] = {}
            for field, series_id in _SERIES.items():
                values[field] = await self._fetch_latest(series_id)

            snapshot = IntermarketSnapshot(
                dxy_value=values.get("dxy_value"),
                us2y_yield=values.get("us2y_yield"),
                us10y_yield=values.get("us10y_yield"),
                us30y_yield=values.get("us30y_yield"),
                vix=values.get("vix"),
                sp500=values.get("sp500"),
                oil_price=values.get("oil_price"),
                natural_gas=values.get("natural_gas"),
                iron_ore=values.get("iron_ore"),
                copper=values.get("copper"),
                snapshot_at=datetime.now(UTC),
                source=self.provider_name,
            )
            self._record_success(time.monotonic() - start)
            return snapshot
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "fred_intermarket_fetch_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            raise

    async def _fetch_latest(self, series_id: str) -> float | None:
        """Return the latest non-missing observation value for a FRED series.

        FRED encodes a missing observation as "."; we walk newest-first and
        return the first parseable value. A per-series error is isolated so a
        single bad series leaves only that field None.
        """
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
                    "limit": "5",
                },
            )
            observations = (
                raw.get("observations", []) if isinstance(raw, dict) else []
            )
            for obs in observations:
                value = self._parse_float(obs.get("value"))
                if value is not None:
                    return value
            return None
        except Exception as exc:
            logger.warning(
                "fred_intermarket_series_skipped",
                extra={
                    "series_id": series_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return None

    @staticmethod
    def _parse_float(val: Any) -> float | None:
        if val is None or val == "" or val == ".":
            return None
        try:
            return float(str(val).replace(",", ""))
        except (ValueError, TypeError):
            return None
