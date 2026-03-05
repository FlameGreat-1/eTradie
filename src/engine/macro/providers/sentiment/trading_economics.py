"""TradingEconomics.com — Sentiment / Positioning provider.

Uses TradingEconomics' country-level confidence indicators (Consumer Confidence,
Business Confidence) as sentiment proxies.  These are institutional-grade
indicators sourced from official statistical agencies — far more reliable than
DailyFX SSI or Reuters sentiment which had limited/no public API access.

API docs: https://docs.tradingeconomics.com/indicators/snapshot
"""

from __future__ import annotations

import time
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.macro.models.provider.sentiment import SentimentReading
from engine.macro.providers.sentiment.base import BaseSentimentProvider

logger = get_logger(__name__)

# Countries we track, mapped to Currency enum.
_COUNTRY_CURRENCY_MAP: dict[str, Currency] = {
    "United States": Currency.USD,
    "Euro Area": Currency.EUR,
    "United Kingdom": Currency.GBP,
    "Japan": Currency.JPY,
    "Switzerland": Currency.CHF,
    "Australia": Currency.AUD,
    "Canada": Currency.CAD,
    "New Zealand": Currency.NZD,
}

# The TE indicator categories we use for sentiment.
_SENTIMENT_CATEGORIES = {"Consumer Confidence", "Business Confidence"}

# Comma-separated country list for the TE API request.
_COUNTRIES_PARAM = ",".join(
    c.lower().replace(" ", "%20") for c in _COUNTRY_CURRENCY_MAP
)


class TradingEconomicsSentimentProvider(BaseSentimentProvider):
    """Derive sentiment readings from TradingEconomics confidence indicators.

    Consumer Confidence and Business Confidence are used as proxies for
    market sentiment.  Values above 50 indicate optimism (bullish lean),
    values below 50 indicate pessimism (bearish lean).  The net positioning
    is computed as a normalised delta from the neutral 50 midpoint.
    """

    provider_name = "tradingeconomics_sentiment"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[SentimentReading]:
        start = time.monotonic()
        try:
            # Fetch all indicators for our tracked countries
            countries_path = ",".join(
                c.lower().replace(" ", "%20") for c in _COUNTRY_CURRENCY_MAP
            )
            raw = await self._http.get(
                f"{self._base_url}/country/{countries_path}",
                provider_name=self.provider_name,
                category=self.category.value,
                params={"c": self._api_key, "f": "json"},
            )
            if not isinstance(raw, list):
                raw = []

            # Filter to only sentiment-relevant categories and aggregate per currency
            currency_scores: dict[Currency, list[float]] = {}
            for item in raw:
                reading = self._extract_confidence(item)
                if reading is not None:
                    currency, value = reading
                    currency_scores.setdefault(currency, []).append(value)

            # Build SentimentReading per currency
            results: list[SentimentReading] = []
            for currency, scores in currency_scores.items():
                avg_confidence = sum(scores) / len(scores)
                # Normalise: confidence > 50 = bullish lean, < 50 = bearish lean
                # Express as long/short percentages for compatibility with model
                long_pct = min(max(avg_confidence, 0.0), 100.0)
                short_pct = 100.0 - long_pct
                results.append(
                    SentimentReading(
                        currency=currency,
                        source="tradingeconomics",
                        long_percentage=round(long_pct, 2),
                        short_percentage=round(short_pct, 2),
                        net_positioning=round(long_pct - short_pct, 2),
                    ),
                )

            self._record_success(time.monotonic() - start)
            return results
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("te_sentiment_fetch_failed", error=str(exc))
            raise

    def _extract_confidence(self, item: dict[str, Any]) -> tuple[Currency, float] | None:
        """Extract a confidence score from a TE indicator row, if relevant."""
        category = str(item.get("Category", ""))
        if category not in _SENTIMENT_CATEGORIES:
            return None

        country = str(item.get("Country", ""))
        currency = _COUNTRY_CURRENCY_MAP.get(country)
        if currency is None:
            return None

        value = item.get("LatestValue")
        if value is None:
            return None
        try:
            return currency, float(value)
        except (ValueError, TypeError):
            return None
