from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.zone import MiniPriceLevel
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class MPLDetector:
    """
    Detects Mini Price Level (MPL) structures.
    
    MPL Definition:
    - Small internal engulfing structure near QML
    - Forms during the HH move (for sells) or LL move (for buys)
    - Can be circled on chart (internal structure)
    - Adds extra confluence when present
    
    Two types:
    - Type 1: MPL with internal engulfing structure (circled)
    - Type 2: MPL breaks cleanly without internal structure (no circle)
    
    MPL is optional but adds significant confluence when present.
    """
    
    def __init__(self, config: SnDConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_bearish_mpl(
        self,
        sequence: CandleSequence,
        qml_level: float,
        h2_index: int,
    ) -> list[MiniPriceLevel]:
        mpl_levels = []
        
        if h2_index < 2:
            return mpl_levels
        
        for i in range(h2_index - 10, h2_index):
            if i < 1 or i >= len(sequence.candles) - 1:
                continue
            
            candle = sequence.candles[i]
            prev_candle = sequence.candles[i - 1]
            next_candle = sequence.candles[i + 1]
            
            has_internal_structure = self._check_internal_engulfing(
                prev_candle,
                candle,
                next_candle,
            )
            
            if candle.is_bullish and has_internal_structure:
                mpl = MiniPriceLevel(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    level=candle.high,
                    timestamp=candle.timestamp,
                    candle_index=i,
                    direction=Direction.BEARISH,
                    has_internal_structure=True,
                    is_type1=True,
                )
                
                mpl_levels.append(mpl)
                
                self._logger.debug(
                    "bearish_mpl_type1_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "mpl_level": candle.high,
                        "has_internal_structure": True,
                    },
                )
            
            elif candle.is_bullish and not has_internal_structure:
                mpl = MiniPriceLevel(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    level=candle.high,
                    timestamp=candle.timestamp,
                    candle_index=i,
                    direction=Direction.BEARISH,
                    has_internal_structure=False,
                    is_type1=False,
                )
                
                mpl_levels.append(mpl)
                
                self._logger.debug(
                    "bearish_mpl_type2_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "mpl_level": candle.high,
                        "has_internal_structure": False,
                    },
                )
        
        return mpl_levels
    
    def detect_bullish_mpl(
        self,
        sequence: CandleSequence,
        qmh_level: float,
        l2_index: int,
    ) -> list[MiniPriceLevel]:
        mpl_levels = []
        
        if l2_index < 2:
            return mpl_levels
        
        for i in range(l2_index - 10, l2_index):
            if i < 1 or i >= len(sequence.candles) - 1:
                continue
            
            candle = sequence.candles[i]
            prev_candle = sequence.candles[i - 1]
            next_candle = sequence.candles[i + 1]
            
            has_internal_structure = self._check_internal_engulfing(
                prev_candle,
                candle,
                next_candle,
            )
            
            if candle.is_bearish and has_internal_structure:
                mpl = MiniPriceLevel(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    level=candle.low,
                    timestamp=candle.timestamp,
                    candle_index=i,
                    direction=Direction.BULLISH,
                    has_internal_structure=True,
                    is_type1=True,
                )
                
                mpl_levels.append(mpl)
                
                self._logger.debug(
                    "bullish_mpl_type1_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "mpl_level": candle.low,
                        "has_internal_structure": True,
                    },
                )
            
            elif candle.is_bearish and not has_internal_structure:
                mpl = MiniPriceLevel(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    level=candle.low,
                    timestamp=candle.timestamp,
                    candle_index=i,
                    direction=Direction.BULLISH,
                    has_internal_structure=False,
                    is_type1=False,
                )
                
                mpl_levels.append(mpl)
                
                self._logger.debug(
                    "bullish_mpl_type2_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "mpl_level": candle.low,
                        "has_internal_structure": False,
                    },
                )
        
        return mpl_levels
    
    def _check_internal_engulfing(
        self,
        prev_candle: object,
        candle: object,
        next_candle: object,
    ) -> bool:
        if candle.is_bullish:
            return (
                prev_candle.close < candle.open
                and next_candle.open > candle.close
                and next_candle.close < candle.open
            )
        else:
            return (
                prev_candle.close > candle.open
                and next_candle.open < candle.close
                and next_candle.close > candle.open
            )
