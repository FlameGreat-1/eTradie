from __future__ import annotations

import abc
import asyncio
import time
from datetime import UTC, datetime
from typing import Any, ClassVar, Optional, TypeVar

from pydantic import BaseModel, ValidationError

from engine.shared.cache import RedisCache
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger
from engine.macro.storage.repositories.snapshot.snapshot import (
    MacroSnapshotRepository,
)
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
                            "duration_ms": round((time.monotonic() - start) * 1000, 2),
                        },
                    )
                    return cached

                # If cache is still empty, and we are not forcing refresh, we MUST NOT hit the APIs.
                # Fallback to the DB.
                db_data = await self._read_from_db()
                if db_data is not None:
                    self._observe("db_hit", start)
                    logger.debug(
                        "collector_db_fallback",
                        extra={
                            "collector": self.collector_name,
                            "namespace": self.cache_namespace,
                            "duration_ms": round((time.monotonic() - start) * 1000, 2),
                        },
                    )
                    # Rehydrate cache asynchronously if we got it from DB
                    if self.cache_model:
                        asyncio.create_task(
                            self._cache.set(
                                self.cache_namespace,
                                self._cache_key(),
                                db_data.model_dump(mode="json"),
                                self.cache_ttl,
                            )
                        )
                    return db_data

                # If DB is also empty or _read_from_db not implemented, return empty dataset to avoid API fetch
                self._observe("empty_fallback", start)
                logger.warning(
                    "collector_cache_and_db_miss_returning_empty",
                    extra={"collector": self.collector_name},
                )
                return self._empty_dataset()

            try:
                result = await self._do_collect()
                await self._persist_snapshot(result)
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
                self.cache_namespace,
                self._cache_key(),
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
        COLLECTOR_RUN_TOTAL.labels(collector=self.collector_name, status=status).inc()
        COLLECTOR_RUN_DURATION.labels(collector=self.collector_name).observe(duration)

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

    async def _read_from_db(self) -> Any | None:
        """Read the last-good persisted snapshot for this collector.

        Called on the analysis read path when the Redis cache is empty,
        so the hot path never makes an external API call. Returns the
        collector's last successfully-collected dataset, rehydrated to
        the same type ``_do_collect()`` returns:

          - When ``cache_model`` is set, the stored JSON is validated
            back into that Pydantic model, so the result is byte-for-
            byte equivalent to the writer's output.
          - When ``cache_model`` is unset (the sentiment collector,
            which returns a raw dict by design), the stored JSON dict
            is returned as-is.

        Returns ``None`` only when no snapshot has ever been persisted
        (a genuinely cold, first-run system) or on a read/validation
        failure; the caller then falls back to ``_empty_dataset()``.
        """
        try:
            async with self._db.read_session() as session:
                repo = MacroSnapshotRepository(session)
                payload = await repo.get_payload(self.cache_namespace)
        except Exception as exc:
            logger.warning(
                "collector_snapshot_read_failed",
                extra={
                    "collector": self.collector_name,
                    "namespace": self.cache_namespace,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return None

        if payload is None:
            return None

        if self.cache_model is None:
            # Subclass returns a raw dict by design (sentiment).
            return payload

        try:
            return self.cache_model.model_validate(payload)
        except ValidationError as exc:
            logger.warning(
                "collector_snapshot_rehydrate_failed",
                extra={
                    "collector": self.collector_name,
                    "namespace": self.cache_namespace,
                    "model": self.cache_model.__name__,
                    "error": str(exc),
                },
            )
            return None

    async def _persist_snapshot(self, dataset: Any) -> None:
        """Persist the collector's final dataset as the last-good snapshot.

        Writer-side durability: after every successful collection the
        scheduler's path stores the exact serialised dataset so a later
        request-path cache miss can be served from it without an API
        call. Best-effort: a snapshot write failure is logged and
        swallowed because the live dataset has already been produced and
        returned to the caller; durability is a convenience for the next
        reader, never a precondition for this collection succeeding.
        """
        if dataset is None:
            return
        try:
            if hasattr(dataset, "model_dump"):
                payload = dataset.model_dump(mode="json")
            elif isinstance(dataset, dict):
                payload = dataset
            else:
                # Nothing serialisable to persist; skip silently.
                return
            collected_at = self._extract_collected_at(payload)
            async with self._db.session() as session:
                repo = MacroSnapshotRepository(session)
                await repo.upsert_payload(
                    self.cache_namespace,
                    payload,
                    collected_at,
                )
        except Exception as exc:
            logger.warning(
                "collector_snapshot_persist_failed",
                extra={
                    "collector": self.collector_name,
                    "namespace": self.cache_namespace,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

    @staticmethod
    def _extract_collected_at(payload: dict[str, Any]) -> datetime:
        """Resolve the dataset's collected_at, defaulting to now (UTC).

        Every macro dataset carries a ``collected_at`` field serialised
        as an ISO-8601 string. We store it on the snapshot row for
        operator visibility (how stale is the last-good value); if it is
        missing or unparseable we fall back to the current time so a
        write never fails on a timestamp technicality.
        """
        raw = payload.get("collected_at")
        if isinstance(raw, str) and raw:
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed
            except ValueError:
                pass
        return datetime.now(UTC)

    @abc.abstractmethod
    def _empty_dataset(self) -> Any:
        """Return an empty dataset for a genuinely cold, first-run system.

        Only reached when neither the cache nor a persisted snapshot has
        any data yet (e.g. a brand-new deployment before the scheduler's
        first successful run). Never reached in steady state.
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
