"""COT-Derived Sentiment Provider (FREE).

Converts Commitment of Traders positioning data (already collected by the
COT collector) into SentimentReading objects per currency.  Speculative
(non-commercial) net positioning is the most reliable free proxy for
market sentiment across all 8 major currencies.

Reads from the global Redis COT cache, so this provider has zero
external API calls and zero cost.
"""

from __future__ import annotations

import time
from typing import Any

from engine.shared.cache import RedisCache
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.macro.models.provider.sentiment import SentimentReading
from engine.macro.providers.sentiment.base import BaseSentimentProvider

logger = get_logger(__name__)

# COT currencies we track (matches CFTC provider output).
_COT_CURRENCIES: set[str] = {
    Currency.USD.value,
    Currency.EUR.value,
    Currency.GBP.value,
    Currency.JPY.value,
    Currency.CHF.value,
    Currency.AUD.value,
    Currency.CAD.value,
    Currency.NZD.value,
}


class COTDerivedSentimentProvider(BaseSentimentProvider):
    """Derive sentiment readings from cached COT positioning data.

    Non-commercial (speculative) net positioning is converted to a
    long/short percentage split.  A large net long position indicates
    bullish sentiment; a large net short indicates bearish sentiment.

    The percentile rank from the COT enrichment is used to normalize
    the reading into a 0-100 scale where 50 is neutral.

    IMPORTANT: This provider reads global COT cache data.
    """

    provider_name = "cot_derived_sentiment"

    def __init__(self, cache: RedisCache) -> None:
        super().__init__()
        self._cache = cache

    async def fetch(self) -> list[SentimentReading]:
        """Fetch sentiment readings from global COT cache."""
        start = time.monotonic()
        try:
            # Read global COT cache: key is "latest"
            cache_key = "latest"
            cot_raw = await self._cache.get("cot", cache_key)
            if not isinstance(cot_raw, dict):
                self._record_success(time.monotonic() - start)
                return []

            positions = cot_raw.get("latest_positions", [])
            if not isinstance(positions, list):
                self._record_success(time.monotonic() - start)
                return []

            readings: list[SentimentReading] = []
            for pos in positions:
                if not isinstance(pos, dict):
                    continue

                currency_str = pos.get("currency", "")
                if currency_str not in _COT_CURRENCIES:
                    continue

                try:
                    currency = Currency(currency_str)
                except ValueError:
                    continue

                percentile = pos.get("percentile_rank", 50.0)
                net = pos.get("non_commercial_net", 0)

                # Convert percentile rank to long/short split.
                # percentile_rank is 0-100 where high = extreme positioning.
                # If net > 0, high percentile = very long.
                # If net < 0, high percentile = very short.
                if net >= 0:
                    long_pct = min(50.0 + (percentile / 2.0), 100.0)
                else:
                    long_pct = max(50.0 - (percentile / 2.0), 0.0)

                short_pct = 100.0 - long_pct
                net_positioning = round(long_pct - short_pct, 2)

                readings.append(
                    SentimentReading(
                        currency=currency,
                        source="cot_positioning",
                        long_percentage=round(long_pct, 2),
                        short_percentage=round(short_pct, 2),
                        net_positioning=net_positioning,
                    )
                )

            self._record_success(time.monotonic() - start)
            return readings
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "cot_derived_sentiment_failed",
                error=str(exc),
            )
            raise
