from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.exceptions import ConfigurationError
from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, Direction, StructureType


class StructureEvent(FrozenModel):
    
    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    event_type: StructureType
    timestamp: datetime
    price: float = Field(gt=0)
    direction: Direction
    broken_level: float = Field(gt=0)
    broken_level_timestamp: datetime
    candle_index: int = Field(ge=0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH


class BreakOfStructure(FrozenModel):
    
    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    timestamp: datetime
    direction: Direction
    broken_level: float = Field(gt=0)
    broken_level_timestamp: datetime
    breakout_price: float = Field(gt=0)
    candle_index: int = Field(ge=0)
    displacement_pips: float = Field(ge=0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
    
    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.BOS,
            timestamp=self.timestamp,
            price=self.breakout_price,
            direction=self.direction,
            broken_level=self.broken_level,
            broken_level_timestamp=self.broken_level_timestamp,
            candle_index=self.candle_index,
        )


class ChangeOfCharacter(FrozenModel):
    
    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    timestamp: datetime
    direction: Direction
    broken_level: float = Field(gt=0)
    broken_level_timestamp: datetime
    breakout_price: float = Field(gt=0)
    candle_index: int = Field(ge=0)
    is_minor: bool = Field(default=True)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
    
    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.CHOCH,
            timestamp=self.timestamp,
            price=self.breakout_price,
            direction=self.direction,
            broken_level=self.broken_level,
            broken_level_timestamp=self.broken_level_timestamp,
            candle_index=self.candle_index,
        )


class BreakInMarketStructure(FrozenModel):
    
    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    timestamp: datetime
    direction: Direction
    broken_level: float = Field(gt=0)
    broken_level_timestamp: datetime
    breakout_price: float = Field(gt=0)
    candle_index: int = Field(ge=0)
    displacement_pips: float = Field(ge=0)
    confirmed: bool = Field(default=False)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
    
    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.BMS,
            timestamp=self.timestamp,
            price=self.breakout_price,
            direction=self.direction,
            broken_level=self.broken_level,
            broken_level_timestamp=self.broken_level_timestamp,
            candle_index=self.candle_index,
        )


class ShiftInMarketStructure(FrozenModel):
    
    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    timestamp: datetime
    direction: Direction
    failed_level: float = Field(gt=0)
    failed_level_timestamp: datetime
    reversal_price: float = Field(gt=0)
    candle_index: int = Field(ge=0)
    is_failure_swing: bool = Field(default=True)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
    
    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.SMS,
            timestamp=self.timestamp,
            price=self.reversal_price,
            direction=self.direction,
            broken_level=self.failed_level,
            broken_level_timestamp=self.failed_level_timestamp,
            candle_index=self.candle_index,
        )


class SRFlip(FrozenModel):
    """Support-to-Resistance Flip.

    Detected when a bearish Marubozu breaks a support level (swing low)
    downward, flipping it into resistance.

    Fields match what SRFlipDetector constructs:
    - original_support_level: the swing low price that was broken
    - original_support_timestamp: when that swing low formed
    - breakout_candle_index: index of the Marubozu that broke it
    - breakout_price: close price of the breakout candle
    - new_resistance_level: same as original_support_level (now resistance)
    - direction: BEARISH (support broken downward)
    - is_valid: whether the flip is confirmed
    """

    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    timestamp: datetime
    original_support_level: float = Field(gt=0)
    original_support_timestamp: datetime
    breakout_candle_index: int = Field(ge=0)
    breakout_price: float = Field(gt=0)
    new_resistance_level: float = Field(gt=0)
    direction: Direction = Field(default=Direction.BEARISH)
    is_valid: bool = Field(default=True)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.replace("/", "").replace("_", "")

    @computed_field
    @property
    def flip_level(self) -> float:
        """Alias for serializers that read flip_level."""
        return self.original_support_level

    @computed_field
    @property
    def previous_role(self) -> str:
        return "SUPPORT"

    @computed_field
    @property
    def new_role(self) -> str:
        return "RESISTANCE"

    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.SR_FLIP,
            timestamp=self.timestamp,
            price=self.breakout_price,
            direction=Direction.BEARISH,
            broken_level=self.original_support_level,
            broken_level_timestamp=self.original_support_timestamp,
            candle_index=self.breakout_candle_index,
        )


class RSFlip(FrozenModel):
    """Resistance-to-Support Flip.

    Detected when a bullish Marubozu breaks a resistance level (swing high)
    upward, flipping it into support.

    Fields match what RSFlipDetector constructs:
    - original_resistance_level: the swing high price that was broken
    - original_resistance_timestamp: when that swing high formed
    - breakout_candle_index: index of the Marubozu that broke it
    - breakout_price: close price of the breakout candle
    - new_support_level: same as original_resistance_level (now support)
    - direction: BULLISH (resistance broken upward)
    - is_valid: whether the flip is confirmed
    """

    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    timestamp: datetime
    original_resistance_level: float = Field(gt=0)
    original_resistance_timestamp: datetime
    breakout_candle_index: int = Field(ge=0)
    breakout_price: float = Field(gt=0)
    new_support_level: float = Field(gt=0)
    direction: Direction = Field(default=Direction.BULLISH)
    is_valid: bool = Field(default=True)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.replace("/", "").replace("_", "")

    @computed_field
    @property
    def flip_level(self) -> float:
        """Alias for serializers that read flip_level."""
        return self.original_resistance_level

    @computed_field
    @property
    def previous_role(self) -> str:
        return "RESISTANCE"

    @computed_field
    @property
    def new_role(self) -> str:
        return "SUPPORT"

    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.RS_FLIP,
            timestamp=self.timestamp,
            price=self.breakout_price,
            direction=Direction.BULLISH,
            broken_level=self.original_resistance_level,
            broken_level_timestamp=self.original_resistance_timestamp,
            candle_index=self.breakout_candle_index,
        )
