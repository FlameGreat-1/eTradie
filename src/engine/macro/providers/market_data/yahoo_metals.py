"""Yahoo Finance metals provider -- gold & silver spot-futures (FREE).

FRED does not expose a usable gold/silver series, so this provider sources them
from Yahoo Finance's free chart endpoint, which returns clean JSON with the
latest price:

  https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=1d
  https://query1.finance.yahoo.com/v8/finance/chart/SI=F?interval=1d&range=1d

``GC=F`` is COMEX gold futures, ``SI=F`` is COMEX silver futures (both USD).
The price is ``result[0].meta.regularMarketPrice``; we fall back to the latest
``indicators.quote[0].close`` if the meta field is absent.

Returns an IntermarketSnapshot with ONLY gold_price / silver_price set; the
intermarket collector merges it with the FRED snapshot via _merge_snapshots
(first non-None per field wins). Best-effort: any failure leaves both None so
the FRED-sourced fields are never affected.

Yahoo rate-limits requests with no User-Agent, so one is sent. No API key.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.macro.models.provider.market_data import IntermarketSnapshot
from engine.macro.providers.market_data.base import BaseMarketDataProvider
from engine.shared.http import HttpClient
from engine.shared.logging import get_logger

logger = get_logger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; etradie-macro/1.0; +https://www.cftc.gov)"


class YahooMetalsProvider(BaseMarketDataProvider):
    """Fetch gold and silver prices from Yahoo Finance."""

    provider_name = "yahoo_metals"

    def __init__(self, http_client: HttpClient, *, base_url: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")

    async def fetch(self) -> IntermarketSnapshot:
        start = time.monotonic()
        try:
            gold = await self._fetch_quote("GC=F")
            silver = await self._fetch_quote("SI=F")

            snapshot = IntermarketSnapshot(
                gold_price=gold,
                silver_price=silver,
                snapshot_at=datetime.now(UTC),
                source=self.provider_name,
            )
            self._record_success(time.monotonic() - start)
            return snapshot
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "yahoo_metals_fetch_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            raise

    async def _fetch_quote(self, symbol: str) -> float | None:
        """Return the latest price for a Yahoo chart symbol, or None.

        Reads result[0].meta.regularMarketPrice, falling back to the last
        non-null close in indicators.quote[0].close. A per-symbol failure is
        isolated so one bad symbol leaves only that metal None.
        """
        try:
            raw = await self._http.get(
                f"{self._base_url}/v8/finance/chart/{symbol}",
                provider_name=self.provider_name,
                category=self.category.value,
                params={"interval": "1d", "range": "1d"},
                headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
            )
            if not isinstance(raw, dict):
                return None

            results = (raw.get("chart", {}) or {}).get("result") or []
            if not results or not isinstance(results[0], dict):
                return None
            result = results[0]

            meta = result.get("meta") or {}
            price = self._safe_float(meta.get("regularMarketPrice"))
            if price is not None:
                return price

            # Fallback: latest non-null close.
            indicators = result.get("indicators") or {}
            quotes = indicators.get("quote") or []
            if quotes and isinstance(quotes[0], dict):
                closes = quotes[0].get("close") or []
                for c in reversed(closes):
                    val = self._safe_float(c)
                    if val is not None:
                        return val
            return None
        except Exception as exc:
            logger.warning(
                "yahoo_metals_symbol_skipped",
                extra={
                    "symbol": symbol,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return None

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
