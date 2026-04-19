from __future__ import annotations

import abc
import asyncio
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

    Implements a read-through cache (cache-aside) pattern with
    single-flight stampede protection. ``collect()`` is the public
    read path used by the analysis pipeline, the rerun endpoint, and
    the Go gateway via /internal/macro/collect: it returns a cached
    value when one is available, coalesces concurrent misses into a
    single provider fetch, and only falls back to executing
    ``_do_collect()`` when no other caller is already doing so.
    ``refresh()`` is the explicit cache-bypass writer path used by
    the APScheduler jobs so the scheduler always produces fresh data
    regardless of cache state; it shares the same instance lock so
    a scheduled refresh never races a request-driven miss.

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
        # Lazy-allocated fetch coalescing lock. Created on first use
        # so it binds to the correct running event loop. The guard
        # lock below protects concurrent first-use callers from each
        # creating a different Lock instance.
        self._fetch_lock: Optional[asyncio.Lock] = None
        self._fetch_lock_guard = asyncio.Lock()

    async def _get_fetch_lock(self) -> asyncio.Lock:
        """Return the instance-wide fetch coalescing lock.

        Created lazily on first call so the Lock binds to the
        currently running asyncio event loop (the collector is
        instantiated during Container() at import/startup, which
        on some runtimes is not the same loop the request handlers
        run on).
        """
        if self._fetch_lock is not None:
            return self._fetch_lock
        async with self._fetch_lock_guard:
            if self._fetch_lock is None:
                self._fetch_lock = asyncio.Lock()
        return self._fetch_lock

    async def collect(self, *, force_refresh: bool = False) -> Any:
        """Return the latest collector dataset.

        Read-through path with single-flight coalescing:

          1. If ``force_refresh`` is False, check Redis. A hit
             returns immediately and is recorded as status=cache_hit.
          2. On miss, acquire the instance fetch lock. If a
             concurrent caller already populated the cache while we
             were waiting, return that value and record the call as
             status=coalesced (observably distinct from a first-try
             cache_hit, so operators can measure how often stampede
             protection actually saved a fetch).
          3. Otherwise execute ``_do_collect()`` exactly once. All
             concurrent waiters take the coalesced path and share
             the single provider fetch. Status is recorded as
             success or error on the sole fetcher.

        Args:
            force_refresh: When True, skip the initial cache read
                and always execute ``_do_collect()``. Used by the
                scheduler.

        Returns:
            The collector-specific dataset.

        Raises:
            Exception: Re-raised from ``_do_collect()``.
        """
        start = time.monotonic()

        if not force_refresh:
            cached = await self._try_read_cache()
            if cached is not None:
                self._observe("cache_hit", start)
                logger.debug(
                    "collector_cache_hit",
                    extra={
                        "collector": self.collector_name,
                        "namespace": self.cache_namespace,
                        "duration_ms": round((time.monotonic() - start) * 1000, 2),
                    },
                )
                return cached

        lock = await self._get_fetch_lock()
        async with lock:
            # Double-checked read under the lock: another waiter may
            # have repopulated the cache while we were blocked.
            if not force_refresh:
                cached = await self._try_read_cache()
                if cached is not None:
                    self._observe("coalesced", start)
                    logger.debug(
                        "collector_fetch_coalesced",
                        extra={
                            "collector": self.collector_name,
                            "namespace": self.cache_namespace,
                            "duration_ms": round(
                                (time.monotonic() - start) * 1000, 2
                            ),
                        },
                    )
                    return cached

            try:
                result = await self._do_collect()
                self._observe("success", start)
                return result
            except Exception as exc:
                self._observe("error", start)
                logger.error(
                    "collector_failed",
                    collector=self.collector_name,
                    error=str(exc),
                )
                raise

    async def refresh(self) -> Any:
        """Force a provider fetch and cache write, bypassing any hit.

        The scheduler's authoritative writer path. Holds the instance
        fetch lock so a scheduled refresh and a request-driven miss
        never double-fetch the same provider in the same instant.
        Semantically equivalent to ``collect(force_refresh=True)``.
        """
        return await self.collect(force_refresh=True)

    async def _try_read_cache(self) -> Any | None:
        """Attempt to read the latest dataset from Redis.

        Returns the rehydrated value on hit, or ``None`` on miss, on
        read/timeout/connection error, or on rehydration validation
        error. A cache read failure is never propagated: the caller
        falls through to a full fetch, so the collector continues to
        function identically when Redis is degraded.
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

    def _observe(self, status: str, start: float) -> None:
        """Record a single collect() invocation in Prometheus.

        Emits both the run total counter with the appropriate status
        label and the duration histogram. Keeping this in one helper
        guarantees every return path from ``collect()`` produces
        consistent telemetry.
        """
        duration = time.monotonic() - start
        COLLECTOR_RUN_TOTAL.labels(
            collector=self.collector_name, status=status
        ).inc()
        COLLECTOR_RUN_DURATION.labels(collector=self.collector_name).observe(
            duration
        )

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
