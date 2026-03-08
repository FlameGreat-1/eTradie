import asyncio
from datetime import datetime, timezone
from typing import Optional

import MetaTrader5 as mt5

from engine.shared.exceptions import (
    ProviderError,
    ProviderTimeoutError,
    ProviderAuthenticationError,
    ProviderUnavailableError,
    ProviderResponseError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROVIDER_REQUEST_DURATION,
    PROVIDER_REQUEST_ERRORS,
    PROVIDER_RESPONSE_SIZE,
)
from engine.ta.broker.base import BrokerBase, BrokerCapabilities
from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.validator import BrokerDataValidator
from engine.ta.constants import Timeframe, TIMEFRAME_MINUTES
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)


_MT5_TIMEFRAME_MAP = {
    Timeframe.M1: mt5.TIMEFRAME_M1,
    Timeframe.M5: mt5.TIMEFRAME_M5,
    Timeframe.M15: mt5.TIMEFRAME_M15,
    Timeframe.M30: mt5.TIMEFRAME_M30,
    Timeframe.H1: mt5.TIMEFRAME_H1,
    Timeframe.H4: mt5.TIMEFRAME_H4,
    Timeframe.D1: mt5.TIMEFRAME_D1,
    Timeframe.W1: mt5.TIMEFRAME_W1,
    Timeframe.MN1: mt5.TIMEFRAME_MN1,
}


class MT5Client(BrokerBase):
    
    def __init__(self, config: MT5Config) -> None:
        super().__init__(broker_id="mt5")
        self.config = config
        self.validator = BrokerDataValidator()
        self._initialized = False
        self._connection_lock = asyncio.Lock()
    
    async def _ensure_initialized(self) -> None:
        async with self._connection_lock:
            if self._initialized:
                return
            
            await asyncio.to_thread(self._initialize_sync)
    
    def _initialize_sync(self) -> None:
        if self._initialized:
            return
        
        try:
            if self.config.terminal_path:
                if not mt5.initialize(path=self.config.terminal_path):
                    error_code = mt5.last_error()
                    raise ProviderUnavailableError(
                        f"MT5 initialization failed: {error_code}",
                        details={"error_code": error_code},
                    )
            else:
                if not mt5.initialize():
                    error_code = mt5.last_error()
                    raise ProviderUnavailableError(
                        f"MT5 initialization failed: {error_code}",
                        details={"error_code": error_code},
                    )
            
            if self.config.account and self.config.password and self.config.server:
                authorized = mt5.login(
                    login=self.config.account,
                    password=self.config.password,
                    server=self.config.server,
                    timeout=self.config.connection_timeout_seconds * 1000,
                )
                
                if not authorized:
                    error_code = mt5.last_error()
                    mt5.shutdown()
                    raise ProviderAuthenticationError(
                        f"MT5 login failed: {error_code}",
                        details={
                            "account": self.config.account,
                            "server": self.config.server,
                            "error_code": error_code,
                        },
                    )
            
            self._initialized = True
            
            logger.info(
                "mt5_initialized",
                extra={
                    "account": self.config.account,
                    "server": self.config.server,
                },
            )
            
        except Exception as e:
            logger.error(
                "mt5_initialization_failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise
    
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
        await self._ensure_initialized()
        
        if start_time and end_time:
            self.validator.validate_time_range(start_time, end_time)
        
        mt5_timeframe = _MT5_TIMEFRAME_MAP.get(timeframe)
        if mt5_timeframe is None:
            raise ProviderError(
                f"Unsupported timeframe: {timeframe}",
                details={"timeframe": timeframe},
            )
        
        start_timer = asyncio.get_event_loop().time()
        
        try:
            if count:
                rates = await asyncio.to_thread(
                    mt5.copy_rates_from_pos,
                    symbol,
                    mt5_timeframe,
                    0,
                    min(count, self.config.max_candles_per_request),
                )
            elif start_time and end_time:
                rates = await asyncio.to_thread(
                    mt5.copy_rates_range,
                    symbol,
                    mt5_timeframe,
                    start_time,
                    end_time,
                )
            elif start_time:
                rates = await asyncio.to_thread(
                    mt5.copy_rates_from,
                    symbol,
                    mt5_timeframe,
                    start_time,
                    self.config.max_candles_per_request,
                )
            else:
                rates = await asyncio.to_thread(
                    mt5.copy_rates_from_pos,
                    symbol,
                    mt5_timeframe,
                    0,
                    500,
                )
            
            duration = asyncio.get_event_loop().time() - start_timer
            
            PROVIDER_REQUEST_DURATION.labels(
                provider="mt5",
                operation="fetch_candles",
            ).observe(duration)
            
            if rates is None or len(rates) == 0:
                error_code = mt5.last_error()
                PROVIDER_REQUEST_ERRORS.labels(
                    provider="mt5",
                    operation="fetch_candles",
                    error_type="no_data",
                ).inc()
                
                raise ProviderResponseError(
                    f"No data returned from MT5: {error_code}",
                    details={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "error_code": error_code,
                    },
                )
            
            candles = []
            for rate in rates:
                candle = Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(rate["time"], tz=timezone.utc),
                    open=float(rate["open"]),
                    high=float(rate["high"]),
                    low=float(rate["low"]),
                    close=float(rate["close"]),
                    volume=float(rate["tick_volume"]),
                )
                candles.append(candle)
            
            sequence = CandleSequence(
                symbol=symbol,
                timeframe=timeframe,
                candles=candles,
            )
            
            self.validator.validate_sequence(sequence)
            
            PROVIDER_RESPONSE_SIZE.labels(
                provider="mt5",
                operation="fetch_candles",
            ).observe(len(candles))
            
            logger.info(
                "mt5_candles_fetched",
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
            PROVIDER_REQUEST_ERRORS.labels(
                provider="mt5",
                operation="fetch_candles",
                error_type=type(e).__name__,
            ).inc()
            
            logger.error(
                "mt5_fetch_candles_failed",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
                exc_info=True,
            )
            
            raise ProviderError(
                f"MT5 fetch candles failed: {e}",
                details={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
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
        await self._ensure_initialized()
        
        info = await asyncio.to_thread(mt5.symbol_info, symbol)
        
        if info is None:
            error_code = mt5.last_error()
            raise ProviderResponseError(
                f"Symbol info not found: {error_code}",
                details={"symbol": symbol, "error_code": error_code},
            )
        
        return {
            "symbol": info.name,
            "description": info.description,
            "point": info.point,
            "digits": info.digits,
            "spread": info.spread,
            "trade_contract_size": info.trade_contract_size,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
        }
    
    async def validate_symbol(self, symbol: str) -> bool:
        try:
            await self.get_symbol_info(symbol)
            return True
        except ProviderResponseError:
            return False
    
    async def health_check(self) -> bool:
        try:
            await self._ensure_initialized()
            
            terminal_info = await asyncio.to_thread(mt5.terminal_info)
            
            if terminal_info is None:
                return False
            
            return terminal_info.connected
            
        except Exception as e:
            logger.error(
                "mt5_health_check_failed",
                extra={"error": str(e)},
            )
            return False
    
    async def shutdown(self) -> None:
        if self._initialized:
            await asyncio.to_thread(mt5.shutdown)
            self._initialized = False
            
            logger.info("mt5_shutdown_complete")
