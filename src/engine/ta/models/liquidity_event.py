from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, Direction, LiquidityType


class LiquidityPool(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    liquidity_type: LiquidityType
    price_level: float = Field(gt=0)
    timestamp: datetime
    strength: int = Field(ge=1, le=10, default=1)
    touch_count: int = Field(ge=1, default=1)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_buy_side(self) -> bool:
        return self.liquidity_type in (
            LiquidityType.BSL,
            LiquidityType.EQUAL_HIGHS,
        )
    
    @computed_field
    @property
    def is_sell_side(self) -> bool:
        return self.liquidity_type in (
            LiquidityType.SSL,
            LiquidityType.EQUAL_LOWS,
        )


class LiquiditySweep(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    liquidity_type: LiquidityType
    swept_level: float = Field(gt=0)
    swept_level_timestamp: datetime
    sweep_high: float = Field(gt=0)
    sweep_low: float = Field(gt=0)
    sweep_pips: float = Field(ge=0)
    closed_back_inside: bool = Field(default=False)
    close_price: Optional[float] = Field(default=None, gt=0)
    candle_index: int = Field(ge=0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish_sweep(self) -> bool:
        return self.liquidity_type in (
            LiquidityType.BSL,
            LiquidityType.EQUAL_HIGHS,
        )
    
    @computed_field
    @property
    def is_bearish_sweep(self) -> bool:
        return self.liquidity_type in (
            LiquidityType.SSL,
            LiquidityType.EQUAL_LOWS,
        )
    
    @computed_field
    @property
    def is_valid_turtle_soup(self) -> bool:
        return self.closed_back_inside and self.sweep_pips >= 5.0


class LiquidityGrab(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    direction: Direction
    grabbed_level: float = Field(gt=0)
    grabbed_level_timestamp: datetime
    grab_price: float = Field(gt=0)
    reversal_price: Optional[float] = Field(default=None, gt=0)
    candle_index: int = Field(ge=0)
    confirmed: bool = Field(default=False)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH


class InducementEvent(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    inducement_level: float = Field(gt=0)
    inducement_timestamp: datetime
    direction: Direction
    cleared: bool = Field(default=False)
    cleared_timestamp: Optional[datetime] = None
    candle_index: int = Field(ge=0)
    is_internal: bool = Field(default=True)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH


class CompressionEvent(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    start_timestamp: datetime
    end_timestamp: Optional[datetime] = None
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    direction: Direction
    candle_count: int = Field(ge=2)
    start_index: int = Field(ge=0)
    end_index: Optional[int] = Field(default=None, ge=0)
    broken: bool = Field(default=False)
    breakout_direction: Optional[Direction] = None
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.high - self.low
    
    @computed_field
    @property
    def is_bullish_compression(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish_compression(self) -> bool:
        return self.direction == Direction.BEARISH


class EqualHighsLows(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    liquidity_type: LiquidityType
    price_level: float = Field(gt=0)
    timestamps: list[datetime] = Field(min_length=2)
    tolerance_pips: float = Field(ge=0, default=2.0)
    candle_indices: list[int] = Field(min_length=2)
    swept: bool = Field(default=False)
    swept_timestamp: Optional[datetime] = None
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @field_validator("liquidity_type")
    @classmethod
    def validate_liquidity_type(cls, v: LiquidityType) -> LiquidityType:
        if v not in (LiquidityType.EQUAL_HIGHS, LiquidityType.EQUAL_LOWS):
            raise ValueError("Liquidity type must be EQUAL_HIGHS or EQUAL_LOWS")
        return v
    
    @computed_field
    @property
    def touch_count(self) -> int:
        return len(self.timestamps)
    
    @computed_field
    @property
    def is_equal_highs(self) -> bool:
        return self.liquidity_type == LiquidityType.EQUAL_HIGHS
    
    @computed_field
    @property
    def is_equal_lows(self) -> bool:
        return self.liquidity_type == LiquidityType.EQUAL_LOWS
    
    def to_liquidity_pool(self) -> LiquidityPool:
        return LiquidityPool(
            symbol=self.symbol,
            timeframe=self.timeframe,
            liquidity_type=self.liquidity_type,
            price_level=self.price_level,
            timestamp=self.timestamps[0],
            strength=min(self.touch_count, 10),
            touch_count=self.touch_count,
        )
