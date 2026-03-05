from __future__ import annotations

import time
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.shared.models.events import MacroBias
from engine.macro.models.processor.sentiment import CurrencySentiment
from engine.macro.providers.sentiment.base import BaseSentimentProvider

logger = get_logger(__name__)


class DailyFXProvider(BaseSentimentProvider):
    provider_name = "dailyfx"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[CurrencySentiment]:
        start = time.monotonic()
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
            raw = await self._http.get(
                f"{self._base_url}/sentiment",
                provider_name=self.provider_name,
                category=self.category.value,
                headers=headers,
            )
            data = raw if isinstance(raw, list) else raw.get("data", []) if isinstance(raw, dict) else []
            results = [s for s in (self._parse(r) for r in data) if s is not None]
            self._record_success(time.monotonic() - start)
            return results
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("dailyfx_fetch_failed", error=str(exc))
            raise

    def _parse(self, raw: dict[str, Any]) -> CurrencySentiment | None:
        symbol = str(raw.get("symbol", "")).upper()[:3]
        try:
            currency = Currency(symbol)
        except ValueError:
            return None
        long_pct = float(raw.get("longPercentage", 50))
        short_pct = float(raw.get("shortPercentage", 50))
        if long_pct > 60:
            lean = MacroBias.BULLISH
        elif short_pct > 60:
            lean = MacroBias.BEARISH
        else:
            lean = MacroBias.NEUTRAL

        return CurrencySentiment(
            currency=currency,
            institutional_long_pct=long_pct,
            institutional_short_pct=short_pct,
            positioning_lean=lean,
            signal=lean,
        )
