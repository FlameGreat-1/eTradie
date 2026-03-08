from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import calculate_pips
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.structure_event import ChangeOfCharacter
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class CHOCHDetector:
    """
    Detects Change of Character (CHOCH) events.
    
    CHOCH is the initial signal of a shift in order flow - earlier and smaller than BMS.
    
    CHOCH occurs when:
    - Bullish CHOCH: Price breaks above a minor swing high (internal structure)
    - Bearish CHOCH: Price breaks below a minor swing low (internal structure)
    
    CHOCH is used as confluence confirmation, not standalone entry.
    Sequence: CHOCH appears first → BMS confirms → entry on RTO to OB.
    """
    
    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_bullish_choch(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[ChangeOfCharacter]:
        choch_events = []
        
        if len(swing_lows) < 2:
            return choch_events
        
        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_lows) - 1):
            current_low = sorted_lows[i]
            next_low = sorted_lows[i + 1]
            
            if next_low.price <= current_low.price:
                continue
            
            if current_low.strength >= 5:
                continue
            
            if next_low.index >= len(sequence.candles):
                continue
            
            breakout_candle = sequence.candles[next_low.index]
            
            if breakout_candle.close <= current_low.price:
                continue
            
            choch = ChangeOfCharacter(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=breakout_candle.timestamp,
                direction=Direction.BULLISH,
                broken_level=current_low.price,
                broken_level_timestamp=current_low.timestamp,
                breakout_price=breakout_candle.close,
                candle_index=next_low.index,
                is_minor=True,
            )
            
            choch_events.append(choch)
            
            self._logger.debug(
                "bullish_choch_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "broken_level": current_low.price,
                    "breakout_price": breakout_candle.close,
                },
            )
        
        return choch_events
    
    def detect_bearish_choch(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[ChangeOfCharacter]:
        choch_events = []
        
        if len(swing_highs) < 2:
            return choch_events
        
        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_highs) - 1):
            current_high = sorted_highs[i]
            next_high = sorted_highs[i + 1]
            
            if next_high.price >= current_high.price:
                continue
            
            if current_high.strength >= 5:
                continue
            
            if next_high.index >= len(sequence.candles):
                continue
            
            breakout_candle = sequence.candles[next_high.index]
            
            if breakout_candle.close >= current_high.price:
                continue
            
            choch = ChangeOfCharacter(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=breakout_candle.timestamp,
                direction=Direction.BEARISH,
                broken_level=current_high.price,
                broken_level_timestamp=current_high.timestamp,
                breakout_price=breakout_candle.close,
                candle_index=next_high.index,
                is_minor=True,
            )
            
            choch_events.append(choch)
            
            self._logger.debug(
                "bearish_choch_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "broken_level": current_high.price,
                    "breakout_price": breakout_candle.close,
                },
            )
        
        return choch_events
    
    def get_latest_choch(
        self,
        choch_events: list[ChangeOfCharacter],
    ) -> Optional[ChangeOfCharacter]:
        if not choch_events:
            return None
        return max(choch_events, key=lambda x: x.timestamp)
