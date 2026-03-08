from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import calculate_pips
from engine.ta.constants import LiquidityType
from engine.ta.models.candle import Candle, CandleSequence
from engine.ta.models.liquidity_event import LiquiditySweep, LiquidityPool
from engine.ta.models.swing import SwingHigh, SwingLow

logger = get_logger(__name__)


class SweepAnalyzer:
    
    def __init__(
        self,
        *,
        min_sweep_pips: float = 2.0,
        turtle_soup_min_pips: float = 5.0,
    ) -> None:
        self.min_sweep_pips = min_sweep_pips
        self.turtle_soup_min_pips = turtle_soup_min_pips
    
    def detect_bsl_sweep(
        self,
        candle: Candle,
        swing_high: SwingHigh,
        candle_index: int,
    ) -> Optional[LiquiditySweep]:
        if candle.high <= swing_high.price:
            return None
        
        sweep_pips = calculate_pips(
            swing_high.price,
            candle.high,
            candle.symbol,
        )
        
        if sweep_pips < self.min_sweep_pips:
            return None
        
        closed_back_inside = candle.close < swing_high.price
        
        return LiquiditySweep(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            timestamp=candle.timestamp,
            liquidity_type=LiquidityType.BSL,
            swept_level=swing_high.price,
            swept_level_timestamp=swing_high.timestamp,
            sweep_high=candle.high,
            sweep_low=candle.low,
            sweep_pips=sweep_pips,
            closed_back_inside=closed_back_inside,
            close_price=candle.close,
            candle_index=candle_index,
        )
    
    def detect_ssl_sweep(
        self,
        candle: Candle,
        swing_low: SwingLow,
        candle_index: int,
    ) -> Optional[LiquiditySweep]:
        if candle.low >= swing_low.price:
            return None
        
        sweep_pips = calculate_pips(
            candle.low,
            swing_low.price,
            candle.symbol,
        )
        
        if sweep_pips < self.min_sweep_pips:
            return None
        
        closed_back_inside = candle.close > swing_low.price
        
        return LiquiditySweep(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            timestamp=candle.timestamp,
            liquidity_type=LiquidityType.SSL,
            swept_level=swing_low.price,
            swept_level_timestamp=swing_low.timestamp,
            sweep_high=candle.high,
            sweep_low=candle.low,
            sweep_pips=sweep_pips,
            closed_back_inside=closed_back_inside,
            close_price=candle.close,
            candle_index=candle_index,
        )
    
    def detect_sweeps_in_sequence(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
        swing_lows: list[SwingLow],
    ) -> list[LiquiditySweep]:
        sweeps = []
        
        for i, candle in enumerate(sequence.candles):
            for swing_high in swing_highs:
                if swing_high.index >= i:
                    continue
                
                sweep = self.detect_bsl_sweep(candle, swing_high, i)
                if sweep:
                    sweeps.append(sweep)
            
            for swing_low in swing_lows:
                if swing_low.index >= i:
                    continue
                
                sweep = self.detect_ssl_sweep(candle, swing_low, i)
                if sweep:
                    sweeps.append(sweep)
        
        return sweeps
    
    def is_turtle_soup(self, sweep: LiquiditySweep) -> bool:
        return (
            sweep.closed_back_inside
            and sweep.sweep_pips >= self.turtle_soup_min_pips
        )
    
    def detect_equal_highs_sweep(
        self,
        candle: Candle,
        equal_highs_level: float,
        candle_index: int,
    ) -> Optional[LiquiditySweep]:
        if candle.high <= equal_highs_level:
            return None
        
        sweep_pips = calculate_pips(
            equal_highs_level,
            candle.high,
            candle.symbol,
        )
        
        if sweep_pips < self.min_sweep_pips:
            return None
        
        closed_back_inside = candle.close < equal_highs_level
        
        return LiquiditySweep(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            timestamp=candle.timestamp,
            liquidity_type=LiquidityType.EQUAL_HIGHS,
            swept_level=equal_highs_level,
            swept_level_timestamp=candle.timestamp,
            sweep_high=candle.high,
            sweep_low=candle.low,
            sweep_pips=sweep_pips,
            closed_back_inside=closed_back_inside,
            close_price=candle.close,
            candle_index=candle_index,
        )
    
    def detect_equal_lows_sweep(
        self,
        candle: Candle,
        equal_lows_level: float,
        candle_index: int,
    ) -> Optional[LiquiditySweep]:
        if candle.low >= equal_lows_level:
            return None
        
        sweep_pips = calculate_pips(
            candle.low,
            equal_lows_level,
            candle.symbol,
        )
        
        if sweep_pips < self.min_sweep_pips:
            return None
        
        closed_back_inside = candle.close > equal_lows_level
        
        return LiquiditySweep(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            timestamp=candle.timestamp,
            liquidity_type=LiquidityType.EQUAL_LOWS,
            swept_level=equal_lows_level,
            swept_level_timestamp=candle.timestamp,
            sweep_high=candle.high,
            sweep_low=candle.low,
            sweep_pips=sweep_pips,
            closed_back_inside=closed_back_inside,
            close_price=candle.close,
            candle_index=candle_index,
        )
    
    def get_strongest_sweep(
        self,
        sweeps: list[LiquiditySweep],
    ) -> Optional[LiquiditySweep]:
        if not sweeps:
            return None
        
        return max(sweeps, key=lambda s: s.sweep_pips)
    
    def get_recent_sweeps(
        self,
        sweeps: list[LiquiditySweep],
        lookback: int = 5,
    ) -> list[LiquiditySweep]:
        if not sweeps:
            return []
        
        sorted_sweeps = sorted(sweeps, key=lambda s: s.timestamp, reverse=True)
        return sorted_sweeps[:lookback]
