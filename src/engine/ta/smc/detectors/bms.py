from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import calculate_pips
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.structure_event import BreakInMarketStructure
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class BMSDetector:
    """
    Detects Break in Market Structure (BMS) events.
    
    BMS occurs when:
    - Bullish BMS: Price breaks above the most recent swing high with displacement
    - Bearish BMS: Price breaks below the most recent swing low with displacement
    
    Requirements (Universal Rule 2):
    - Must have clear swing structure (HH+HL or LH+LL)
    - Must have displacement (minimum pips threshold)
    - Must close substantially beyond the level (not just a wick)
    """
    
    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_bullish_bms(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[BreakInMarketStructure]:
        bms_events = []
        
        if len(swing_lows) < 2:
            return bms_events
        
        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_lows) - 1):
            current_low = sorted_lows[i]
            next_low = sorted_lows[i + 1]
            
            if next_low.price <= current_low.price:
                continue
            
            if next_low.index >= len(sequence.candles):
                continue
            
            breakout_candle = sequence.candles[next_low.index]
            
            displacement = calculate_pips(
                current_low.price,
                breakout_candle.close,
                sequence.symbol,
            )
            
            if displacement < self.config.min_displacement_pips:
                continue
            
            if breakout_candle.close <= current_low.price:
                continue
            
            bms = BreakInMarketStructure(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=breakout_candle.timestamp,
                direction=Direction.BULLISH,
                broken_level=current_low.price,
                broken_level_timestamp=current_low.timestamp,
                breakout_price=breakout_candle.close,
                candle_index=next_low.index,
                displacement_pips=displacement,
                confirmed=True,
            )
            
            bms_events.append(bms)
            
            self._logger.debug(
                "bullish_bms_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "broken_level": current_low.price,
                    "breakout_price": breakout_candle.close,
                    "displacement_pips": displacement,
                },
            )
        
        return bms_events
    
    def detect_bearish_bms(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[BreakInMarketStructure]:
        bms_events = []
        
        if len(swing_highs) < 2:
            return bms_events
        
        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_highs) - 1):
            current_high = sorted_highs[i]
            next_high = sorted_highs[i + 1]
            
            if next_high.price >= current_high.price:
                continue
            
            if next_high.index >= len(sequence.candles):
                continue
            
            breakout_candle = sequence.candles[next_high.index]
            
            displacement = calculate_pips(
                breakout_candle.close,
                current_high.price,
                sequence.symbol,
            )
            
            if displacement < self.config.min_displacement_pips:
                continue
            
            if breakout_candle.close >= current_high.price:
                continue
            
            bms = BreakInMarketStructure(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=breakout_candle.timestamp,
                direction=Direction.BEARISH,
                broken_level=current_high.price,
                broken_level_timestamp=current_high.timestamp,
                breakout_price=breakout_candle.close,
                candle_index=next_high.index,
                displacement_pips=displacement,
                confirmed=True,
            )
            
            bms_events.append(bms)
            
            self._logger.debug(
                "bearish_bms_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "broken_level": current_high.price,
                    "breakout_price": breakout_candle.close,
                    "displacement_pips": displacement,
                },
            )
        
        return bms_events
    
    def get_latest_bms(
        self,
        bms_events: list[BreakInMarketStructure],
    ) -> Optional[BreakInMarketStructure]:
        if not bms_events:
            return None
        return max(bms_events, key=lambda x: x.timestamp)
