from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.compression import CompressionAnalyzer
from engine.ta.common.analyzers.marubozu import MarubozuAnalyzer
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class FakeoutTest:
    """
    Represents a single fakeout test (R1, R2, R3, R4 or S1, S2, S3, S4).
    
    Fakeout = price tests the SR/RS Flip zone but fails to break through.
    Multiple tests confirm the zone is holding and trend is intact.
    
    Diamond Fakeout (Fake QM) = exhaustion warning at end of trend.
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        test_number: int,
        level: float,
        timestamp: object,
        candle_index: int,
        direction: Direction,
        is_diamond_fakeout: bool = False,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.test_number = test_number
        self.level = level
        self.timestamp = timestamp
        self.candle_index = candle_index
        self.direction = direction
        self.is_diamond_fakeout = is_diamond_fakeout


class FakeoutDetector:
    """
    Detects fakeout/exhaustion sequences at SR/RS Flip zones.
    
    Fakeout Requirements (Universal Rule 7):
    - Price tests SR/RS Flip zone repeatedly
    - Each test fails to break through (R1, R2, R3, R4 or S1, S2, S3, S4)
    - More tests = stronger zone (Universal Rule 8)
    - Compression inside fakeout zone = conviction (Universal Rule 5)
    - Diamond Fakeout at end = exhaustion warning (Universal Rule 6)
    - Fakeout broken by Marubozu = entry imminent (Universal Rule 7)
    
    Diamond Fakeout:
    - Looks like QM structure but is NOT a real QM
    - Appears at fakeout zone near end of long trend
    - Warns that move may be exhausting
    - Do NOT trade as QM - it's a signal to tighten management
    """
    
    def __init__(
        self,
        config: SnDConfig,
        compression_analyzer: CompressionAnalyzer,
        marubozu_analyzer: MarubozuAnalyzer,
    ) -> None:
        self.config = config
        self.compression_analyzer = compression_analyzer
        self.marubozu_analyzer = marubozu_analyzer
        self._logger = get_logger(__name__)
    
    def detect_resistance_fakeouts(
        self,
        sequence: CandleSequence,
        sr_flip_level: float,
        sr_flip_index: int,
    ) -> list[FakeoutTest]:
        fakeouts = []
        
        test_number = 1
        
        for i in range(sr_flip_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if candle.high >= sr_flip_level and candle.close < sr_flip_level:
                is_diamond = self._check_diamond_fakeout(
                    sequence,
                    i,
                    Direction.BEARISH,
                )
                
                fakeout = FakeoutTest(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    test_number=test_number,
                    level=sr_flip_level,
                    timestamp=candle.timestamp,
                    candle_index=i,
                    direction=Direction.BEARISH,
                    is_diamond_fakeout=is_diamond,
                )
                
                fakeouts.append(fakeout)
                
                self._logger.debug(
                    "resistance_fakeout_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "test_number": test_number,
                        "level": sr_flip_level,
                        "is_diamond": is_diamond,
                    },
                )
                
                test_number += 1
            
            if candle.close > sr_flip_level:
                break
        
        return fakeouts
    
    def detect_support_fakeouts(
        self,
        sequence: CandleSequence,
        rs_flip_level: float,
        rs_flip_index: int,
    ) -> list[FakeoutTest]:
        fakeouts = []
        
        test_number = 1
        
        for i in range(rs_flip_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if candle.low <= rs_flip_level and candle.close > rs_flip_level:
                is_diamond = self._check_diamond_fakeout(
                    sequence,
                    i,
                    Direction.BULLISH,
                )
                
                fakeout = FakeoutTest(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    test_number=test_number,
                    level=rs_flip_level,
                    timestamp=candle.timestamp,
                    candle_index=i,
                    direction=Direction.BULLISH,
                    is_diamond_fakeout=is_diamond,
                )
                
                fakeouts.append(fakeout)
                
                self._logger.debug(
                    "support_fakeout_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "test_number": test_number,
                        "level": rs_flip_level,
                        "is_diamond": is_diamond,
                    },
                )
                
                test_number += 1
            
            if candle.close < rs_flip_level:
                break
        
        return fakeouts
    
    def check_compression_at_fakeout(
        self,
        sequence: CandleSequence,
        fakeout_index: int,
    ) -> bool:
        if fakeout_index < self.config.compression_min_candles:
            return False
        
        start_index = max(0, fakeout_index - self.config.compression_min_candles)
        
        compression_candles = sequence.candles[start_index:fakeout_index + 1]
        
        return self.compression_analyzer.is_compression(
            compression_candles,
            sequence.symbol,
        )
    
    def check_fakeout_broken_by_marubozu(
        self,
        sequence: CandleSequence,
        fakeout_level: float,
        direction: Direction,
        last_fakeout_index: int,
    ) -> Optional[int]:
        for i in range(last_fakeout_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if direction == Direction.BULLISH:
                if self.marubozu_analyzer.is_bullish_marubozu(candle):
                    if candle.close > fakeout_level:
                        return i
            
            else:
                if self.marubozu_analyzer.is_bearish_marubozu(candle):
                    if candle.close < fakeout_level:
                        return i
        
        return None
    
    def _check_diamond_fakeout(
        self,
        sequence: CandleSequence,
        candle_index: int,
        direction: Direction,
    ) -> bool:
        if candle_index < 2 or candle_index >= len(sequence.candles) - 1:
            return False
        
        prev_candle = sequence.candles[candle_index - 1]
        candle = sequence.candles[candle_index]
        next_candle = sequence.candles[candle_index + 1]
        
        if direction == Direction.BEARISH:
            if (prev_candle.high < candle.high and 
                next_candle.high < candle.high and
                candle.close < prev_candle.close):
                return True
        
        else:
            if (prev_candle.low > candle.low and 
                next_candle.low > candle.low and
                candle.close > prev_candle.close):
                return True
        
        return False
