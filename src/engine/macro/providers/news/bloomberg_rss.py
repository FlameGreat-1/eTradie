from __future__ import annotations

import time

from engine.shared.logging import get_logger
from engine.shared.rss import RSSParser
from engine.macro.models.provider.news import NewsItem
from engine.macro.providers.news.base import (
    BaseNewsProvider,
    classify_impact,
    compute_dedupe_hash,
    extract_currencies,
)

logger = get_logger(__name__)


class BloombergRSSProvider(BaseNewsProvider):
    provider_name = "bloomberg_rss"

    def __init__(self, rss_parser: RSSParser, *, feed_url: str) -> None:
        super().__init__()
        self._rss = rss_parser
        self._feed_url = feed_url

    async def fetch(self) -> list[NewsItem]:
        start = time.monotonic()
        try:
            entries = await self._rss.fetch_and_parse(
                self._feed_url,
                provider_name=self.provider_name,
                category=self.category.value,
            )
            items = []
            for entry in entries:
                full_text = f"{entry.title} {entry.summary}"
                items.append(
                    NewsItem(
                        headline=entry.title,
                        source="bloomberg",
                        url=entry.link,
                        summary=entry.summary[:1000],
                        currencies_mentioned=extract_currencies(full_text),
                        impact=classify_impact(full_text),
                        published_at=entry.published_at,
                        dedupe_hash=compute_dedupe_hash("bloomberg", entry.title),
                    ),
                )
            self._record_success(time.monotonic() - start)
            return items
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("bloomberg_rss_fetch_failed", error=str(exc))
            raise
