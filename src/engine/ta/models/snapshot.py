from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.models.structure_event import (
    BreakOfStructure,
    ChangeOfCharacter,
    BreakInMarketStructure,
    ShiftInMarketStructure,
    SRFlip,
    RSFlip,
)
from engine.ta.models.liquidity_event import (
    LiquiditySweep,
    LiquidityGrab,
    InducementEvent,
    EqualHighsLows,
)
from engine.ta.models.zone import (
    OrderBlock,
    FairValueGap,
    BreakerBlock,
    SupplyZone,
    DemandZone,
    QuasiModoLevel,
    MiniPriceLevel,
)
from engine.ta.models.fibonacci import FibonacciRetracement, DealingRange
from engine.ta.models.session import SessionState
from engine.ta.models.candidate import TechnicalCandidate


class TechnicalSnapshot(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    
    candles: CandleSequence
    
    swing_highs: list[SwingHigh] = Field(default_factory=list)
    swing_lows: list[SwingLow] = Field(default_factory=list)
    
    bos_events: list[BreakOfStructure] = Field(default_factory=list)
    choch_events: list[ChangeOfCharacter] = Field(default_factory=list)
    bms_events: list[BreakInMarketStructure] = Field(default_factory=list)
    sms_events: list[ShiftInMarketStructure] = Field(default_factory=list)
    sr_flips: list[SRFlip] = Field(default_factory=list)
    rs_flips: list[RSFlip] = Field(default_factory=list)
    
    liquidity_sweeps: list[LiquiditySweep] = Field(default_factory=list)
    liquidity_grabs: list[LiquidityGrab] = Field(default_factory=list)
    inducement_events: list[InducementEvent] = Field(default_factory=list)
    equal_highs_lows: list[EqualHighsLows] = Field(default_factory=list)
    
    order_blocks: list[OrderBlock] = Field(default_factory=list)
    fvgs: list[FairValueGap] = Field(default_factory=list)
    breaker_blocks: list[BreakerBlock] = Field(default_factory=list)
    
    supply_zones: list[SupplyZone] = Field(default_factory=list)
    demand_zones: list[DemandZone] = Field(default_factory=list)
    
    qml_levels: list[QuasiModoLevel] = Field(default_factory=list)
    mpl_levels: list[MiniPriceLevel] = Field(default_factory=list)
    
    fibonacci_retracements: list[FibonacciRetracement] = Field(default_factory=list)
    dealing_ranges: list[DealingRange] = Field(default_factory=list)
    
    session_state: Optional[SessionState] = None
    
    trend_direction: Direction = Field(default=Direction.NEUTRAL)
    
    candidates: list[TechnicalCandidate] = Field(default_factory=list)
    
    metadata: dict = Field(default_factory=dict)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def latest_candle_timestamp(self) -> datetime:
        return self.candles.end_time
    
    @computed_field
    @property
    def candle_count(self) -> int:
        return self.candles.count
    
    @computed_field
    @property
    def has_bullish_structure(self) -> bool:
        return self.trend_direction == Direction.BULLISH
    
    @computed_field
    @property
    def has_bearish_structure(self) -> bool:
        return self.trend_direction == Direction.BEARISH
    
    @computed_field
    @property
    def has_neutral_structure(self) -> bool:
        return self.trend_direction == Direction.NEUTRAL
    
    @computed_field
    @property
    def total_swing_points(self) -> int:
        return len(self.swing_highs) + len(self.swing_lows)
    
    @computed_field
    @property
    def total_structure_events(self) -> int:
        return (
            len(self.bos_events)
            + len(self.choch_events)
            + len(self.bms_events)
            + len(self.sms_events)
            + len(self.sr_flips)
            + len(self.rs_flips)
        )
    
    @computed_field
    @property
    def total_liquidity_events(self) -> int:
        return (
            len(self.liquidity_sweeps)
            + len(self.liquidity_grabs)
            + len(self.inducement_events)
            + len(self.equal_highs_lows)
        )
    
    @computed_field
    @property
    def total_zones(self) -> int:
        return (
            len(self.order_blocks)
            + len(self.fvgs)
            + len(self.breaker_blocks)
            + len(self.supply_zones)
            + len(self.demand_zones)
        )
    
    @computed_field
    @property
    def total_candidates(self) -> int:
        return len(self.candidates)
    
    @computed_field
    @property
    def has_candidates(self) -> bool:
        return self.total_candidates > 0
    
    def get_latest_bos(self) -> Optional[BreakOfStructure]:
        if not self.bos_events:
            return None
        return max(self.bos_events, key=lambda x: x.timestamp)
    
    def get_latest_choch(self) -> Optional[ChangeOfCharacter]:
        if not self.choch_events:
            return None
        return max(self.choch_events, key=lambda x: x.timestamp)
    
    def get_latest_bms(self) -> Optional[BreakInMarketStructure]:
        if not self.bms_events:
            return None
        return max(self.bms_events, key=lambda x: x.timestamp)
    
    def get_latest_sms(self) -> Optional[ShiftInMarketStructure]:
        if not self.sms_events:
            return None
        return max(self.sms_events, key=lambda x: x.timestamp)
    
    def get_unmitigated_order_blocks(self) -> list[OrderBlock]:
        return [ob for ob in self.order_blocks if not ob.mitigated]
    
    def get_unfilled_fvgs(self) -> list[FairValueGap]:
        return [fvg for fvg in self.fvgs if not fvg.filled]
    
    def get_unbroken_supply_zones(self) -> list[SupplyZone]:
        return [zone for zone in self.supply_zones if not zone.broken]
    
    def get_unbroken_demand_zones(self) -> list[DemandZone]:
        return [zone for zone in self.demand_zones if not zone.broken]
    
    def get_bullish_candidates(self) -> list[TechnicalCandidate]:
        return [c for c in self.candidates if c.is_bullish]
    
    def get_bearish_candidates(self) -> list[TechnicalCandidate]:
        return [c for c in self.candidates if c.is_bearish]
    
    def get_smc_candidates(self) -> list[TechnicalCandidate]:
        return [c for c in self.candidates if c.is_smc]
    
    def get_snd_candidates(self) -> list[TechnicalCandidate]:
        return [c for c in self.candidates if c.is_snd]


class MultiTimeframeSnapshot(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timestamp: datetime
    
    htf_snapshot: TechnicalSnapshot
    ltf_snapshot: TechnicalSnapshot
    
    htf_ltf_aligned: bool = Field(default=False)
    
    alignment_metadata: dict = Field(default_factory=dict)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def htf_timeframe(self) -> Timeframe:
        return self.htf_snapshot.timeframe
    
    @computed_field
    @property
    def ltf_timeframe(self) -> Timeframe:
        return self.ltf_snapshot.timeframe
    
    @computed_field
    @property
    def htf_trend(self) -> Direction:
        return self.htf_snapshot.trend_direction
    
    @computed_field
    @property
    def ltf_trend(self) -> Direction:
        return self.ltf_snapshot.trend_direction
    
    @computed_field
    @property
    def trends_aligned(self) -> bool:
        return self.htf_trend == self.ltf_trend and self.htf_trend != Direction.NEUTRAL
    
    @computed_field
    @property
    def total_candidates(self) -> int:
        return self.htf_snapshot.total_candidates + self.ltf_snapshot.total_candidates
    
    def get_all_candidates(self) -> list[TechnicalCandidate]:
        return self.htf_snapshot.candidates + self.ltf_snapshot.candidates
    
    def get_aligned_candidates(self) -> list[TechnicalCandidate]:
        if not self.htf_ltf_aligned:
            return []
        
        return [
            c for c in self.get_all_candidates()
            if c.direction == self.htf_trend
        ]
