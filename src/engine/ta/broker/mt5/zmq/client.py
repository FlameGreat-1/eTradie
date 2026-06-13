"""ZeroMQ REQ/REP client implementing BrokerBase.

Communicates with the ZeroMQ Expert Advisor running on a Windows
PC's MT5 terminal.  Uses a simple JSON protocol over ZeroMQ
REQ/REP sockets.

Protocol commands:
    PING                -> {"status": "ok"}
    CANDLES             -> [{"time": ..., "open": ..., ...}, ...]
    CANDLE_LATEST       -> {"time": ..., "open": ..., ...}
    SYMBOL_INFO         -> {"symbol": ..., "digits": ..., ...}

All blocking zmq operations are wrapped in asyncio.to_thread
so the event loop is never blocked.
"""

from __future__ import annotations

import asyncio
import time as _time
from datetime import UTC, datetime
from typing import Any

import zmq
import zmq.asyncio as zmq_async

from engine.shared.exceptions import (
    ProviderError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    BROKER_INFLIGHT_GATE_REJECTIONS_TOTAL,
    BROKER_INFLIGHT_GATE_WAIT_SECONDS,
    BROKER_REQUEST_DEADLINE_EXCEEDED_TOTAL,
    PROVIDER_RESPONSE_SIZE,
    TA_BROKER_ERRORS_TOTAL,
    TA_BROKER_FETCH_DURATION,
)
from engine.ta.broker.base import (
    AccountInfo,
    BrokerBase,
    BrokerCapabilities,
    HistoryDealInfo,
    OrderResult,
    PendingOrderInfo,
    PositionInfo,
    TickPrice,
)
from engine.ta.broker.connectivity import (
    HeartbeatResult,
    OutboundRateLimiter,
    ReconnectPolicy,
    TickFreshnessGuard,
)
from engine.ta.broker.mt5.clock_skew import ClockSkewMonitor, EAClockSample
from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.ea_identity import (
    EAIdentitySnapshot,
    EAIdentityVerifier,
    ExpectedEAIdentity,
)
from engine.ta.broker.validator import BrokerDataValidator
from engine.ta.constants import Timeframe
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)

_ZMQ_TIMEFRAME_MAP: dict[Timeframe, str] = {
    Timeframe.M1: "M1",
    Timeframe.M5: "M5",
    Timeframe.M15: "M15",
    Timeframe.M30: "M30",
    Timeframe.H1: "H1",
    Timeframe.H3: "H3",
    Timeframe.H4: "H4",
    Timeframe.H6: "H6",
    Timeframe.H8: "H8",
    Timeframe.H12: "H12",
    Timeframe.D1: "D1",
    Timeframe.W1: "W1",
    Timeframe.MN1: "MN1",
}


class ZmqClient(BrokerBase):
    """Native ZeroMQ bridge to a Windows MT5 terminal."""

    def __init__(  # nosec B107
        self,
        config: MT5Config,
        auth_token: str = "",
        *,
        freshness_guard: TickFreshnessGuard | None = None,
        reconnect_policy: ReconnectPolicy | None = None,
        identity_verifier: EAIdentityVerifier | None = None,
        expected_identity: ExpectedEAIdentity | None = None,
        clock_skew_monitor: ClockSkewMonitor | None = None,
        outbound_limiter: OutboundRateLimiter | None = None,
        inflight_limit: int = 0,
        outbound_limit_deadline_secs: float = 0.5,
    ) -> None:
        super().__init__(broker_id="mt5")
        self.config = config
        self.auth_token = (auth_token or getattr(config, "zmq_auth_token", "")).strip()
        self.validator = BrokerDataValidator()
        # None defaults preserve prior behaviour bit-for-bit. The engine
        # factory wires production-grade defaults; tests that construct
        # ZmqClient directly are unaffected. Audit ref: CHECKLIST Section 2.
        self._freshness_guard = freshness_guard
        self._reconnect_policy = reconnect_policy
        # Section 4 (CHECKLIST): EA identity verification + clock skew.
        self._identity_verifier = identity_verifier
        self._expected_identity = expected_identity
        self._clock_skew = clock_skew_monitor
        self._identity_verified = False
        # Section 5 (CHECKLIST): outbound rate limit + in-flight gate.
        # The outbound limiter throttles ENGINE -> EA traffic so a
        # misbehaving analysis loop cannot flood one user's EA. The
        # in-flight gate caps the number of concurrent commands on the
        # TRADING socket only (candles socket already runs on its own
        # lock+socket pair and must remain unthrottled to keep CANDLES
        # independent of trading throughput).
        self._outbound_limiter = outbound_limiter
        self._outbound_limit_deadline_secs = max(0.0, float(outbound_limit_deadline_secs))
        self._inflight_limit = max(0, int(inflight_limit))
        self._inflight_gate: asyncio.Semaphore | None = (
            asyncio.Semaphore(self._inflight_limit) if self._inflight_limit > 0 else None
        )
        self._endpoint = f"tcp://{config.zmq_host}:{config.zmq_port}"
        # The trading socket carries every command except CANDLES: ticks,
        # account info, positions, order placement, modifications. It must
        # remain responsive at all times.
        self._ctx: zmq_async.Context | None = None  # type: ignore[type-arg]
        self._socket: zmq_async.Socket | None = None  # type: ignore[type-arg]
        self._lock = asyncio.Lock()
        self._initialized = False
        # CHECKLIST hardening: track when the trading socket last
        # came up so a successful tick fetch shortly afterward can
        # be attributed to a 'recovery' for SLO observability. See
        # docs/architecture/broker-connectivity.md for the contract.
        self._connect_ts: float = 0.0
        # Window during which a successful get_tick_price() after a
        # (re)connect counts as a 'tick recovery'. Wider than typical
        # broker reply latency (~250ms) so a slow reply still
        # counts; tight enough that an unrelated tick fetch hours
        # later does NOT inflate the metric.
        self._tick_recovery_window_secs: float = 30.0
        # The candles socket is a fully isolated REQ/REP pair used only by
        # fetch_candles(). The MT5 EA binds a single REP socket but ZMQ
        # serializes replies internally, so two REQ clients can submit work
        # in parallel without corrupting each other's REQ/REP state machine.
        # Isolating the historical-data path means a slow CopyRates() call
        # for a fresh intraday symbol never blocks live tick polling, order
        # placement, or position monitoring on the trading socket.
        self._candles_socket: zmq_async.Socket | None = None  # type: ignore[type-arg]
        self._candles_lock = asyncio.Lock()
        self._candles_initialized = False

    @property
    def provider_name(self) -> str:
        return "zmq"

    @property
    def account_id(self) -> str:
        return f"{self.config.zmq_host}:{self.config.zmq_port}"

    # -- Connection management -------------------------------------------------

    def _ensure_context(self) -> None:
        """Lazily create the shared ZMQ context."""
        if self._ctx is None:
            self._ctx = zmq_async.Context()

    def _connect_sync(self) -> None:
        """Create the trading REQ socket (used by every non-CANDLES command)."""
        if self._initialized:
            return
        self._ensure_context()
        assert self._ctx is not None
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.setsockopt(zmq.RCVTIMEO, self.config.timeout_seconds * 1000)
        self._socket.setsockopt(zmq.SNDTIMEO, self.config.timeout_seconds * 1000)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.connect(self._endpoint)
        self._initialized = True
        # Record the connect moment so a successful tick fetch shortly
        # afterward can be attributed to recovery. See
        # get_tick_price() for the metric increment.
        self._connect_ts = _time.monotonic()
        logger.info(
            "zmq_connected",
            extra={"endpoint": self._endpoint, "socket": "trading"},
        )

    def _connect_candles_sync(self) -> None:
        """Create the candles-only REQ socket."""
        if self._candles_initialized:
            return
        self._ensure_context()
        assert self._ctx is not None
        self._candles_socket = self._ctx.socket(zmq.REQ)
        self._candles_socket.setsockopt(zmq.RCVTIMEO, self.config.timeout_seconds * 1000)
        self._candles_socket.setsockopt(zmq.SNDTIMEO, self.config.timeout_seconds * 1000)
        self._candles_socket.setsockopt(zmq.LINGER, 0)
        self._candles_socket.connect(self._endpoint)
        self._candles_initialized = True
        logger.info(
            "zmq_connected",
            extra={"endpoint": self._endpoint, "socket": "candles"},
        )

    async def _send_recv_async(self, request: dict[str, Any]) -> dict[str, Any] | list[Any]:
        """Send JSON request and receive JSON response on the trading socket."""
        return await self._send_recv_on(self._socket, request, socket_label="trading")

    async def _send_recv_candles_async(self, request: dict[str, Any]) -> dict[str, Any] | list[Any]:
        """Send JSON request and receive JSON response on the candles socket."""
        return await self._send_recv_on(self._candles_socket, request, socket_label="candles")

    async def _send_recv_on(
        self,
        sock: zmq_async.Socket | None,
        request: dict[str, Any],
        *,
        socket_label: str,
    ) -> dict[str, Any] | list[Any]:
        """Shared send/recv implementation parameterised by socket."""
        import json

        if sock is None:
            raise ProviderUnavailableError(
                "ZMQ socket not initialized",
                details={"endpoint": self._endpoint, "socket": socket_label},
            )

        payload = json.dumps(request).encode("utf-8")
        try:
            async with asyncio.timeout(self.config.timeout_seconds):
                await sock.send(payload)
        except TimeoutError:
            raise ProviderTimeoutError(
                "ZMQ send timed out",
                details={
                    "endpoint": self._endpoint,
                    "socket": socket_label,
                    "timeout": self.config.timeout_seconds,
                },
            )

        try:
            async with asyncio.timeout(self.config.timeout_seconds):
                raw_reply = await sock.recv()
        except TimeoutError:
            raise ProviderTimeoutError(
                "ZMQ recv timed out",
                details={
                    "endpoint": self._endpoint,
                    "socket": socket_label,
                    "timeout": self.config.timeout_seconds,
                },
            )

        decoded_reply = raw_reply.decode("utf-8")
        reply = [] if not decoded_reply else json.loads(decoded_reply)

        # Check for EA-level errors.
        if isinstance(reply, dict) and reply.get("error"):
            raise ProviderResponseError(
                f"ZMQ EA error: {reply['error']}",
                details={"reply": reply, "socket": socket_label},
            )

        from typing import cast

        return cast(dict[str, Any] | list[Any], reply)

    async def _request(
        self,
        request: dict[str, Any],
        *,
        request_deadline_secs: float | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Thread-safe async wrapper around the trading-socket ZMQ call.

        Section 5 additions:
          - outbound rate limiter is checked BEFORE acquiring the lock
            so a throttled call returns fast and does not block the
            socket.
          - in-flight gate caps concurrent trading-socket commands.
          - request_deadline_secs propagates the upstream HTTP request
            deadline so a slow EA cannot pin the engine after the
            upstream gateway has given up.
        """
        # 1) Outbound rate limit (per provider/account_id).
        if self._outbound_limiter is not None:
            await self._outbound_limiter.raise_if_exhausted(deadline_secs=self._outbound_limit_deadline_secs)

        # 2) In-flight gate. Bounded by request_deadline so a backlog
        # cannot silently build up.
        gate_deadline = request_deadline_secs if request_deadline_secs and request_deadline_secs > 0 else 5.0
        if self._inflight_gate is not None:
            gate_start = _time.monotonic()
            try:
                async with asyncio.timeout(gate_deadline):
                    await self._inflight_gate.acquire()
            except TimeoutError:
                BROKER_INFLIGHT_GATE_REJECTIONS_TOTAL.labels(
                    provider="zmq",
                    account_id=self.account_id,
                ).inc()
                raise ProviderTimeoutError(
                    "in-flight gate exhausted before deadline",
                    details={
                        "endpoint": self._endpoint,
                        "gate_deadline_secs": gate_deadline,
                        "inflight_limit": self._inflight_limit,
                    },
                )
            BROKER_INFLIGHT_GATE_WAIT_SECONDS.labels(provider="zmq").observe(_time.monotonic() - gate_start)

        try:
            return await self._request_inner(request, request_deadline_secs=request_deadline_secs)
        finally:
            if self._inflight_gate is not None:
                self._inflight_gate.release()

    async def _request_inner(
        self,
        request: dict[str, Any],
        *,
        request_deadline_secs: float | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Original _request body. Kept as a separate inner method so
        the Section-5 gating wraps it without disturbing the legacy
        socket recovery logic.
        """
        async with self._lock:
            try:
                was_initialized = self._initialized
                if not self._initialized:
                    self._connect_sync()

                # Auto-authenticate on first connect (or reconnect) if it's not a PING command
                if not was_initialized and request.get("command") not in (
                    "PING",
                    "HEALTH",
                ):
                    try:
                        await self._send_recv_async({"command": "PING", "auth_token": self.auth_token})
                    except ProviderResponseError as e:
                        logger.warning("zmq_initial_auth_failed", extra={"error": str(e)})
                # Section 4 (CHECKLIST): one-shot identity verification on
                # every fresh authenticated socket. Reset _identity_verified
                # so a reconnect re-verifies. Skipped for EA_IDENTITY itself
                # to avoid infinite recursion, and for the lightweight
                # PING/HEALTH/EA_CLOCK heartbeat paths to keep them cheap.
                if (
                    not was_initialized
                    and self._identity_verifier is not None
                    and self._expected_identity is not None
                    and not self._identity_verified
                    and request.get("command")
                    not in (
                        "PING",
                        "HEALTH",
                        "EA_IDENTITY",
                        "EA_CLOCK",
                    )
                ):
                    try:
                        ident_raw = await self._send_recv_async({"command": "EA_IDENTITY"})
                        if isinstance(ident_raw, dict):
                            snapshot = EAIdentitySnapshot.from_dict(ident_raw)
                            self._identity_verifier.verify(snapshot, self._expected_identity)
                            self._identity_verified = True
                    except ProviderResponseError:
                        # Old EA build does not understand EA_IDENTITY -
                        # leave _identity_verified=False; callers can
                        # still drive verification explicitly via
                        # ea_identity().
                        logger.warning(
                            "zmq_identity_command_unsupported",
                            extra={"endpoint": self._endpoint},
                        )

                # Section 5: if a deadline is in play, wrap the send/recv
                # in asyncio.timeout so a slow EA does not pin the engine.
                try:
                    if request_deadline_secs and request_deadline_secs > 0:
                        async with asyncio.timeout(request_deadline_secs):
                            return await self._send_recv_async(request)
                    return await self._send_recv_async(request)
                except TimeoutError:
                    BROKER_REQUEST_DEADLINE_EXCEEDED_TOTAL.labels(
                        provider="zmq",
                        account_id=self.account_id,
                    ).inc()
                    raise ProviderTimeoutError(
                        "request deadline elapsed waiting for EA reply",
                        details={
                            "endpoint": self._endpoint,
                            "request_deadline_secs": request_deadline_secs,
                        },
                    )
                except ProviderResponseError as e:
                    # Re-auth inline if the EA was restarted (ZMQ socket is stateless, so EA forgets us)
                    if "Not authenticated" in str(e):
                        try:
                            await self._send_recv_async({"command": "PING", "auth_token": self.auth_token})
                        except ProviderResponseError as ping_e:
                            raise ping_e from e

                        # Retry original request after successful re-auth
                        return await self._send_recv_async(request)
                    raise
            except ProviderResponseError:
                # Normal EA responses containing errors (e.g., {"error": "Invalid symbol"})
                # mean the request-reply cycle finished successfully. We just re-raise.
                raise
            except asyncio.CancelledError as e:
                # If the HTTP client (e.g. Go execution service) times out and cancels
                # the request, FastAPI raises CancelledError. We MUST destroy the ZMQ
                # socket because it is still waiting for a reply from MT5. Leaving it
                # open poisons the REQ/REP sequence for the next caller.
                logger.warning("zmq_request_cancelled_resetting", extra={"error": str(e)})
                if self._socket:
                    self._socket.close(linger=0)
                    self._socket = None
                self._initialized = False
                raise
            except Exception as e:
                # Any other error (Timeout, ZMQError) means the REQ/REP state machine
                # is desynchronized or poisoned. We MUST destroy the socket to recover.
                logger.warning("zmq_socket_poisoned_resetting", extra={"error": str(e)})
                if self._socket:
                    self._socket.close(linger=0)
                    self._socket = None
                self._initialized = False
                # Section 4: a reset wipes the identity-verified flag
                # so the next request re-verifies on the new socket.
                self._identity_verified = False
                raise

    async def _request_candles(self, request: dict[str, Any]) -> dict[str, Any] | list[Any]:
        """Thread-safe async wrapper around the candles-socket ZMQ call.

        Mirrors _request() but operates on the dedicated candles socket so a
        slow CopyRates() call inside the EA cannot block the trading socket.
        Recovery semantics are identical: on cancellation or any non-EA
        exception the candles socket is destroyed and reconnected on the
        next call to keep the REQ/REP state machine consistent.
        """
        async with self._candles_lock:
            try:
                was_initialized = self._candles_initialized
                if not self._candles_initialized:
                    self._connect_candles_sync()

                # Each ZMQ socket is independently authenticated by the EA.
                if not was_initialized:
                    try:
                        await self._send_recv_candles_async({"command": "PING", "auth_token": self.auth_token})
                    except ProviderResponseError as e:
                        logger.warning(
                            "zmq_candles_initial_auth_failed",
                            extra={"error": str(e)},
                        )

                try:
                    return await self._send_recv_candles_async(request)
                except ProviderResponseError as e:
                    if "Not authenticated" in str(e):
                        try:
                            await self._send_recv_candles_async({"command": "PING", "auth_token": self.auth_token})
                        except ProviderResponseError as ping_e:
                            raise ping_e from e
                        return await self._send_recv_candles_async(request)
                    raise
            except ProviderResponseError:
                raise
            except asyncio.CancelledError as e:
                logger.warning(
                    "zmq_candles_request_cancelled_resetting",
                    extra={"error": str(e)},
                )
                if self._candles_socket:
                    self._candles_socket.close(linger=0)
                    self._candles_socket = None
                self._candles_initialized = False
                raise
            except Exception as e:
                logger.warning(
                    "zmq_candles_socket_poisoned_resetting",
                    extra={"error": str(e)},
                )
                if self._candles_socket:
                    self._candles_socket.close(linger=0)
                    self._candles_socket = None
                self._candles_initialized = False
                raise

    # -- BrokerBase implementation ---------------------------------------------

    async def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_realtime=True,
            supports_historical=True,
            supports_tick_data=self.config.enable_tick_data,
            supports_symbol_info=True,
            max_candles_per_request=self.config.max_candles_per_request,
            rate_limit_per_minute=1000,
            requires_authentication=True,
        )

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        count: int | None = None,
    ) -> CandleSequence:
        if start_time and end_time:
            self.validator.validate_time_range(start_time, end_time)

        zmq_tf = _ZMQ_TIMEFRAME_MAP.get(timeframe)
        if zmq_tf is None:
            raise ProviderError(
                f"Unsupported timeframe: {timeframe}",
                details={"timeframe": timeframe},
            )

        start_timer = _time.monotonic()

        try:
            request: dict[str, Any] = {
                "command": "CANDLES",
                "symbol": symbol,
                "timeframe": zmq_tf,
            }
            if count:
                request["count"] = min(count, self.config.max_candles_per_request)
            else:
                request["count"] = 500
            if start_time:
                request["start_time"] = start_time.strftime("%Y.%m.%d %H:%M:%S")
            if end_time:
                request["end_time"] = end_time.strftime("%Y.%m.%d %H:%M:%S")

            raw = await self._request_candles(request)

            duration = _time.monotonic() - start_timer

            TA_BROKER_FETCH_DURATION.labels(
                broker="mt5",
                symbol=symbol,
                timeframe=timeframe.value,
            ).observe(duration)

            if not raw or not isinstance(raw, list) or len(raw) == 0:
                TA_BROKER_ERRORS_TOTAL.labels(
                    broker="mt5",
                    error_type="no_data",
                ).inc()
                raise ProviderResponseError(
                    "No data returned from ZMQ EA",
                    details={"symbol": symbol, "timeframe": timeframe},
                )

            candles = self._parse_candles(raw, symbol, timeframe)

            if start_time and end_time:
                candles = [c for c in candles if start_time <= c.timestamp <= end_time]

            if not candles:
                raise ProviderResponseError(
                    "No candles within requested time range",
                    details={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "start_time": start_time.isoformat() if start_time else None,
                        "end_time": end_time.isoformat() if end_time else None,
                    },
                )

            sequence = CandleSequence(
                symbol=symbol,
                timeframe=timeframe,
                candles=candles,
            )

            self.validator.validate_sequence(sequence)

            PROVIDER_RESPONSE_SIZE.labels(
                provider="mt5",
                category="candles",
            ).observe(len(candles))

            logger.info(
                "zmq_candles_fetched",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": len(candles),
                    "duration_seconds": duration,
                },
            )

            return sequence

        except ProviderError:
            raise
        except Exception as e:
            TA_BROKER_ERRORS_TOTAL.labels(
                broker="mt5",
                error_type=type(e).__name__,
            ).inc()

            logger.error(
                "zmq_fetch_candles_failed",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise ProviderError(
                f"ZMQ fetch candles failed: {e}",
                details={"symbol": symbol, "timeframe": timeframe, "error": str(e)},
            ) from e

    async def fetch_latest_candle(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Candle:
        sequence = await self.fetch_candles(
            symbol=symbol,
            timeframe=timeframe,
            count=1,
        )
        if sequence.count == 0:
            raise ProviderResponseError(
                "No candles returned",
                details={"symbol": symbol, "timeframe": timeframe},
            )
        return sequence.candles[-1]

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        reply = await self._request(
            {
                "command": "SYMBOL_INFO",
                "symbol": symbol,
            }
        )

        if not reply or not isinstance(reply, dict):
            raise ProviderResponseError(
                "Empty symbol info from ZMQ EA",
                details={"symbol": symbol},
            )

        return {
            "symbol": reply.get("symbol", symbol),
            "description": reply.get("description", ""),
            "path": reply.get("path", ""),
            "point": reply.get("point", 0.0),
            "digits": reply.get("digits", 5),
            "spread": reply.get("spread", 0),
            "trade_contract_size": reply.get("trade_contract_size", 100000),
            "volume_min": reply.get("volume_min", 0.01),
            "volume_max": reply.get("volume_max", 100.0),
            "volume_step": reply.get("volume_step", 0.01),
            "trade_tick_value": reply.get("trade_tick_value", 0.0),
            "trade_tick_size": reply.get("trade_tick_size", 0.0),
        }

    async def validate_symbol(self, symbol: str) -> bool:
        try:
            await self.get_symbol_info(symbol)
            return True
        except ProviderResponseError:
            return False

    async def get_all_symbol_names(self) -> list[str]:
        """Fetch all symbol names (fast call)."""
        symbols = await self.get_all_symbols()
        return [s["name"] for s in symbols]

    async def get_all_symbols(self) -> list[dict[str, Any]]:
        """Fetch all symbols from the MT5 Market Watch via ZMQ EA."""
        reply = await self._request({"command": "GET_ALL_SYMBOLS"})

        if not reply or not isinstance(reply, dict):
            raise ProviderResponseError(
                "Invalid response from GET_ALL_SYMBOLS",
                details={"reply_type": type(reply).__name__},
            )

        raw_symbols = reply.get("symbols", [])
        if not isinstance(raw_symbols, list):
            return []

        symbols: list[dict[str, Any]] = []
        for s in raw_symbols:
            if not isinstance(s, dict):
                continue
            name = s.get("name", "")
            if not name:
                continue
            symbols.append(
                {
                    "name": name,
                    "description": s.get("description", ""),
                    "path": s.get("path", ""),
                }
            )

        logger.info(
            "zmq_all_symbols_fetched",
            extra={"count": len(symbols)},
        )
        return symbols

    async def health_check(self) -> bool:
        try:
            reply = await self._request({"command": "PING", "auth_token": self.auth_token})
            if isinstance(reply, dict):
                return reply.get("status") == "ok"
            return False
        except Exception as e:
            logger.error(
                "zmq_health_check_failed",
                extra={"error": str(e)},
            )
            return False

    async def shutdown(self) -> None:
        async with self._lock:
            if self._socket is not None:
                self._socket.close(linger=0)
                self._socket = None
            self._initialized = False
        async with self._candles_lock:
            if self._candles_socket is not None:
                self._candles_socket.close(linger=0)
                self._candles_socket = None
            self._candles_initialized = False
        # Tear down the shared context only after both sockets are gone so
        # an in-flight close on either side cannot race the context term.
        if self._ctx is not None:
            self._ctx.term()
            self._ctx = None
        logger.info("zmq_shutdown_complete")

    # -- Trading methods (Execution + Management bridge) -----------------------

    async def get_account_info(self) -> AccountInfo:
        raw = await self._request({"command": "ACCOUNT_INFO"})
        if not isinstance(raw, dict):
            raise ProviderResponseError(
                "Invalid account info from ZMQ EA",
                details={"raw_type": type(raw).__name__},
            )

        return AccountInfo(
            balance=float(raw.get("balance", 0)),
            equity=float(raw.get("equity", 0)),
            margin=float(raw.get("margin", 0)),
            free_margin=float(raw.get("margin_free", 0)),
            currency=raw.get("currency", "USD"),
        )

    async def get_positions(self) -> list[PositionInfo]:
        raw = await self._request({"command": "POSITIONS"})
        if not isinstance(raw, list):
            raise ProviderResponseError(
                "Invalid positions response from ZMQ EA",
                details={"raw_type": type(raw).__name__},
            )

        positions = []
        for p in raw:
            direction = "BUY" if p.get("type", 0) == 0 else "SELL"
            positions.append(
                PositionInfo(
                    symbol=p.get("symbol", ""),
                    direction=direction,
                    entry_price=float(p.get("price_open", 0)),
                    current_price=float(p.get("price_current", 0)),
                    stop_loss=float(p.get("sl", 0)),
                    take_profit=float(p.get("tp", 0)),
                    volume=float(p.get("volume", 0)),
                    profit=float(p.get("profit", 0)),
                    commission=float(p.get("commission", 0)),
                    swap=float(p.get("swap", 0)),
                    ticket=str(p.get("ticket", "")),
                    comment=p.get("comment", ""),
                    open_time=int(p.get("time_setup", 0)),
                )
            )

        if positions:
            logger.info("zmq_positions_fetched", extra={"count": len(positions)})
        else:
            logger.debug("zmq_positions_fetched", extra={"count": 0})
        return positions

    async def get_history(self, days: int = 30) -> list[HistoryDealInfo]:
        raw = await self._request({"command": "HISTORY", "days": days})
        if not isinstance(raw, list):
            raise ProviderResponseError(
                "Invalid history response from ZMQ EA",
                details={"raw_type": type(raw).__name__},
            )

        history = []
        for h in raw:
            history.append(
                HistoryDealInfo(
                    ticket=str(h.get("ticket", "")),
                    position_id=str(h.get("position_id", "")),
                    symbol=h.get("symbol", ""),
                    direction=h.get("direction", "BUY"),
                    volume=float(h.get("volume", 0)),
                    price=float(h.get("price", 0)),
                    profit=float(h.get("profit", 0)),
                    commission=float(h.get("commission", 0)),
                    swap=float(h.get("swap", 0)),
                    time=int(h.get("time", 0)),
                    comment=h.get("comment", ""),
                )
            )

        logger.info("zmq_history_fetched", extra={"count": len(history)})
        return history

    async def get_pending_orders(self) -> list[PendingOrderInfo]:
        raw = await self._request({"command": "PENDING_ORDERS"})
        if not isinstance(raw, list):
            raise ProviderResponseError(
                "Invalid pending orders response from ZMQ EA",
                details={"raw_type": type(raw).__name__},
            )

        orders = []
        for o in raw:
            orders.append(
                PendingOrderInfo(
                    symbol=o.get("symbol", ""),
                    order_type=int(o.get("type", 2)),
                    price=float(o.get("price_open", 0)),
                    stop_loss=float(o.get("sl", 0)),
                    take_profit=float(o.get("tp", 0)),
                    volume=float(o.get("volume", 0)),
                    ticket=str(o.get("ticket", "")),
                    comment=o.get("comment", ""),
                    open_time=int(o.get("time_setup", 0)),
                )
            )

        logger.info("zmq_pending_orders_fetched", extra={"count": len(orders)})
        return orders

    async def get_position(self, ticket: str) -> PositionInfo:
        raw = await self._request({"command": "POSITION", "ticket": ticket})
        if not isinstance(raw, dict):
            raise ProviderResponseError(
                f"Position {ticket} not found",
                details={"ticket": ticket},
            )

        direction = "BUY" if raw.get("type", 0) == 0 else "SELL"
        return PositionInfo(
            symbol=raw.get("symbol", ""),
            direction=direction,
            entry_price=float(raw.get("price_open", 0)),
            current_price=float(raw.get("price_current", 0)),
            stop_loss=float(raw.get("sl", 0)),
            take_profit=float(raw.get("tp", 0)),
            volume=float(raw.get("volume", 0)),
            profit=float(raw.get("profit", 0)),
            ticket=str(raw.get("ticket", ticket)),
            comment=raw.get("comment", ""),
            open_time=int(raw.get("time_setup", 0)),
        )

    async def get_tick_price(self, symbol: str) -> TickPrice:
        raw = await self._request({"command": "TICK_PRICE", "symbol": symbol})
        if not isinstance(raw, dict):
            raise ProviderResponseError(
                f"Tick price not available for {symbol}",
                details={"symbol": symbol},
            )

        tick = TickPrice(
            bid=float(raw.get("bid", 0)),
            ask=float(raw.get("ask", 0)),
            time=int(raw.get("time", 0)),
        )
        # Section 2 anti-stale guard. Raises ProviderStalePriceError
        # when the broker's reported tick timestamp is older than
        # config.connectivity.tickMaxAgeSecs. Bypassed when no guard
        # was injected (test path / back-test replay).
        if self._freshness_guard is not None:
            self._freshness_guard.assert_fresh(symbol=symbol, tick_unix_ts=tick.time)
        # CHECKLIST hardening: when this tick fetch succeeded within
        # _tick_recovery_window_secs of the most recent socket
        # connect, count it as a 'recovery'. The metric gives
        # operators empirical evidence that REQ/REP's request-driven
        # contract produces clean recovery after a reconnect (the
        # design property documented in
        # docs/architecture/broker-connectivity.md).
        if self._connect_ts > 0.0:
            since_connect = _time.monotonic() - self._connect_ts
            if 0.0 <= since_connect <= self._tick_recovery_window_secs:
                try:
                    from engine.shared.metrics.prometheus import (
                        BROKER_TICK_FETCH_RECOVERY_TOTAL,
                    )

                    BROKER_TICK_FETCH_RECOVERY_TOTAL.labels(
                        provider=self.provider_name,
                        account_id=self.account_id,
                    ).inc()
                except ImportError:
                    # The metric is added alongside this code. A
                    # downstream consumer pulling an older
                    # prometheus.py loses only the SLO counter, not
                    # the actual recovery behaviour.
                    pass
                # Reset so the SAME connect only counts once. The
                # next successful tick on the same socket does NOT
                # re-fire the metric. A future reconnect re-arms it.
                self._connect_ts = 0.0
        return tick

    async def ea_identity(self) -> EAIdentitySnapshot:
        """Fetch + parse the EA's EA_IDENTITY reply.

        When an EAIdentityVerifier + ExpectedEAIdentity are injected,
        the snapshot is verified BEFORE being returned. An identity
        mismatch raises EAIdentityMismatchError which the caller
        propagates to the connection manager's kill-switch.
        Audit ref: CHECKLIST Section 4.
        """
        raw = await self._request({"command": "EA_IDENTITY"})
        if not isinstance(raw, dict):
            raise ProviderResponseError(
                "Invalid EA_IDENTITY reply",
                details={"raw_type": type(raw).__name__},
            )
        snapshot = EAIdentitySnapshot.from_dict(raw)
        if self._identity_verifier is not None and self._expected_identity is not None:
            self._identity_verifier.verify(snapshot, self._expected_identity)
            self._identity_verified = True
        return snapshot

    async def ea_clock(self) -> EAClockSample:
        """Fetch + parse the EA's EA_CLOCK reply.

        When a ClockSkewMonitor is injected, the new sample is fed
        into the monitor. Returns the parsed sample regardless.
        """
        raw = await self._request({"command": "EA_CLOCK"})
        if not isinstance(raw, dict):
            raise ProviderResponseError(
                "Invalid EA_CLOCK reply",
                details={"raw_type": type(raw).__name__},
            )
        sample = EAClockSample.from_dict(raw)
        if self._clock_skew is not None:
            self._clock_skew.sample(_time.time(), sample)
        return sample

    async def heartbeat_probe(self) -> HeartbeatResult:
        """Single-shot HEALTH probe consumed by BrokerHeartbeatService.

        Uses the same _request() path as the rest of the client so the
        same socket-poison recovery applies. Returns a HeartbeatResult;
        never raises (errors are folded into ok=False).
        Audit ref: CHECKLIST Section 2 - 'Detection of silent disconnect'
        + 'Heartbeat system per MT terminal'.
        """
        try:
            raw = await self._request({"command": "HEALTH"})
            if not isinstance(raw, dict):
                return HeartbeatResult(
                    ok=False,
                    error_type="ProviderResponseError",
                    error_message=f"HEALTH returned non-dict: {type(raw).__name__}",
                )
            broker_connected = bool(raw.get("mt5_connected"))
            authenticated = bool(raw.get("authenticated"))
            ok = broker_connected and authenticated
            return HeartbeatResult(
                ok=ok,
                broker_connected=broker_connected,
                authenticated=authenticated,
                uptime_seconds=float(raw.get("uptime_seconds") or 0.0),
                raw=raw,
                error_type="" if ok else "DisconnectedFromBroker",
                error_message=("" if ok else f"mt5_connected={broker_connected} authenticated={authenticated}"),
            )
        except Exception as exc:  # noqa: BLE001
            return HeartbeatResult(
                ok=False,
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
            )

    async def place_order(
        self,
        *,
        symbol: str,
        direction: str,
        order_type: str,
        price: float,
        stop_loss: float,
        take_profit: float,
        lot_size: float,
        comment: str = "",
    ) -> OrderResult:
        request = {
            "command": "ORDER_SEND",
            "symbol": symbol,
            "direction": direction.upper(),
            "order_type": order_type.upper(),
            "price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "lot_size": lot_size,
            "comment": comment,
        }

        try:
            raw = await self._request(request)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"ZMQ place order failed: {e}",
                details={"symbol": symbol, "error": str(e)},
            ) from e

        if not isinstance(raw, dict):
            raw = {}

        status = raw.get("status", "FILLED" if order_type.upper() == "MARKET" else "PLACED")

        logger.info(
            "zmq_order_placed",
            extra={
                "symbol": symbol,
                "direction": direction,
                "order_type": order_type,
                "lot_size": lot_size,
                "order_id": raw.get("order_id", 0),
                "status": status,
            },
        )

        return OrderResult(
            order_id=int(raw.get("order_id", 0)),
            price=float(raw.get("price", price)),
            status=status,
            error=raw.get("error") or "",
        )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            raw = await self._request({"command": "ORDER_CANCEL", "order_id": order_id})
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"ZMQ cancel order failed: {e}",
                details={"order_id": order_id, "error": str(e)},
            ) from e

        success = True
        if isinstance(raw, dict) and not raw.get("success", True):
            raise ProviderResponseError(
                f"Cancel order failed: {raw.get('error', 'unknown')}",
                details={"order_id": order_id, "reply": raw},
            )

        logger.info("zmq_order_cancelled", extra={"order_id": order_id})
        return success

    async def modify_position(
        self,
        *,
        ticket: str,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        request = {
            "command": "POSITION_MODIFY",
            "ticket": ticket,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }

        try:
            raw = await self._request(request)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"ZMQ modify position failed: {e}",
                details={"ticket": ticket, "error": str(e)},
            ) from e

        if isinstance(raw, dict) and not raw.get("success", True):
            raise ProviderResponseError(
                f"Modify position failed: {raw.get('error', 'unknown')}",
                details={"ticket": ticket, "reply": raw},
            )

        logger.info(
            "zmq_position_modified",
            extra={
                "ticket": ticket,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            },
        )
        return True

    async def close_partial(
        self,
        *,
        ticket: str,
        volume: float,
    ) -> dict[str, Any]:
        request = {
            "command": "POSITION_CLOSE_PARTIAL",
            "ticket": ticket,
            "volume": volume,
        }

        try:
            raw = await self._request(request)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"ZMQ partial close failed: {e}",
                details={"ticket": ticket, "volume": volume, "error": str(e)},
            ) from e

        if not isinstance(raw, dict):
            raw = {}

        if not raw.get("success", True):
            raise ProviderResponseError(
                f"Partial close failed: {raw.get('error', 'unknown')}",
                details={"ticket": ticket, "volume": volume, "reply": raw},
            )

        logger.info(
            "zmq_partial_close_executed",
            extra={
                "ticket": ticket,
                "volume": volume,
                "close_price": raw.get("close_price", 0),
            },
        )

        return {
            "success": True,
            "close_price": float(raw.get("close_price", 0)),
        }

    async def close_position(self, ticket: str) -> dict[str, Any]:
        try:
            raw = await self._request({"command": "POSITION_CLOSE", "ticket": ticket})
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"ZMQ close position failed: {e}",
                details={"ticket": ticket, "error": str(e)},
            ) from e

        if not isinstance(raw, dict):
            raw = {}

        if not raw.get("success", True):
            raise ProviderResponseError(
                f"Close position failed: {raw.get('error', 'unknown')}",
                details={"ticket": ticket, "reply": raw},
            )

        logger.info(
            "zmq_position_closed",
            extra={"ticket": ticket, "close_price": raw.get("close_price", 0)},
        )

        return {
            "success": True,
            "close_price": float(raw.get("close_price", 0)),
        }

    # -- Parsing ---------------------------------------------------------------

    @staticmethod
    def _parse_candles(
        raw: list[dict[str, Any]],
        symbol: str,
        timeframe: Timeframe,
    ) -> list[Candle]:
        """Convert ZMQ EA candle dicts to domain Candle models.

        The EA returns candles as:
        {
            "time": 1705312800,   (unix timestamp)
            "open": 1.09500,
            "high": 1.09600,
            "low": 1.09400,
            "close": 1.09550,
            "tick_volume": 1234
        }
        """
        candles: list[Candle] = []
        for bar in raw:
            ts_raw = bar.get("time")
            if ts_raw is None:
                continue

            if isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(ts_raw, tz=UTC)
            elif isinstance(ts_raw, str):
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            else:
                continue

            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts,
                open=float(bar["open"]),
                high=float(bar["high"]),
                low=float(bar["low"]),
                close=float(bar["close"]),
                volume=float(bar.get("tick_volume", 0)),
            )
            candles.append(candle)

        return candles
