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
    """Base class for all macro data collectors.

    Every collector is user-scoped: the ``user_id`` parameter is required
    on every ``collect()`` call and is propagated to ``_do_collect()``,
    storage, and cache operations.  This ensures complete tenant isolation
    in a multi-tenant financial application.

    Cache keys are namespaced by ``{cache_namespace}:{user_id}:latest``
    so that User A's cached macro data never leaks to User B.
    """

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

    async def collect(self, user_id: str) -> Any:
        """Run the collector for a specific user.

        Args:
            user_id: The authenticated user's ID.  Must not be empty.
                     All collected data is tagged with this ID for
                     tenant isolation.

        Returns:
            The collector-specific dataset.

        Raises:
            ValueError: If ``user_id`` is empty.
            Exception: Re-raised from ``_do_collect``.
        """
        if not user_id:
            raise ValueError(
                f"{self.collector_name}: user_id is required for "
                f"multi-tenant data isolation"
            )

        start = time.monotonic()
        try:
            result = await self._do_collect(user_id)
            duration = time.monotonic() - start
            COLLECTOR_RUN_TOTAL.labels(
                collector=self.collector_name, status="success"
            ).inc()
            COLLECTOR_RUN_DURATION.labels(collector=self.collector_name).observe(
                duration
            )
            return result
        except Exception as exc:
            duration = time.monotonic() - start
            COLLECTOR_RUN_TOTAL.labels(
                collector=self.collector_name, status="error"
            ).inc()
            COLLECTOR_RUN_DURATION.labels(collector=self.collector_name).observe(
                duration
            )
            logger.error(
                "collector_failed",
                collector=self.collector_name,
                user_id=user_id,
                error=str(exc),
            )
            raise

    @abc.abstractmethod
    async def _do_collect(self, user_id: str) -> Any:
        """Subclass implementation of the collection logic.

        Args:
            user_id: The authenticated user's ID.  Subclasses MUST pass
                     this to all storage and cache operations.
        """
        ...

    async def _fetch_with_failover(self, providers: list[BaseProvider]) -> Any:
        """Fetch data from providers with automatic failover.

        Provider data is public market data (RSS feeds, APIs) and does
        not vary per user, so no user_id is needed here.  User scoping
        is applied when the data is *stored* and *cached*.
        """
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

    def _user_cache_key(self, user_id: str, suffix: str = "latest") -> str:
        """Build a user-scoped cache key.

        Format: ``{user_id}:{suffix}``
        The cache namespace is prepended by the RedisCache layer.
        """
        return f"{user_id}:{suffix}"

    def _record_items_stored(self, count: int) -> None:
        COLLECTOR_ITEMS_STORED.labels(collector=self.collector_name).inc(count)
