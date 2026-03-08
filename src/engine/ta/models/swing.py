from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, Direction


class SwingPoint(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    price: float = Field(gt=0)
    index: int = Field(ge=0)
    strength: int = Field(ge=1, le=10, default=1)
    direction: Direction
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_high(self) -> bool:
        return self.direction == Direction.BEARISH
    
    @computed_field
    @property
    def is_low(self) -> bool:
        return self.direction == Direction.BULLISH


class SwingHigh(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    price: float = Field(gt=0)
    index: int = Field(ge=0)
    strength: int = Field(ge=1, le=10, default=1)
    left_bars: int = Field(ge=1)
    right_bars: int = Field(ge=1)
    is_equal_high: bool = Field(default=False)
    equal_high_tolerance_pips: Optional[float] = Field(default=None, ge=0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def direction(self) -> Direction:
        return Direction.BEARISH
    
    def to_swing_point(self) -> SwingPoint:
        return SwingPoint(
            symbol=self.symbol,
            timeframe=self.timeframe,
            timestamp=self.timestamp,
            price=self.price,
            index=self.index,
            strength=self.strength,
            direction=self.direction,
        )


class SwingLow(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    price: float = Field(gt=0)
    index: int = Field(ge=0)
    strength: int = Field(ge=1, le=10, default=1)
    left_bars: int = Field(ge=1)
    right_bars: int = Field(ge=1)
    is_equal_low: bool = Field(default=False)
    equal_low_tolerance_pips: Optional[float] = Field(default=None, ge=0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def direction(self) -> Direction:
        return Direction.BULLISH
    
    def to_swing_point(self) -> SwingPoint:
        return SwingPoint(
            symbol=self.symbol,
            timeframe=self.timeframe,
            timestamp=self.timestamp,
            price=self.price,
            index=self.index,
            strength=self.strength,
            direction=self.direction,
        )
