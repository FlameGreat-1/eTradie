from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from engine.shared.exceptions import ProviderError
from engine.shared.logging import get_logger
from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)


class BrokerCapabilities(FrozenModel):

    supports_realtime: bool = Field(default=True)
    supports_historical: bool = Field(default=True)
    supports_tick_data: bool = Field(default=False)
    supports_symbol_info: bool = Field(default=True)
    max_candles_per_request: int = Field(default=5000, ge=1)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    requires_authentication: bool = Field(default=True)


class AccountInfo(FrozenModel):
    """Live broker account state."""

    balance: float = Field(ge=0)
    equity: float
    margin: float = Field(ge=0)
    free_margin: float
    currency: str = Field(default="USD", min_length=2, max_length=5)


class PositionInfo(FrozenModel):
    """Open broker position."""

    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    stop_loss: float = Field(ge=0)
    take_profit: float = Field(ge=0)
    volume: float = Field(gt=0)
    profit: float
    commission: float = Field(default=0.0)
    swap: float = Field(default=0.0)
    ticket: str
    comment: Optional[str] = Field(default="")
    open_time: int = Field(default=0)  # Unix timestamp


class HistoryDealInfo(FrozenModel):
    """Historical deal at the broker."""

    ticket: str
    position_id: str
    symbol: str
    direction: str
    volume: float
    price: float
    profit: float
    commission: float
    swap: float
    time: int
    comment: Optional[str] = Field(default="")


class PendingOrderInfo(FrozenModel):
    """Pending limit/stop order at the broker."""

    symbol: str
    order_type: int  # MT5 order type enum
    price: float = Field(gt=0)
    stop_loss: float = Field(ge=0)
    take_profit: float = Field(ge=0)
    volume: float = Field(gt=0)
    ticket: str
    comment: Optional[str] = Field(default="")
    open_time: int = Field(default=0)  # Unix timestamp


class TickPrice(FrozenModel):
    """Latest bid/ask for a symbol."""

    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    time: int = Field(default=0)  # Unix timestamp


class OrderResult(FrozenModel):
    """Broker response after order placement."""

    order_id: int = Field(default=0)
    price: float = Field(ge=0, default=0.0)
    status: str  # "PLACED", "FILLED", "REJECTED"
    error: str = Field(default="")


class BrokerBase(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the broker provider (e.g., 'metaapi', 'zmq')."""

    @property
    @abstractmethod
    def account_id(self) -> str:
        """Return the broker account ID."""

    @abstractmethod
    async def get_all_symbol_names(self) -> list[str]:
        """Return a simple list of all available symbol names."""

    def __init__(self, broker_id: str) -> None:
        self.broker_id = broker_id
        self._logger = get_logger(f"{__name__}.{broker_id}")

    @abstractmethod
    async def get_capabilities(self) -> BrokerCapabilities:
        pass

    @abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        count: Optional[int] = None,
    ) -> CandleSequence:
        pass

    @abstractmethod
    async def fetch_latest_candle(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Candle:
        pass

    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> dict:
        pass

    @abstractmethod
    async def validate_symbol(self, symbol: str) -> bool:
        pass

    @abstractmethod
    async def get_all_symbols(self) -> list[dict]:
        """Return all available broker symbols with name, description, and category path."""

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    async def fetch_candles_safe(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        count: Optional[int] = None,
    ) -> Optional[CandleSequence]:
        try:
            return await self.fetch_candles(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                count=count,
            )
        except ProviderError as e:
            self._logger.error(
                "broker_fetch_failed",
                extra={
                    "broker_id": self.broker_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
            )
            return None
        except Exception as e:
            self._logger.error(
                "broker_fetch_unexpected_error",
                extra={
                    "broker_id": self.broker_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
                exc_info=True,
            )
            return None

    async def fetch_latest_candle_safe(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Optional[Candle]:
        try:
            return await self.fetch_latest_candle(
                symbol=symbol,
                timeframe=timeframe,
            )
        except ProviderError as e:
            self._logger.error(
                "broker_fetch_latest_failed",
                extra={
                    "broker_id": self.broker_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
            )
            return None
        except Exception as e:
            self._logger.error(
                "broker_fetch_latest_unexpected_error",
                extra={
                    "broker_id": self.broker_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
                exc_info=True,
            )
            return None

    # -- Trading methods (required by Go Execution + Management) ---------------

    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Return live account balance, equity, margin, free margin."""

    @abstractmethod
    async def get_positions(self) -> list[PositionInfo]:
        """Return all open positions at the broker."""

    @abstractmethod
    async def get_history(self, days: int = 30) -> list[HistoryDealInfo]:
        """Return historical closed deals for the last N days."""

    @abstractmethod
    async def get_pending_orders(self) -> list[PendingOrderInfo]:
        """Return all pending limit/stop orders at the broker."""

    @abstractmethod
    async def get_position(self, ticket: str) -> PositionInfo:
        """Return a single open position by broker ticket."""

    @abstractmethod
    async def get_tick_price(self, symbol: str) -> TickPrice:
        """Return the latest bid/ask for a symbol."""

    @abstractmethod
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
        """Place a limit or market order with SL/TP at the broker."""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order by broker order ID. Returns True on success."""

    @abstractmethod
    async def modify_position(
        self,
        *,
        ticket: str,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        """Modify SL/TP on an existing open position. Returns True on success."""

    @abstractmethod
    async def close_partial(
        self,
        *,
        ticket: str,
        volume: float,
    ) -> dict[str, Any]:
        """Partially close a position. Returns close price and success status."""

    @abstractmethod
    async def close_position(self, ticket: str) -> dict[str, Any]:
        """Fully close a position at market. Returns close price and success status."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shut down the broker connection and release resources."""
