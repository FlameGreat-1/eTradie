from datetime import datetime
from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Session, SESSION_UTC_RANGES, Timeframe
from engine.ta.models.candle import Candle, CandleSequence
from engine.ta.models.session import SessionState, SessionRange, SessionWindow, get_session_window

logger = get_logger(__name__)


class SessionAnalyzer:
    
    def __init__(self) -> None:
        self.asia_window = get_session_window(Session.ASIA)
        self.london_window = get_session_window(Session.LONDON)
        self.ny_window = get_session_window(Session.NEW_YORK)
    
    def identify_session(self, timestamp: datetime) -> SessionState:
        hour_utc = timestamp.hour
        
        active_sessions: list[Session] = []
        
        if self.asia_window.contains_hour(hour_utc):
            active_sessions.append(Session.ASIA)
        
        if self.london_window.contains_hour(hour_utc):
            active_sessions.append(Session.LONDON)
        
        if self.ny_window.contains_hour(hour_utc):
            active_sessions.append(Session.NEW_YORK)
        
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
    
    def extract_session_range(
        self,
        sequence: CandleSequence,
        session: Session,
    ) -> Optional[SessionRange]:
        session_window = get_session_window(session)
        
        session_candles = [
            c for c in sequence.candles
            if session_window.contains_timestamp(c.timestamp)
        ]
        
        if not session_candles:
            return None
        
        high = max(c.high for c in session_candles)
        low = min(c.low for c in session_candles)
        open_price = session_candles[0].open
        close_price = session_candles[-1].close
        
        return SessionRange(
            symbol=sequence.symbol,
            timeframe=sequence.timeframe,
            session=session,
            start_time=session_candles[0].timestamp,
            end_time=session_candles[-1].timestamp,
            high=high,
            low=low,
            open=open_price,
            close=close_price,
        )
    
    def get_session_candles(
        self,
        sequence: CandleSequence,
        session: Session,
    ) -> list[Candle]:
        session_window = get_session_window(session)
        
        return [
            c for c in sequence.candles
            if session_window.contains_timestamp(c.timestamp)
        ]
    
    def is_london_ny_overlap(self, timestamp: datetime) -> bool:
        hour_utc = timestamp.hour
        
        return (
            self.london_window.contains_hour(hour_utc)
            and self.ny_window.contains_hour(hour_utc)
        )
    
    def get_session_boundaries(
        self,
        sequence: CandleSequence,
    ) -> dict[Session, Optional[SessionRange]]:
        return {
            Session.ASIA: self.extract_session_range(sequence, Session.ASIA),
            Session.LONDON: self.extract_session_range(sequence, Session.LONDON),
            Session.NEW_YORK: self.extract_session_range(sequence, Session.NEW_YORK),
        }
    
    def tag_candles_with_session(
        self,
        sequence: CandleSequence,
    ) -> dict[int, SessionState]:
        session_tags = {}
        
        for i, candle in enumerate(sequence.candles):
            session_state = self.identify_session(candle.timestamp)
            session_tags[i] = session_state
        
        return session_tags
