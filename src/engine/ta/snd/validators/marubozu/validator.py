from engine.shared.logging import get_logger
from engine.ta.common.analyzers.marubozu import MarubozuAnalyzer
from engine.ta.common.utils.price.math import calculate_body_percentage
from engine.ta.models.candle import Candle
from engine.ta.models.candle import CandleSequence
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class MarubozuValidator:
    """
    Validates Marubozu quality and eligibility for SnD patterns.
    
    Universal Rule 1: Marubozu is Non-Negotiable
    
    Every breakout must be a single Marubozu candle:
    - Full body (>= 80% of total range)
    - Minimal wicks (<= 10% of total range)
    - Substantial close beyond the level
    - Single candle only
    
    This validator ensures strict compliance with Marubozu requirements.
    No exceptions. No partial implementations.
    """
    
    def __init__(
        self,
        config: SnDConfig,
        marubozu_analyzer: MarubozuAnalyzer,
    ) -> None:
        self.config = config
        self.marubozu_analyzer = marubozu_analyzer
        self._logger = get_logger(__name__)
    
    def validate_bullish_marubozu(
        self,
        candle: Candle,
    ) -> bool:
        """
        Validate bullish Marubozu for RS Flip breakout.
        
        Requirements:
        - Must be bullish candle
        - Body percentage >= threshold (default 80%)
        - Upper wick <= max wick percentage (default 10%)
        - Lower wick <= max wick percentage (default 10%)
        """
        if not candle.is_bullish:
            self._logger.debug(
                "marubozu_validation_failed_not_bullish",
                extra={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                },
            )
            return False
        
        body_pct = calculate_body_percentage(
            candle.open,
            candle.close,
            candle.high,
            candle.low,
        )
        
        if body_pct < self.config.marubozu_body_percentage_threshold:
            self._logger.debug(
                "marubozu_validation_failed_body_percentage",
                extra={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "body_pct": body_pct,
                    "threshold": self.config.marubozu_body_percentage_threshold,
                },
            )
            return False
        
        total_range = candle.high - candle.low
        
        if total_range == 0:
            return False
        
        upper_wick = candle.high - candle.close
        lower_wick = candle.open - candle.low
        
        upper_wick_pct = (upper_wick / total_range) * 100.0
        lower_wick_pct = (lower_wick / total_range) * 100.0
        
        if upper_wick_pct > self.config.marubozu_max_wick_percentage:
            self._logger.debug(
                "marubozu_validation_failed_upper_wick",
                extra={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "upper_wick_pct": upper_wick_pct,
                    "max_wick": self.config.marubozu_max_wick_percentage,
                },
            )
            return False
        
        if lower_wick_pct > self.config.marubozu_max_wick_percentage:
            self._logger.debug(
                "marubozu_validation_failed_lower_wick",
                extra={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "lower_wick_pct": lower_wick_pct,
                    "max_wick": self.config.marubozu_max_wick_percentage,
                },
            )
            return False
        
        return True
    
    def validate_bearish_marubozu(
        self,
        candle: Candle,
    ) -> bool:
        """
        Validate bearish Marubozu for SR Flip breakout.
        
        Requirements:
        - Must be bearish candle
        - Body percentage >= threshold (default 80%)
        - Upper wick <= max wick percentage (default 10%)
        - Lower wick <= max wick percentage (default 10%)
        """
        if not candle.is_bearish:
            self._logger.debug(
                "marubozu_validation_failed_not_bearish",
                extra={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                },
            )
            return False
        
        body_pct = calculate_body_percentage(
            candle.open,
            candle.close,
            candle.high,
            candle.low,
        )
        
        if body_pct < self.config.marubozu_body_percentage_threshold:
            self._logger.debug(
                "marubozu_validation_failed_body_percentage",
                extra={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "body_pct": body_pct,
                    "threshold": self.config.marubozu_body_percentage_threshold,
                },
            )
            return False
        
        total_range = candle.high - candle.low
        
        if total_range == 0:
            return False
        
        upper_wick = candle.high - candle.open
        lower_wick = candle.close - candle.low
        
        upper_wick_pct = (upper_wick / total_range) * 100.0
        lower_wick_pct = (lower_wick / total_range) * 100.0
        
        if upper_wick_pct > self.config.marubozu_max_wick_percentage:
            self._logger.debug(
                "marubozu_validation_failed_upper_wick",
                extra={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "upper_wick_pct": upper_wick_pct,
                    "max_wick": self.config.marubozu_max_wick_percentage,
                },
            )
            return False
        
        if lower_wick_pct > self.config.marubozu_max_wick_percentage:
            self._logger.debug(
                "marubozu_validation_failed_lower_wick",
                extra={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "lower_wick_pct": lower_wick_pct,
                    "max_wick": self.config.marubozu_max_wick_percentage,
                },
            )
            return False
        
        return True
    
    def validate_sr_flip_marubozu(
        self,
        sequence: CandleSequence,
        breakout_candle_index: int,
    ) -> bool:
        """Validate SR Flip breakout candle is a valid bearish Marubozu."""
        if breakout_candle_index >= len(sequence.candles):
            return False
        
        candle = sequence.candles[breakout_candle_index]
        
        return self.validate_bearish_marubozu(candle)
    
    def validate_rs_flip_marubozu(
        self,
        sequence: CandleSequence,
        breakout_candle_index: int,
    ) -> bool:
        """Validate RS Flip breakout candle is a valid bullish Marubozu."""
        if breakout_candle_index >= len(sequence.candles):
            return False
        
        candle = sequence.candles[breakout_candle_index]
        
        return self.validate_bullish_marubozu(candle)
    
    def validate_fakeout_breakout_marubozu(
        self,
        sequence: CandleSequence,
        breakout_candle_index: int,
        is_bullish: bool,
    ) -> bool:
        """
        Validate fakeout breakout candle is a valid Marubozu.
        
        This is the Marubozu that breaks through the fakeout zone,
        signaling that the Supply/Demand zone (QML/QMH) is directly ahead.
        """
        if breakout_candle_index >= len(sequence.candles):
            return False
        
        candle = sequence.candles[breakout_candle_index]
        
        if is_bullish:
            return self.validate_bullish_marubozu(candle)
        else:
            return self.validate_bearish_marubozu(candle)
