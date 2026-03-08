from datetime import datetime, time
from typing import Optional

from pydantic import Field, field_validator, computed_field

from engine.shared.exceptions import ConfigurationError
from engine.shared.models.base import FrozenModel
from engine.ta.constants import Session, SESSION_UTC_RANGES, Timeframe


class SessionWindow(FrozenModel):
    
    session: Session
    start_hour_utc: int = Field(ge=0, le=23)
    end_hour_utc: int = Field(ge=0, le=23)
    
    @computed_field
    @property
    def duration_hours(self) -> int:
        if self.end_hour_utc >= self.start_hour_utc:
            return self.end_hour_utc - self.start_hour_utc
        else:
            return (24 - self.start_hour_utc) + self.end_hour_utc
    
    def contains_hour(self, hour_utc: int) -> bool:
        if hour_utc < 0 or hour_utc > 23:
            raise ConfigurationError(
                "Hour must be between 0 and 23",
                details={"hour_utc": hour_utc},
            )
        
        if self.end_hour_utc >= self.start_hour_utc:
            return self.start_hour_utc <= hour_utc < self.end_hour_utc
        else:
            return hour_utc >= self.start_hour_utc or hour_utc < self.end_hour_utc
    
    def contains_timestamp(self, timestamp: datetime) -> bool:
        hour_utc = timestamp.hour
        return self.contains_hour(hour_utc)


class SessionState(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    timestamp: datetime
    active_session: Session
    is_overlap: bool = Field(default=False)
    overlapping_sessions: list[Session] = Field(default_factory=list)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    @computed_field
    @property
    def is_asia(self) -> bool:
        return self.active_session == Session.ASIA
    
    @computed_field
    @property
    def is_london(self) -> bool:
        return self.active_session == Session.LONDON
    
    @computed_field
    @property
    def is_new_york(self) -> bool:
        return self.active_session == Session.NEW_YORK
    
    @computed_field
    @property
    def is_london_ny_overlap(self) -> bool:
        return (
            self.is_overlap
            and Session.LONDON in self.overlapping_sessions
            and Session.NEW_YORK in self.overlapping_sessions
        )


class SessionRange(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Timeframe
    session: Session
    start_time: datetime
    end_time: datetime
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    open: float = Field(gt=0)
    close: float = Field(gt=0)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")
    
    def model_post_init(self, __context) -> None:
        if self.high < self.low:
            raise ConfigurationError(
                "Session high must be >= low",
                details={
                    "symbol": self.symbol,
                    "session": self.session,
                    "high": self.high,
                    "low": self.low,
                },
            )
        
        if self.end_time <= self.start_time:
            raise ConfigurationError(
                "Session end time must be after start time",
                details={
                    "symbol": self.symbol,
                    "session": self.session,
                    "start_time": self.start_time.isoformat(),
                    "end_time": self.end_time.isoformat(),
                },
            )
    
    @computed_field
    @property
    def range_size(self) -> float:
        return self.high - self.low
    
    @computed_field
    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2.0
    
    @computed_field
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @computed_field
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


def get_session_window(session: Session) -> SessionWindow:
    start_hour, end_hour = SESSION_UTC_RANGES.get(session, (0, 0))
    
    return SessionWindow(
        session=session,
        start_hour_utc=start_hour,
        end_hour_utc=end_hour,
    )


def identify_active_session(timestamp: datetime) -> SessionState:
    hour_utc = timestamp.hour
    
    active_sessions: list[Session] = []
    
    for session in [Session.ASIA, Session.LONDON, Session.NEW_YORK]:
        window = get_session_window(session)
        if window.contains_hour(hour_utc):
            active_sessions.append(session)
    
    if not active_sessions:
        primary_session = Session.ASIA
        is_overlap = False
        overlapping = []
    elif len(active_sessions) == 1:
        primary_session = active_sessions[0]
        is_overlap = False
        overlapping = []
    else:
        if Session.LONDON in active_sessions and Session.NEW_YORK in active_sessions:
            primary_session = Session.OVERLAP_LONDON_NY
        else:
            primary_session = active_sessions[0]
        
        is_overlap = True
        overlapping = active_sessions
    
    return SessionState(
        symbol="GENERIC",
        timeframe=Timeframe.H1,
        timestamp=timestamp,
        active_session=primary_session,
        is_overlap=is_overlap,
        overlapping_sessions=overlapping,
    )
