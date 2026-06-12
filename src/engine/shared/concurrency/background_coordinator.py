"""Background task coordinator for the chart-candles pipeline.

Provides a single, reusable primitive that solves three problems the
fire-and-forget ``asyncio.create_task`` pattern in the chart endpoint
introduced:

  1. **Idempotency / cooldown.** A pre-warm wave for (user, symbol) must
     fire at most once per cooldown window, regardless of how many cache
     hits occur for that symbol's timeframes in the meantime. Without
     this guard, every dashboard click stacks another 13-fetch wave on
     the broker, eventually exhausting MetaAPI's per-account rate budget
     and producing the cascade of 504s and connection resets that
     motivates this branch.

  2. **Single-flight per key.** Two simultaneous cache hits for the same
     (user, symbol) must coalesce onto one wave, not two. The cooldown
     guard alone is racy under concurrent cache hits because both hits
     can read "no recent wave" and both schedule one. We resolve this
     deterministically with a per-key asyncio.Lock checked under the
     same critical section as the cooldown timestamp.

  3. **Lifecycle ownership.** Every spawned task is registered in a
     WeakSet so the FastAPI lifespan can cancel them cleanly on shutdown
     and so they cannot be garbage-collected mid-flight (which CPython
     does not actually do for live tasks but the diagnostic warning is
     still emitted under PYTHONDEVMODE). Spawned coroutines are wrapped
     in a top-level try/except so a single buggy wave can never crash
     the engine event loop.

The coordinator is deliberately framework-agnostic. It knows nothing
about chart candles, MetaAPI, Redis, or HTTP -- it only orchestrates
the scheduling of opaque async callables keyed by an opaque string.
This keeps the unit-test surface narrow and makes the same primitive
reusable for any future SWR pipeline (account info, positions, symbol
info) that needs the same guarantees.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from weakref import WeakSet

from engine.shared.logging import get_logger

logger = get_logger(__name__)


class BackgroundTaskCoordinator:
    """Schedule and bound opaque background tasks keyed by string.

    Public surface:
        * schedule_once(key, factory, *, cooldown_s, timeout_s)
            Spawn a wave for ``key`` if and only if no wave was scheduled
            for the same key within the last ``cooldown_s`` seconds.
            The spawned task is wrapped with ``asyncio.wait_for`` so it
            cannot run longer than ``timeout_s``.

        * shutdown()
            Cancel every in-flight task and wait briefly for them to
            unwind. Idempotent.

    Thread-safety: this primitive is single-event-loop. All public
    methods must be called from the loop that owns the coordinator.
    """

    __slots__ = (
        "_in_flight",
        "_last_started",
        "_locks",
        "_shutdown",
        "_tasks",
    )

    def __init__(self) -> None:
        # Per-key monotonic timestamp of the last successfully scheduled wave.
        # We read+write this under the per-key lock so the cooldown check
        # is atomic with the spawn decision.
        self._last_started: dict[str, float] = {}
        # Per-key lock so the cooldown check + spawn decision is atomic.
        # Locks are kept around (not GC'd) because a busy key will keep
        # using the same lock; the bookkeeping is O(unique keys ever seen)
        # which is bounded in practice by users × symbols.
        self._locks: dict[str, asyncio.Lock] = {}
        # Set of currently-running asyncio.Task objects so shutdown can
        # cancel them. WeakSet so completed tasks self-evict.
        self._tasks: WeakSet[asyncio.Task] = WeakSet()
        # Number of currently-in-flight tasks per key. Used to keep the
        # idempotency guarantee correct when a wave is already running
        # AND its cooldown has elapsed; without this counter we could
        # spawn a duplicate wave concurrent with the first.
        self._in_flight: dict[str, int] = {}
        self._shutdown = False

    def _lock_for(self, key: str) -> asyncio.Lock:
        lk = self._locks.get(key)
        if lk is None:
            lk = asyncio.Lock()
            self._locks[key] = lk
        return lk

    async def schedule_once(
        self,
        key: str,
        factory: Callable[[], Awaitable[None]],
        *,
        cooldown_s: float,
        timeout_s: float,
    ) -> bool:
        """Schedule a one-shot background wave for ``key`` if eligible.

        Eligibility (all must hold):
          * coordinator is not shutting down;
          * no other wave for ``key`` is currently in flight;
          * the last successfully scheduled wave for ``key`` is older
            than ``cooldown_s`` seconds (or none has ever run).

        Returns True if a wave was spawned, False if it was suppressed.
        Returning False is the normal case under heavy click load and
        is not an error.

        ``factory`` is invoked with no arguments and must return a
        coroutine. We do not accept a coroutine directly because if
        eligibility fails we must NOT have created one (creating an
        un-awaited coroutine triggers a RuntimeWarning).
        """
        if self._shutdown:
            return False

        lock = self._lock_for(key)
        async with lock:
            if self._in_flight.get(key, 0) > 0:
                return False
            now = time.monotonic()
            last = self._last_started.get(key, 0.0)
            if (now - last) < cooldown_s:
                return False
            # Commit: record the spawn before releasing the lock so a
            # concurrent caller observes the cooldown immediately.
            self._last_started[key] = now
            self._in_flight[key] = self._in_flight.get(key, 0) + 1

        task = asyncio.create_task(
            self._run_guarded(key, factory, timeout_s),
            name=f"bg-coord:{key}",
        )
        self._tasks.add(task)
        return True

    async def _run_guarded(
        self,
        key: str,
        factory: Callable[[], Awaitable[None]],
        timeout_s: float,
    ) -> None:
        try:
            try:
                await asyncio.wait_for(factory(), timeout=timeout_s)
            except TimeoutError:
                logger.warning(
                    "background_task_timeout",
                    extra={"key": key, "timeout_seconds": timeout_s},
                )
            except asyncio.CancelledError:
                # Re-raise so the task is recorded as cancelled rather
                # than swallowed -- shutdown() relies on this.
                raise
            except Exception as exc:
                logger.warning(
                    "background_task_failed",
                    extra={
                        "key": key,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
        finally:
            # Decrement under the per-key lock so a concurrent
            # schedule_once() observes the post-completion state
            # atomically with the cooldown timestamp.
            try:
                async with self._lock_for(key):
                    n = self._in_flight.get(key, 0) - 1
                    if n <= 0:
                        self._in_flight.pop(key, None)
                    else:
                        self._in_flight[key] = n
            except Exception:  # nosec B110
                # Bookkeeping must never propagate.
                pass

    async def shutdown(self, *, drain_timeout_s: float = 2.0) -> None:
        """Cancel every in-flight task and wait briefly for them to unwind.

        Idempotent. Safe to call from the FastAPI lifespan shutdown hook.
        """
        if self._shutdown:
            return
        self._shutdown = True
        tasks = [t for t in self._tasks if not t.done()]
        for t in tasks:
            t.cancel()
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=drain_timeout_s,
                )
            except TimeoutError:
                logger.warning(
                    "background_task_coordinator_shutdown_drain_timeout",
                    extra={
                        "pending": sum(1 for t in tasks if not t.done()),
                        "drain_timeout_s": drain_timeout_s,
                    },
                )
