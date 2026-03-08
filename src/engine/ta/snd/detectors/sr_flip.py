from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.marubozu import MarubozuAnalyzer
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.structure_event import SRFlip
from engine.ta.models.swing import SwingLow
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class SRFlipDetector:
    """
    Detects Support-to-Resistance Flip (SR Flip) structures.
    
    SR Flip Formation (Universal Rule 1):
    - Support level exists (swing low)
    - Single bearish Marubozu breaks Support downward
    - Support becomes Resistance (SR Flip zone created)
    - Price retraces up to SR Flip zone
    - Fakeouts form at zone (R1, R2, R3, R4)
    - Entry in Supply zone between SR Flip and QML
    
    Requirements:
    - Marubozu is non-negotiable (full body, minimal wicks)
    - Must be substantial close below the level
    - Creates the bottom boundary of Supply zone
    """
    
    def __init__(
        self,
        config: SnDConfig,
        marubozu_analyzer: MarubozuAnalyzer,
    ) -> None:
        self.config = config
        self.marubozu_analyzer = marubozu_analyzer
        self._logger = get_logger(__name__)
    
    def detect_sr_flips(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[SRFlip]:
        sr_flips = []
        
        for swing_low in swing_lows:
            if swing_low.index >= len(sequence.candles) - 1:
                continue
            
            for i in range(swing_low.index + 1, len(sequence.candles)):
                candle = sequence.candles[i]
                
                if not self.marubozu_analyzer.is_bearish_marubozu(candle):
                    continue
                
                if candle.close >= swing_low.price:
                    continue
                
                sr_flip = SRFlip(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    timestamp=candle.timestamp,
                    original_support_level=swing_low.price,
                    original_support_timestamp=swing_low.timestamp,
                    breakout_candle_index=i,
                    breakout_price=candle.close,
                    new_resistance_level=swing_low.price,
                    direction=Direction.BEARISH,
                    is_valid=True,
                )
                
                sr_flips.append(sr_flip)
                
                self._logger.debug(
                    "sr_flip_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "original_support": swing_low.price,
                        "breakout_price": candle.close,
                        "new_resistance": swing_low.price,
                    },
                )
                
                break
        
        return sr_flips
    
    def get_latest_sr_flip(
        self,
        sr_flips: list[SRFlip],
    ) -> Optional[SRFlip]:
        if not sr_flips:
            return None
        
        valid_flips = [flip for flip in sr_flips if flip.is_valid]
        
        if not valid_flips:
            return None
        
        return max(valid_flips, key=lambda x: x.timestamp)
    
    def validate_sr_flip_with_marubozu(
        self,
        sr_flip: SRFlip,
        sequence: CandleSequence,
    ) -> bool:
        if sr_flip.breakout_candle_index >= len(sequence.candles):
            return False
        
        breakout_candle = sequence.candles[sr_flip.breakout_candle_index]
        
        return self.marubozu_analyzer.is_bearish_marubozu(breakout_candle)
