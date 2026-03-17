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

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    strength: int = Field(ge=1, le=10, default=1)
    tested: bool = Field(default=False)
    test_count: int = Field(ge=0, default=0)
    broken: bool = Field(default=False)
    broken_timestamp: Optional[datetime] = None

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

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    strength: int = Field(ge=1, le=10, default=1)
    tested: bool = Field(default=False)
    test_count: int = Field(ge=0, default=0)
    broken: bool = Field(default=False)
    broken_timestamp: Optional[datetime] = None

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
    """Quasimodo Level (QML / QMH).

    QML (bearish): H -> HH -> break of H level = QML established.
      - qml_price = H price (the level where Supply zone sits)
      - h_price / hh_price = H and HH swing high prices
      - h_timestamp / hh_timestamp = timestamps of H and HH
      - hh_index = candle index of the HH swing

    QMH (bullish): L -> LL -> break of L level = QMH established.
      - qml_price = L price (the level where Demand zone sits)
      - l_price / ll_price = L and LL swing low prices
      - l_timestamp / ll_timestamp = timestamps of L and LL
      - ll_index = candle index of the LL swing
    """

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    qml_price: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction

    # QML (bearish) fields: H -> HH structure
    h_price: Optional[float] = Field(default=None, gt=0)
    hh_price: Optional[float] = Field(default=None, gt=0)
    h_timestamp: Optional[datetime] = None
    hh_timestamp: Optional[datetime] = None
    hh_index: Optional[int] = Field(default=None, ge=0)

    # QMH (bullish) fields: L -> LL structure
    l_price: Optional[float] = Field(default=None, gt=0)
    ll_price: Optional[float] = Field(default=None, gt=0)
    l_timestamp: Optional[datetime] = None
    ll_timestamp: Optional[datetime] = None
    ll_index: Optional[int] = Field(default=None, ge=0)

    # Break confirmation
    break_timestamp: Optional[datetime] = None
    is_valid: bool = Field(default=True)

    tested: bool = Field(default=False)
    test_timestamp: Optional[datetime] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")

    @computed_field
    @property
    def is_qml(self) -> bool:
        return self.direction == Direction.BEARISH

    @computed_field
    @property
    def is_qmh(self) -> bool:
        return self.direction == Direction.BULLISH


class MiniPriceLevel(FrozenModel):

    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    mpl_price: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction
    has_internal_structure: bool = Field(default=False)
    tested: bool = Field(default=False)
    test_timestamp: Optional[datetime] = None

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
