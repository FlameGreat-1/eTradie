from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import calculate_pips, calculate_body_percentage
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.structure_event import BreakInMarketStructure, ChangeOfCharacter
from engine.ta.models.zone import OrderBlock
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class OrderBlockDetector:
    """
    Detects Order Blocks (OB) according to strict SMC definition.
    
    OB Definition (Universal Rule 4):
    - Bullish OB = last BEARISH candle before bullish move that caused BMS higher
    - Bearish OB = last BULLISH candle before bearish move that caused BMS lower
    - SL always goes beyond the OB (below for buys, above for sells)
    
    7 Rules of a Tradeable OB (all must be satisfied):
    1. Must sponsor a BOS/CHOCH
    2. Must have FVG associated
    3. Must have liquidity/inducement present
    4. Must take out opposing OB
    5. Must be at Premium (sells) or Discount (buys)
    6. Must have BPR (FVG within FVG, OB within OB on subsequent TF)
    7. Select HTF OBs, refine to LTF
    
    This detector handles rules 1 and 4. Other rules validated separately.
    """
    
    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_bullish_ob(
        self,
        sequence: CandleSequence,
        bms_event: BreakInMarketStructure,
    ) -> Optional[OrderBlock]:
        if bms_event.direction != Direction.BULLISH:
            return None
        
        if bms_event.candle_index < 1:
            return None
        
        for i in range(bms_event.candle_index - 1, -1, -1):
            candle = sequence.candles[i]
            
            if not candle.is_bearish:
                continue
            
            body_pct = calculate_body_percentage(
                candle.open,
                candle.close,
                candle.high,
                candle.low,
            )
            
            if body_pct < self.config.ob_body_percentage_threshold:
                continue
            
            displacement = calculate_pips(
                candle.low,
                bms_event.breakout_price,
                sequence.symbol,
            )
            
            if displacement < self.config.min_displacement_pips:
                continue
            
            ob = OrderBlock(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                upper_bound=candle.high,
                lower_bound=candle.low,
                timestamp=candle.timestamp,
                candle_index=i,
                direction=Direction.BULLISH,
                displacement_pips=displacement,
                is_breaker=False,
                mitigated=False,
            )
            
            self._logger.debug(
                "bullish_ob_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "upper_bound": ob.upper_bound,
                    "lower_bound": ob.lower_bound,
                    "displacement_pips": displacement,
                },
            )
            
            return ob
        
        return None
    
    def detect_bearish_ob(
        self,
        sequence: CandleSequence,
        bms_event: BreakInMarketStructure,
    ) -> Optional[OrderBlock]:
        if bms_event.direction != Direction.BEARISH:
            return None
        
        if bms_event.candle_index < 1:
            return None
        
        for i in range(bms_event.candle_index - 1, -1, -1):
            candle = sequence.candles[i]
            
            if not candle.is_bullish:
                continue
            
            body_pct = calculate_body_percentage(
                candle.open,
                candle.close,
                candle.high,
                candle.low,
            )
            
            if body_pct < self.config.ob_body_percentage_threshold:
                continue
            
            displacement = calculate_pips(
                bms_event.breakout_price,
                candle.high,
                sequence.symbol,
            )
            
            if displacement < self.config.min_displacement_pips:
                continue
            
            ob = OrderBlock(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                upper_bound=candle.high,
                lower_bound=candle.low,
                timestamp=candle.timestamp,
                candle_index=i,
                direction=Direction.BEARISH,
                displacement_pips=displacement,
                is_breaker=False,
                mitigated=False,
            )
            
            self._logger.debug(
                "bearish_ob_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "upper_bound": ob.upper_bound,
                    "lower_bound": ob.lower_bound,
                    "displacement_pips": displacement,
                },
            )
            
            return ob
        
        return None
    
    def detect_ob_from_choch(
        self,
        sequence: CandleSequence,
        choch_event: ChangeOfCharacter,
    ) -> Optional[OrderBlock]:
        if choch_event.candle_index < 1:
            return None
        
        if choch_event.direction == Direction.BULLISH:
            for i in range(choch_event.candle_index - 1, -1, -1):
                candle = sequence.candles[i]
                
                if candle.is_bearish:
                    ob = OrderBlock(
                        symbol=sequence.symbol,
                        timeframe=sequence.timeframe,
                        upper_bound=candle.high,
                        lower_bound=candle.low,
                        timestamp=candle.timestamp,
                        candle_index=i,
                        direction=Direction.BULLISH,
                        displacement_pips=0.0,
                        is_breaker=False,
                        mitigated=False,
                    )
                    return ob
        
        else:
            for i in range(choch_event.candle_index - 1, -1, -1):
                candle = sequence.candles[i]
                
                if candle.is_bullish:
                    ob = OrderBlock(
                        symbol=sequence.symbol,
                        timeframe=sequence.timeframe,
                        upper_bound=candle.high,
                        lower_bound=candle.low,
                        timestamp=candle.timestamp,
                        candle_index=i,
                        direction=Direction.BEARISH,
                        displacement_pips=0.0,
                        is_breaker=False,
                        mitigated=False,
                    )
                    return ob
        
        return None
