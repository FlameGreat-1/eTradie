from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

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


class BrokerBase(ABC):
    
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
