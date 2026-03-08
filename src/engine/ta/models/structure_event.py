from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.exceptions import ConfigurationError
from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, Direction, StructureType


class StructureEvent(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
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
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH


class BreakOfStructure(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
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
        return v.upper().replace("/", "").replace("_", "")
    
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
    
    symbol: str = Field(min_length=6, max_length=10)
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
        return v.upper().replace("/", "").replace("_", "")
    
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
    
    symbol: str = Field(min_length=6, max_length=10)
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
        return v.upper().replace("/", "").replace("_", "")
    
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
    
    symbol: str = Field(min_length=6, max_length=10)
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
        return v.upper().replace("/", "").replace("_", "")
    
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
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    flip_level: float = Field(gt=0)
    flip_level_timestamp: datetime
    breakout_price: float = Field(gt=0)
    candle_index: int = Field(ge=0)
    previous_role: str = Field(default="SUPPORT")
    new_role: str = Field(default="RESISTANCE")
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @field_validator("previous_role", "new_role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("SUPPORT", "RESISTANCE"):
            raise ValueError("Role must be SUPPORT or RESISTANCE")
        return v
    
    def model_post_init(self, __context) -> None:
        if self.previous_role == self.new_role:
            raise ConfigurationError(
                "Previous role and new role cannot be the same",
                details={
                    "previous_role": self.previous_role,
                    "new_role": self.new_role,
                },
            )
    
    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.SR_FLIP,
            timestamp=self.timestamp,
            price=self.breakout_price,
            direction=Direction.BEARISH,
            broken_level=self.flip_level,
            broken_level_timestamp=self.flip_level_timestamp,
            candle_index=self.candle_index,
        )


class RSFlip(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    flip_level: float = Field(gt=0)
    flip_level_timestamp: datetime
    breakout_price: float = Field(gt=0)
    candle_index: int = Field(ge=0)
    previous_role: str = Field(default="RESISTANCE")
    new_role: str = Field(default="SUPPORT")
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @field_validator("previous_role", "new_role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("SUPPORT", "RESISTANCE"):
            raise ValueError("Role must be SUPPORT or RESISTANCE")
        return v
    
    def model_post_init(self, __context) -> None:
        if self.previous_role == self.new_role:
            raise ConfigurationError(
                "Previous role and new role cannot be the same",
                details={
                    "previous_role": self.previous_role,
                    "new_role": self.new_role,
                },
            )
    
    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.RS_FLIP,
            timestamp=self.timestamp,
            price=self.breakout_price,
            direction=Direction.BULLISH,
            broken_level=self.flip_level,
            broken_level_timestamp=self.flip_level_timestamp,
            candle_index=self.candle_index,
        )
