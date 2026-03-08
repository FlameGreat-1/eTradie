from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.utils.price.math import calculate_pips
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.zone import FairValueGap
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class FVGDetector:
    """
    Detects Fair Value Gaps (FVG) - imbalances in price delivery.
    
    FVG Requirements (OB Rule 2):
    - Occurs in 3-candle sequence
    - Wick of candle 1 does NOT overlap with wick of candle 3
    - Creates a gap where price delivery was inefficient
    - Price will return to fill/mitigate the FVG before continuing
    
    An OB without an FVG is significantly weaker.
    FVG within FVG (on subsequent timeframe) = extra confluence (BPR).
    """
    
    def __init__(
        self,
        config: SMCConfig,
        candle_analyzer: CandleAnalyzer,
    ) -> None:
        self.config = config
        self.candle_analyzer = candle_analyzer
        self._logger = get_logger(__name__)
    
    def detect_fvgs(
        self,
        sequence: CandleSequence,
    ) -> list[FairValueGap]:
        fvgs = []
        
        for i in range(len(sequence.candles) - 2):
            candle1 = sequence.candles[i]
            candle2 = sequence.candles[i + 1]
            candle3 = sequence.candles[i + 2]
            
            imbalance = self.candle_analyzer.detect_imbalance(
                candle1,
                candle2,
                candle3,
            )
            
            if not imbalance:
                continue
            
            gap_low, gap_high = imbalance
            
            gap_size_pips = calculate_pips(gap_low, gap_high, sequence.symbol)
            
            if gap_size_pips < self.config.fvg_min_gap_pips:
                continue
            
            direction = Direction.BULLISH if candle2.is_bullish else Direction.BEARISH
            
            fvg = FairValueGap(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                upper_bound=gap_high,
                lower_bound=gap_low,
                timestamp=candle2.timestamp,
                candle_index=i + 1,
                direction=direction,
                filled=False,
            )
            
            fvgs.append(fvg)
            
            self._logger.debug(
                "fvg_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "direction": str(direction),
                    "gap_low": gap_low,
                    "gap_high": gap_high,
                    "gap_size_pips": gap_size_pips,
                },
            )
        
        return fvgs
    
    def check_fvg_fill(
        self,
        fvg: FairValueGap,
        sequence: CandleSequence,
    ) -> tuple[bool, Optional[float]]:
        if fvg.candle_index >= len(sequence.candles) - 1:
            return False, None
        
        for i in range(fvg.candle_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if candle.low <= fvg.lower_bound and candle.high >= fvg.upper_bound:
                fill_percentage = 100.0
                return True, fill_percentage
            
            if fvg.lower_bound <= candle.low <= fvg.upper_bound:
                fill_percentage = ((candle.high - fvg.lower_bound) / fvg.range_size) * 100.0
                return True, fill_percentage
            
            if fvg.lower_bound <= candle.high <= fvg.upper_bound:
                fill_percentage = ((fvg.upper_bound - candle.low) / fvg.range_size) * 100.0
                return True, fill_percentage
        
        return False, None
    
    def get_unfilled_fvgs(
        self,
        fvgs: list[FairValueGap],
    ) -> list[FairValueGap]:
        return [fvg for fvg in fvgs if not fvg.filled]
