from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector

logger = get_logger(__name__)


class SentimentCollector(BaseCollector):
    collector_name = "sentiment"
    cache_namespace = "sentiment"

    async def _do_collect(self) -> dict[str, Any]:
        all_sentiments = []
        sources = []
        for provider in self._providers:
            try:
                data = await provider.fetch()
                all_sentiments.extend(data)
                sources.append(provider.provider_name)
            except Exception:
                logger.warning("sentiment_provider_skipped", provider=provider.provider_name)

        result = {
            "sentiments": [
                s.model_dump(mode="json") if hasattr(s, "model_dump") else s
                for s in all_sentiments
            ],
            "sources": sources,
            "collected_at": datetime.now(UTC).isoformat(),
        }
        await self._cache.set(
            self.cache_namespace, "latest",
            result,
            self.cache_ttl,
        )
        self._record_items_stored(len(all_sentiments))
        return result
