from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.models.collector.news import NewsDataSet
from engine.macro.collectors.base import BaseCollector

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
