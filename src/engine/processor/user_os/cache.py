"""Redis-backed cache for the compressed user Trading Operating System.

The cached value is the OUTPUT of
engine.processor.user_os.context_builder.build_user_operating_context
— a deterministic, prompt-safe instruction block — not the raw
Profile JSON returned by the gateway. Caching the compressed block
means a cache hit avoids BOTH the HTTP round-trip to the gateway
AND the local compression pass, which is the maximum work we can
elide per analysis cycle.

VERSIONING
----------

The gateway's user_trading_systems row carries a monotonically
increasing `version` column that is bumped on every Save. The cache
key embeds the version so a stale entry becomes naturally unreachable
the moment the user updates their profile:

    user_os:<user_id>:v<version>     → compressed dict
    user_os:<user_id>:absent         → negative-cache sentinel

The positive entry has a long TTL (1 hour); the negative entry has a
short TTL (60 seconds) because a previously-skipped user could build
their profile at any time and we want the next cycle after a save to
use the real profile.

FAILURE MODE
------------

Every operation is wrapped to swallow CacheError / CacheTimeoutError /
CacheConnectionError. A Redis outage degrades the engine to the
pre-cache HTTP-fetch path, NEVER blocks the LLM pipeline. Per
PRACTICE.md: a missing user OS must fall back to the default
institutional profile, never abort analysis.

METRICS
-------

Exported via USER_OS_CACHE_OPS_TOTAL{operation, outcome}:
    operation = 'positive_get' | 'negative_get' | 'positive_set' |
                'negative_set' | 'invalidate'
    outcome   = 'hit' | 'miss' | 'error' | 'success'
"""

from __future__ import annotations

from typing import Any, Optional

from engine.shared.cache import RedisCache
from engine.shared.exceptions import (
    CacheConnectionError,
    CacheError,
    CacheTimeoutError,
    CacheValidationError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import USER_OS_CACHE_OPS_TOTAL

logger = get_logger(__name__)

_NAMESPACE = "user_os"
_POSITIVE_TTL_SECONDS = 3600  # 1 hour
_NEGATIVE_TTL_SECONDS = 60    # 60 seconds
_ABSENT_SUFFIX = "absent"


class UserOSCache:
    """Two-tier (positive + negative) cache for the compressed user OS.

    Wraps the shared RedisCache. Construction never fails — a None
    cache (no Redis configured, e.g. unit tests) results in a no-op
    cache where every get returns 'miss' and every set is a no-op.
    Callers can therefore treat UserOSCache as always-available.
    """

    def __init__(self, *, cache: Optional[RedisCache]) -> None:
        self._cache = cache

    # ---------------------------------------------------------------
    # Key construction
    # ---------------------------------------------------------------

    @staticmethod
    def _positive_key(user_id: str, version: int) -> str:
        # version is a monotonically increasing non-negative int from
        # the gateway. We coerce defensively to keep the cache key
        # syntactically valid even on corrupt input.
        v = max(0, int(version))
        return f"{user_id}:v{v}"

    @staticmethod
    def _negative_key(user_id: str) -> str:
        return f"{user_id}:{_ABSENT_SUFFIX}"

    # ---------------------------------------------------------------
    # Positive cache (active profile)
    # ---------------------------------------------------------------

    async def get_compressed(
        self,
        user_id: str,
        version: int,
        *,
        trace_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Return the cached compressed context for the user/version pair.

        Returns None on miss, on any cache error, or when the cache is
        not configured. Never raises — callers must treat None as
        'unknown' and proceed to fetch.
        """
        if self._cache is None or not user_id:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="positive_get", outcome="miss"
            ).inc()
            return None
        try:
            value = await self._cache.get(
                _NAMESPACE,
                self._positive_key(user_id, version),
                trace_id=trace_id,
            )
        except (CacheValidationError, CacheTimeoutError, CacheConnectionError, CacheError) as exc:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="positive_get", outcome="error"
            ).inc()
            logger.debug(
                "user_os_cache_get_error",
                extra={
                    "user_id": user_id,
                    "version": version,
                    "trace_id": trace_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return None
        if value is None:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="positive_get", outcome="miss"
            ).inc()
            return None
        if not isinstance(value, dict):
            # Defensive: the cache should only ever hold dicts under
            # this namespace. A non-dict means someone wrote junk;
            # treat as miss so the caller refetches a clean value.
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="positive_get", outcome="miss"
            ).inc()
            return None
        USER_OS_CACHE_OPS_TOTAL.labels(
            operation="positive_get", outcome="hit"
        ).inc()
        return value

    async def set_compressed(
        self,
        user_id: str,
        version: int,
        compressed: dict[str, Any],
        *,
        trace_id: Optional[str] = None,
    ) -> None:
        """Cache the compressed context for a user/version pair.

        Best-effort: a Redis error is swallowed; the LLM call still
        proceeds and the next cycle simply re-fetches.
        """
        if self._cache is None or not user_id:
            return
        try:
            await self._cache.set(
                _NAMESPACE,
                self._positive_key(user_id, version),
                compressed,
                ttl_seconds=_POSITIVE_TTL_SECONDS,
                trace_id=trace_id,
            )
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="positive_set", outcome="success"
            ).inc()
        except (CacheValidationError, CacheTimeoutError, CacheConnectionError, CacheError) as exc:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="positive_set", outcome="error"
            ).inc()
            logger.debug(
                "user_os_cache_set_error",
                extra={
                    "user_id": user_id,
                    "version": version,
                    "trace_id": trace_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

    # ---------------------------------------------------------------
    # Negative cache (user has no active profile)
    # ---------------------------------------------------------------

    async def is_absent(
        self,
        user_id: str,
        *,
        trace_id: Optional[str] = None,
    ) -> bool:
        """Return True iff a negative-cache sentinel exists for the user.

        A True result lets the caller short-circuit the HTTP fetch and
        the compression pass: we already know the user has no active
        profile and should use the default institutional behaviour.
        """
        if self._cache is None or not user_id:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="negative_get", outcome="miss"
            ).inc()
            return False
        try:
            value = await self._cache.get(
                _NAMESPACE,
                self._negative_key(user_id),
                trace_id=trace_id,
            )
        except (CacheValidationError, CacheTimeoutError, CacheConnectionError, CacheError) as exc:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="negative_get", outcome="error"
            ).inc()
            logger.debug(
                "user_os_cache_absent_check_error",
                extra={
                    "user_id": user_id,
                    "trace_id": trace_id,
                    "error": str(exc),
                },
            )
            return False
        if value is None:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="negative_get", outcome="miss"
            ).inc()
            return False
        USER_OS_CACHE_OPS_TOTAL.labels(
            operation="negative_get", outcome="hit"
        ).inc()
        return True

    async def set_absent(
        self,
        user_id: str,
        *,
        trace_id: Optional[str] = None,
    ) -> None:
        """Write the negative-cache sentinel for a user with no active profile.

        TTL is short by design — a previously-unprofiled user can
        build a profile at any time and we must not stale-cache them
        for too long. Active invalidation (Workstream B) busts this
        immediately when the user saves.
        """
        if self._cache is None or not user_id:
            return
        try:
            # The value is irrelevant — only the key's presence matters.
            # We use a small dict so JSON serialisation succeeds.
            await self._cache.set(
                _NAMESPACE,
                self._negative_key(user_id),
                {"_absent": True},
                ttl_seconds=_NEGATIVE_TTL_SECONDS,
                trace_id=trace_id,
            )
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="negative_set", outcome="success"
            ).inc()
        except (CacheValidationError, CacheTimeoutError, CacheConnectionError, CacheError) as exc:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="negative_set", outcome="error"
            ).inc()
            logger.debug(
                "user_os_cache_absent_set_error",
                extra={
                    "user_id": user_id,
                    "trace_id": trace_id,
                    "error": str(exc),
                },
            )

    # ---------------------------------------------------------------
    # Invalidation
    # ---------------------------------------------------------------

    async def invalidate(
        self,
        user_id: str,
        *,
        trace_id: Optional[str] = None,
    ) -> None:
        """Drop both the negative sentinel for the user.

        Positive entries are NOT explicitly deleted here because they
        are version-keyed: a Save bumps the version, which makes the
        old positive entry naturally unreachable. We only delete the
        negative entry so a user who previously skipped (negative
        cached) and now saves is picked up on the very next cycle
        instead of having to wait for the 60-second negative TTL.

        Best-effort. A Redis error is logged but never raised — the
        positive cache's version-keying provides safety even when
        explicit invalidation fails.
        """
        if self._cache is None or not user_id:
            return
        try:
            await self._cache.delete(
                _NAMESPACE,
                self._negative_key(user_id),
                trace_id=trace_id,
            )
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="invalidate", outcome="success"
            ).inc()
            logger.info(
                "user_os_cache_invalidated",
                extra={"user_id": user_id, "trace_id": trace_id},
            )
        except (CacheValidationError, CacheTimeoutError, CacheConnectionError, CacheError) as exc:
            USER_OS_CACHE_OPS_TOTAL.labels(
                operation="invalidate", outcome="error"
            ).inc()
            logger.warning(
                "user_os_cache_invalidate_failed",
                extra={
                    "user_id": user_id,
                    "trace_id": trace_id,
                    "error": str(exc),
                },
            )
