"""Broker heartbeat service.

Runs one async task per active broker connection. Each task:
  1. Calls a provider-specific HealthProbe (HEALTH for ZMQ;
     account-info GET for MetaAPI).
  2. Writes the result to Redis hash
     'etradie:broker:hb:<provider>:<account_id>' so the gateway can
     surface it to the dashboard without hitting the broker itself.
  3. Increments Prometheus counters.
  4. After N consecutive failures, marks the connection DEGRADED.
  5. After a recovery (a single successful probe after degradation),
     marks it CONNECTED again.

The service is process-wide; the engine startup hook constructs it
with the global Redis client + scheduler manager and registers a
probe function per active broker connection at engine boot.

The probe contract is intentionally narrow (returns HeartbeatResult)
so both ZmqClient and MetaApiClient can plug in without coupling to
anything inside this module.

Audit ref: CHECKLIST Section 2 - 'Heartbeat system per MT terminal',
'Detection of silent disconnect'.
"""
from __future__ import annotations

import asyncio
import json
import time as _time
from dataclasses import dataclass, field
from enum import StrEnum, unique
from typing import Awaitable, Callable

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    BROKER_CONNECTION_STATE,
    BROKER_HEARTBEAT_FAILURES_TOTAL,
    BROKER_HEARTBEAT_TOTAL,
)

logger = get_logger(__name__)


@unique
class HeartbeatState(StrEnum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HeartbeatResult:
    """Result of one HealthProbe invocation.

    Attributes:
        ok: True when the probe completed and the broker reports
            connected+authenticated. False otherwise.
        broker_connected: Broker-reported terminal-to-broker state.
        authenticated: EA-reported auth state (ZMQ only; MetaAPI
            always True when ok=True).
        uptime_seconds: Broker-reported uptime; 0 when unknown.
        raw: Free-form dict for debugging; persisted to Redis.
        error_type: Type name of the exception that caused ok=False;
            empty when ok=True.
        error_message: Truncated str(exception).
    """

    ok: bool
    broker_connected: bool = False
    authenticated: bool = False
    uptime_seconds: float = 0.0
    raw: dict = field(default_factory=dict)
    error_type: str = ""
    error_message: str = ""


HeartbeatProbeFn = Callable[[], Awaitable[HeartbeatResult]]


@dataclass
class _ConnState:
    """Per-connection mutable state held by the service."""

    provider: str
    account_id: str
    probe: HeartbeatProbeFn
    consecutive_failures: int = 0
    state: HeartbeatState = HeartbeatState.UNKNOWN
    last_success_ts: float = 0.0
    task: asyncio.Task | None = None


class BrokerHeartbeatService:
    """Manages heartbeat tasks across all active broker connections.

    The service is intentionally not a singleton; the engine startup
    constructs one instance and passes it through DI. Construct with
    a Redis client and the connectivity-config values; call register()
    for each broker connection at startup and unregister() at
    connection-delete time.
    """

    REDIS_HASH_PREFIX = "etradie:broker:hb:"

    def __init__(
        self,
        *,
        redis_client,
        interval_secs: float,
        timeout_secs: float,
        failure_threshold: int,
    ) -> None:
        if interval_secs <= 0:
            raise ValueError("interval_secs must be > 0")
        if timeout_secs <= 0 or timeout_secs > interval_secs:
            raise ValueError("timeout_secs must be > 0 and <= interval_secs")
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self._redis = redis_client
        self._interval = interval_secs
        self._timeout = timeout_secs
        self._failure_threshold = failure_threshold
        self._connections: dict[tuple[str, str], _ConnState] = {}
        self._stopped = asyncio.Event()

    # -- Public API ----------------------------------------------------

    def register(
        self,
        *,
        provider: str,
        account_id: str,
        probe: HeartbeatProbeFn,
    ) -> None:
        """Start the heartbeat loop for a new connection.

        Idempotent: re-registering the same (provider, account_id)
        cancels the existing task and starts a new one with the
        supplied probe. This is what happens when a user re-provisions
        their broker connection (creds change, hosted Deployment
        recreated, etc.).
        """
        key = (provider, account_id)
        existing = self._connections.get(key)
        if existing is not None and existing.task is not None and not existing.task.done():
            existing.task.cancel()
        state = _ConnState(
            provider=provider,
            account_id=account_id,
            probe=probe,
        )
        state.task = asyncio.create_task(
            self._loop(state),
            name=f"broker-heartbeat:{provider}:{account_id}",
        )
        self._connections[key] = state

    def unregister(self, *, provider: str, account_id: str) -> None:
        """Stop the heartbeat loop and clear the Redis hash."""
        key = (provider, account_id)
        state = self._connections.pop(key, None)
        if state is None:
            return
        if state.task is not None and not state.task.done():
            state.task.cancel()
        # Best-effort Redis cleanup; fire-and-forget to avoid blocking
        # the caller (connection-delete is a hot path).
        asyncio.create_task(self._delete_hash(provider, account_id))

    async def stop(self) -> None:
        """Cancel every loop. Called on engine shutdown."""
        self._stopped.set()
        tasks = [
            s.task for s in self._connections.values()
            if s.task is not None and not s.task.done()
        ]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._connections.clear()

    def state_of(self, *, provider: str, account_id: str) -> HeartbeatState:
        """Return the in-memory state. The dashboard reads Redis directly;
        this getter is for tests + the engine's own /readiness check."""
        s = self._connections.get((provider, account_id))
        return s.state if s is not None else HeartbeatState.UNKNOWN

    # -- Internal ------------------------------------------------------

    async def _loop(self, state: _ConnState) -> None:
        """Per-connection heartbeat loop. Cancellation-safe.

        The loop deliberately sleeps the full interval AFTER the probe
        completes (not before) so the first tick happens immediately
        on registration - the dashboard sees a green light within
        seconds of a successful provision_account().
        """
        while not self._stopped.is_set():
            try:
                try:
                    result = await asyncio.wait_for(
                        state.probe(),
                        timeout=self._timeout,
                    )
                except asyncio.TimeoutError:
                    result = HeartbeatResult(
                        ok=False,
                        error_type="TimeoutError",
                        error_message=f"probe timed out after {self._timeout}s",
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    result = HeartbeatResult(
                        ok=False,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:500],
                    )
                self._apply_result(state, result)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "broker_heartbeat_loop_unexpected_error",
                    extra={
                        "provider": state.provider,
                        "account_id": state.account_id,
                        "error": str(exc),
                    },
                    exc_info=True,
                )
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                raise

    def _apply_result(self, state: _ConnState, result: HeartbeatResult) -> None:
        # -- Update Prometheus counters
        if result.ok:
            BROKER_HEARTBEAT_TOTAL.labels(
                provider=state.provider,
                account_id=state.account_id,
                status="ok",
            ).inc()
            state.consecutive_failures = 0
            state.last_success_ts = _time.time()
            previous = state.state
            state.state = HeartbeatState.CONNECTED
            BROKER_CONNECTION_STATE.labels(
                provider=state.provider,
                account_id=state.account_id,
            ).set(1)
            if previous != HeartbeatState.CONNECTED:
                logger.info(
                    "broker_heartbeat_recovered",
                    extra={
                        "provider": state.provider,
                        "account_id": state.account_id,
                        "previous_state": previous.value,
                    },
                )
        else:
            BROKER_HEARTBEAT_TOTAL.labels(
                provider=state.provider,
                account_id=state.account_id,
                status="failed",
            ).inc()
            BROKER_HEARTBEAT_FAILURES_TOTAL.labels(
                provider=state.provider,
                account_id=state.account_id,
                error_type=result.error_type or "unknown",
            ).inc()
            state.consecutive_failures += 1
            if state.consecutive_failures >= self._failure_threshold:
                previous = state.state
                state.state = (
                    HeartbeatState.DISCONNECTED
                    if not result.broker_connected
                    else HeartbeatState.DEGRADED
                )
                BROKER_CONNECTION_STATE.labels(
                    provider=state.provider,
                    account_id=state.account_id,
                ).set(0)
                if previous != state.state:
                    logger.warning(
                        "broker_heartbeat_degraded",
                        extra={
                            "provider": state.provider,
                            "account_id": state.account_id,
                            "previous_state": previous.value,
                            "new_state": state.state.value,
                            "consecutive_failures": state.consecutive_failures,
                            "error_type": result.error_type,
                        },
                    )

        # -- Persist to Redis (best-effort)
        asyncio.create_task(self._write_hash(state, result))

    async def _write_hash(self, state: _ConnState, result: HeartbeatResult) -> None:
        try:
            key = self.REDIS_HASH_PREFIX + f"{state.provider}:{state.account_id}"
            payload = {
                "state": state.state.value,
                "ok": "1" if result.ok else "0",
                "broker_connected": "1" if result.broker_connected else "0",
                "authenticated": "1" if result.authenticated else "0",
                "uptime_seconds": str(int(result.uptime_seconds)),
                "last_seen_at": str(int(_time.time())),
                "consecutive_failures": str(state.consecutive_failures),
                "error_type": result.error_type,
                "raw": json.dumps(result.raw, default=str)[:2000],
            }
            await self._redis.hset(key, mapping=payload)
            # 2x interval so a transient Redis outage does not blank the
            # dashboard immediately; the next successful tick refreshes.
            await self._redis.expire(key, int(self._interval * 4))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "broker_heartbeat_redis_write_failed",
                extra={
                    "provider": state.provider,
                    "account_id": state.account_id,
                    "error": str(exc),
                },
            )

    async def _delete_hash(self, provider: str, account_id: str) -> None:
        try:
            key = self.REDIS_HASH_PREFIX + f"{provider}:{account_id}"
            await self._redis.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "broker_heartbeat_redis_delete_failed",
                extra={
                    "provider": provider,
                    "account_id": account_id,
                    "error": str(exc),
                },
            )
