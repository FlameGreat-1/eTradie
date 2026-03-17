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
    """Support-to-Resistance Flip.

    Supports two construction styles:
    - Detector style: ``original_support_level``, ``original_support_timestamp``,
      ``breakout_candle_index``, ``new_resistance_level``, ``direction``, ``is_valid``.
    - Legacy/serializer style: ``flip_level``, ``flip_level_timestamp``,
      ``breakout_price``, ``candle_index``, ``previous_role``, ``new_role``.

    Both sets of fields are kept in sync via ``model_post_init``.
    """

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime

    # --- Detector-style fields ---
    original_support_level: Optional[float] = Field(default=None, gt=0)
    original_support_timestamp: Optional[datetime] = None
    breakout_candle_index: Optional[int] = Field(default=None, ge=0)
    new_resistance_level: Optional[float] = Field(default=None, gt=0)
    direction: Optional[Direction] = None
    is_valid: bool = Field(default=True)

    # --- Legacy/serializer-style fields ---
    flip_level: Optional[float] = Field(default=None, gt=0)
    flip_level_timestamp: Optional[datetime] = None
    breakout_price: Optional[float] = Field(default=None, gt=0)
    candle_index: int = Field(ge=0, default=0)
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

        # Sync detector-style → legacy-style
        if self.original_support_level is not None and self.flip_level is None:
            object.__setattr__(self, "flip_level", self.original_support_level)
        if self.flip_level is not None and self.original_support_level is None:
            object.__setattr__(self, "original_support_level", self.flip_level)

        if self.original_support_timestamp is not None and self.flip_level_timestamp is None:
            object.__setattr__(self, "flip_level_timestamp", self.original_support_timestamp)
        if self.flip_level_timestamp is not None and self.original_support_timestamp is None:
            object.__setattr__(self, "original_support_timestamp", self.flip_level_timestamp)

        if self.breakout_candle_index is not None and self.candle_index == 0:
            object.__setattr__(self, "candle_index", self.breakout_candle_index)
        if self.candle_index != 0 and self.breakout_candle_index is None:
            object.__setattr__(self, "breakout_candle_index", self.candle_index)

        if self.new_resistance_level is not None and self.flip_level is None:
            object.__setattr__(self, "flip_level", self.new_resistance_level)

    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.SR_FLIP,
            timestamp=self.timestamp,
            price=self.breakout_price or self.flip_level or 0.0,
            direction=self.direction or Direction.BEARISH,
            broken_level=self.flip_level or self.original_support_level or 0.0,
            broken_level_timestamp=self.flip_level_timestamp or self.original_support_timestamp or self.timestamp,
            candle_index=self.candle_index,
        )


class RSFlip(FrozenModel):
    """Resistance-to-Support Flip.

    Supports two construction styles:
    - Detector style: ``original_resistance_level``, ``original_resistance_timestamp``,
      ``breakout_candle_index``, ``new_support_level``, ``direction``, ``is_valid``.
    - Legacy/serializer style: ``flip_level``, ``flip_level_timestamp``,
      ``breakout_price``, ``candle_index``, ``previous_role``, ``new_role``.

    Both sets of fields are kept in sync via ``model_post_init``.
    """

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime

    # --- Detector-style fields ---
    original_resistance_level: Optional[float] = Field(default=None, gt=0)
    original_resistance_timestamp: Optional[datetime] = None
    breakout_candle_index: Optional[int] = Field(default=None, ge=0)
    new_support_level: Optional[float] = Field(default=None, gt=0)
    direction: Optional[Direction] = None
    is_valid: bool = Field(default=True)

    # --- Legacy/serializer-style fields ---
    flip_level: Optional[float] = Field(default=None, gt=0)
    flip_level_timestamp: Optional[datetime] = None
    breakout_price: Optional[float] = Field(default=None, gt=0)
    candle_index: int = Field(ge=0, default=0)
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

        # Sync detector-style → legacy-style
        if self.original_resistance_level is not None and self.flip_level is None:
            object.__setattr__(self, "flip_level", self.original_resistance_level)
        if self.flip_level is not None and self.original_resistance_level is None:
            object.__setattr__(self, "original_resistance_level", self.flip_level)

        if self.original_resistance_timestamp is not None and self.flip_level_timestamp is None:
            object.__setattr__(self, "flip_level_timestamp", self.original_resistance_timestamp)
        if self.flip_level_timestamp is not None and self.original_resistance_timestamp is None:
            object.__setattr__(self, "original_resistance_timestamp", self.flip_level_timestamp)

        if self.breakout_candle_index is not None and self.candle_index == 0:
            object.__setattr__(self, "candle_index", self.breakout_candle_index)
        if self.candle_index != 0 and self.breakout_candle_index is None:
            object.__setattr__(self, "breakout_candle_index", self.candle_index)

        if self.new_support_level is not None and self.flip_level is None:
            object.__setattr__(self, "flip_level", self.new_support_level)

    def to_structure_event(self) -> StructureEvent:
        return StructureEvent(
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type=StructureType.RS_FLIP,
            timestamp=self.timestamp,
            price=self.breakout_price or self.flip_level or 0.0,
            direction=self.direction or Direction.BULLISH,
            broken_level=self.flip_level or self.original_resistance_level or 0.0,
            broken_level_timestamp=self.flip_level_timestamp or self.original_resistance_timestamp or self.timestamp,
            candle_index=self.candle_index,
        )
