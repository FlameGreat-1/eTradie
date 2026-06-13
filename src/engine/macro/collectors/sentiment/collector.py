from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.risk_environment import assess_risk_environment
from engine.macro.storage.repositories.sentiment.reading import SentimentRepository
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class SentimentCollector(BaseCollector):
    """Collect sentiment data from all registered sentiment providers.

    This collector is global: it reads global COT
    cache and reads global intermarket cache for risk assessment.

    Persists sentiment readings to both database (via SentimentRepository)
    and cache for durability and fast access.
    """

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
                logger.warning(
                    "sentiment_provider_skipped",
                    provider=provider.provider_name,
                )

        # Persist sentiment readings to database for durability.
        now = datetime.now(UTC)
        if all_sentiments:
            async with self._db.session() as session:
                repo = SentimentRepository(session)
                rows = [
                    {
                        "currency": (
                            s.currency.value
                            if hasattr(s, "currency") and hasattr(s.currency, "value")
                            else str(getattr(s, "currency", ""))
                        ),
                        "source": (getattr(s, "source", "") if hasattr(s, "source") else ""),
                        "long_percentage": getattr(s, "long_percentage", 50.0),
                        "short_percentage": getattr(s, "short_percentage", 50.0),
                        "net_positioning": getattr(s, "net_positioning", 0.0),
                        "collected_at": now,
                    }
                    for s in all_sentiments
                ]
                if rows:
                    await repo.bulk_upsert(
                        rows,
                        index_elements=["currency", "source"],
                        update_fields=[
                            "long_percentage",
                            "short_percentage",
                            "net_positioning",
                            "collected_at",
                        ],
                    )

        # Read global intermarket cache for risk environment assessment.
        # Cache key is global: latest
        intermarket_raw = await self._cache.get(
            "intermarket",
            self._cache_key(),
        )
        vix: float | None = None
        us2y: float | None = None
        us10y: float | None = None
        if isinstance(intermarket_raw, dict):
            latest = intermarket_raw.get("latest") or {}
            vix = latest.get("vix")
            us2y = latest.get("us2y_yield")
            us10y = latest.get("us10y_yield")

        risk_assessment = assess_risk_environment(
            vix=vix,
            us2y_yield=us2y,
            us10y_yield=us10y,
        )

        result = {
            "sentiments": [s.model_dump(mode="json") if hasattr(s, "model_dump") else s for s in all_sentiments],
            "sources": sources,
            "risk_environment": risk_assessment.environment.value,
            "risk_assessment": risk_assessment.model_dump(mode="json"),
            "collected_at": now.isoformat(),
        }
        await self._cache.set(
            self.cache_namespace,
            self._cache_key(),
            result,
            self.cache_ttl,
        )
        self._record_items_stored(len(all_sentiments))
        return result

    def _empty_dataset(self) -> dict[str, Any]:
        return {}
