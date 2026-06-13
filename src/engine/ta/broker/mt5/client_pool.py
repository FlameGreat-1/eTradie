"""Per-connection broker client pool.

Before this module existed, every HTTP handler that needed a broker
call would call factory.create_mt5_broker_from_connection() and
construct a brand-new ZmqClient (with its own REQ socket, its own
asyncio.Lock, its own heartbeat task). Two concurrent requests for
the same user opened two REQ sockets racing on the EA's single REP
socket. ZMQ's REQ/REP state machine is strict: one REQ must complete
before the next REQ on the same socket; with two sockets sharing one
REP, the EA's reply could be matched to either REQ socket's queue
leading to 'Operation cannot be accomplished in current state'.

This pool fixes that by caching ONE client per (provider, account_id)
for the lifetime of the engine process (with idle eviction). The
pool itself is asyncio.Lock-guarded per key so two concurrent first-
touch coroutines do not each instantiate a client.

Audit ref: CHECKLIST Section 5 - 'No global locks blocking unrelated
users', 'Each user's terminal is isolated'.
"""

from __future__ import annotations

import asyncio
import time as _time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    BROKER_CLIENT_POOL_EVICTIONS_TOTAL,
    BROKER_CLIENT_POOL_SIZE,
)
from engine.ta.broker.base import BrokerBase

logger = get_logger(__name__)

# Type of the factory the caller passes in. Async-returning because
# real construction may need to call back into k8s / vault / db at
# warm-up time. The factory is invoked at most once per pool key.
ClientFactory = Callable[[], Awaitable[BrokerBase]]


@dataclass
class _PoolEntry:
    client: BrokerBase
    created_at: float
    last_used: float
    provider: str
    account_id: str


class BrokerClientPool:
    """Process-local cache of broker clients keyed by (provider, account_id).

    Construction synchronisation: a per-key asyncio.Lock ensures that
    only one coroutine ever runs the factory for a given key, even
    under 100 concurrent get() calls.

    Idle eviction: a single sweeper coroutine (started by ``start()``
    and stopped by ``stop()``) walks the cache every
    ``sweep_interval_secs`` and evicts entries whose
    ``last_used`` exceeds ``idle_timeout_secs``. Eviction is best-
    effort and bounded; clients with a ``close()`` method are closed.
    """

    def __init__(
        self,
        *,
        idle_timeout_secs: float = 600.0,
        sweep_interval_secs: float = 60.0,
    ) -> None:
        if idle_timeout_secs <= 0:
            raise ValueError("idle_timeout_secs must be > 0")
        if sweep_interval_secs <= 0:
            raise ValueError("sweep_interval_secs must be > 0")
        self._idle_timeout = idle_timeout_secs
        self._sweep_interval = sweep_interval_secs
        self._entries: dict[tuple[str, str], _PoolEntry] = {}
        self._key_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._sweeper: asyncio.Task[None] | None = None
        self._closing = False

    def _key_lock(self, key: tuple[str, str]) -> asyncio.Lock:
        # setdefault returns the existing value when the key is present,
        # so concurrent misses see the same canonical Lock regardless of
        # which one wins the insert race.
        return self._key_locks.setdefault(key, asyncio.Lock())

    async def get(
        self,
        provider: str,
        account_id: str,
        factory: ClientFactory,
    ) -> BrokerBase:
        """Return the cached client for (provider, account_id), constructing
        it via ``factory`` exactly once when missing.
        """
        if self._closing:
            raise RuntimeError("BrokerClientPool is closed")

        key = (provider, account_id or "unknown")
        # Fast path: hit.
        entry = self._entries.get(key)
        if entry is not None:
            entry.last_used = _time.monotonic()
            return entry.client

        # Slow path: miss. Take the per-key lock so concurrent misses
        # collapse into one factory invocation.
        lock = self._key_lock(key)
        async with lock:
            entry = self._entries.get(key)
            if entry is not None:
                entry.last_used = _time.monotonic()
                return entry.client
            try:
                client = await factory()
            except BaseException:
                # CancelledError must NOT leave a half-built entry. Just
                # re-raise; the next caller will retry.
                raise
            now = _time.monotonic()
            entry = _PoolEntry(
                client=client,
                created_at=now,
                last_used=now,
                provider=provider,
                account_id=account_id or "unknown",
            )
            self._entries[key] = entry
            BROKER_CLIENT_POOL_SIZE.labels(provider=provider).set(sum(1 for k in self._entries if k[0] == provider))
            logger.info(
                "broker_client_pool_added",
                extra={
                    "provider": provider,
                    "account_id": (
                        (account_id[:12] + "...") if account_id and len(account_id) > 12 else (account_id or "unknown")
                    ),
                    "pool_size": len(self._entries),
                },
            )
            return client

    async def evict(self, provider: str, account_id: str, *, reason: str = "explicit") -> bool:
        """Evict a single entry. Returns True when an entry was removed."""
        key = (provider, account_id or "unknown")
        entry = self._entries.pop(key, None)
        if entry is None:
            return False
        await self._close_client_quietly(entry.client)
        BROKER_CLIENT_POOL_EVICTIONS_TOTAL.labels(reason=reason).inc()
        BROKER_CLIENT_POOL_SIZE.labels(provider=provider).set(sum(1 for k in self._entries if k[0] == provider))
        logger.info(
            "broker_client_pool_evicted",
            extra={"provider": provider, "reason": reason},
        )
        return True

    async def _close_client_quietly(self, client: BrokerBase) -> None:
        close = getattr(client, "close", None)
        if close is None:
            return
        try:
            result = close()
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "broker_client_pool_close_failed",
                extra={"error": str(exc)},
            )

    async def _sweep_once(self) -> int:
        now = _time.monotonic()
        to_evict: list[tuple[str, str]] = []
        for key, entry in list(self._entries.items()):
            if (now - entry.last_used) > self._idle_timeout:
                to_evict.append(key)
        for provider, account_id in to_evict:
            await self.evict(provider, account_id, reason="idle")
        return len(to_evict)

    async def _sweeper_loop(self) -> None:
        try:
            while not self._closing:
                try:
                    await asyncio.sleep(self._sweep_interval)
                    if self._closing:
                        return
                    n = await self._sweep_once()
                    if n:
                        logger.debug(
                            "broker_client_pool_sweep",
                            extra={"evicted": n, "remaining": len(self._entries)},
                        )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "broker_client_pool_sweep_failed",
                        extra={"error": str(exc)},
                    )
        except asyncio.CancelledError:
            return

    async def start(self) -> None:
        """Launch the background sweeper. Idempotent."""
        if self._sweeper is None:
            self._sweeper = asyncio.create_task(self._sweeper_loop(), name="broker-client-pool-sweeper")

    async def stop(self) -> None:
        """Cancel the sweeper and close every cached client."""
        self._closing = True
        if self._sweeper is not None:
            self._sweeper.cancel()
            try:
                await self._sweeper
            except (asyncio.CancelledError, Exception):
                pass
            self._sweeper = None
        # Snapshot and clear to avoid mutation-during-iteration.
        entries = list(self._entries.items())
        self._entries.clear()
        for (provider, _), entry in entries:
            await self._close_client_quietly(entry.client)
            BROKER_CLIENT_POOL_EVICTIONS_TOTAL.labels(reason="close").inc()
            BROKER_CLIENT_POOL_SIZE.labels(provider=provider).set(0)

    def size(self) -> int:
        return len(self._entries)
