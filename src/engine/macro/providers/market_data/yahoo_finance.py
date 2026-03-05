from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.macro.models.provider.market_data import IntermarketSnapshot
from engine.macro.providers.market_data.base import BaseMarketDataProvider

logger = get_logger(__name__)

_YAHOO_SYMBOLS = {
    "dxy": "DX-Y.NYB",
    "gold": "GC=F",
    "silver": "SI=F",
    "oil": "CL=F",
    "us10y": "^TNX",
    "us2y": "^IRX",
    "sp500": "^GSPC",
    "vix": "^VIX",
}


class YahooFinanceProvider(BaseMarketDataProvider):
    provider_name = "yahoo_finance"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> IntermarketSnapshot:
        start = time.monotonic()
        try:
            symbols_str = ",".join(_YAHOO_SYMBOLS.values())
            headers = {
                "X-RapidAPI-Key": self._api_key,
                "X-RapidAPI-Host": "yahoo-finance15.p.rapidapi.com",
            }
            raw = await self._http.get(
                f"{self._base_url}/market/get-quotes",
                provider_name=self.provider_name,
                category=self.category.value,
                headers=headers,
                params={"symbols": symbols_str},
            )
            snapshot = self._parse_response(raw)
            self._record_success(time.monotonic() - start)
            return snapshot
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("yahoo_finance_fetch_failed", error=str(exc))
            raise

    def _parse_response(self, raw: Any) -> IntermarketSnapshot:
        prices: dict[str, float | None] = {}
        results = []
        if isinstance(raw, dict):
            results = raw.get("body", []) if isinstance(raw.get("body"), list) else []

        symbol_to_key = {v: k for k, v in _YAHOO_SYMBOLS.items()}
        for item in results:
            if isinstance(item, dict):
                sym = item.get("symbol", "")
                key = symbol_to_key.get(sym)
                if key:
                    prices[key] = self._safe_float(item.get("regularMarketPrice"))

        return IntermarketSnapshot(
            dxy_value=prices.get("dxy"),
            gold_price=prices.get("gold"),
            silver_price=prices.get("silver"),
            oil_price=prices.get("oil"),
            us10y_yield=prices.get("us10y"),
            us2y_yield=prices.get("us2y"),
            sp500=prices.get("sp500"),
            vix=prices.get("vix"),
            snapshot_at=datetime.now(UTC),
            source="yahoo_finance",
        )

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
