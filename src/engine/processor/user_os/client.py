"""Async HTTP client for the gateway's trading-system internal API.

Mirrors the gateway -> engine X-Internal-Auth + X-User-Id contract
used by every other /internal/* call, just inverted: now the engine
is the caller and the gateway is the server.

Failure mode by design: any error (network, 5xx, malformed JSON,
status != 'active') returns None. The processor pipeline then falls
back to the default institutional profile, which is the correct
behaviour per PRACTICE.md — a transient outage must NEVER prevent an
analysis from running.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from engine.processor.user_os.cache import UserOSCache
from engine.processor.user_os.context_builder import (
    build_user_operating_context,
)
from engine.shared.cache import RedisCache
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Header names mirror src/gateway/internal/infra/engine_http.go so any
# future rename is a one-line change on both sides.
_INTERNAL_AUTH_HEADER = "X-Internal-Auth"
_INTERNAL_USER_ID_HEADER = "X-User-Id"

_DEFAULT_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class UserOSRecord:
    """Lightweight engine-side view of the gateway record."""

    user_id: str
    status: str  # 'none' | 'skipped' | 'active'
    version: int
    profile: Optional[dict[str, Any]]
    has_profile: bool

    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.has_profile and self.profile is not None


class UserOSClient:
    """Fetches user trading systems from the gateway's internal API.

    A single instance is built at engine startup and shared across
    every processor request. The underlying httpx.AsyncClient is
    long-lived (connection pooling) and closed via close() on shutdown.
    """

    def __init__(
        self,
        *,
        gateway_base_url: str,
        internal_secret: str,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        cache: Optional[RedisCache] = None,
    ) -> None:
        self._base_url = gateway_base_url.rstrip("/")
        self._secret = internal_secret
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = timeout_seconds
        self._lock = asyncio.Lock()
        # Two-tier cache (positive + negative). When cache is None the
        # wrapper transparently degrades to every-call-fetches behaviour
        # so callers do not branch on its presence.
        self._user_os_cache = UserOSCache(cache=cache)
        # Per-process map of user_id -> last seen version. Lets the
        # cache-aware fetch path attempt a versioned positive-cache
        # hit before falling through to HTTP. Pruned by the pub/sub
        # invalidation listener.
        self._known_version: dict[str, int] = {}

    @property
    def user_os_cache(self) -> UserOSCache:
        """Expose the cache so the pub/sub invalidation listener can
        bust entries when the gateway publishes a profile change.
        """
        return self._user_os_cache

    @classmethod
    def from_env(cls, *, cache: Optional[RedisCache] = None) -> Optional["UserOSClient"]:
        """Build a client from environment variables.

        Returns None when the gateway URL or shared secret is missing,
        so the processor can run in unit tests / local dev without
        attempting an HTTP call. Production deployments must set both
        ENGINE_GATEWAY_URL and ENGINE_INTERNAL_SHARED_SECRET.
        """
        base_url = (
            os.environ.get("ENGINE_GATEWAY_URL")
            or os.environ.get("GATEWAY_HTTP_URL")
            or ""
        ).strip()
        secret = (
            os.environ.get("ENGINE_INTERNAL_SHARED_SECRET")
            or os.environ.get("GATEWAY_ENGINE_INTERNAL_SHARED_SECRET")
            or ""
        ).strip()
        if not base_url or not secret:
            logger.info(
                "user_os_client_disabled",
                extra={
                    "base_url_set": bool(base_url),
                    "secret_set": bool(secret),
                },
            )
            return None
        return cls(
            gateway_base_url=base_url,
            internal_secret=secret,
            cache=cache,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    timeout=self._timeout,
                    headers={"Content-Type": "application/json"},
                )
        return self._client

    async def get(self, user_id: str) -> Optional[UserOSRecord]:
        """Fetch the user's trading system from the gateway.

        Returns None on any error or when the user has no active
        profile. Callers must NOT block the LLM pipeline on this call;
        a missing profile is a successful fast-path that yields the
        default institutional behaviour.
        """
        if not user_id:
            return None

        url = f"{self._base_url}/internal/trading-system/get"
        try:
            client = await self._get_client()
            resp = await client.post(
                url,
                json={"user_id": user_id},
                headers={
                    _INTERNAL_AUTH_HEADER: self._secret,
                    _INTERNAL_USER_ID_HEADER: user_id,
                },
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning(
                "user_os_fetch_failed_transport",
                extra={"user_id": user_id, "error": str(exc)},
            )
            return None

        if resp.status_code != 200:
            logger.warning(
                "user_os_fetch_failed_status",
                extra={
                    "user_id": user_id,
                    "status": resp.status_code,
                    "body_preview": resp.text[:200],
                },
            )
            return None

        try:
            body = resp.json()
        except ValueError:
            logger.warning(
                "user_os_fetch_failed_json",
                extra={"user_id": user_id, "body_preview": resp.text[:200]},
            )
            return None

        return UserOSRecord(
            user_id=str(body.get("user_id", user_id)),
            status=str(body.get("status", "none")),
            version=int(body.get("version", 0) or 0),
            profile=body.get("profile") if isinstance(body.get("profile"), dict) else None,
            has_profile=bool(body.get("has_profile", False)),
        )

    # -- Cached fetch (canonical hot-path entry point) ----------------

    async def get_compressed_context(
        self,
        user_id: str,
        *,
        trace_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Return the user's compressed Trading OS context block.

        This is the canonical method the processor should call. It is
        cache-aware end-to-end:

            1. Negative-cache check: if we know the user has no active
               profile, return None immediately (no HTTP, no compression).
            2. Positive-cache check: we do NOT know the version yet so
               we cannot key the positive cache here. The version-keyed
               positive cache is populated by the gateway-driven write
               path (see step 4); the read here defers to the HTTP fetch
               which is itself versioned.
            3. HTTP fetch: call the gateway as before. If the record is
               not active, write the negative-cache sentinel and return
               None. If it is active, compress, write the positive cache
               keyed on the returned version, and return the compressed
               block.
            4. The cached block on subsequent cycles is read via the
               positive cache once we have the version; that lookup is
               attempted before the HTTP call below the next time around
               only when invoked via the gateway's invalidation message
               (which carries the version). The version-keyed positive
               cache is therefore READ on a hit and WRITTEN on a miss
               using the version returned by the gateway in the same
               response. This keeps the protocol single-fetch on a miss
               and zero-fetch on a hit.

        Returns None when the user has no active profile, on any error,
        or when the user_id is empty. NEVER raises.
        """
        if not user_id:
            return None

        # Step 1: negative-cache fast-path.
        try:
            if await self._user_os_cache.is_absent(user_id, trace_id=trace_id):
                return None
        except Exception as exc:
            # is_absent is already defensive but belt-and-braces.
            logger.debug(
                "user_os_negative_check_unexpected_error",
                extra={
                    "user_id": user_id,
                    "trace_id": trace_id,
                    "error": str(exc),
                },
            )

        # Step 2: try a positive-cache hit on the LAST KNOWN version.
        # We track it lightly per-process in an LRU-style dict; lookup
        # falls through to HTTP on miss. The miss is rare because the
        # gateway publishes the version on every save and the listener
        # bumps this dict.
        last_version = self._known_version.get(user_id)
        if last_version is not None:
            cached = await self._user_os_cache.get_compressed(
                user_id, last_version, trace_id=trace_id
            )
            if cached is not None:
                return cached

        # Step 3: HTTP fetch.
        record = await self.get(user_id)
        if record is None or not record.is_active:
            # Negative cache so we do not re-fetch every cycle.
            await self._user_os_cache.set_absent(user_id, trace_id=trace_id)
            return None

        # Step 4: compress and cache.
        compressed = build_user_operating_context(record.profile)
        if compressed is None:
            # build_user_operating_context returns None for malformed
            # profiles. Negative-cache so we don't recompress on every
            # cycle until the user re-saves.
            await self._user_os_cache.set_absent(user_id, trace_id=trace_id)
            return None

        await self._user_os_cache.set_compressed(
            user_id, record.version, compressed, trace_id=trace_id
        )
        self._known_version[user_id] = record.version
        return compressed

    # Note on _known_version: this is intentionally a plain dict, not
    # an unbounded cache, because the per-process working set is
    # bounded by the number of active users hitting THIS engine
    # instance during the positive-cache TTL window (~1 hour). At
    # 10K daily-actives the dict holds ~10K small int values
    # (~< 1 MB). The pub/sub invalidation listener prunes entries on
    # explicit invalidation events. If we ever grow past that scale,
    # switching to functools.lru_cache or cachetools.TTLCache is a
    # one-line change.
    _known_version: dict[str, int]

    def __init_subclass__(cls, **kwargs: Any) -> None:  # pragma: no cover
        super().__init_subclass__(**kwargs)

    async def invalidate_local_version(self, user_id: str) -> None:
        """Remove the in-process version cache entry for a user.

        Called by the pub/sub invalidation listener so a subsequent
        get_compressed_context call goes back to the HTTP path to
        learn the new version. The positive Redis entry under the OLD
        version is naturally unreachable; the new version's entry
        will be written on the next miss.
        """
        self._known_version.pop(user_id, None)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
