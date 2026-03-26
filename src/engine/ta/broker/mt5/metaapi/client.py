"""MetaApi.cloud REST client implementing BrokerBase.

Communicates with MetaApi cloud servers to fetch candle data,
symbol info, and health status.  Uses the shared HttpClient
for all HTTP calls (inheriting circuit breaker, retries, metrics).

No local MT5 terminal or Windows dependency required.
"""

from __future__ import annotations

import asyncio
import time as _time
from datetime import datetime, timezone
from typing import Any, Optional

from engine.shared.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from engine.shared.http.client import HttpClient
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

# MetaApi uses standard timeframe strings.
_METAAPI_TIMEFRAME_MAP: dict[Timeframe, str] = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1d",
    Timeframe.W1: "1w",
    Timeframe.MN1: "1mn",
}


class MetaApiClient(BrokerBase):
    """Cloud-based MT5 data provider via MetaApi.cloud REST API."""

    _DEFAULT_BASE_URL = "https://mt-client-api-v1.agiliumtrade.agiliumtrade.ai"

    def __init__(
        self,
        config: MT5Config,
        http_client: HttpClient,
    ) -> None:
        super().__init__(broker_id="mt5")
        self.config = config
        self._http = http_client
        self.validator = BrokerDataValidator()
        self._account_id = config.metaapi_account_id
        self._base_url = config.metaapi_base_url if config.metaapi_base_url else self._DEFAULT_BASE_URL
        self._auth_headers = {
            "auth-token": config.metaapi_token,
        }

    # -- Helpers ---------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}/users/current/accounts/{self._account_id}{path}"

    async def _api_get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        category: str = "candles",
    ) -> Any:
        """Execute authenticated GET against MetaApi."""
        return await self._http.get(
            self._url(path),
            provider_name="metaapi",
            category=category,
            headers=self._auth_headers,
            params=params,
            timeout_override=self.config.timeout_seconds,
        )

    # -- BrokerBase implementation ---------------------------------------------

    async def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_realtime=True,
            supports_historical=True,
            supports_tick_data=self.config.enable_tick_data,
            supports_symbol_info=True,
            max_candles_per_request=self.config.max_candles_per_request,
            rate_limit_per_minute=60,
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

        ma_tf = _METAAPI_TIMEFRAME_MAP.get(timeframe)
        if ma_tf is None:
            raise ProviderError(
                f"Unsupported timeframe: {timeframe}",
                details={"timeframe": timeframe},
            )

        start_timer = _time.monotonic()

        try:
            params: dict[str, Any] = {}
            if start_time:
                params["startTime"] = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            if count:
                params["limit"] = min(count, self.config.max_candles_per_request)
            else:
                params["limit"] = 500

            path = (
                f"/historical-market-data/symbols/{symbol}/timeframes/{ma_tf}/candles"
            )
            raw = await self._api_get(path, params=params, category="candles")

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
                    "No data returned from MetaApi",
                    details={"symbol": symbol, "timeframe": timeframe},
                )

            candles = self._parse_candles(raw, symbol, timeframe)

            # Apply time range filter if both bounds provided.
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
                "metaapi_candles_fetched",
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
                "metaapi_fetch_candles_failed",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise ProviderError(
                f"MetaApi fetch candles failed: {e}",
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
        path = f"/symbols/{symbol}/specification"
        try:
            info = await self._api_get(path, category="symbol_info")
        except Exception as e:
            raise ProviderResponseError(
                f"Symbol info not found: {e}",
                details={"symbol": symbol, "error": str(e)},
            ) from e

        if not info or not isinstance(info, dict):
            raise ProviderResponseError(
                "Empty symbol info from MetaApi",
                details={"symbol": symbol},
            )

        return {
            "symbol": info.get("symbol", symbol),
            "description": info.get("description", ""),
            "point": info.get("point", 0.0),
            "digits": info.get("digits", 5),
            "spread": info.get("spread", 0),
            "trade_contract_size": info.get("contractSize", 100000),
            "volume_min": info.get("minVolume", 0.01),
            "volume_max": info.get("maxVolume", 100.0),
            "volume_step": info.get("volumeStep", 0.01),
            "trade_tick_value": info.get("tradeTickValue", 0.0),
            "trade_tick_size": info.get("tickSize", 0.0),
        }

    async def validate_symbol(self, symbol: str) -> bool:
        try:
            await self.get_symbol_info(symbol)
            return True
        except ProviderResponseError:
            return False

    async def health_check(self) -> bool:
        try:
            info = await self._http.get(
                f"{self._base_url}/users/current/accounts/{self._account_id}",
                provider_name="metaapi",
                category="health",
                headers=self._auth_headers,
                timeout_override=10,
            )
            if not isinstance(info, dict):
                return False
            state = info.get("state", "")
            connection_status = info.get("connectionStatus", "")
            return state == "DEPLOYED" and connection_status == "CONNECTED"
        except Exception as e:
            logger.error(
                "metaapi_health_check_failed",
                extra={"error": str(e)},
            )
            return False

    async def shutdown(self) -> None:
        logger.info("metaapi_shutdown_complete")

    # -- Trading methods (Execution + Management bridge) -----------------------

    async def _api_post(
        self,
        path: str,
        payload: dict[str, Any],
        category: str = "trade",
    ) -> Any:
        """Execute authenticated POST against MetaApi."""
        return await self._http.post(
            self._url(path),
            json_body=payload,
            provider_name="metaapi",
            category=category,
            headers=self._auth_headers,
            timeout_override=self.config.timeout_seconds,
        )

    async def get_account_info(self) -> AccountInfo:
        raw = await self._api_get("/account-information", category="account")
        if not isinstance(raw, dict):
            raise ProviderResponseError(
                "Invalid account info response",
                details={"raw_type": type(raw).__name__},
            )

        return AccountInfo(
            balance=float(raw.get("balance", 0)),
            equity=float(raw.get("equity", 0)),
            margin=float(raw.get("margin", 0)),
            free_margin=float(raw.get("freeMargin", raw.get("margin_free", 0))),
            currency=raw.get("currency", "USD"),
        )

    async def get_positions(self) -> list[PositionInfo]:
        raw = await self._api_get("/positions", category="positions")
        if not isinstance(raw, list):
            raise ProviderResponseError(
                "Invalid positions response",
                details={"raw_type": type(raw).__name__},
            )

        positions = []
        for p in raw:
            direction = (
                "BUY"
                if p.get("type", "POSITION_TYPE_BUY") == "POSITION_TYPE_BUY"
                else "SELL"
            )
            positions.append(
                PositionInfo(
                    symbol=p.get("symbol", ""),
                    direction=direction,
                    entry_price=float(p.get("openPrice", 0)),
                    current_price=float(p.get("currentPrice", 0)),
                    stop_loss=float(p.get("stopLoss", 0)),
                    take_profit=float(p.get("takeProfit", 0)),
                    volume=float(p.get("volume", 0)),
                    profit=float(p.get("profit", 0)),
                    ticket=str(p.get("id", "")),
                    comment=p.get("comment", ""),
                    open_time=int(p.get("time", 0)),
                )
            )

        logger.info("metaapi_positions_fetched", extra={"count": len(positions)})
        return positions

    async def get_pending_orders(self) -> list[PendingOrderInfo]:
        raw = await self._api_get("/orders", category="orders")
        if not isinstance(raw, list):
            raise ProviderResponseError(
                "Invalid orders response",
                details={"raw_type": type(raw).__name__},
            )

        orders = []
        _type_map = {
            "ORDER_TYPE_BUY_LIMIT": 2,
            "ORDER_TYPE_SELL_LIMIT": 3,
            "ORDER_TYPE_BUY_STOP": 4,
            "ORDER_TYPE_SELL_STOP": 5,
        }
        for o in raw:
            order_type_str = o.get("type", "")
            order_type_int = _type_map.get(order_type_str, 2)
            orders.append(
                PendingOrderInfo(
                    symbol=o.get("symbol", ""),
                    order_type=order_type_int,
                    price=float(o.get("openPrice", 0)),
                    stop_loss=float(o.get("stopLoss", 0)),
                    take_profit=float(o.get("takeProfit", 0)),
                    volume=float(o.get("volume", 0)),
                    ticket=str(o.get("id", "")),
                    comment=o.get("comment", ""),
                    open_time=int(o.get("time", 0)),
                )
            )

        logger.info("metaapi_pending_orders_fetched", extra={"count": len(orders)})
        return orders

    async def get_position(self, ticket: str) -> PositionInfo:
        raw = await self._api_get(f"/positions/{ticket}", category="position")
        if not isinstance(raw, dict):
            raise ProviderResponseError(
                f"Position {ticket} not found",
                details={"ticket": ticket},
            )

        direction = (
            "BUY"
            if raw.get("type", "POSITION_TYPE_BUY") == "POSITION_TYPE_BUY"
            else "SELL"
        )
        return PositionInfo(
            symbol=raw.get("symbol", ""),
            direction=direction,
            entry_price=float(raw.get("openPrice", 0)),
            current_price=float(raw.get("currentPrice", 0)),
            stop_loss=float(raw.get("stopLoss", 0)),
            take_profit=float(raw.get("takeProfit", 0)),
            volume=float(raw.get("volume", 0)),
            profit=float(raw.get("profit", 0)),
            ticket=str(raw.get("id", ticket)),
            comment=raw.get("comment", ""),
            open_time=int(raw.get("time", 0)),
        )

    async def get_tick_price(self, symbol: str) -> TickPrice:
        raw = await self._api_get(
            f"/symbols/{symbol}/current-price",
            category="tick",
        )
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
        is_buy = direction.upper() == "BUY"
        is_market = order_type.upper() == "MARKET"

        if is_market:
            action_type = "ORDER_TYPE_BUY" if is_buy else "ORDER_TYPE_SELL"
        else:
            action_type = "ORDER_TYPE_BUY_LIMIT" if is_buy else "ORDER_TYPE_SELL_LIMIT"

        payload: dict[str, Any] = {
            "actionType": action_type,
            "symbol": symbol,
            "volume": lot_size,
            "stopLoss": stop_loss,
            "takeProfit": take_profit,
            "comment": comment,
        }

        if comment:
            # Use comment (AnalysisID) as the idempotency key for MetaApi.
            payload["clientId"] = comment

        if order_type.upper() != "MARKET" and price > 0:
            payload["openPrice"] = price

        try:
            raw = await self._api_post("/trade", payload, category="order_send")
        except Exception as e:
            logger.error(
                "metaapi_place_order_failed",
                extra={"symbol": symbol, "direction": direction, "error": str(e)},
            )
            raise ProviderError(
                f"Place order failed: {e}",
                details={"symbol": symbol, "direction": direction, "error": str(e)},
            ) from e

        if not isinstance(raw, dict):
            raw = {}

        status = "FILLED" if order_type.upper() == "MARKET" else "PLACED"
        string_code = raw.get("stringCode", "")
        if string_code and "REJECT" in string_code.upper():
            status = "REJECTED"

        order_id = raw.get("orderId", 0)
        if not order_id:
            order_id = raw.get("positionId", 0)

        logger.info(
            "metaapi_order_placed",
            extra={
                "symbol": symbol,
                "direction": direction,
                "order_type": order_type,
                "lot_size": lot_size,
                "order_id": order_id,
                "status": status,
            },
        )

        return OrderResult(
            order_id=int(order_id) if order_id else 0,
            price=float(raw.get("openPrice", price)),
            status=status,
            error=raw.get("message", ""),
        )

    async def cancel_order(self, order_id: str) -> bool:
        payload = {
            "actionType": "ORDER_CANCEL",
            "orderId": order_id,
        }

        # For cancel order, the clientId can be the order_id itself to ensure idempotency.
        payload["clientId"] = f"cancel_{order_id}"

        try:
            raw = await self._api_post("/trade", payload, category="order_cancel")
        except Exception as e:
            logger.error(
                "metaapi_cancel_order_failed",
                extra={"order_id": order_id, "error": str(e)},
            )
            raise ProviderError(
                f"Cancel order failed: {e}",
                details={"order_id": order_id, "error": str(e)},
            ) from e

        logger.info("metaapi_order_cancelled", extra={"order_id": order_id})
        return True

    async def modify_position(
        self,
        *,
        ticket: str,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        payload: dict[str, Any] = {
            "actionType": "POSITION_MODIFY",
            "positionId": ticket,
            "stopLoss": stop_loss,
            "takeProfit": take_profit,
        }

        # Ensure idempotency by hashing the ticket and new parameters
        payload["clientId"] = f"mod_{ticket}_{stop_loss}_{take_profit}"

        try:
            await self._api_post("/trade", payload, category="position_modify")
        except Exception as e:
            logger.error(
                "metaapi_modify_position_failed",
                extra={"ticket": ticket, "error": str(e)},
            )
            raise ProviderError(
                f"Modify position failed: {e}",
                details={"ticket": ticket, "error": str(e)},
            ) from e

        logger.info(
            "metaapi_position_modified",
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
        payload: dict[str, Any] = {
            "actionType": "POSITION_PARTIAL",
            "positionId": ticket,
            "volume": volume,
        }

        payload["clientId"] = f"part_{ticket}_{volume}"

        try:
            raw = await self._api_post(
                "/trade", payload, category="position_close_partial"
            )
        except Exception as e:
            logger.error(
                "metaapi_close_partial_failed",
                extra={"ticket": ticket, "volume": volume, "error": str(e)},
            )
            raise ProviderError(
                f"Partial close failed: {e}",
                details={"ticket": ticket, "volume": volume, "error": str(e)},
            ) from e

        if not isinstance(raw, dict):
            raw = {}

        logger.info(
            "metaapi_partial_close_executed",
            extra={
                "ticket": ticket,
                "volume": volume,
                "close_price": raw.get("closePrice", 0),
            },
        )

        return {
            "success": True,
            "close_price": float(raw.get("closePrice", 0)),
        }

    async def close_position(self, ticket: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "actionType": "POSITION_CLOSE_ID",
            "positionId": ticket,
        }

        try:
            raw = await self._api_post("/trade", payload, category="position_close")
        except Exception as e:
            logger.error(
                "metaapi_close_position_failed",
                extra={"ticket": ticket, "error": str(e)},
            )
            raise ProviderError(
                f"Close position failed: {e}",
                details={"ticket": ticket, "error": str(e)},
            ) from e

        if not isinstance(raw, dict):
            raw = {}

        logger.info(
            "metaapi_position_closed",
            extra={"ticket": ticket, "close_price": raw.get("closePrice", 0)},
        )

        return {
            "success": True,
            "close_price": float(raw.get("closePrice", 0)),
        }

    # -- Parsing ---------------------------------------------------------------

    @staticmethod
    def _parse_candles(
        raw: list[dict[str, Any]],
        symbol: str,
        timeframe: Timeframe,
    ) -> list[Candle]:
        """Convert MetaApi candle dicts to domain Candle models.

        MetaApi returns candles as:
        {
            "time": "2024-01-15T10:00:00.000Z",
            "brokerTime": "2024-01-15 12:00:00.000",
            "open": 1.09500,
            "high": 1.09600,
            "low": 1.09400,
            "close": 1.09550,
            "tickVolume": 1234
        }
        """
        candles: list[Candle] = []
        for bar in raw:
            time_str = bar.get("time", "")
            if not time_str:
                continue

            # Parse ISO timestamp from MetaApi.
            ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))

            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts,
                open=float(bar["open"]),
                high=float(bar["high"]),
                low=float(bar["low"]),
                close=float(bar["close"]),
                volume=float(bar.get("tickVolume", 0)),
            )
            candles.append(candle)

        return candles
