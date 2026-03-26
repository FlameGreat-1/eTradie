"""Commodity Proxy Provider — Iron Ore & Dairy GDT (FREE).

Fetches niche commodity prices that are not available from TwelveData:
- Iron Ore (62% Fe CFR China): AUD correlation proxy
- Dairy GDT Price Index: NZD correlation proxy

Uses free public data sources with no API key required.
Designed to be used alongside TwelveData in the intermarket collector
to enrich the IntermarketSnapshot with these niche fields.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.macro.models.provider.market_data import IntermarketSnapshot
from engine.macro.providers.market_data.base import BaseMarketDataProvider

logger = get_logger(__name__)


class CommodityProxyProvider(BaseMarketDataProvider):
    """Fetch iron ore and dairy GDT prices from free public sources.

    Returns an IntermarketSnapshot with only iron_ore and dairy_gdt
    populated. The intermarket collector merges this with TwelveData's
    snapshot to produce a complete picture.
    """

    provider_name = "commodity_proxy"

    def __init__(
        self,
        http_client: HttpClient,
        *,
        iron_ore_url: str,
        dairy_gdt_url: str,
    ) -> None:
        super().__init__()
        self._http = http_client
        self._iron_ore_url = iron_ore_url
        self._dairy_gdt_url = dairy_gdt_url

    async def fetch(self) -> IntermarketSnapshot:
        start = time.monotonic()
        try:
            iron_ore = await self._fetch_iron_ore()
            dairy_gdt = await self._fetch_dairy_gdt()

            snapshot = IntermarketSnapshot(
                iron_ore=iron_ore,
                dairy_gdt=dairy_gdt,
                snapshot_at=datetime.now(UTC),
                source="commodity_proxy",
            )
            self._record_success(time.monotonic() - start)
            return snapshot
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("commodity_proxy_fetch_failed", error=str(exc))
            raise

    async def _fetch_iron_ore(self) -> float | None:
        """Fetch iron ore price from public markets page."""
        try:
            html = await self._http.get(
                self._iron_ore_url,
                provider_name=self.provider_name,
                category=self.category.value,
                headers={"Accept": "text/html"},
                raw_response=True,
            )
            if not isinstance(html, str):
                return None

            price_match = re.search(
                r'price["\s:>]+([\d]+\.?[\d]*)'
                r'|([\d]+\.\d{2})\s*(?:USD|usd)',
                html,
                re.IGNORECASE,
            )
            if price_match:
                val = price_match.group(1) or price_match.group(2)
                return float(val)
            return None
        except Exception as exc:
            logger.warning("iron_ore_fetch_skipped", error=str(exc))
            return None

    async def _fetch_dairy_gdt(self) -> float | None:
        """Fetch dairy GDT price index from public results page."""
        try:
            html = await self._http.get(
                self._dairy_gdt_url,
                provider_name=self.provider_name,
                category=self.category.value,
                headers={"Accept": "text/html"},
                raw_response=True,
            )
            if not isinstance(html, str):
                return None

            index_match = re.search(
                r'(?:GDT\s*Price\s*Index|price\s*index)[^\d]*([\d]+\.?[\d]*)',
                html,
                re.IGNORECASE,
            )
            if index_match:
                return float(index_match.group(1))
            return None
        except Exception as exc:
            logger.warning("dairy_gdt_fetch_skipped", error=str(exc))
            return None
