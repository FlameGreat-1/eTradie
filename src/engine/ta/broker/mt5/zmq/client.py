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
from datetime import datetime, timezone
from typing import Any, Optional

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
    PROVIDER_RESPONSE_SIZE,
    TA_BROKER_ERRORS_TOTAL,
    TA_BROKER_FETCH_DURATION,
)
from engine.ta.broker.base import (
    AccountInfo,
    BrokerBase,
    BrokerCapabilities,
    OrderResult,
    PendingOrderInfo,
    PositionInfo,
    TickPrice,
)
from engine.ta.broker.mt5.config import MT5Config
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
    Timeframe.H4: "H4",
    Timeframe.D1: "D1",
    Timeframe.W1: "W1",
    Timeframe.MN1: "MN1",
}


class ZmqClient(BrokerBase):
    """Native ZeroMQ bridge to a Windows MT5 terminal."""

    def __init__(self, config: MT5Config) -> None:
        super().__init__(broker_id="mt5")
        self.config = config
        self.validator = BrokerDataValidator()
        self._endpoint = f"tcp://{config.zmq_host}:{config.zmq_port}"
        self._ctx: zmq_async.Context | None = None  # type: ignore[type-arg]
        self._socket: zmq_async.Socket | None = None  # type: ignore[type-arg]
        self._lock = asyncio.Lock()
        self._initialized = False

    # -- Connection management -------------------------------------------------

    def _connect_sync(self) -> None:
        """Create ZMQ context and REQ socket."""
        if self._initialized:
            return
        self._ctx = zmq_async.Context()
        self._socket = self._ctx.socket(zmq.REQ)
        self._socket.setsockopt(zmq.RCVTIMEO, self.config.timeout_seconds * 1000)
        self._socket.setsockopt(zmq.SNDTIMEO, self.config.timeout_seconds * 1000)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.connect(self._endpoint)
        self._initialized = True
        logger.info(
            "zmq_connected",
            extra={"endpoint": self._endpoint},
        )

    async def _send_recv_async(self, request: dict[str, Any]) -> dict[str, Any] | list[Any]:
        """Send JSON request and receive JSON response asynchronously."""
        import json

        if self._socket is None:
            raise ProviderUnavailableError(
                "ZMQ socket not initialized",
                details={"endpoint": self._endpoint},
            )

        payload = json.dumps(request).encode("utf-8")
        try:
            await self._socket.send(payload)
        except zmq.Again:
            raise ProviderTimeoutError(
                "ZMQ send timed out",
                details={"endpoint": self._endpoint, "timeout": self.config.timeout_seconds},
            )

        try:
            raw_reply = await self._socket.recv()
        except zmq.Again:
            raise ProviderTimeoutError(
                "ZMQ recv timed out",
                details={"endpoint": self._endpoint, "timeout": self.config.timeout_seconds},
            )

        reply = json.loads(raw_reply.decode("utf-8"))

        # Check for EA-level errors.
        if isinstance(reply, dict) and reply.get("error"):
            raise ProviderResponseError(
                f"ZMQ EA error: {reply['error']}",
                details={"reply": reply},
            )

        from typing import cast
        return cast(dict[str, Any] | list[Any], reply)

    async def _request(self, request: dict[str, Any]) -> dict[str, Any] | list[Any]:
        """Thread-safe async wrapper around the ZMQ call."""
        async with self._lock:
            if not self._initialized:
                self._connect_sync()
            return await self._send_recv_async(request)

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
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        count: Optional[int] = None,
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

            raw = await self._request(request)

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
                candles = [
                    c for c in candles
                    if start_time <= c.timestamp <= end_time
                ]

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

    async def get_symbol_info(self, symbol: str) -> dict:
        reply = await self._request({
            "command": "SYMBOL_INFO",
            "symbol": symbol,
        })

        if not reply or not isinstance(reply, dict):
            raise ProviderResponseError(
                "Empty symbol info from ZMQ EA",
                details={"symbol": symbol},
            )

        return {
            "symbol": reply.get("symbol", symbol),
            "description": reply.get("description", ""),
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

    async def health_check(self) -> bool:
        try:
            reply = await self._request({"command": "PING"})
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
        def _close() -> None:
            if self._socket is not None:
                self._socket.close(linger=0)
                self._socket = None
            if self._ctx is not None:
                self._ctx.term()
                self._ctx = None
            self._initialized = False

        _close()
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
            positions.append(PositionInfo(
                symbol=p.get("symbol", ""),
                direction=direction,
                entry_price=float(p.get("price_open", 0)),
                current_price=float(p.get("price_current", 0)),
                stop_loss=float(p.get("sl", 0)),
                take_profit=float(p.get("tp", 0)),
                volume=float(p.get("volume", 0)),
                profit=float(p.get("profit", 0)),
                ticket=str(p.get("ticket", "")),
                comment=p.get("comment", ""),
                open_time=int(p.get("time_setup", 0)),
            ))

        logger.info("zmq_positions_fetched", extra={"count": len(positions)})
        return positions

    async def get_pending_orders(self) -> list[PendingOrderInfo]:

        raw = await self._request({"command": "PENDING_ORDERS"})
        if not isinstance(raw, list):
            raise ProviderResponseError(
                "Invalid pending orders response from ZMQ EA",
                details={"raw_type": type(raw).__name__},
            )

        orders = []
        for o in raw:
            orders.append(PendingOrderInfo(
                symbol=o.get("symbol", ""),
                order_type=int(o.get("type", 2)),
                price=float(o.get("price_open", 0)),
                stop_loss=float(o.get("sl", 0)),
                take_profit=float(o.get("tp", 0)),
                volume=float(o.get("volume", 0)),
                ticket=str(o.get("ticket", "")),
                comment=o.get("comment", ""),
                open_time=int(o.get("time_setup", 0)),
            ))

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

        return TickPrice(
            bid=float(raw.get("bid", 0)),
            ask=float(raw.get("ask", 0)),
            time=int(raw.get("time", 0)),
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
            error=raw.get("error", ""),
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
            extra={"ticket": ticket, "stop_loss": stop_loss, "take_profit": take_profit},
        )
        return True

    async def close_partial(
        self,
        *,
        ticket: str,
        volume: float,
    ) -> dict:
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
            extra={"ticket": ticket, "volume": volume, "close_price": raw.get("close_price", 0)},
        )

        return {
            "success": True,
            "close_price": float(raw.get("close_price", 0)),
        }

    async def close_position(self, ticket: str) -> dict:
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
                ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
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
