from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.models.base import FrozenModel
from engine.ta.constants import Timeframe, Direction, CandidatePattern


class TechnicalCandidate(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    pattern: CandidatePattern
    direction: Direction
    timestamp: datetime
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    risk_reward_ratio: Optional[float] = Field(default=None, gt=0)
    framework: str = Field(pattern=r"^(SMC|SND)$")
    
    htf_timeframe: Optional[Timeframe] = None
    ltf_timeframe: Optional[Timeframe] = None
    
    htf_context: dict = Field(default_factory=dict)
    ltf_confirmation: dict = Field(default_factory=dict)
    
    zone_upper: Optional[float] = Field(default=None, gt=0)
    zone_lower: Optional[float] = Field(default=None, gt=0)
    
    liquidity_swept: bool = Field(default=False)
    swept_level: Optional[float] = Field(default=None, gt=0)
    
    structure_broken: bool = Field(default=False)
    broken_level: Optional[float] = Field(default=None, gt=0)
    
    session_context: Optional[str] = None
    
    fib_level: Optional[str] = None
    
    metadata: dict = Field(default_factory=dict)
    
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
    
    @computed_field
    @property
    def is_smc(self) -> bool:
        return self.framework == "SMC"
    
    @computed_field
    @property
    def is_snd(self) -> bool:
        return self.framework == "SND"
    
    @computed_field
    @property
    def stop_loss_pips(self) -> float:
        return abs(self.entry_price - self.stop_loss) * 10000
    
    @computed_field
    @property
    def take_profit_pips(self) -> Optional[float]:
        if self.take_profit is None:
            return None
        return abs(self.take_profit - self.entry_price) * 10000


class SMCCandidate(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    pattern: CandidatePattern
    direction: Direction
    timestamp: datetime
    
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    
    htf_timeframe: Timeframe
    ltf_timeframe: Timeframe
    
    bms_detected: bool = Field(default=False)
    bms_price: Optional[float] = Field(default=None, gt=0)
    bms_timestamp: Optional[datetime] = None
    
    choch_detected: bool = Field(default=False)
    choch_price: Optional[float] = Field(default=None, gt=0)
    choch_timestamp: Optional[datetime] = None
    
    sms_detected: bool = Field(default=False)
    sms_price: Optional[float] = Field(default=None, gt=0)
    sms_timestamp: Optional[datetime] = None
    
    order_block_upper: Optional[float] = Field(default=None, gt=0)
    order_block_lower: Optional[float] = Field(default=None, gt=0)
    order_block_timestamp: Optional[datetime] = None
    
    fvg_upper: Optional[float] = Field(default=None, gt=0)
    fvg_lower: Optional[float] = Field(default=None, gt=0)
    fvg_timestamp: Optional[datetime] = None
    
    liquidity_swept: bool = Field(default=False)
    swept_level: Optional[float] = Field(default=None, gt=0)
    sweep_timestamp: Optional[datetime] = None
    
    inducement_cleared: bool = Field(default=False)
    inducement_level: Optional[float] = Field(default=None, gt=0)
    
    ltf_confirmation: bool = Field(default=False)
    ltf_confirmation_timestamp: Optional[datetime] = None
    
    displacement_pips: Optional[float] = Field(default=None, ge=0)
    
    fib_level: Optional[str] = None
    
    session_context: Optional[str] = None
    
    metadata: dict = Field(default_factory=dict)
    
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
    
    def to_technical_candidate(self) -> TechnicalCandidate:
        htf_context = {}
        if self.bms_detected:
            htf_context["bms_price"] = self.bms_price
            htf_context["bms_timestamp"] = self.bms_timestamp.isoformat() if self.bms_timestamp else None
        if self.choch_detected:
            htf_context["choch_price"] = self.choch_price
            htf_context["choch_timestamp"] = self.choch_timestamp.isoformat() if self.choch_timestamp else None
        if self.sms_detected:
            htf_context["sms_price"] = self.sms_price
            htf_context["sms_timestamp"] = self.sms_timestamp.isoformat() if self.sms_timestamp else None
        
        ltf_confirmation = {
            "confirmed": self.ltf_confirmation,
            "confirmation_timestamp": self.ltf_confirmation_timestamp.isoformat() if self.ltf_confirmation_timestamp else None,
        }
        
        return TechnicalCandidate(
            symbol=self.symbol,
            timeframe=self.timeframe,
            pattern=self.pattern,
            direction=self.direction,
            timestamp=self.timestamp,
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            framework="SMC",
            htf_timeframe=self.htf_timeframe,
            ltf_timeframe=self.ltf_timeframe,
            htf_context=htf_context,
            ltf_confirmation=ltf_confirmation,
            zone_upper=self.order_block_upper or self.fvg_upper,
            zone_lower=self.order_block_lower or self.fvg_lower,
            liquidity_swept=self.liquidity_swept,
            swept_level=self.swept_level,
            structure_broken=self.bms_detected or self.choch_detected,
            broken_level=self.bms_price or self.choch_price,
            session_context=self.session_context,
            fib_level=self.fib_level,
            metadata=self.metadata,
        )


class SNDCandidate(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    pattern: CandidatePattern
    direction: Direction
    timestamp: datetime
    
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    
    htf_timeframe: Timeframe
    ltf_timeframe: Timeframe
    
    qml_detected: bool = Field(default=False)
    qml_price: Optional[float] = Field(default=None, gt=0)
    qml_timestamp: Optional[datetime] = None
    
    sr_flip_detected: bool = Field(default=False)
    sr_flip_price: Optional[float] = Field(default=None, gt=0)
    sr_flip_timestamp: Optional[datetime] = None
    
    rs_flip_detected: bool = Field(default=False)
    rs_flip_price: Optional[float] = Field(default=None, gt=0)
    rs_flip_timestamp: Optional[datetime] = None
    
    mpl_detected: bool = Field(default=False)
    mpl_price: Optional[float] = Field(default=None, gt=0)
    mpl_timestamp: Optional[datetime] = None
    
    supply_zone_upper: Optional[float] = Field(default=None, gt=0)
    supply_zone_lower: Optional[float] = Field(default=None, gt=0)
    supply_zone_timestamp: Optional[datetime] = None
    
    demand_zone_upper: Optional[float] = Field(default=None, gt=0)
    demand_zone_lower: Optional[float] = Field(default=None, gt=0)
    demand_zone_timestamp: Optional[datetime] = None
    
    fakeout_detected: bool = Field(default=False)
    fakeout_level: Optional[float] = Field(default=None, gt=0)
    fakeout_timestamp: Optional[datetime] = None
    
    previous_highs_count: int = Field(ge=0, default=0)
    previous_lows_count: int = Field(ge=0, default=0)
    
    marubozu_detected: bool = Field(default=False)
    marubozu_timestamp: Optional[datetime] = None
    
    compression_detected: bool = Field(default=False)
    compression_candle_count: Optional[int] = Field(default=None, ge=0)
    
    ltf_confirmation: bool = Field(default=False)
    ltf_confirmation_timestamp: Optional[datetime] = None
    
    fib_level: Optional[str] = None
    
    session_context: Optional[str] = None
    
    metadata: dict = Field(default_factory=dict)
    
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
    
    def to_technical_candidate(self) -> TechnicalCandidate:
        htf_context = {}
        if self.qml_detected:
            htf_context["qml_price"] = self.qml_price
            htf_context["qml_timestamp"] = self.qml_timestamp.isoformat() if self.qml_timestamp else None
        if self.sr_flip_detected:
            htf_context["sr_flip_price"] = self.sr_flip_price
            htf_context["sr_flip_timestamp"] = self.sr_flip_timestamp.isoformat() if self.sr_flip_timestamp else None
        if self.rs_flip_detected:
            htf_context["rs_flip_price"] = self.rs_flip_price
            htf_context["rs_flip_timestamp"] = self.rs_flip_timestamp.isoformat() if self.rs_flip_timestamp else None
        if self.mpl_detected:
            htf_context["mpl_price"] = self.mpl_price
            htf_context["mpl_timestamp"] = self.mpl_timestamp.isoformat() if self.mpl_timestamp else None
        
        ltf_confirmation = {
            "confirmed": self.ltf_confirmation,
            "confirmation_timestamp": self.ltf_confirmation_timestamp.isoformat() if self.ltf_confirmation_timestamp else None,
            "marubozu_detected": self.marubozu_detected,
            "compression_detected": self.compression_detected,
        }
        
        zone_upper = self.supply_zone_upper or self.demand_zone_upper
        zone_lower = self.supply_zone_lower or self.demand_zone_lower
        
        return TechnicalCandidate(
            symbol=self.symbol,
            timeframe=self.timeframe,
            pattern=self.pattern,
            direction=self.direction,
            timestamp=self.timestamp,
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            framework="SND",
            htf_timeframe=self.htf_timeframe,
            ltf_timeframe=self.ltf_timeframe,
            htf_context=htf_context,
            ltf_confirmation=ltf_confirmation,
            zone_upper=zone_upper,
            zone_lower=zone_lower,
            liquidity_swept=self.fakeout_detected,
            swept_level=self.fakeout_level,
            structure_broken=self.sr_flip_detected or self.rs_flip_detected,
            broken_level=self.sr_flip_price or self.rs_flip_price,
            session_context=self.session_context,
            fib_level=self.fib_level,
            metadata=self.metadata,
        )
