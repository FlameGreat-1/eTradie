from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.exceptions import ConfigurationError
from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, Direction, ZoneType


class Zone(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    zone_type: ZoneType
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction
    
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
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.upper_bound - self.lower_bound
    
    @computed_field
    @property
    def midpoint(self) -> float:
        return (self.upper_bound + self.lower_bound) / 2.0
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
    
    def contains_price(self, price: float) -> bool:
        return self.lower_bound <= price <= self.upper_bound
    
    def overlaps_with(self, other: "Zone") -> bool:
        return not (
            self.upper_bound < other.lower_bound
            or self.lower_bound > other.upper_bound
        )


class OrderBlock(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction
    displacement_pips: float = Field(ge=0)
    is_breaker: bool = Field(default=False)
    mitigated: bool = Field(default=False)
    mitigation_timestamp: Optional[datetime] = None
    
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
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.upper_bound - self.lower_bound
    
    @computed_field
    @property
    def midpoint(self) -> float:
        return (self.upper_bound + self.lower_bound) / 2.0
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
    
    def to_zone(self) -> Zone:
        return Zone(
            symbol=self.symbol,
            timeframe=self.timeframe,
            zone_type=ZoneType.ORDER_BLOCK,
            upper_bound=self.upper_bound,
            lower_bound=self.lower_bound,
            timestamp=self.timestamp,
            candle_index=self.candle_index,
            direction=self.direction,
        )


class FairValueGap(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction
    filled: bool = Field(default=False)
    fill_timestamp: Optional[datetime] = None
    fill_percentage: float = Field(ge=0, le=100, default=0.0)
    
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
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.upper_bound - self.lower_bound
    
    @computed_field
    @property
    def midpoint(self) -> float:
        return (self.upper_bound + self.lower_bound) / 2.0
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
    
    def to_zone(self) -> Zone:
        return Zone(
            symbol=self.symbol,
            timeframe=self.timeframe,
            zone_type=ZoneType.FVG,
            upper_bound=self.upper_bound,
            lower_bound=self.lower_bound,
            timestamp=self.timestamp,
            candle_index=self.candle_index,
            direction=self.direction,
        )


class BreakerBlock(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction
    original_ob_timestamp: datetime
    broken_timestamp: datetime
    mitigated: bool = Field(default=False)
    mitigation_timestamp: Optional[datetime] = None
    
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
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.upper_bound - self.lower_bound
    
    @computed_field
    @property
    def midpoint(self) -> float:
        return (self.upper_bound + self.lower_bound) / 2.0
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
    
    def to_zone(self) -> Zone:
        return Zone(
            symbol=self.symbol,
            timeframe=self.timeframe,
            zone_type=ZoneType.BREAKER,
            upper_bound=self.upper_bound,
            lower_bound=self.lower_bound,
            timestamp=self.timestamp,
            candle_index=self.candle_index,
            direction=self.direction,
        )


class SupplyZone(FrozenModel):
    """Supply Zone.

    Supports construction from SupplyDemandDetector which passes
    ``qml_level``, ``qml_timestamp``, ``sr_flip_level``,
    ``sr_flip_timestamp``, ``is_valid`` instead of ``candle_index``.
    """

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0, default=0)
    strength: int = Field(ge=1, le=10, default=1)
    tested: bool = Field(default=False)
    test_count: int = Field(ge=0, default=0)
    broken: bool = Field(default=False)
    broken_timestamp: Optional[datetime] = None

    # --- SnD detector fields ---
    qml_level: Optional[float] = Field(default=None, gt=0)
    qml_timestamp: Optional[datetime] = None
    sr_flip_level: Optional[float] = Field(default=None, gt=0)
    sr_flip_timestamp: Optional[datetime] = None
    is_valid: bool = Field(default=True)
    
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
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.upper_bound - self.lower_bound
    
    @computed_field
    @property
    def midpoint(self) -> float:
        return (self.upper_bound + self.lower_bound) / 2.0
    
    def to_zone(self) -> Zone:
        return Zone(
            symbol=self.symbol,
            timeframe=self.timeframe,
            zone_type=ZoneType.SUPPLY,
            upper_bound=self.upper_bound,
            lower_bound=self.lower_bound,
            timestamp=self.timestamp,
            candle_index=self.candle_index,
            direction=Direction.BEARISH,
        )


class DemandZone(FrozenModel):
    """Demand Zone.

    Supports construction from SupplyDemandDetector which passes
    ``qmh_level``, ``qmh_timestamp``, ``rs_flip_level``,
    ``rs_flip_timestamp``, ``is_valid`` instead of ``candle_index``.
    """

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0, default=0)
    strength: int = Field(ge=1, le=10, default=1)
    tested: bool = Field(default=False)
    test_count: int = Field(ge=0, default=0)
    broken: bool = Field(default=False)
    broken_timestamp: Optional[datetime] = None

    # --- SnD detector fields ---
    qmh_level: Optional[float] = Field(default=None, gt=0)
    qmh_timestamp: Optional[datetime] = None
    rs_flip_level: Optional[float] = Field(default=None, gt=0)
    rs_flip_timestamp: Optional[datetime] = None
    is_valid: bool = Field(default=True)
    
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
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.upper_bound - self.lower_bound
    
    @computed_field
    @property
    def midpoint(self) -> float:
        return (self.upper_bound + self.lower_bound) / 2.0
    
    def to_zone(self) -> Zone:
        return Zone(
            symbol=self.symbol,
            timeframe=self.timeframe,
            zone_type=ZoneType.DEMAND,
            upper_bound=self.upper_bound,
            lower_bound=self.lower_bound,
            timestamp=self.timestamp,
            candle_index=self.candle_index,
            direction=Direction.BULLISH,
        )


class QuasiModoLevel(FrozenModel):
    """Quasimodo Level (QML/QMH).

    Supports two construction styles:
    - Detector style: ``level``, ``h1_price``, ``h1_timestamp``, ``h2_price``,
      ``h2_timestamp``, ``break_candle_index``, ``break_timestamp``, ``is_valid``.
    - Legacy/serializer style: ``qml_price``, ``h_price``, ``hh_price``,
      ``h_timestamp``, ``hh_timestamp``, ``candle_index``, ``tested``.

    Both sets of fields are kept in sync via ``model_post_init``.
    """

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    direction: Direction

    # --- Detector-style fields (primary) ---
    level: Optional[float] = Field(default=None, gt=0)
    h1_price: Optional[float] = Field(default=None, gt=0)
    h1_timestamp: Optional[datetime] = None
    h2_price: Optional[float] = Field(default=None, gt=0)
    h2_timestamp: Optional[datetime] = None
    h2_index: Optional[int] = Field(default=None, ge=0)
    l2_index: Optional[int] = Field(default=None, ge=0)
    break_candle_index: Optional[int] = Field(default=None, ge=0)
    break_timestamp: Optional[datetime] = None
    is_valid: bool = Field(default=True)

    # --- Legacy/serializer-style fields ---
    qml_price: Optional[float] = Field(default=None, gt=0)
    h_price: Optional[float] = Field(default=None, gt=0)
    hh_price: Optional[float] = Field(default=None, gt=0)
    h_timestamp: Optional[datetime] = None
    hh_timestamp: Optional[datetime] = None
    candle_index: int = Field(ge=0, default=0)
    tested: bool = Field(default=False)
    test_timestamp: Optional[datetime] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")

    def model_post_init(self, __context) -> None:
        # Sync detector-style → legacy-style
        if self.level is not None and self.qml_price is None:
            object.__setattr__(self, "qml_price", self.level)
        if self.qml_price is not None and self.level is None:
            object.__setattr__(self, "level", self.qml_price)

        if self.h1_price is not None and self.h_price is None:
            object.__setattr__(self, "h_price", self.h1_price)
        if self.h_price is not None and self.h1_price is None:
            object.__setattr__(self, "h1_price", self.h_price)

        if self.h2_price is not None and self.hh_price is None:
            object.__setattr__(self, "hh_price", self.h2_price)
        if self.hh_price is not None and self.h2_price is None:
            object.__setattr__(self, "h2_price", self.hh_price)

        if self.h1_timestamp is not None and self.h_timestamp is None:
            object.__setattr__(self, "h_timestamp", self.h1_timestamp)
        if self.h_timestamp is not None and self.h1_timestamp is None:
            object.__setattr__(self, "h1_timestamp", self.h_timestamp)

        if self.h2_timestamp is not None and self.hh_timestamp is None:
            object.__setattr__(self, "hh_timestamp", self.h2_timestamp)
        if self.hh_timestamp is not None and self.h2_timestamp is None:
            object.__setattr__(self, "h2_timestamp", self.hh_timestamp)

        if self.break_candle_index is not None and self.candle_index == 0:
            object.__setattr__(self, "candle_index", self.break_candle_index)

    @computed_field
    @property
    def is_qml(self) -> bool:
        return self.direction == Direction.BEARISH

    @computed_field
    @property
    def is_qmh(self) -> bool:
        return self.direction == Direction.BULLISH


class MiniPriceLevel(FrozenModel):
    """Mini Price Level (MPL).

    Supports two construction styles:
    - Detector style: ``level``, ``is_type1``.
    - Legacy/serializer style: ``mpl_price``, ``has_internal_structure``.

    Both sets of fields are kept in sync via ``model_post_init``.
    """

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction

    # --- Detector-style fields ---
    level: Optional[float] = Field(default=None, gt=0)
    is_type1: Optional[bool] = Field(default=None)

    # --- Legacy/serializer-style fields ---
    mpl_price: Optional[float] = Field(default=None, gt=0)
    has_internal_structure: bool = Field(default=False)
    tested: bool = Field(default=False)
    test_timestamp: Optional[datetime] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")

    def model_post_init(self, __context) -> None:
        # Sync detector-style → legacy-style
        if self.level is not None and self.mpl_price is None:
            object.__setattr__(self, "mpl_price", self.level)
        if self.mpl_price is not None and self.level is None:
            object.__setattr__(self, "level", self.mpl_price)

        if self.is_type1 is not None:
            object.__setattr__(self, "has_internal_structure", self.is_type1)
        elif self.has_internal_structure and self.is_type1 is None:
            object.__setattr__(self, "is_type1", self.has_internal_structure)

    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH

    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
