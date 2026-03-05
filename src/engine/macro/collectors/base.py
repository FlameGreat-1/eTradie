from __future__ import annotations

import abc
import time
from typing import Any, TypeVar

from engine.shared.cache import RedisCache
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    COLLECTOR_ITEMS_STORED,
    COLLECTOR_RUN_DURATION,
    COLLECTOR_RUN_TOTAL,
)
from engine.macro.providers.base import BaseProvider

logger = get_logger(__name__)
T = TypeVar("T")


class BaseCollector(abc.ABC):
    collector_name: str = "base"
    cache_namespace: str = "collector"
    cache_ttl: int = 600

    def __init__(
        self,
        providers: list[BaseProvider],
        cache: RedisCache,
        db: DatabaseManager,
    ) -> None:
        self._providers = providers
        self._cache = cache
        self._db = db

    async def collect(self) -> Any:
        start = time.monotonic()
        try:
            result = await self._do_collect()
            duration = time.monotonic() - start
            COLLECTOR_RUN_TOTAL.labels(collector=self.collector_name, status="success").inc()
            COLLECTOR_RUN_DURATION.labels(collector=self.collector_name).observe(duration)
            return result
        except Exception as exc:
            duration = time.monotonic() - start
            COLLECTOR_RUN_TOTAL.labels(collector=self.collector_name, status="error").inc()
            COLLECTOR_RUN_DURATION.labels(collector=self.collector_name).observe(duration)
            logger.error("collector_failed", collector=self.collector_name, error=str(exc))
            raise

    @abc.abstractmethod
    async def _do_collect(self) -> Any:
        ...

    async def _fetch_with_failover(self, providers: list[BaseProvider]) -> Any:
        last_exc: Exception | None = None
        for provider in providers:
            try:
                return await provider.fetch()
            except Exception as exc:
                logger.warning(
                    "provider_failover",
                    collector=self.collector_name,
                    failed_provider=provider.provider_name,
                    error=str(exc),
                )
                last_exc = exc
        if last_exc:
            raise last_exc
        return None

    def _record_items_stored(self, count: int) -> None:
        COLLECTOR_ITEMS_STORED.labels(collector=self.collector_name).inc(count)
