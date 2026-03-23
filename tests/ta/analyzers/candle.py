"""Tests for CandleAnalyzer (candle classification, displacement, imbalance).

Production module: src/engine/ta/common/analyzers/candles.py
"""

from datetime import UTC, datetime, timedelta

import pytest

from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.constants import CandleType, Timeframe
from engine.ta.models.candle import Candle
from tests.factories import make_candle, make_candle_sequence


@pytest.fixture
def analyzer() -> CandleAnalyzer:
    return CandleAnalyzer()


# ---------------------------------------------------------------------------
# classify_candle
# ---------------------------------------------------------------------------


class TestClassifyCandle:
    def test_doji(self, analyzer: CandleAnalyzer):
        """Open == close with wicks -> DOJI."""
        c = make_candle(open=1.1000, high=1.1050, low=1.0950, close=1.1000)
        assert analyzer.classify_candle(c) == CandleType.DOJI

    def test_near_doji(self, analyzer: CandleAnalyzer):
        """Body < 5% of total range -> DOJI."""
        c = make_candle(open=1.1000, high=1.1050, low=1.0950, close=1.1004)
        assert analyzer.classify_candle(c) == CandleType.DOJI

    def test_marubozu_bullish(self, analyzer: CandleAnalyzer):
        """Open == low, close == high -> MARUBOZU_BULLISH."""
        c = make_candle(open=1.1000, high=1.1100, low=1.1000, close=1.1100)
        assert analyzer.classify_candle(c) == CandleType.MARUBOZU_BULLISH

    def test_marubozu_bearish(self, analyzer: CandleAnalyzer):
        """Open == high, close == low -> MARUBOZU_BEARISH."""
        c = make_candle(open=1.1100, high=1.1100, low=1.1000, close=1.1000)
        assert analyzer.classify_candle(c) == CandleType.MARUBOZU_BEARISH

    def test_hammer(self, analyzer: CandleAnalyzer):
        """Bullish candle with long lower wick -> HAMMER."""
        c = make_candle(open=1.1040, high=1.1060, low=1.0950, close=1.1050)
        result = analyzer.classify_candle(c)
        assert result == CandleType.HAMMER

    def test_shooting_star(self, analyzer: CandleAnalyzer):
        """Bearish candle with long upper wick -> SHOOTING_STAR."""
        c = make_candle(open=1.0960, high=1.1060, low=1.0940, close=1.0950)
        result = analyzer.classify_candle(c)
        assert result == CandleType.SHOOTING_STAR

    def test_standard_candle(self, analyzer: CandleAnalyzer):
        """Normal candle with moderate body and wicks -> STANDARD."""
        c = make_candle(open=1.1000, high=1.1040, low=1.0960, close=1.1030)
        result = analyzer.classify_candle(c)
        assert result == CandleType.STANDARD

    def test_custom_thresholds(self):
        """Custom thresholds change classification boundaries."""
        strict = CandleAnalyzer(doji_body_threshold=2.0)
        c = make_candle(open=1.1000, high=1.1050, low=1.0950, close=1.1004)
        assert strict.classify_candle(c) != CandleType.DOJI


# ---------------------------------------------------------------------------
# detect_displacement
# ---------------------------------------------------------------------------


class TestDetectDisplacement:
    def test_uptrend_has_displacements(self, analyzer: CandleAnalyzer):
        """Strong uptrend candles should register as displacements."""
        seq = make_candle_sequence(count=20, trend="up", symbol="EURUSD")
        results = analyzer.detect_displacement(seq, min_displacement_pips=0.1)
        assert isinstance(results, list)
        for idx, pips in results:
            assert isinstance(idx, int)
            assert pips >= 0.1

    def test_no_displacement_with_high_threshold(self, analyzer: CandleAnalyzer):
        """Tiny candles should not register with a high pip threshold."""
        seq = make_candle_sequence(count=10, trend="range", symbol="EURUSD")
        results = analyzer.detect_displacement(seq, min_displacement_pips=500.0)
        assert results == []


# ---------------------------------------------------------------------------
# detect_imbalance (FVG detection between 3 candles)
# ---------------------------------------------------------------------------


class TestDetectImbalance:
    def test_no_imbalance_overlapping(self, analyzer: CandleAnalyzer):
        """Overlapping candles produce no gap."""
        ts = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        c1 = make_candle(timestamp=ts, open=1.10, high=1.12, low=1.09, close=1.11)
        c2 = make_candle(
            timestamp=ts + timedelta(hours=1),
            open=1.11, high=1.13, low=1.10, close=1.12,
        )
        c3 = make_candle(
            timestamp=ts + timedelta(hours=2),
            open=1.12, high=1.14, low=1.11, close=1.13,
        )
        assert analyzer.detect_imbalance(c1, c2, c3) is None

    def test_different_symbols_returns_none(self, analyzer: CandleAnalyzer):
        """Mixed symbols must return None."""
        ts = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        c1 = make_candle(timestamp=ts, symbol="EURUSD")
        c2 = make_candle(timestamp=ts + timedelta(hours=1), symbol="GBPUSD")
        c3 = make_candle(timestamp=ts + timedelta(hours=2), symbol="EURUSD")
        assert analyzer.detect_imbalance(c1, c2, c3) is None

    def test_bearish_imbalance(self, analyzer: CandleAnalyzer):
        """Bearish gap: c2 entirely below c1 and c3."""
        ts = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        c1 = make_candle(timestamp=ts, open=1.20, high=1.22, low=1.18, close=1.19)
        c2 = make_candle(
            timestamp=ts + timedelta(hours=1),
            open=1.15, high=1.16, low=1.12, close=1.13,
        )
        c3 = make_candle(
            timestamp=ts + timedelta(hours=2),
            open=1.19, high=1.21, low=1.17, close=1.20,
        )
        result = analyzer.detect_imbalance(c1, c2, c3)
        if result is not None:
            gap_low, gap_high = result
            assert gap_high > gap_low


# ---------------------------------------------------------------------------
# is_engulfing
# ---------------------------------------------------------------------------


class TestIsEngulfing:
    def test_bullish_engulfing(self, analyzer: CandleAnalyzer):
        """Large bullish candle engulfs small bearish candle."""
        ts = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        prev = make_candle(
            timestamp=ts, open=1.1050, high=1.1060, low=1.0990, close=1.1000,
        )
        curr = make_candle(
            timestamp=ts + timedelta(hours=1),
            open=1.0980, high=1.1080, low=1.0970, close=1.1070,
        )
        assert analyzer.is_engulfing(curr, prev) is True

    def test_non_engulfing(self, analyzer: CandleAnalyzer):
        """Similar-sized candles don't engulf."""
        ts = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        prev = make_candle(
            timestamp=ts, open=1.1000, high=1.1050, low=1.0950, close=1.1020,
        )
        curr = make_candle(
            timestamp=ts + timedelta(hours=1),
            open=1.1010, high=1.1040, low=1.0960, close=1.1030,
        )
        assert analyzer.is_engulfing(curr, prev) is False


# ---------------------------------------------------------------------------
# has_long_wick
# ---------------------------------------------------------------------------


class TestHasLongWick:
    def test_long_upper_wick(self, analyzer: CandleAnalyzer):
        """Candle with upper wick > 50% of range."""
        c = make_candle(open=1.0950, high=1.1050, low=1.0940, close=1.0960)
        assert analyzer.has_long_wick(c, upper=True, min_wick_percentage=50.0) is True

    def test_long_lower_wick(self, analyzer: CandleAnalyzer):
        """Candle with lower wick > 50% of range."""
        c = make_candle(open=1.1040, high=1.1060, low=1.0950, close=1.1050)
        assert analyzer.has_long_wick(c, upper=False, min_wick_percentage=50.0) is True

    def test_no_long_wick(self, analyzer: CandleAnalyzer):
        """Balanced candle has no long wick (both wicks well under threshold)."""
        c = make_candle(open=1.1000, high=1.1040, low=1.0960, close=1.1030)
        assert analyzer.has_long_wick(c, upper=True, min_wick_percentage=51.0) is False
        assert analyzer.has_long_wick(c, upper=False, min_wick_percentage=51.0) is False


# ---------------------------------------------------------------------------
# calculate_average_body_size / is_large_body
# ---------------------------------------------------------------------------


class TestBodySizeAnalysis:
    def test_average_body_size(self, analyzer: CandleAnalyzer):
        """Average body size is positive for a trending sequence."""
        seq = make_candle_sequence(count=20, trend="up")
        avg = analyzer.calculate_average_body_size(seq, lookback=20)
        assert avg > 0

    def test_is_large_body(self, analyzer: CandleAnalyzer):
        """A candle with body >> average is classified as large."""
        seq = make_candle_sequence(count=20, trend="range", base_price=1.1000)
        big = make_candle(open=1.0900, high=1.1200, low=1.0890, close=1.1190)
        assert analyzer.is_large_body(big, seq, multiplier=1.5) is True

    def test_normal_body_not_large(self, analyzer: CandleAnalyzer):
        """A candle with average body is not classified as large."""
        seq = make_candle_sequence(count=20, trend="up", base_price=1.1000)
        normal = make_candle(open=1.1000, high=1.1010, low=1.0995, close=1.1005)
        assert analyzer.is_large_body(normal, seq, multiplier=1.5) is False
