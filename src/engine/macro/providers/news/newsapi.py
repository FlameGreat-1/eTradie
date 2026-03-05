from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.macro.models.provider.news import NewsItem
from engine.macro.providers.news.base import (
    BaseNewsProvider,
    classify_impact,
    compute_dedupe_hash,
    extract_currencies,
)

logger = get_logger(__name__)


class NewsAPIProvider(BaseNewsProvider):
    provider_name = "newsapi"

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[NewsItem]:
        start = time.monotonic()
        try:
            raw = await self._http.get(
                f"{self._base_url}/everything",
                provider_name=self.provider_name,
                category=self.category.value,
                params={
                    "apiKey": self._api_key,
                    "q": "forex OR central bank OR interest rate OR inflation OR GDP",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": "50",
                },
            )
            articles = raw.get("articles", []) if isinstance(raw, dict) else []
            items = [self._parse(a) for a in articles if isinstance(a, dict)]
            self._record_success(time.monotonic() - start)
            return items
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("newsapi_fetch_failed", error=str(exc))
            raise

    def _parse(self, article: dict[str, Any]) -> NewsItem:
        headline = str(article.get("title", ""))
        description = str(article.get("description", ""))
        full_text = f"{headline} {description}"
        try:
            pub = datetime.fromisoformat(str(article.get("publishedAt", "")).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pub = datetime.now(UTC)

        return NewsItem(
            headline=headline,
            source=str(article.get("source", {}).get("name", "newsapi")),
            url=str(article.get("url", "")),
            summary=description[:1000],
            currencies_mentioned=extract_currencies(full_text),
            impact=classify_impact(full_text),
            published_at=pub,
            dedupe_hash=compute_dedupe_hash("newsapi", headline),
        )
