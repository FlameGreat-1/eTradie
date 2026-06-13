from typing import Any, ClassVar

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import is_within_tolerance
from engine.ta.constants import Timeframe
from engine.ta.models.candle import CandleSequence
from engine.ta.models.swing import SwingHigh, SwingLow

logger = get_logger(__name__)


class SwingAnalyzer:
    # Timeframe-adaptive bar requirements for higher timeframes.
    #
    # HTFs (D1, W1, MN1) naturally have far fewer candles per
    # lookback window (30-60 candles vs 300-1500 on LTF).  Using
    # the default left_bars=5 / right_bars=5 on these timeframes
    # causes two critical data quality problems:
    #
    #   1. The last `right_bars` candles can NEVER be swing points,
    #      which means recent swing structure in the final 5 candles
    #      is invisible -- exactly where the most actionable data is.
    #
    #   2. During impulsive V-shaped recoveries or corrections where
    #      every candle makes a new high/low, intermediate swing
    #      points never satisfy the right-side confirmation check
    #      because the next candle immediately exceeds them.
    #
    # These reduced values ensure intermediate swing structure is
    # captured -- enabling BMS, CHoCH, SMS, and trend direction to
    # accurately reflect recent price action on higher timeframes.
    #
    # LTF timeframes (M1-H4) are NOT affected and retain the
    # original left_bars=5 / right_bars=5 defaults.
    _HTF_BAR_OVERRIDES: ClassVar[dict[Timeframe, tuple[int, int]]] = {
        Timeframe.D1: (3, 3),
        Timeframe.W1: (2, 2),
        Timeframe.MN1: (2, 1),
    }

    def __init__(
        self,
        *,
        left_bars: int = 5,
        right_bars: int = 5,
        equal_tolerance_pips: float = 2.0,
    ) -> None:
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.equal_tolerance_pips = equal_tolerance_pips

    def _get_effective_bars(
        self,
        sequence: CandleSequence,
    ) -> tuple[int, int]:
        """Return (left_bars, right_bars) adapted for the sequence's timeframe.

        For HTF timeframes (D1, W1, MN1) where candle counts are
        naturally low (30-60), the default left_bars=5 / right_bars=5
        prevents detection of intermediate swing structure during
        impulsive recovery or correction phases.  This method returns
        reduced bar requirements for those timeframes while preserving
        the original defaults for all LTF timeframes (M1-H4).

        Returns:
            Tuple of (effective_left_bars, effective_right_bars).
        """
        override = self._HTF_BAR_OVERRIDES.get(sequence.timeframe)
        if override is not None:
            return override
        return (self.left_bars, self.right_bars)

    def detect_swing_highs(
        self,
        sequence: CandleSequence,
    ) -> list[SwingHigh]:
        swing_highs = []
        candles = sequence.candles
        effective_left, effective_right = self._get_effective_bars(sequence)

        for i in range(effective_left, len(candles) - effective_right):
            current = candles[i]

            is_swing_high = True

            for j in range(i - effective_left, i):
                if candles[j].high >= current.high:
                    is_swing_high = False
                    break

            if is_swing_high:
                for j in range(i + 1, i + effective_right + 1):
                    if candles[j].high >= current.high:
                        is_swing_high = False
                        break

            if is_swing_high:
                is_equal = self._check_equal_high(
                    current.high,
                    swing_highs,
                    current.symbol,
                )

                swing_high = SwingHigh(
                    symbol=current.symbol,
                    timeframe=current.timeframe,
                    timestamp=current.timestamp,
                    price=current.high,
                    index=i,
                    strength=self._calculate_strength(candles, i, is_high=True),
                    left_bars=effective_left,
                    right_bars=effective_right,
                    is_equal_high=is_equal,
                    equal_high_tolerance_pips=(self.equal_tolerance_pips if is_equal else None),
                )

                swing_highs.append(swing_high)

        return swing_highs

    def detect_swing_lows(
        self,
        sequence: CandleSequence,
    ) -> list[SwingLow]:
        swing_lows = []
        candles = sequence.candles
        effective_left, effective_right = self._get_effective_bars(sequence)

        for i in range(effective_left, len(candles) - effective_right):
            current = candles[i]

            is_swing_low = True

            for j in range(i - effective_left, i):
                if candles[j].low <= current.low:
                    is_swing_low = False
                    break

            if is_swing_low:
                for j in range(i + 1, i + effective_right + 1):
                    if candles[j].low <= current.low:
                        is_swing_low = False
                        break

            if is_swing_low:
                is_equal = self._check_equal_low(
                    current.low,
                    swing_lows,
                    current.symbol,
                )

                swing_low = SwingLow(
                    symbol=current.symbol,
                    timeframe=current.timeframe,
                    timestamp=current.timestamp,
                    price=current.low,
                    index=i,
                    strength=self._calculate_strength(candles, i, is_high=False),
                    left_bars=effective_left,
                    right_bars=effective_right,
                    is_equal_low=is_equal,
                    equal_low_tolerance_pips=(self.equal_tolerance_pips if is_equal else None),
                )

                swing_lows.append(swing_low)

        return swing_lows

    def _calculate_strength(
        self,
        candles: list[Any],
        index: int,
        is_high: bool,
    ) -> int:
        """Calculate swing strength based on an unbroken streak of dominance.

        Instead of a fixed window, this measures how far away the nearest
        candle is that exceeds the swing point in BOTH directions.

        - Internal swings hit higher/lower candles very quickly (e.g., bounded
          by the parent swing point in a pullback).
        - Major structural pivots remain dominant for long stretches (40+ candles).
        """
        current = candles[index]

        left_count = 0
        for i in range(index - 1, -1, -1):
            if is_high and candles[i].high <= current.high or not is_high and candles[i].low >= current.low:
                left_count += 1
            else:
                break

        right_count = 0
        for i in range(index + 1, len(candles)):
            if is_high and candles[i].high <= current.high or not is_high and candles[i].low >= current.low:
                right_count += 1
            else:
                break

        total_dominated = left_count + right_count

        if total_dominated < 14:
            return 3  # Extremely minor
        if total_dominated < 20:
            return 5  # Minor internal
        if total_dominated < 30:
            return 7  # Intermediate
        if total_dominated < 40:
            return 8  # Standard structural (CHOCH max cutoff)
        if total_dominated < 50:
            return 9  # Strong structural
        return 10  # Major macro structural pivot

    def _check_equal_high(
        self,
        price: float,
        existing_highs: list[SwingHigh],
        symbol: str,
    ) -> bool:
        if not existing_highs:
            return False

        recent_highs = existing_highs[-5:] if len(existing_highs) > 5 else existing_highs

        for swing_high in recent_highs:
            if is_within_tolerance(
                price,
                swing_high.price,
                self.equal_tolerance_pips,
                symbol,
            ):
                return True

        return False

    def _check_equal_low(
        self,
        price: float,
        existing_lows: list[SwingLow],
        symbol: str,
    ) -> bool:
        if not existing_lows:
            return False

        recent_lows = existing_lows[-5:] if len(existing_lows) > 5 else existing_lows

        for swing_low in recent_lows:
            if is_within_tolerance(
                price,
                swing_low.price,
                self.equal_tolerance_pips,
                symbol,
            ):
                return True

        return False

    def get_latest_swing_high(
        self,
        swing_highs: list[SwingHigh],
    ) -> SwingHigh | None:
        if not swing_highs:
            return None
        return max(swing_highs, key=lambda x: x.timestamp)

    def get_latest_swing_low(
        self,
        swing_lows: list[SwingLow],
    ) -> SwingLow | None:
        if not swing_lows:
            return None
        return max(swing_lows, key=lambda x: x.timestamp)

    def get_highest_swing_high(
        self,
        swing_highs: list[SwingHigh],
    ) -> SwingHigh | None:
        if not swing_highs:
            return None
        return max(swing_highs, key=lambda x: x.price)

    def get_lowest_swing_low(
        self,
        swing_lows: list[SwingLow],
    ) -> SwingLow | None:
        if not swing_lows:
            return None
        return min(swing_lows, key=lambda x: x.price)
