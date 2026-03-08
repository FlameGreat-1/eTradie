from datetime import datetime
from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import DealingRange, PremiumDiscountZone
from engine.ta.models.session import SessionRange
from engine.ta.constants import PriceZone, Timeframe

logger = get_logger(__name__)


class DealingRangeAnalyzer:
    
    def __init__(
        self,
        *,
        min_range_pips: float = 20.0,
        equilibrium_tolerance_percentage: float = 2.0,
    ) -> None:
        self.min_range_pips = min_range_pips
        self.equilibrium_tolerance_percentage = equilibrium_tolerance_percentage
    
    def create_from_session(
        self,
        session_range: SessionRange,
    ) -> Optional[DealingRange]:
        from engine.ta.common.utils.price.math import calculate_pips
        
        range_pips = calculate_pips(
            session_range.low,
            session_range.high,
            session_range.symbol,
        )
        
        if range_pips < self.min_range_pips:
            return None
        
        return DealingRange(
            symbol=session_range.symbol,
            timeframe=session_range.timeframe,
            high=session_range.high,
            low=session_range.low,
            start_time=session_range.start_time,
            end_time=session_range.end_time,
        )
    
    def create_from_sequence(
        self,
        sequence: CandleSequence,
        start_index: int,
        end_index: int,
    ) -> Optional[DealingRange]:
        if start_index < 0 or end_index >= len(sequence.candles) or start_index > end_index:
            return None
        
        range_candles = sequence.candles[start_index:end_index + 1]
        
        high = max(c.high for c in range_candles)
        low = min(c.low for c in range_candles)
        
        from engine.ta.common.utils.price.math import calculate_pips
        
        range_pips = calculate_pips(low, high, sequence.symbol)
        
        if range_pips < self.min_range_pips:
            return None
        
        return DealingRange(
            symbol=sequence.symbol,
            timeframe=sequence.timeframe,
            high=high,
            low=low,
            start_time=range_candles[0].timestamp,
            end_time=range_candles[-1].timestamp,
        )
    
    def get_equilibrium(self, dealing_range: DealingRange) -> float:
        return dealing_range.equilibrium
    
    def get_premium_zone(self, dealing_range: DealingRange) -> PremiumDiscountZone:
        return dealing_range.premium_zone
    
    def get_discount_zone(self, dealing_range: DealingRange) -> PremiumDiscountZone:
        return dealing_range.discount_zone
    
    def is_at_premium(self, price: float, dealing_range: DealingRange) -> bool:
        return dealing_range.is_at_premium(price)
    
    def is_at_discount(self, price: float, dealing_range: DealingRange) -> bool:
        return dealing_range.is_at_discount(price)
    
    def is_at_equilibrium(self, price: float, dealing_range: DealingRange) -> bool:
        return dealing_range.is_at_equilibrium(price)
    
    def get_zone_for_price(self, price: float, dealing_range: DealingRange) -> PriceZone:
        return dealing_range.get_zone_for_price(price)
    
    def calculate_distance_from_equilibrium(
        self,
        price: float,
        dealing_range: DealingRange,
    ) -> float:
        from engine.ta.common.utils.price.math import calculate_pips
        
        return calculate_pips(
            dealing_range.equilibrium,
            price,
            dealing_range.symbol,
        )
    
    def is_range_active(
        self,
        dealing_range: DealingRange,
        current_time: datetime,
    ) -> bool:
        if dealing_range.end_time is None:
            return True
        
        return current_time <= dealing_range.end_time
    
    def has_price_left_range(
        self,
        price: float,
        dealing_range: DealingRange,
    ) -> bool:
        return not dealing_range.contains_price(price)
