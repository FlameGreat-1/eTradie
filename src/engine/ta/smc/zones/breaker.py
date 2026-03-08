from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.zone import OrderBlock, BreakerBlock
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class BreakerDetector:
    """
    Detects Breaker Blocks - Order Blocks that have been broken and flipped.
    
    Breaker Block Formation:
    - An OB is created
    - Price breaks through the OB in the opposite direction
    - The broken OB now becomes a Breaker Block
    - Breaker acts as support/resistance in the new direction
    
    Breaker blocks are stronger than regular OBs because they represent
    a failed institutional level that has now flipped polarity.
    """
    
    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_breaker_from_ob(
        self,
        sequence: CandleSequence,
        ob: OrderBlock,
    ) -> Optional[BreakerBlock]:
        if ob.candle_index >= len(sequence.candles) - 1:
            return None
        
        broken = False
        broken_timestamp = None
        
        for i in range(ob.candle_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if ob.direction == Direction.BULLISH:
                if candle.close < ob.lower_bound:
                    broken = True
                    broken_timestamp = candle.timestamp
                    break
            
            else:
                if candle.close > ob.upper_bound:
                    broken = True
                    broken_timestamp = candle.timestamp
                    break
        
        if not broken or not broken_timestamp:
            return None
        
        new_direction = Direction.BEARISH if ob.direction == Direction.BULLISH else Direction.BULLISH
        
        breaker = BreakerBlock(
            symbol=ob.symbol,
            timeframe=ob.timeframe,
            upper_bound=ob.upper_bound,
            lower_bound=ob.lower_bound,
            timestamp=ob.timestamp,
            candle_index=ob.candle_index,
            direction=new_direction,
            original_ob_timestamp=ob.timestamp,
            broken_timestamp=broken_timestamp,
            mitigated=False,
        )
        
        self._logger.debug(
            "breaker_block_detected",
            extra={
                "symbol": ob.symbol,
                "timeframe": ob.timeframe,
                "original_direction": str(ob.direction),
                "new_direction": str(new_direction),
                "broken_timestamp": broken_timestamp.isoformat(),
            },
        )
        
        return breaker
    
    def check_breaker_mitigation(
        self,
        breaker: BreakerBlock,
        sequence: CandleSequence,
    ) -> bool:
        if breaker.candle_index >= len(sequence.candles) - 1:
            return False
        
        for i in range(breaker.candle_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if breaker.direction == Direction.BULLISH:
                if candle.low <= breaker.lower_bound:
                    return True
            
            else:
                if candle.high >= breaker.upper_bound:
                    return True
        
        return False
