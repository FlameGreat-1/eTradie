from datetime import datetime, timedelta
from typing import Optional

from engine.shared.exceptions import ProviderValidationError
from engine.shared.logging import get_logger
from engine.ta.constants import Timeframe, TIMEFRAME_MINUTES
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)


class BrokerDataValidator:
    
    def __init__(
        self,
        *,
        max_gap_multiplier: float = 2.0,
        min_candles_required: int = 1,
    ) -> None:
        self.max_gap_multiplier = max_gap_multiplier
        self.min_candles_required = min_candles_required
    
    def validate_candle(self, candle: Candle) -> None:
        if candle.high < candle.low:
            raise ProviderValidationError(
                "Invalid candle: high < low",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "high": candle.high,
                    "low": candle.low,
                },
            )
        
        if candle.open <= 0 or candle.close <= 0:
            raise ProviderValidationError(
                "Invalid candle: open or close <= 0",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "open": candle.open,
                    "close": candle.close,
                },
            )
        
        if candle.high < candle.open or candle.high < candle.close:
            raise ProviderValidationError(
                "Invalid candle: high < open or close",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "high": candle.high,
                    "open": candle.open,
                    "close": candle.close,
                },
            )
        
        if candle.low > candle.open or candle.low > candle.close:
            raise ProviderValidationError(
                "Invalid candle: low > open or close",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "low": candle.low,
                    "open": candle.open,
                    "close": candle.close,
                },
            )
        
        if candle.volume < 0:
            raise ProviderValidationError(
                "Invalid candle: volume < 0",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "volume": candle.volume,
                },
            )
    
    def validate_sequence(self, sequence: CandleSequence) -> None:
        if sequence.count < self.min_candles_required:
            raise ProviderValidationError(
                f"Insufficient candles: got {sequence.count}, required {self.min_candles_required}",
                details={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "count": sequence.count,
                    "required": self.min_candles_required,
                },
            )
        
        for candle in sequence.candles:
            self.validate_candle(candle)
        
        self._validate_timestamp_continuity(sequence)
        
        self._validate_symbol_consistency(sequence)
        
        self._validate_timeframe_consistency(sequence)
    
    def _validate_timestamp_continuity(self, sequence: CandleSequence) -> None:
        if sequence.count < 2:
            return
        
        timeframe_minutes = TIMEFRAME_MINUTES.get(sequence.timeframe)
        if timeframe_minutes is None:
            raise ProviderValidationError(
                f"Unknown timeframe: {sequence.timeframe}",
                details={"timeframe": sequence.timeframe},
            )
        
        expected_delta = timedelta(minutes=timeframe_minutes)
        max_allowed_gap = timedelta(
            minutes=int(timeframe_minutes * self.max_gap_multiplier)
        )
        
        for i in range(1, len(sequence.candles)):
            prev_candle = sequence.candles[i - 1]
            curr_candle = sequence.candles[i]
            
            actual_delta = curr_candle.timestamp - prev_candle.timestamp
            
            if actual_delta < expected_delta:
                raise ProviderValidationError(
                    "Candles too close together",
                    details={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "prev_timestamp": prev_candle.timestamp.isoformat(),
                        "curr_timestamp": curr_candle.timestamp.isoformat(),
                        "actual_delta_minutes": actual_delta.total_seconds() / 60,
                        "expected_delta_minutes": timeframe_minutes,
                    },
                )
            
            if actual_delta > max_allowed_gap:
                logger.warning(
                    "broker_data_gap_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "prev_timestamp": prev_candle.timestamp.isoformat(),
                        "curr_timestamp": curr_candle.timestamp.isoformat(),
                        "gap_minutes": actual_delta.total_seconds() / 60,
                        "max_allowed_minutes": max_allowed_gap.total_seconds() / 60,
                    },
                )
    
    def _validate_symbol_consistency(self, sequence: CandleSequence) -> None:
        symbols = {candle.symbol for candle in sequence.candles}
        
        if len(symbols) > 1:
            raise ProviderValidationError(
                "Multiple symbols in sequence",
                details={
                    "expected_symbol": sequence.symbol,
                    "found_symbols": list(symbols),
                },
            )
        
        if sequence.symbol not in symbols:
            raise ProviderValidationError(
                "Sequence symbol mismatch",
                details={
                    "sequence_symbol": sequence.symbol,
                    "candle_symbols": list(symbols),
                },
            )
    
    def _validate_timeframe_consistency(self, sequence: CandleSequence) -> None:
        timeframes = {candle.timeframe for candle in sequence.candles}
        
        if len(timeframes) > 1:
            raise ProviderValidationError(
                "Multiple timeframes in sequence",
                details={
                    "expected_timeframe": sequence.timeframe,
                    "found_timeframes": [str(tf) for tf in timeframes],
                },
            )
        
        if sequence.timeframe not in timeframes:
            raise ProviderValidationError(
                "Sequence timeframe mismatch",
                details={
                    "sequence_timeframe": sequence.timeframe,
                    "candle_timeframes": [str(tf) for tf in timeframes],
                },
            )
    
    def validate_time_range(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> None:
        if start_time is not None and end_time is not None:
            if end_time <= start_time:
                raise ProviderValidationError(
                    "End time must be after start time",
                    details={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                )
            
            if end_time > datetime.now():
                raise ProviderValidationError(
                    "End time cannot be in the future",
                    details={
                        "end_time": end_time.isoformat(),
                        "now": datetime.now().isoformat(),
                    },
                )
