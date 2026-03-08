from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import (
    calculate_body_percentage,
    calculate_wick_percentage,
)
from engine.ta.constants import CandleType
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)


class CandleAnalyzer:
    
    def __init__(
        self,
        *,
        marubozu_body_threshold: float = 80.0,
        hammer_lower_wick_threshold: float = 60.0,
        shooting_star_upper_wick_threshold: float = 60.0,
        doji_body_threshold: float = 5.0,
    ) -> None:
        self.marubozu_body_threshold = marubozu_body_threshold
        self.hammer_lower_wick_threshold = hammer_lower_wick_threshold
        self.shooting_star_upper_wick_threshold = shooting_star_upper_wick_threshold
        self.doji_body_threshold = doji_body_threshold
    
    def classify_candle(self, candle: Candle) -> CandleType:
        body_pct = calculate_body_percentage(
            candle.open,
            candle.close,
            candle.high,
            candle.low,
        )
        
        if body_pct <= self.doji_body_threshold:
            return CandleType.DOJI
        
        if body_pct >= self.marubozu_body_threshold:
            if candle.is_bullish:
                return CandleType.MARUBOZU_BULLISH
            else:
                return CandleType.MARUBOZU_BEARISH
        
        lower_wick_pct = calculate_wick_percentage(
            candle.open,
            candle.close,
            candle.high,
            candle.low,
            upper=False,
        )
        
        upper_wick_pct = calculate_wick_percentage(
            candle.open,
            candle.close,
            candle.high,
            candle.low,
            upper=True,
        )
        
        if candle.is_bullish and lower_wick_pct >= self.hammer_lower_wick_threshold:
            return CandleType.HAMMER
        
        if candle.is_bearish and upper_wick_pct >= self.shooting_star_upper_wick_threshold:
            return CandleType.SHOOTING_STAR
        
        return CandleType.STANDARD
    
    def detect_displacement(
        self,
        sequence: CandleSequence,
        min_displacement_pips: float = 20.0,
    ) -> list[tuple[int, float]]:
        from engine.ta.common.utils.price.math import calculate_pips
        
        displacements = []
        
        for i in range(len(sequence.candles)):
            candle = sequence.candles[i]
            
            displacement = calculate_pips(
                candle.open,
                candle.close,
                candle.symbol,
            )
            
            if displacement >= min_displacement_pips:
                displacements.append((i, displacement))
        
        return displacements
    
    def detect_imbalance(
        self,
        candle1: Candle,
        candle2: Candle,
        candle3: Candle,
    ) -> Optional[tuple[float, float]]:
        if candle1.symbol != candle2.symbol or candle2.symbol != candle3.symbol:
            return None
        
        if candle2.low > candle1.high and candle2.low > candle3.high:
            gap_low = max(candle1.high, candle3.high)
            gap_high = candle2.low
            
            if gap_high > gap_low:
                return (gap_low, gap_high)
        
        if candle2.high < candle1.low and candle2.high < candle3.low:
            gap_high = min(candle1.low, candle3.low)
            gap_low = candle2.high
            
            if gap_high > gap_low:
                return (gap_low, gap_high)
        
        return None
    
    def is_engulfing(self, current: Candle, previous: Candle) -> bool:
        return current.engulfs(previous)
    
    def has_long_wick(
        self,
        candle: Candle,
        upper: bool = True,
        min_wick_percentage: float = 50.0,
    ) -> bool:
        wick_pct = calculate_wick_percentage(
            candle.open,
            candle.close,
            candle.high,
            candle.low,
            upper=upper,
        )
        
        return wick_pct >= min_wick_percentage
    
    def calculate_average_body_size(
        self,
        sequence: CandleSequence,
        lookback: int = 20,
    ) -> float:
        candles = sequence.candles[-lookback:] if len(sequence.candles) > lookback else sequence.candles
        
        if not candles:
            return 0.0
        
        total_body = sum(c.body_size for c in candles)
        return total_body / len(candles)
    
    def is_large_body(
        self,
        candle: Candle,
        sequence: CandleSequence,
        multiplier: float = 1.5,
    ) -> bool:
        avg_body = self.calculate_average_body_size(sequence)
        
        if avg_body == 0:
            return False
        
        return candle.body_size >= (avg_body * multiplier)
