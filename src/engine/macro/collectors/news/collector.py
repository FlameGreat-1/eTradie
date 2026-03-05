from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.news import NewsDataSet
from engine.macro.storage.repositories.news.item import NewsRepository

logger = get_logger(__name__)


class NewsCollector(BaseCollector):
    collector_name = "news"
    cache_namespace = "news"

    async def _do_collect(self) -> NewsDataSet:
        all_items = []
        seen_hashes: set[str] = set()
        sources = []

        for provider in self._providers:
            try:
                items = await provider.fetch()
                for item in items:
                    if item.dedupe_hash and item.dedupe_hash not in seen_hashes:
                        seen_hashes.add(item.dedupe_hash)
                        all_items.append(item)
                sources.append(provider.provider_name)
            except Exception:
                logger.warning("news_provider_skipped", provider=provider.provider_name)

        async with self._db.session() as session:
            repo = NewsRepository(session)
            for item in all_items:
                if await repo.exists_by_hash(item.dedupe_hash):
                    continue
                rows = [{
                    "headline": item.headline,
                    "source": item.source,
                    "url": item.url,
                    "summary": item.summary,
                    "currencies": [c.value for c in item.currencies_mentioned],
                    "sentiment": item.sentiment.value,
                    "impact": item.impact.value,
                    "dedupe_hash": item.dedupe_hash,
                    "published_at": item.published_at,
                }]
                await repo.bulk_upsert(
                    rows,
                    index_elements=["dedupe_hash"],
                )

        dataset = NewsDataSet(
            items=all_items,
            sources=sources,
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace, "latest",
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_items))
        return dataset
