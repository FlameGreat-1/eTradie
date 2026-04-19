from __future__ import annotations

import abc
import time
from typing import Any, ClassVar, Optional, TypeVar

from pydantic import BaseModel, ValidationError

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

    Implements a read-through cache (cache-aside) pattern. ``collect()``
    is the public read path used by the analysis pipeline, the rerun
    endpoint, and the Go gateway via /internal/macro/collect: it
    returns a cached value when one is available and only falls back
    to a full provider fetch on a miss. ``refresh()`` is the explicit
    cache-bypass writer path used by the APScheduler jobs so the
    scheduler always produces fresh data regardless of cache state.

    Subclasses must:
      - implement ``_do_collect()`` which performs the expensive fetch
        + DB write + cache write and returns the collector-specific
        dataset,
      - set ``cache_namespace`` to a stable Redis namespace string
        matching what ``_do_collect()`` writes to,
      - optionally set ``cache_model`` to the Pydantic class used to
        rehydrate cached values. When unset, cached values are
        returned as their raw JSON-decoded form (used by the sentiment
        collector which intentionally returns ``dict[str, Any]``).

    Every collector is global: no user_id is required.
    Cache keys are namespaced by ``{cache_namespace}:latest``.
    """

    collector_name: ClassVar[str] = "base"
    cache_namespace: ClassVar[str] = "collector"
    cache_ttl: int = 600
    cache_model: ClassVar[Optional[type[BaseModel]]] = None

    def __init__(
        self,
        providers: list[BaseProvider],
        cache: RedisCache,
        db: DatabaseManager,
    ) -> None:
        self._providers = providers
        self._cache = cache
        self._db = db

    async def collect(self, *, force_refresh: bool = False) -> Any:
        """Return the latest collector dataset.

        Read-through path: look up the value in Redis first. On hit,
        rehydrate via ``cache_model`` (if declared) and return
        immediately. On miss, on cache-read failure, or when the
        caller sets ``force_refresh=True``, invoke ``_do_collect()``
        which fetches from providers, persists to the database, and
        writes the cache.

        Args:
            force_refresh: When True, skip the cache read and always
                execute ``_do_collect()``. Used by the scheduler to
                guarantee the cache is periodically refreshed.

        Returns:
            The collector-specific dataset. Type matches the return
            type of the subclass ``_do_collect()``.

        Raises:
            Exception: Re-raised from ``_do_collect()`` on cache miss.
        """
        start = time.monotonic()

        if not force_refresh:
            cached = await self._try_read_cache()
            if cached is not None:
                duration = time.monotonic() - start
                COLLECTOR_RUN_TOTAL.labels(
                    collector=self.collector_name, status="cache_hit"
                ).inc()
                COLLECTOR_RUN_DURATION.labels(
                    collector=self.collector_name
                ).observe(duration)
                logger.debug(
                    "collector_cache_hit",
                    extra={
                        "collector": self.collector_name,
                        "namespace": self.cache_namespace,
                        "duration_ms": round(duration * 1000, 2),
                    },
                )
                return cached

        try:
            result = await self._do_collect()
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
                error=str(exc),
            )
            raise

    async def refresh(self) -> Any:
        """Force a provider fetch and cache write, bypassing any hit.

        This is the authoritative writer path. The APScheduler macro
        jobs call this on their configured intervals so Redis is
        always populated with a fresh dataset regardless of whether
        downstream readers are hitting the cache. Semantically
        equivalent to ``collect(force_refresh=True)``.
        """
        return await self.collect(force_refresh=True)

    async def _try_read_cache(self) -> Any | None:
        """Attempt to read the latest dataset from Redis.

        Returns the rehydrated value on hit, or ``None`` on miss, on
        read/timeout/connection error, or on rehydration validation
        error. A cache read failure is never propagated: the caller
        falls through to a full fetch, so the collector continues to
        function identically to today when Redis is degraded.
        """
        try:
            raw = await self._cache.get(
                self.cache_namespace, self._cache_key(),
            )
        except Exception as exc:
            logger.warning(
                "collector_cache_read_failed",
                extra={
                    "collector": self.collector_name,
                    "namespace": self.cache_namespace,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return None

        if raw is None:
            return None

        if self.cache_model is None:
            # Subclass opted out of Pydantic rehydration (e.g. the
            # sentiment collector returns a raw dict by design).
            return raw

        try:
            return self.cache_model.model_validate(raw)
        except ValidationError as exc:
            logger.warning(
                "collector_cache_rehydrate_failed",
                extra={
                    "collector": self.collector_name,
                    "namespace": self.cache_namespace,
                    "model": self.cache_model.__name__,
                    "error": str(exc),
                },
            )
            return None

    @abc.abstractmethod
    async def _do_collect(self) -> Any:
        """Subclass implementation of the collection logic.

        Must fetch from providers, persist to the database (if
        applicable), and write the result to the cache under
        ``self.cache_namespace`` + ``self._cache_key()`` with
        ``self.cache_ttl``. The returned value must be deserializable
        from its own cached JSON form via ``self.cache_model`` when
        that attribute is set.
        """
        ...

    async def _fetch_with_failover(self, providers: list[BaseProvider]) -> Any:
        """Fetch data from providers with automatic failover.

        Provider data is public market data (RSS feeds, APIs).
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

    def _cache_key(self, suffix: str = "latest") -> str:
        """Build a global cache key.

        Format: ``{suffix}``
        The cache namespace is prepended by the RedisCache layer.
        """
        return suffix

    def _record_items_stored(self, count: int) -> None:
        COLLECTOR_ITEMS_STORED.labels(collector=self.collector_name).inc(count)
