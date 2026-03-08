from engine.shared.logging import get_logger
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.liquidity_event import LiquiditySweep
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class TurtleSoupDetector:
    """
    Detects Turtle Soup patterns (liquidity sweep with reversal).
    
    Turtle Soup Requirements (Pattern 1/6):
    - Price raids BSL/SSL zone (PDH/PWH/PMH/HOD/Old High/Equal Highs for sells)
    - Sweeps 5-20+ pips above/below the level
    - Single candle closes back inside the range (closed_back_inside = True)
    - Entry against the sweep
    - Minimum 10 pip SL beyond the sweep high/low (Universal Rule 12)
    
    This is the baseline SMC pattern - needs session confluence to be valid.
    
    Combined with SH + BMS + RTO = highest confluence setup (Pattern 5/10).
    """
    
    def __init__(
        self,
        config: SMCConfig,
        sweep_analyzer: SweepAnalyzer,
    ) -> None:
        self.config = config
        self.sweep_analyzer = sweep_analyzer
        self._logger = get_logger(__name__)
    
    def detect_turtle_soup_short(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[LiquiditySweep]:
        turtle_soup_events = []
        
        for i, candle in enumerate(sequence.candles):
            for swing_high in swing_highs:
                if swing_high.index >= i:
                    continue
                
                sweep = self.sweep_analyzer.detect_bsl_sweep(
                    candle,
                    swing_high,
                    i,
                )
                
                if not sweep:
                    continue
                
                if not sweep.closed_back_inside:
                    continue
                
                if sweep.sweep_pips < self.config.turtle_soup_min_pips:
                    continue
                
                turtle_soup_events.append(sweep)
                
                self._logger.info(
                    "turtle_soup_short_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "swept_level": sweep.swept_level,
                        "sweep_high": sweep.sweep_high,
                        "sweep_pips": sweep.sweep_pips,
                        "closed_back_inside": sweep.closed_back_inside,
                    },
                )
        
        return turtle_soup_events
    
    def detect_turtle_soup_long(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[LiquiditySweep]:
        turtle_soup_events = []
        
        for i, candle in enumerate(sequence.candles):
            for swing_low in swing_lows:
                if swing_low.index >= i:
                    continue
                
                sweep = self.sweep_analyzer.detect_ssl_sweep(
                    candle,
                    swing_low,
                    i,
                )
                
                if not sweep:
                    continue
                
                if not sweep.closed_back_inside:
                    continue
                
                if sweep.sweep_pips < self.config.turtle_soup_min_pips:
                    continue
                
                turtle_soup_events.append(sweep)
                
                self._logger.info(
                    "turtle_soup_long_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "swept_level": sweep.swept_level,
                        "sweep_low": sweep.sweep_low,
                        "sweep_pips": sweep.sweep_pips,
                        "closed_back_inside": sweep.closed_back_inside,
                    },
                )
        
        return turtle_soup_events
    
    def is_valid_turtle_soup(self, sweep: LiquiditySweep) -> bool:
        return self.sweep_analyzer.is_turtle_soup(sweep)
