"""Tests for TA constants and enums."""

from engine.ta.constants import (
    TIMEFRAME_MINUTES,
    Direction,
    Session,
    SESSION_UTC_RANGES,
    Timeframe,
)


class TestTimeframe:
    def test_all_timeframes_have_minutes(self):
        for tf in Timeframe:
            assert tf in TIMEFRAME_MINUTES, f"{tf} missing from TIMEFRAME_MINUTES"

    def test_minutes_ordering(self):
        ordered = sorted(Timeframe, key=lambda tf: TIMEFRAME_MINUTES[tf])
        assert ordered[0] == Timeframe.M1
        assert ordered[-1] == Timeframe.MN1

    def test_specific_values(self):
        assert TIMEFRAME_MINUTES[Timeframe.M1] == 1
        assert TIMEFRAME_MINUTES[Timeframe.M5] == 5
        assert TIMEFRAME_MINUTES[Timeframe.H1] == 60
        assert TIMEFRAME_MINUTES[Timeframe.H4] == 240
        assert TIMEFRAME_MINUTES[Timeframe.D1] == 1440
        assert TIMEFRAME_MINUTES[Timeframe.W1] == 10080


class TestDirection:
    def test_values(self):
        assert Direction.BULLISH == "BULLISH"
        assert Direction.BEARISH == "BEARISH"
        assert Direction.NEUTRAL == "NEUTRAL"


class TestSession:
    def test_all_sessions_have_ranges(self):
        for session in Session:
            assert session in SESSION_UTC_RANGES

    def test_overlap_within_london_and_ny(self):
        overlap_start, overlap_end = SESSION_UTC_RANGES[Session.OVERLAP_LONDON_NY]
        london_start, london_end = SESSION_UTC_RANGES[Session.LONDON]
        ny_start, ny_end = SESSION_UTC_RANGES[Session.NEW_YORK]
        assert overlap_start >= ny_start
        assert overlap_end <= london_end
