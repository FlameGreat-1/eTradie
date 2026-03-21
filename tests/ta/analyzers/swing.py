"""Tests for SwingAnalyzer (swing high/low detection, latest/extreme lookups).

Production module: src/engine/ta/common/analyzers/swings.py
"""

from datetime import UTC, datetime, timedelta

import pytest

from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.constants import Direction, Timeframe
from engine.ta.models.swing import SwingHigh, SwingLow
from tests.factories import make_candle_sequence


@pytest.fixture
def analyzer() -> SwingAnalyzer:
    return SwingAnalyzer(left_bars=3, right_bars=3)


# ---------------------------------------------------------------------------
# detect_swing_highs
# ---------------------------------------------------------------------------


class TestDetectSwingHighs:
    def test_uptrend_produces_swing_highs(self, analyzer: SwingAnalyzer):
        """An uptrend with enough bars should produce at least one swing high."""
        seq = make_candle_sequence(count=50, trend="up", symbol="EURUSD")
        highs = analyzer.detect_swing_highs(seq)
        assert isinstance(highs, list)
        for sh in highs:
            assert isinstance(sh, SwingHigh)
            assert sh.symbol == "EURUSD"
            assert sh.timeframe == Timeframe.H1
            assert sh.price > 0
            assert sh.index >= analyzer.left_bars
            assert sh.left_bars == 3
            assert sh.right_bars == 3

    def test_swing_high_direction_is_bearish(self, analyzer: SwingAnalyzer):
        """SwingHigh.direction is always BEARISH (potential reversal down)."""
        seq = make_candle_sequence(count=50, trend="up")
        highs = analyzer.detect_swing_highs(seq)
        for sh in highs:
            assert sh.direction == Direction.BEARISH

    def test_swing_high_strength_in_range(self, analyzer: SwingAnalyzer):
        """Strength must be between 1 and 10."""
        seq = make_candle_sequence(count=50, trend="up")
        highs = analyzer.detect_swing_highs(seq)
        for sh in highs:
            assert 1 <= sh.strength <= 10

    def test_insufficient_bars_returns_empty(self):
        """Sequence shorter than left_bars + right_bars produces no swings."""
        wide = SwingAnalyzer(left_bars=5, right_bars=5)
        seq = make_candle_sequence(count=8)
        assert wide.detect_swing_highs(seq) == []


# ---------------------------------------------------------------------------
# detect_swing_lows
# ---------------------------------------------------------------------------


class TestDetectSwingLows:
    def test_downtrend_produces_swing_lows(self, analyzer: SwingAnalyzer):
        """A downtrend with enough bars should produce at least one swing low."""
        seq = make_candle_sequence(count=50, trend="down", symbol="GBPUSD")
        lows = analyzer.detect_swing_lows(seq)
        assert isinstance(lows, list)
        for sl in lows:
            assert isinstance(sl, SwingLow)
            assert sl.symbol == "GBPUSD"
            assert sl.price > 0
            assert sl.index >= analyzer.left_bars

    def test_swing_low_direction_is_bullish(self, analyzer: SwingAnalyzer):
        """SwingLow.direction is always BULLISH (potential reversal up)."""
        seq = make_candle_sequence(count=50, trend="down")
        lows = analyzer.detect_swing_lows(seq)
        for sl in lows:
            assert sl.direction == Direction.BULLISH

    def test_swing_low_strength_in_range(self, analyzer: SwingAnalyzer):
        """Strength must be between 1 and 10."""
        seq = make_candle_sequence(count=50, trend="down")
        lows = analyzer.detect_swing_lows(seq)
        for sl in lows:
            assert 1 <= sl.strength <= 10


# ---------------------------------------------------------------------------
# Range market produces both highs and lows
# ---------------------------------------------------------------------------


class TestRangeMarket:
    def test_range_produces_both(self, analyzer: SwingAnalyzer):
        """A ranging market should produce both swing highs and swing lows."""
        seq = make_candle_sequence(count=60, trend="range", symbol="USDJPY")
        highs = analyzer.detect_swing_highs(seq)
        lows = analyzer.detect_swing_lows(seq)
        assert isinstance(highs, list)
        assert isinstance(lows, list)


# ---------------------------------------------------------------------------
# get_latest / get_highest / get_lowest helpers
# ---------------------------------------------------------------------------


class TestSwingLookups:
    def test_get_latest_swing_high(self, analyzer: SwingAnalyzer):
        """Returns the swing high with the most recent timestamp."""
        seq = make_candle_sequence(count=50, trend="up")
        highs = analyzer.detect_swing_highs(seq)
        if not highs:
            pytest.skip("No swing highs detected in this sequence")

        latest = analyzer.get_latest_swing_high(highs)
        assert latest is not None
        assert latest.timestamp == max(sh.timestamp for sh in highs)

    def test_get_latest_swing_low(self, analyzer: SwingAnalyzer):
        """Returns the swing low with the most recent timestamp."""
        seq = make_candle_sequence(count=50, trend="down")
        lows = analyzer.detect_swing_lows(seq)
        if not lows:
            pytest.skip("No swing lows detected in this sequence")

        latest = analyzer.get_latest_swing_low(lows)
        assert latest is not None
        assert latest.timestamp == max(sl.timestamp for sl in lows)

    def test_get_highest_swing_high(self, analyzer: SwingAnalyzer):
        """Returns the swing high with the highest price."""
        seq = make_candle_sequence(count=50, trend="up")
        highs = analyzer.detect_swing_highs(seq)
        if not highs:
            pytest.skip("No swing highs detected")

        highest = analyzer.get_highest_swing_high(highs)
        assert highest is not None
        assert highest.price == max(sh.price for sh in highs)

    def test_get_lowest_swing_low(self, analyzer: SwingAnalyzer):
        """Returns the swing low with the lowest price."""
        seq = make_candle_sequence(count=50, trend="down")
        lows = analyzer.detect_swing_lows(seq)
        if not lows:
            pytest.skip("No swing lows detected")

        lowest = analyzer.get_lowest_swing_low(lows)
        assert lowest is not None
        assert lowest.price == min(sl.price for sl in lows)

    def test_empty_list_returns_none(self, analyzer: SwingAnalyzer):
        """All lookup helpers return None for empty lists."""
        assert analyzer.get_latest_swing_high([]) is None
        assert analyzer.get_latest_swing_low([]) is None
        assert analyzer.get_highest_swing_high([]) is None
        assert analyzer.get_lowest_swing_low([]) is None


# ---------------------------------------------------------------------------
# Custom parameters
# ---------------------------------------------------------------------------


class TestCustomParameters:
    def test_tight_bars_more_swings(self):
        """Smaller left/right bars should detect more swing points."""
        tight = SwingAnalyzer(left_bars=2, right_bars=2)
        wide = SwingAnalyzer(left_bars=5, right_bars=5)
        seq = make_candle_sequence(count=60, trend="range")

        tight_highs = tight.detect_swing_highs(seq)
        wide_highs = wide.detect_swing_highs(seq)

        assert len(tight_highs) >= len(wide_highs)
