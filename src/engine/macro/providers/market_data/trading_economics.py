"""TradingEconomics.com — Market Data provider (backup for TwelveData).

Provides live quotes for commodities, currencies, indices, and bonds.
Used as failover backup when TwelveData is unavailable.

API docs: https://docs.tradingeconomics.com/markets/snapshot
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

_COMMODITY_NAMES: dict[str, str] = {
    "Gold": "gold",
    "Silver": "silver",
    "Crude Oil WTI": "oil",
    "Brent Crude Oil": "oil",
    "Iron Ore": "iron_ore",
    "Copper": "copper",
    "Natural Gas": "natural_gas",
}

_INDEX_NAMES: dict[str, str] = {
    "S&P 500": "sp500",
    "VIX": "vix",
    "Dollar Index": "dxy",
    "US Dollar Index": "dxy",
}


class TradingEconomicsMarketDataProvider(BaseMarketDataProvider):
    """Fetch intermarket data from TradingEconomics.

    Acts as backup for TwelveData. Fetches commodities, index, and bond
    endpoints and merges into a single IntermarketSnapshot. Includes
    iron ore (AUD proxy) and dairy GDT (NZD proxy) when available.
    """

    provider_name = "tradingeconomics_market"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> IntermarketSnapshot:
        start = time.monotonic()
        try:
            prices: dict[str, float | None] = {}

            commodities = await self._fetch_endpoint("/markets/commodities")
            for item in commodities:
                name = str(item.get("Name", ""))
                for keyword, key in _COMMODITY_NAMES.items():
                    if keyword.lower() in name.lower() and key not in prices:
                        prices[key] = self._safe_float(item.get("Last"))

            indices = await self._fetch_endpoint("/markets/index")
            for item in indices:
                name = str(item.get("Name", ""))
                for keyword, key in _INDEX_NAMES.items():
                    if keyword.lower() in name.lower() and key not in prices:
                        prices[key] = self._safe_float(item.get("Last"))

            bonds_10y = await self._fetch_endpoint("/markets/bond", extra_params={"type": "10Y"})
            for item in bonds_10y:
                if str(item.get("Country", "")).lower() == "united states":
                    prices["us10y"] = self._safe_float(item.get("Last"))
                    break

            bonds_2y = await self._fetch_endpoint("/markets/bond", extra_params={"type": "2Y"})
            for item in bonds_2y:
                if str(item.get("Country", "")).lower() == "united states":
                    prices["us2y"] = self._safe_float(item.get("Last"))
                    break

            bonds_30y = await self._fetch_endpoint("/markets/bond", extra_params={"type": "30Y"})
            for item in bonds_30y:
                if str(item.get("Country", "")).lower() == "united states":
                    prices["us30y"] = self._safe_float(item.get("Last"))
                    break

            # Dairy GDT index for NZD correlation
            dairy_gdt: float | None = None
            try:
                agri = await self._fetch_endpoint("/markets/commodities")
                for item in agri:
                    name = str(item.get("Name", "")).lower()
                    if "dairy" in name or "milk" in name or "gdt" in name:
                        dairy_gdt = self._safe_float(item.get("Last"))
                        break
            except Exception:
                pass

            snapshot = IntermarketSnapshot(
                dxy_value=prices.get("dxy"),
                gold_price=prices.get("gold"),
                silver_price=prices.get("silver"),
                oil_price=prices.get("oil"),
                iron_ore=prices.get("iron_ore"),
                dairy_gdt=dairy_gdt,
                copper=prices.get("copper"),
                natural_gas=prices.get("natural_gas"),
                us10y_yield=prices.get("us10y"),
                us2y_yield=prices.get("us2y"),
                us30y_yield=prices.get("us30y"),
                sp500=prices.get("sp500"),
                vix=prices.get("vix"),
                snapshot_at=datetime.now(UTC),
                source="tradingeconomics",
            )
            self._record_success(time.monotonic() - start)
            return snapshot
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("te_market_fetch_failed", error=str(exc))
            raise

    async def _fetch_endpoint(
        self,
        path: str,
        *,
        extra_params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {"c": self._api_key, "f": "json"}
        if extra_params:
            params.update(extra_params)
        raw = await self._http.get(
            f"{self._base_url}{path}",
            provider_name=self.provider_name,
            category=self.category.value,
            params=params,
        )
        return raw if isinstance(raw, list) else []

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
