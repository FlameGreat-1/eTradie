from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.exceptions import ConfigurationError
from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, Direction, ZoneType


class Zone(FrozenModel):

    symbol: str = Field(min_length=3, max_length=30)
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

    symbol: str = Field(min_length=3, max_length=30)
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

    symbol: str = Field(min_length=3, max_length=30)
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

    symbol: str = Field(min_length=3, max_length=30)
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
    """Supply zone bounded by QML (upper) and SR Flip (lower).

    Fields match what SupplyDemandDetector.create_supply_zone() passes:
    - qml_level, qml_timestamp: the QML price level and when it formed
    - sr_flip_level, sr_flip_timestamp: the SR Flip level and when it formed
    - is_valid: whether the zone is confirmed

    upper_bound/lower_bound are derived from max/min of qml and sr_flip.
    """

    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    qml_level: float = Field(gt=0)
    qml_timestamp: datetime
    sr_flip_level: float = Field(gt=0)
    sr_flip_timestamp: datetime
    is_valid: bool = Field(default=True)
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
    def candle_index(self) -> int:
        """Compatibility alias -- supply zones don't have a single candle index."""
        return 0

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
    """Demand zone bounded by RS Flip (upper) and QMH (lower).

    Fields match what SupplyDemandDetector.create_demand_zone() passes:
    - qmh_level, qmh_timestamp: the QMH price level and when it formed
    - rs_flip_level, rs_flip_timestamp: the RS Flip level and when it formed
    - is_valid: whether the zone is confirmed

    upper_bound/lower_bound are derived from max/min of qmh and rs_flip.
    """

    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    upper_bound: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    timestamp: datetime
    qmh_level: float = Field(gt=0)
    qmh_timestamp: datetime
    rs_flip_level: float = Field(gt=0)
    rs_flip_timestamp: datetime
    is_valid: bool = Field(default=True)
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
    def candle_index(self) -> int:
        """Compatibility alias -- demand zones don't have a single candle index."""
        return 0

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
    """Quasimodo Level (QML for sells, QMH for buys).

    Init field names match what QMDetector constructs:
    - qml_price: the QML/QMH price (first H for sells, first L for buys)
    - h_price, h_timestamp: first swing high price and time  (bearish QM)
    - hh_price, hh_timestamp: higher-high price and time     (bearish QM)
    - hh_index: candle index of the higher-high
    - l_price, l_timestamp: first swing low price and time   (bullish QM)
    - ll_price, ll_timestamp: lower-low price and time       (bullish QM)
    - ll_index: candle index of the lower-low
    - candle_index: index of candle that broke the level
    - break_timestamp: when the break occurred
    - is_valid: whether the QM structure is confirmed

    For bearish QM (QML): H -> HH -> break below H = QML
    For bullish QM (QMH): L -> LL -> break above L = QMH
    """

    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    qml_price: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction

    # ── Bearish QM fields (H -> HH -> break) ────────────────────────
    h_price: Optional[float] = Field(default=None, gt=0)
    hh_price: Optional[float] = Field(default=None, gt=0)
    h_timestamp: Optional[datetime] = None
    hh_timestamp: Optional[datetime] = None
    hh_index: Optional[int] = Field(default=None, ge=0)

    # ── Bullish QM fields (L -> LL -> break) ─────────────────────────
    l_price: Optional[float] = Field(default=None, gt=0)
    ll_price: Optional[float] = Field(default=None, gt=0)
    l_timestamp: Optional[datetime] = None
    ll_timestamp: Optional[datetime] = None
    ll_index: Optional[int] = Field(default=None, ge=0)

    break_timestamp: datetime
    is_valid: bool = Field(default=True)
    tested: bool = Field(default=False)
    test_timestamp: Optional[datetime] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")

    # ── Computed aliases for backward compatibility ───────────────────

    @computed_field
    @property
    def level(self) -> float:
        """Alias used by SnD detector/builder code that reads .level."""
        return self.qml_price

    @computed_field
    @property
    def h1_price(self) -> float:
        """Alias: first swing point price."""
        return self.h_price if self.h_price is not None else (self.l_price or 0.0)

    @computed_field
    @property
    def h2_price(self) -> float:
        """Alias: second swing point price."""
        return self.hh_price if self.hh_price is not None else (self.ll_price or 0.0)

    @computed_field
    @property
    def h1_timestamp(self) -> Optional[datetime]:
        """Alias: first swing point timestamp."""
        return self.h_timestamp if self.h_timestamp is not None else self.l_timestamp

    @computed_field
    @property
    def h2_timestamp(self) -> Optional[datetime]:
        """Alias: second swing point timestamp."""
        return self.hh_timestamp if self.hh_timestamp is not None else self.ll_timestamp

    @computed_field
    @property
    def break_candle_index(self) -> int:
        """Alias for serializers that read break_candle_index."""
        return self.candle_index

    @computed_field
    @property
    def h2_index(self) -> Optional[int]:
        """Index alias used by SnDDetector for MPL detection range."""
        return self.hh_index if self.hh_index is not None else self.ll_index

    @computed_field
    @property
    def l2_index(self) -> Optional[int]:
        """Index alias used by SnDDetector for MPL detection range (QMH)."""
        return self.ll_index if self.ll_index is not None else self.hh_index

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

    Fields match what MPLDetector constructs:
    - level: the MPL price (candle high for bearish, candle low for bullish)
    - is_type1: True if internal engulfing structure exists (circled)
    - has_internal_structure: same as is_type1

    Two types:
    - Type 1: MPL with internal engulfing structure (circled on chart)
    - Type 2: MPL breaks cleanly without internal structure
    """

    symbol: str = Field(min_length=3, max_length=30)
    timeframe: Timeframe
    level: float = Field(gt=0)
    timestamp: datetime
    candle_index: int = Field(ge=0)
    direction: Direction
    has_internal_structure: bool = Field(default=False)
    is_type1: bool = Field(default=False)
    tested: bool = Field(default=False)
    test_timestamp: Optional[datetime] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")

    @computed_field
    @property
    def mpl_price(self) -> float:
        """Alias for serializers that read mpl_price."""
        return self.level

    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.direction == Direction.BULLISH

    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.direction == Direction.BEARISH
