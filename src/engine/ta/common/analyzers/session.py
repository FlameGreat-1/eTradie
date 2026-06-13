from datetime import datetime

from engine.shared.logging import get_logger
from engine.ta.constants import Session, Timeframe
from engine.ta.models.candle import Candle, CandleSequence
from engine.ta.models.session import (
    SessionRange,
    SessionState,
    get_session_window,
)

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
            overlapping: list[Session] = []
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
    ) -> SessionRange | None:
        """Aggregate every candle in the sequence whose hour matches ``session``.

        NOTE: this method returns a *synthetic* range that merges every
        occurrence of ``session`` across the full sequence.  On a
        multi-day sequence the resulting high/low spans every matching
        session, not just one.  That is useful for broad reference
        views (see ``get_session_boundaries``) but it is NOT the right
        primitive for per-session patterns such as AMD, which reason
        about a single completed Asian session followed by one London /
        NY cycle.  Per-session callers should use
        ``extract_most_recent_session_range`` instead.
        """
        session_window = get_session_window(session)

        session_candles = [c for c in sequence.candles if session_window.contains_timestamp(c.timestamp)]

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

    def extract_most_recent_session_range(
        self,
        sequence: CandleSequence,
        session: Session,
    ) -> SessionRange | None:
        """Return the range of the most recent contiguous ``session`` block.

        Walks ``sequence.candles`` in reverse.  Finds the first candle
        whose hour falls in the session window and then extends
        backwards until it hits a candle outside the window.  The
        resulting contiguous block is the most recent fully-captured
        (or partially-captured, if the sequence ends mid-session)
        occurrence of that session.

        Contiguity is defined as "the previous candle in the sequence
        is also in the session window".  This works uniformly across
        FX / crypto timeframes because it relies on sequence ordering
        rather than absolute clock spacing, and it correctly stops at
        the session boundary even when data is missing (the gap
        candle will fail the window test and end the block).

        Returns ``None`` when the sequence contains no candles whose
        hour matches the session window.

        This is the primitive that per-session patterns (AMD) must
        use; see ``extract_session_range`` for the aggregated
        alternative.
        """
        session_window = get_session_window(session)

        candles = sequence.candles
        if not candles:
            return None

        end_index: int | None = None
        for i in range(len(candles) - 1, -1, -1):
            if session_window.contains_timestamp(candles[i].timestamp):
                end_index = i
                break

        if end_index is None:
            return None

        start_index = end_index
        while start_index - 1 >= 0 and session_window.contains_timestamp(candles[start_index - 1].timestamp):
            start_index -= 1

        block = candles[start_index : end_index + 1]

        high = max(c.high for c in block)
        low = min(c.low for c in block)
        open_price = block[0].open
        close_price = block[-1].close

        return SessionRange(
            symbol=sequence.symbol,
            timeframe=sequence.timeframe,
            session=session,
            start_time=block[0].timestamp,
            end_time=block[-1].timestamp,
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

        return [c for c in sequence.candles if session_window.contains_timestamp(c.timestamp)]

    def is_london_ny_overlap(self, timestamp: datetime) -> bool:
        hour_utc = timestamp.hour

        return self.london_window.contains_hour(hour_utc) and self.ny_window.contains_hour(hour_utc)

    def get_session_boundaries(
        self,
        sequence: CandleSequence,
    ) -> dict[Session, SessionRange | None]:
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
