from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import calculate_body_percentage
from engine.ta.constants import Direction
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)


class MarubozuAnalyzer:
    
    def __init__(
        self,
        *,
        min_body_percentage: float = 80.0,
        max_wick_percentage: float = 10.0,
        min_displacement_pips: float = 15.0,
    ) -> None:
        self.min_body_percentage = min_body_percentage
        self.max_wick_percentage = max_wick_percentage
        self.min_displacement_pips = min_displacement_pips
    
    def is_marubozu(self, candle: Candle) -> bool:
        body_pct = calculate_body_percentage(
            candle.open,
            candle.close,
            candle.high,
            candle.low,
        )
        
        if body_pct < self.min_body_percentage:
            return False
        
        if candle.upper_wick_percentage > self.max_wick_percentage:
            return False
        
        if candle.lower_wick_percentage > self.max_wick_percentage:
            return False
        
        from engine.ta.common.utils.price.math import calculate_pips
        
        displacement = calculate_pips(
            candle.open,
            candle.close,
            candle.symbol,
        )
        
        if displacement < self.min_displacement_pips:
            return False
        
        return True
    
    def is_bullish_marubozu(self, candle: Candle) -> bool:
        return candle.is_bullish and self.is_marubozu(candle)
    
    def is_bearish_marubozu(self, candle: Candle) -> bool:
        return candle.is_bearish and self.is_marubozu(candle)
    
    def detect_marubozu_sequence(
        self,
        sequence: CandleSequence,
        min_consecutive: int = 2,
    ) -> list[tuple[int, int, Direction]]:
        marubozu_sequences = []
        
        i = 0
        while i < len(sequence.candles):
            candle = sequence.candles[i]
            
            if not self.is_marubozu(candle):
                i += 1
                continue
            
            direction = Direction.BULLISH if candle.is_bullish else Direction.BEARISH
            start_idx = i
            count = 1
            
            j = i + 1
            while j < len(sequence.candles):
                next_candle = sequence.candles[j]
                
                if not self.is_marubozu(next_candle):
                    break
                
                next_direction = Direction.BULLISH if next_candle.is_bullish else Direction.BEARISH
                
                if next_direction != direction:
                    break
                
                count += 1
                j += 1
            
            if count >= min_consecutive:
                marubozu_sequences.append((start_idx, start_idx + count - 1, direction))
            
            i = j if j > i else i + 1
        
        return marubozu_sequences
    
    def get_marubozu_displacement(
        self,
        sequence: CandleSequence,
        start_idx: int,
        end_idx: int,
    ) -> float:
        if start_idx < 0 or end_idx >= len(sequence.candles) or start_idx > end_idx:
            return 0.0
        
        start_candle = sequence.candles[start_idx]
        end_candle = sequence.candles[end_idx]
        
        from engine.ta.common.utils.price.math import calculate_pips
        
        if start_candle.is_bullish:
            displacement = calculate_pips(
                start_candle.open,
                end_candle.close,
                start_candle.symbol,
            )
        else:
            displacement = calculate_pips(
                end_candle.close,
                start_candle.open,
                start_candle.symbol,
            )
        
        return displacement
    
    def find_strongest_marubozu(
        self,
        sequence: CandleSequence,
    ) -> Optional[tuple[int, Candle, float]]:
        strongest_idx = None
        strongest_candle = None
        strongest_displacement = 0.0
        
        for i, candle in enumerate(sequence.candles):
            if not self.is_marubozu(candle):
                continue
            
            from engine.ta.common.utils.price.math import calculate_pips
            
            displacement = calculate_pips(
                candle.open,
                candle.close,
                candle.symbol,
            )
            
            if displacement > strongest_displacement:
                strongest_idx = i
                strongest_candle = candle
                strongest_displacement = displacement
        
        if strongest_candle is None:
            return None
        
        return (strongest_idx, strongest_candle, strongest_displacement)
