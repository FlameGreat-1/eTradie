"""Tests for FibonacciAnalyzer (retracement levels, OTE zone, price zones).

Production module: src/engine/ta/common/analyzers/fibonacci.py
"""

from datetime import UTC, datetime

import pytest

from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.constants import (
    FibonacciLevel,
    PriceZone,
    Timeframe,
)
from engine.ta.models.fibonacci import FibonacciRetracement, PremiumDiscountZone
from engine.ta.models.swing import SwingHigh, SwingLow


@pytest.fixture
def analyzer() -> FibonacciAnalyzer:
    return FibonacciAnalyzer()


@pytest.fixture
def swing_high() -> SwingHigh:
    return SwingHigh(
        symbol="EURUSD",
        timeframe=Timeframe.H4,
        timestamp=datetime(2024, 6, 15, 12, 0, tzinfo=UTC),
        price=2.0000,
        index=50,
        strength=5,
        left_bars=5,
        right_bars=5,
    )


@pytest.fixture
def swing_low() -> SwingLow:
    return SwingLow(
        symbol="EURUSD",
        timeframe=Timeframe.H4,
        timestamp=datetime(2024, 6, 10, 8, 0, tzinfo=UTC),
        price=1.0000,
        index=30,
        strength=4,
        left_bars=5,
        right_bars=5,
    )


@pytest.fixture
def bullish_retracement(swing_high, swing_low) -> FibonacciRetracement:
    return FibonacciRetracement(
        symbol="EURUSD",
        timeframe=Timeframe.H4,
        swing_high=swing_high.price,
        swing_low=swing_low.price,
        swing_high_timestamp=swing_high.timestamp,
        swing_low_timestamp=swing_low.timestamp,
        is_bullish=True,
    )


@pytest.fixture
def bearish_retracement(swing_high, swing_low) -> FibonacciRetracement:
    return FibonacciRetracement(
        symbol="EURUSD",
        timeframe=Timeframe.H4,
        swing_high=swing_high.price,
        swing_low=swing_low.price,
        swing_high_timestamp=swing_high.timestamp,
        swing_low_timestamp=swing_low.timestamp,
        is_bullish=False,
    )


# ---------------------------------------------------------------------------
# create_retracement
# ---------------------------------------------------------------------------


class TestCreateRetracement:
    def test_builds_from_swing_points(self, analyzer, swing_high, swing_low):
        """create_retracement produces a valid FibonacciRetracement."""
        ret = analyzer.create_retracement(swing_high, swing_low, is_bullish=True)
        assert isinstance(ret, FibonacciRetracement)
        assert ret.symbol == "EURUSD"
        assert ret.timeframe == Timeframe.H4
        assert ret.swing_high == 2.0000
        assert ret.swing_low == 1.0000
        assert ret.is_bullish is True
        assert ret.range_size == 1.0

    def test_bearish_retracement(self, analyzer, swing_high, swing_low):
        ret = analyzer.create_retracement(swing_high, swing_low, is_bullish=False)
        assert ret.is_bullish is False


# ---------------------------------------------------------------------------
# calculate_level_price
# ---------------------------------------------------------------------------


class TestCalculateLevelPrice:
    def test_bullish_levels(self, analyzer):
        """Bullish retracement: levels measured up from swing low."""
        high, low = 2.0000, 1.0000

        # SMC convention: bullish level = swing_high - range*fib.
        assert analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_0, True) == 2.0000
        assert analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_50, True) == 1.5000
        assert round(analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_618, True), 4) == 1.3820
        assert round(analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_786, True), 4) == 1.2140
        assert analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_100, True) == 1.0000

    def test_bearish_levels(self, analyzer):
        """Bearish retracement: levels measured down from swing high."""
        high, low = 2.0000, 1.0000

        # SMC convention: bearish level = swing_low + range*fib.
        assert analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_0, False) == 1.0000
        assert analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_50, False) == 1.5000
        assert round(analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_618, False), 4) == 1.6180
        assert round(analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_786, False), 4) == 1.7860
        assert analyzer.calculate_level_price(high, low, FibonacciLevel.LEVEL_100, False) == 2.0000


# ---------------------------------------------------------------------------
# get_ote_zone
# ---------------------------------------------------------------------------


class TestGetOTEZone:
    def test_bullish_ote_zone(self, analyzer, bullish_retracement):
        """Bullish OTE zone is between 61.8% and 78.6% retracement (discount)."""
        zone = analyzer.get_ote_zone(bullish_retracement)
        assert isinstance(zone, PremiumDiscountZone)
        assert zone.zone_type == PriceZone.DISCOUNT
        # SMC bullish: 0.786 level (1.214) is the lower bound, 0.618
        # level (1.382) is the upper bound (price retraced DOWN from 2.0).
        assert round(zone.lower_bound, 4) == 1.2140
        assert round(zone.upper_bound, 4) == 1.3820

    def test_bearish_ote_zone(self, analyzer, bearish_retracement):
        """Bearish OTE zone is between 61.8% and 78.6% retracement (premium)."""
        zone = analyzer.get_ote_zone(bearish_retracement)
        assert isinstance(zone, PremiumDiscountZone)
        assert zone.zone_type == PriceZone.PREMIUM
        # SMC bearish: 0.618 level (1.618) is the lower bound, 0.786
        # level (1.786) is the upper bound (price retraced UP from 1.0).
        assert round(zone.lower_bound, 4) == 1.6180
        assert round(zone.upper_bound, 4) == 1.7860


# ---------------------------------------------------------------------------
# is_at_ote
# ---------------------------------------------------------------------------


class TestIsAtOTE:
    def test_price_inside_ote(self, analyzer, bullish_retracement):
        """Price within the bullish OTE band [1.214, 1.382] returns True."""
        assert analyzer.is_at_ote(1.3000, bullish_retracement) is True

    def test_price_outside_ote(self, analyzer, bullish_retracement):
        """Price far above the bullish OTE band returns False."""
        assert analyzer.is_at_ote(1.7000, bullish_retracement) is False

    def test_price_at_ote_boundary_with_tolerance(self, analyzer, bullish_retracement):
        """Price just outside the OTE lower bound but within pip tolerance."""
        # Bullish OTE lower bound is ~1.2140; tolerance 5 pips = 0.0005
        # for EURUSD, so 1.2136 (4 pips below) is still inside.
        assert analyzer.is_at_ote(1.2136, bullish_retracement, tolerance_pips=5.0) is True


# ---------------------------------------------------------------------------
# Zone classification (premium / discount / equilibrium)
# ---------------------------------------------------------------------------


class TestZoneClassification:
    def test_premium_zone(self, analyzer, bullish_retracement):
        """Price above 50% is premium for bullish retracement."""
        assert analyzer.is_at_premium(1.8000, bullish_retracement) is True
        assert analyzer.is_at_discount(1.8000, bullish_retracement) is False

    def test_discount_zone(self, analyzer, bullish_retracement):
        """Price below 50% is discount for bullish retracement."""
        assert analyzer.is_at_discount(1.2000, bullish_retracement) is True
        assert analyzer.is_at_premium(1.2000, bullish_retracement) is False

    def test_equilibrium_zone(self, analyzer, bullish_retracement):
        """Price at 50% level is equilibrium."""
        assert analyzer.is_at_equilibrium(1.5000, bullish_retracement) is True


# ---------------------------------------------------------------------------
# get_nearest_fib_level
# ---------------------------------------------------------------------------


class TestGetNearestFibLevel:
    def test_nearest_to_50(self, analyzer, bullish_retracement):
        """Price at 1.5000 is nearest to 50% level."""
        level = analyzer.get_nearest_fib_level(1.5000, bullish_retracement)
        assert level == FibonacciLevel.LEVEL_50

    def test_nearest_to_618(self, analyzer, bullish_retracement):
        """SMC bullish 61.8% level sits at 1.382; price 1.3800 is nearest it."""
        level = analyzer.get_nearest_fib_level(1.3800, bullish_retracement)
        assert level == FibonacciLevel.LEVEL_618

    def test_nearest_to_0(self, analyzer, bullish_retracement):
        """SMC bullish 0.0 level is the swing high (2.0); 1.9900 is nearest it."""
        level = analyzer.get_nearest_fib_level(1.9900, bullish_retracement)
        assert level == FibonacciLevel.LEVEL_0


# ---------------------------------------------------------------------------
# calculate_retracement_percentage
# ---------------------------------------------------------------------------


class TestRetracementPercentage:
    def test_50_percent_retracement(self, analyzer):
        pct = analyzer.calculate_retracement_percentage(1.5000, 2.0000, 1.0000)
        assert pct == 50.0

    def test_full_retracement(self, analyzer):
        pct = analyzer.calculate_retracement_percentage(2.0000, 2.0000, 1.0000)
        assert pct == 100.0

    def test_no_retracement(self, analyzer):
        pct = analyzer.calculate_retracement_percentage(1.0000, 2.0000, 1.0000)
        assert pct == 0.0

    def test_zero_range(self, analyzer):
        pct = analyzer.calculate_retracement_percentage(1.5000, 1.5000, 1.5000)
        assert pct == 0.0


# ---------------------------------------------------------------------------
# get_all_ote_levels
# ---------------------------------------------------------------------------


class TestOTELevels:
    def test_returns_three_ote_levels(self, analyzer):
        # OTE_LEVELS = [0.618, 0.705, 0.786]. 50% is equilibrium (not OTE)
        # and 78.6% is the level (not 79%).
        levels = analyzer.get_all_ote_levels()
        assert len(levels) == 3
        assert FibonacciLevel.LEVEL_618 in levels
        assert FibonacciLevel.LEVEL_705 in levels
        assert FibonacciLevel.LEVEL_786 in levels
        assert FibonacciLevel.LEVEL_50 not in levels
        assert FibonacciLevel.LEVEL_79 not in levels
