from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.liquidity_event import CompressionEvent

logger = get_logger(__name__)


class CompressionAnalyzer:
    
    def __init__(
        self,
        *,
        min_candles: int = 3,
        max_range_pips: float = 15.0,
        min_range_pips: float = 5.0,
    ) -> None:
        self.min_candles = min_candles
        self.max_range_pips = max_range_pips
        self.min_range_pips = min_range_pips
    
    def detect_compression(
        self,
        sequence: CandleSequence,
    ) -> list[CompressionEvent]:
        compressions = []
        
        i = 0
        while i < len(sequence.candles) - self.min_candles + 1:
            compression = self._find_compression_at_index(sequence, i)
            
            if compression:
                compressions.append(compression)
                i = compression.end_index + 1 if compression.end_index else i + 1
            else:
                i += 1
        
        return compressions
    
    def _find_compression_at_index(
        self,
        sequence: CandleSequence,
        start_index: int,
    ) -> Optional[CompressionEvent]:
        candles = sequence.candles
        
        if start_index + self.min_candles > len(candles):
            return None
        
        start_candle = candles[start_index]
        
        high = start_candle.high
        low = start_candle.low
        candle_count = 1
        end_index = start_index
        
        for i in range(start_index + 1, len(candles)):
            current = candles[i]
            
            temp_high = max(high, current.high)
            temp_low = min(low, current.low)
            
            from engine.ta.common.utils.price.math import calculate_pips
            
            temp_range_pips = calculate_pips(temp_low, temp_high, current.symbol)
            
            if temp_range_pips > self.max_range_pips:
                break
            
            high = temp_high
            low = temp_low
            candle_count += 1
            end_index = i
            
            if candle_count >= self.min_candles:
                range_pips = calculate_pips(low, high, current.symbol)
                
                if range_pips < self.min_range_pips:
                    continue
                
                direction = self._determine_compression_direction(
                    candles[start_index:end_index + 1]
                )
                
                return CompressionEvent(
                    symbol=start_candle.symbol,
                    timeframe=start_candle.timeframe,
                    start_timestamp=start_candle.timestamp,
                    end_timestamp=current.timestamp,
                    high=high,
                    low=low,
                    direction=direction,
                    candle_count=candle_count,
                    start_index=start_index,
                    end_index=end_index,
                )
        
        return None
    
    def _determine_compression_direction(self, candles: list) -> Direction:
        if not candles:
            return Direction.NEUTRAL
        
        first_close = candles[0].close
        last_close = candles[-1].close
        
        if last_close > first_close:
            return Direction.BULLISH
        elif last_close < first_close:
            return Direction.BEARISH
        else:
            return Direction.NEUTRAL
    
    def detect_breakout(
        self,
        compression: CompressionEvent,
        sequence: CandleSequence,
    ) -> Optional[Direction]:
        if compression.end_index is None:
            return None
        
        if compression.end_index + 1 >= len(sequence.candles):
            return None
        
        breakout_candle = sequence.candles[compression.end_index + 1]
        
        if breakout_candle.close > compression.high:
            return Direction.BULLISH
        elif breakout_candle.close < compression.low:
            return Direction.BEARISH
        
        return None
    
    def is_valid_compression(
        self,
        compression: CompressionEvent,
    ) -> bool:
        if compression.candle_count < self.min_candles:
            return False
        
        from engine.ta.common.utils.price.math import calculate_pips
        
        range_pips = calculate_pips(
            compression.low,
            compression.high,
            compression.symbol,
        )
        
        if range_pips < self.min_range_pips or range_pips > self.max_range_pips:
            return False
        
        return True
    
    def get_compression_midpoint(self, compression: CompressionEvent) -> float:
        return (compression.high + compression.low) / 2.0
