from __future__ import annotations

import time
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.macro.models.provider.sentiment import SentimentReading
from engine.macro.providers.sentiment.base import BaseSentimentProvider

logger = get_logger(__name__)


class ReutersSentimentProvider(BaseSentimentProvider):
    provider_name = "reuters_sentiment"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[SentimentReading]:
        start = time.monotonic()
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
            raw = await self._http.get(
                f"{self._base_url}/sentiment/fx",
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
            logger.error("reuters_sentiment_fetch_failed", error=str(exc))
            raise

    def _parse(self, raw: dict[str, Any]) -> SentimentReading | None:
        symbol = str(raw.get("currency", "")).upper()[:3]
        try:
            currency = Currency(symbol)
        except ValueError:
            return None
        long_pct = float(raw.get("long_pct", 50))
        short_pct = float(raw.get("short_pct", 50))
        return SentimentReading(
            currency=currency,
            source="reuters",
            long_percentage=long_pct,
            short_percentage=short_pct,
            net_positioning=long_pct - short_pct,
        )
