from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.structure_event import ShiftInMarketStructure
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class SMSDetector:
    """
    Detects Shift in Market Structure (SMS) events.
    
    SMS occurs when price fails to break the last swing high/low (failure swing),
    signaling trend exhaustion and potential reversal.
    
    SMS Requirements:
    - Bullish SMS: Price in downtrend fails to break last swing low
    - Bearish SMS: Price in uptrend fails to break last swing high
    - Must be followed by BMS in opposite direction to confirm reversal
    
    Pattern: SMS + BMS + RTO (Pattern 3/8)
    """
    
    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_bullish_sms(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[ShiftInMarketStructure]:
        sms_events = []
        
        if len(swing_lows) < 3:
            return sms_events
        
        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_lows) - 2):
            low1 = sorted_lows[i]
            low2 = sorted_lows[i + 1]
            low3 = sorted_lows[i + 2]
            
            if not (low2.price < low1.price):
                continue
            
            if low3.price < low2.price:
                continue
            
            if low3.index >= len(sequence.candles):
                continue
            
            reversal_candle = sequence.candles[low3.index]
            
            sms = ShiftInMarketStructure(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=reversal_candle.timestamp,
                direction=Direction.BULLISH,
                failed_level=low2.price,
                failed_level_timestamp=low2.timestamp,
                reversal_price=reversal_candle.close,
                candle_index=low3.index,
                is_failure_swing=True,
            )
            
            sms_events.append(sms)
            
            self._logger.debug(
                "bullish_sms_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "failed_level": low2.price,
                    "reversal_price": reversal_candle.close,
                },
            )
        
        return sms_events
    
    def detect_bearish_sms(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[ShiftInMarketStructure]:
        sms_events = []
        
        if len(swing_highs) < 3:
            return sms_events
        
        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_highs) - 2):
            high1 = sorted_highs[i]
            high2 = sorted_highs[i + 1]
            high3 = sorted_highs[i + 2]
            
            if not (high2.price > high1.price):
                continue
            
            if high3.price > high2.price:
                continue
            
            if high3.index >= len(sequence.candles):
                continue
            
            reversal_candle = sequence.candles[high3.index]
            
            sms = ShiftInMarketStructure(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=reversal_candle.timestamp,
                direction=Direction.BEARISH,
                failed_level=high2.price,
                failed_level_timestamp=high2.timestamp,
                reversal_price=reversal_candle.close,
                candle_index=high3.index,
                is_failure_swing=True,
            )
            
            sms_events.append(sms)
            
            self._logger.debug(
                "bearish_sms_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "failed_level": high2.price,
                    "reversal_price": reversal_candle.close,
                },
            )
        
        return sms_events
    
    def get_latest_sms(
        self,
        sms_events: list[ShiftInMarketStructure],
    ) -> Optional[ShiftInMarketStructure]:
        if not sms_events:
            return None
        return max(sms_events, key=lambda x: x.timestamp)
