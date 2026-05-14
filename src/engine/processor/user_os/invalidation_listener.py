"""Async Redis pub/sub listener for user OS cache invalidation.

The gateway publishes a JSON message to the channel
'etradie:user_os:invalidate' after every profile mutation (save,
skip, reset). This listener subscribes to that channel and calls
UserOSCache.invalidate() + UserOSClient.invalidate_local_version()
for the affected user so the next analysis cycle fetches the fresh
profile instead of serving a stale cached block.

FAILURE MODE
------------
The listener runs as a background asyncio task. If Redis is
unavailable or the subscription drops, the listener logs a warning
and retries with exponential backoff. A listener outage degrades
cache invalidation to TTL-based expiry (1 hour for positive entries,
60 seconds for negative entries) -- the LLM pipeline is never
affected.

LIFECYCLE
----------
Start: call start() from the FastAPI lifespan before yield.
Stop:  call stop() from the FastAPI lifespan after yield.
Both are idempotent and safe to call multiple times.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from engine.processor.user_os.client import UserOSClient
from engine.shared.cache import RedisCache
from engine.shared.logging import get_logger

logger = get_logger(__name__)

_CHANNEL = "etradie:user_os:invalidate"
_RECONNECT_BASE_DELAY_S = 1.0
_RECONNECT_MAX_DELAY_S = 60.0


class UserOSInvalidationListener:
    """Subscribes to the gateway's invalidation channel and busts the
    engine-side user OS cache on every profile mutation event.

    Designed to be started once at engine startup and stopped on
    graceful shutdown. The underlying Redis pub/sub connection is
    separate from the shared RedisCache connection pool so a slow
    subscriber never blocks cache reads/writes.
    """

    def __init__(
        self,
        *,
        cache: RedisCache,
        user_os_client: Optional[UserOSClient],
    ) -> None:
        self._cache = cache
        self._user_os_client = user_os_client
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the background listener task."""
        if self._task is not None and not self._task.done():
            return  # Already running.
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._run_with_reconnect(),
            name="user_os_invalidation_listener",
        )
        logger.info(
            "user_os_invalidation_listener_started",
            extra={"channel": _CHANNEL},
        )

    async def stop(self) -> None:
        """Signal the listener to stop and wait for it to exit."""
        self._stop_event.set()
        if self._task is not None and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        logger.info("user_os_invalidation_listener_stopped")

    async def _run_with_reconnect(self) -> None:
        """Outer loop: reconnect with exponential backoff on any error."""
        delay = _RECONNECT_BASE_DELAY_S
        while not self._stop_event.is_set():
            try:
                await self._subscribe_loop()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                logger.warning(
                    "user_os_invalidation_listener_error",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "reconnect_in_seconds": delay,
                    },
                )
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=delay
                    )
                except asyncio.TimeoutError:
                    pass
                delay = min(delay * 2, _RECONNECT_MAX_DELAY_S)
            else:
                # Clean exit from _subscribe_loop means stop was requested.
                break

    async def _subscribe_loop(self) -> None:
        """Inner loop: subscribe and process messages until stop is set."""
        # Use the raw aioredis PubSub object from the shared cache.
        # The shared cache's connection pool is NOT used for pub/sub
        # (pub/sub requires a dedicated connection); pubsub() creates
        # a new connection automatically.
        pubsub = self._cache.pubsub()
        try:
            await pubsub.subscribe(_CHANNEL)
            logger.debug(
                "user_os_invalidation_subscribed",
                extra={"channel": _CHANNEL},
            )
            while not self._stop_event.is_set():
                # get_message with a short timeout so we can check
                # stop_event frequently without blocking indefinitely.
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message is None:
                    continue
                await self._handle_message(message)
        finally:
            try:
                await pubsub.unsubscribe(_CHANNEL)
                await pubsub.aclose()
            except Exception:
                pass

    async def _handle_message(self, message: dict) -> None:
        """Process a single invalidation message."""
        try:
            raw = message.get("data", b"")
            if isinstance(raw, int):
                # Subscription confirmation integer -- ignore.
                return
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            payload = json.loads(raw)
            user_id = str(payload.get("user_id", "")).strip()
            event = str(payload.get("event", "")).strip()
            if not user_id:
                return
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            logger.warning(
                "user_os_invalidation_bad_message",
                extra={"error": str(exc), "raw": str(message)[:200]},
            )
            return

        # 1. Bust the Redis negative-cache sentinel.
        if self._user_os_client is not None:
            await self._user_os_client.user_os_cache.invalidate(
                user_id, trace_id=None
            )
            # 2. Clear the in-process version cache so the next
            #    get_compressed_context() call goes back to HTTP to
            #    learn the new version.
            await self._user_os_client.invalidate_local_version(user_id)

        logger.info(
            "user_os_cache_invalidated_via_pubsub",
            extra={"user_id": user_id, "event": event},
        )
