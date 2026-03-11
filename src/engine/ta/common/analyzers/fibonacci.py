from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import (
    FibonacciLevel,
    FIBONACCI_VALUES,
    OTE_LEVELS,
    PriceZone,
)
from engine.ta.models.fibonacci import FibonacciRetracement, PremiumDiscountZone
from engine.ta.models.swing import SwingHigh, SwingLow

logger = get_logger(__name__)


class FibonacciAnalyzer:
    
    def __init__(
        self,
        *,
        equilibrium_tolerance_percentage: float = 2.0,
    ) -> None:
        self.equilibrium_tolerance_percentage = equilibrium_tolerance_percentage
    
    def create_retracement(
        self,
        swing_high: SwingHigh,
        swing_low: SwingLow,
        is_bullish: bool,
    ) -> FibonacciRetracement:
        return FibonacciRetracement(
            symbol=swing_high.symbol,
            timeframe=swing_high.timeframe,
            swing_high=swing_high.price,
            swing_low=swing_low.price,
            swing_high_timestamp=swing_high.timestamp,
            swing_low_timestamp=swing_low.timestamp,
            is_bullish=is_bullish,
        )
    
    def calculate_level_price(
        self,
        swing_high: float,
        swing_low: float,
        level: FibonacciLevel,
        is_bullish: bool,
    ) -> float:
        fib_value = FIBONACCI_VALUES.get(level)
        
        if fib_value is None:
            raise ValueError(f"Unknown Fibonacci level: {level}")
        
        range_size = swing_high - swing_low
        
        if is_bullish:
            return swing_low + (range_size * fib_value)
        else:
            return swing_high - (range_size * fib_value)
    
    def get_ote_zone(
        self,
        retracement: FibonacciRetracement,
    ) -> PremiumDiscountZone:
        level_618 = retracement.get_level_price(FibonacciLevel.LEVEL_618)
        level_786 = retracement.get_level_price(FibonacciLevel.LEVEL_786)
        
        if retracement.is_bullish:
            upper = level_786
            lower = level_618
        else:
            upper = level_618
            lower = level_786
        
        equilibrium = (upper + lower) / 2.0
        
        return PremiumDiscountZone(
            symbol=retracement.symbol,
            timeframe=retracement.timeframe,
            zone_type=PriceZone.DISCOUNT if retracement.is_bullish else PriceZone.PREMIUM,
            upper_bound=upper,
            lower_bound=lower,
            equilibrium=equilibrium,
        )
    
    def is_at_ote(
        self,
        price: float,
        retracement: FibonacciRetracement,
        tolerance_pips: float = 5.0,
    ) -> bool:
        ote_zone = self.get_ote_zone(retracement)
        
        tolerance = tolerance_pips * float(get_pip_value(retracement.symbol))
        
        return (
            ote_zone.lower_bound - tolerance <= price <= ote_zone.upper_bound + tolerance
        )
    
    def get_zone_for_price(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> PriceZone:
        return retracement.get_zone_for_price(price)
    
    def is_at_premium(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> bool:
        return self.get_zone_for_price(price, retracement) == PriceZone.PREMIUM
    
    def is_at_discount(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> bool:
        return self.get_zone_for_price(price, retracement) == PriceZone.DISCOUNT
    
    def is_at_equilibrium(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> bool:
        return self.get_zone_for_price(price, retracement) == PriceZone.EQUILIBRIUM
    
    def get_nearest_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[FibonacciLevel]:
        all_levels = retracement.get_all_levels()
        
        if not all_levels:
            return None
        
        nearest_level = None
        min_distance = float('inf')
        
        for level, level_price in all_levels.items():
            distance = abs(price - level_price)
            
            if distance < min_distance:
                min_distance = distance
                nearest_level = level
        
        return nearest_level
    
    def calculate_retracement_percentage(
        self,
        current_price: float,
        swing_high: float,
        swing_low: float,
    ) -> float:
        range_size = swing_high - swing_low
        
        if range_size == 0:
            return 0.0
        
        retracement = abs(current_price - swing_low)
        
        return (retracement / range_size) * 100.0
    
    def get_all_ote_levels(self) -> list[FibonacciLevel]:
        return list(OTE_LEVELS)
