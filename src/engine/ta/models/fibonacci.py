from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.exceptions import ConfigurationError
from engine.shared.models.base import FrozenModel
from engine.ta.constants import (
    Timeframe,
    FibonacciLevel,
    FIBONACCI_VALUES,
    OTE_LEVELS,
    PriceZone,
)


class FibonacciRetracement(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    swing_high: float = Field(gt=0)
    swing_low: float = Field(gt=0)
    swing_high_timestamp: datetime
    swing_low_timestamp: datetime
    is_bullish: bool
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    def model_post_init(self, __context) -> None:
        if self.swing_high <= self.swing_low:
            raise ConfigurationError(
                "Swing high must be > swing low",
                details={
                    "swing_high": self.swing_high,
                    "swing_low": self.swing_low,
                },
            )
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.swing_high - self.swing_low
    
    def get_level_price(self, level: FibonacciLevel) -> float:
        fib_value = FIBONACCI_VALUES.get(level)
        
        if fib_value is None:
            raise ConfigurationError(
                f"Unknown Fibonacci level: {level}",
                details={"level": level},
            )
        
        if self.is_bullish:
            return self.swing_low + (self.range_size * fib_value)
        else:
            return self.swing_high - (self.range_size * fib_value)
    
    def get_all_levels(self) -> dict[FibonacciLevel, float]:
        return {
            level: self.get_level_price(level)
            for level in FIBONACCI_VALUES.keys()
        }
    
    def get_ote_levels(self) -> dict[FibonacciLevel, float]:
        return {
            level: self.get_level_price(level)
            for level in OTE_LEVELS
        }
    
    def get_zone_for_price(self, price: float) -> PriceZone:
        if price < self.swing_low or price > self.swing_high:
            if self.is_bullish:
                return PriceZone.PREMIUM if price > self.swing_high else PriceZone.DISCOUNT
            else:
                return PriceZone.DISCOUNT if price > self.swing_high else PriceZone.PREMIUM
        
        level_50 = self.get_level_price(FibonacciLevel.LEVEL_50)
        
        tolerance = self.range_size * 0.02
        
        if abs(price - level_50) <= tolerance:
            return PriceZone.EQUILIBRIUM
        
        if self.is_bullish:
            if price > level_50:
                return PriceZone.PREMIUM
            else:
                return PriceZone.DISCOUNT
        else:
            if price < level_50:
                return PriceZone.PREMIUM
            else:
                return PriceZone.DISCOUNT
    
    def is_at_ote(self, price: float, tolerance_pips: float = 5.0) -> Optional[FibonacciLevel]:
        ote_levels = self.get_ote_levels()
        
        for level, level_price in ote_levels.items():
            if abs(price - level_price) <= (tolerance_pips * 0.0001):
                return level
        
        return None


class PremiumDiscountZone(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    zone_type: PriceZone
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    equilibrium: float = Field(gt=0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    def model_post_init(self, __context) -> None:
        if self.upper_bound <= self.lower_bound:
            raise ConfigurationError(
                "Upper bound must be > lower bound",
                details={
                    "upper_bound": self.upper_bound,
                    "lower_bound": self.lower_bound,
                },
            )
        
        expected_equilibrium = (self.upper_bound + self.lower_bound) / 2.0
        tolerance = (self.upper_bound - self.lower_bound) * 0.01
        
        if abs(self.equilibrium - expected_equilibrium) > tolerance:
            raise ConfigurationError(
                "Equilibrium must be midpoint of bounds",
                details={
                    "equilibrium": self.equilibrium,
                    "expected": expected_equilibrium,
                    "upper_bound": self.upper_bound,
                    "lower_bound": self.lower_bound,
                },
            )
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.upper_bound - self.lower_bound
    
    def contains_price(self, price: float) -> bool:
        return self.lower_bound <= price <= self.upper_bound
    
    def distance_from_equilibrium(self, price: float) -> float:
        return abs(price - self.equilibrium)


class DealingRange(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    start_time: datetime
    end_time: Optional[datetime] = None
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    def model_post_init(self, __context) -> None:
        if self.high <= self.low:
            raise ConfigurationError(
                "High must be > low",
                details={"high": self.high, "low": self.low},
            )
        
        if self.end_time and self.end_time <= self.start_time:
            raise ConfigurationError(
                "End time must be after start time",
                details={
                    "start_time": self.start_time.isoformat(),
                    "end_time": self.end_time.isoformat(),
                },
            )
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.high - self.low
    
    @computed_field
    @property
    def equilibrium(self) -> float:
        return (self.high + self.low) / 2.0
    
    @computed_field
    @property
    def premium_zone(self) -> PremiumDiscountZone:
        return PremiumDiscountZone(
            symbol=self.symbol,
            timeframe=self.timeframe,
            zone_type=PriceZone.PREMIUM,
            upper_bound=self.high,
            lower_bound=self.equilibrium,
            equilibrium=self.equilibrium + (self.range_size / 4.0),
        )
    
    @computed_field
    @property
    def discount_zone(self) -> PremiumDiscountZone:
        return PremiumDiscountZone(
            symbol=self.symbol,
            timeframe=self.timeframe,
            zone_type=PriceZone.DISCOUNT,
            upper_bound=self.equilibrium,
            lower_bound=self.low,
            equilibrium=self.equilibrium - (self.range_size / 4.0),
        )
    
    def get_zone_for_price(self, price: float) -> PriceZone:
        tolerance = self.range_size * 0.02
        
        if abs(price - self.equilibrium) <= tolerance:
            return PriceZone.EQUILIBRIUM
        
        if price > self.equilibrium:
            return PriceZone.PREMIUM
        else:
            return PriceZone.DISCOUNT
    
    def is_at_premium(self, price: float) -> bool:
        return self.get_zone_for_price(price) == PriceZone.PREMIUM
    
    def is_at_discount(self, price: float) -> bool:
        return self.get_zone_for_price(price) == PriceZone.DISCOUNT
    
    def is_at_equilibrium(self, price: float) -> bool:
        return self.get_zone_for_price(price) == PriceZone.EQUILIBRIUM
    
    def contains_price(self, price: float) -> bool:
        return self.low <= price <= self.high
