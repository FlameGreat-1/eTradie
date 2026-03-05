from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.macro.models.provider.market_data import IntermarketSnapshot
from engine.macro.providers.market_data.base import BaseMarketDataProvider

logger = get_logger(__name__)

_SYMBOLS = {
    "dxy": "DXY",
    "gold": "XAU/USD",
    "silver": "XAG/USD",
    "oil": "CL",
    "sp500": "SPX",
    "vix": "VIX",
}


class TwelveDataProvider(BaseMarketDataProvider):
    provider_name = "twelve_data"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> IntermarketSnapshot:
        start = time.monotonic()
        try:
            symbols_str = ",".join(_SYMBOLS.values())
            raw = await self._http.get(
                f"{self._base_url}/price",
                provider_name=self.provider_name,
                category=self.category.value,
                params={"symbol": symbols_str, "apikey": self._api_key},
            )
            snapshot = self._parse_response(raw)
            self._record_success(time.monotonic() - start)
            return snapshot
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("twelve_data_fetch_failed", error=str(exc))
            raise

    def _parse_response(self, raw: Any) -> IntermarketSnapshot:
        prices: dict[str, float | None] = {}
        if isinstance(raw, dict):
            for key, symbol in _SYMBOLS.items():
                entry = raw.get(symbol, {})
                if isinstance(entry, dict):
                    prices[key] = self._safe_float(entry.get("price"))
                else:
                    prices[key] = None

        return IntermarketSnapshot(
            dxy_value=prices.get("dxy"),
            gold_price=prices.get("gold"),
            silver_price=prices.get("silver"),
            oil_price=prices.get("oil"),
            sp500=prices.get("sp500"),
            vix=prices.get("vix"),
            snapshot_at=datetime.now(UTC),
            source="twelve_data",
        )

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
