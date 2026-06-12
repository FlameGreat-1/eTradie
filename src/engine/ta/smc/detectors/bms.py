from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import calculate_pips
from engine.ta.constants import Direction, Timeframe
from engine.ta.models.candle import CandleSequence
from engine.ta.models.structure_event import BreakInMarketStructure
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)

# Timeframe scaling factors relative to H1 (baseline = 1.0).
# Higher timeframes produce larger pip moves naturally, so thresholds
# must be scaled up.  Lower timeframes produce smaller pip moves, so
# thresholds are scaled down.
_TF_SCALE: dict[Timeframe, float] = {
    Timeframe.M1: 0.10,
    Timeframe.M5: 0.20,
    Timeframe.M15: 0.35,
    Timeframe.M30: 0.50,
    Timeframe.H1: 1.00,
    Timeframe.H3: 1.50,
    Timeframe.H4: 2.00,
    Timeframe.H6: 3.00,
    Timeframe.H8: 4.00,
    Timeframe.H12: 5.00,
    Timeframe.D1: 5.00,
    Timeframe.W1: 12.00,
    Timeframe.MN1: 25.00,
}


def _tf_scale(timeframe: Timeframe) -> float:
    """Return the pip-threshold scaling factor for *timeframe*."""
    return _TF_SCALE.get(timeframe, 1.0)


class BMSDetector:
    """
    Detects Break in Market Structure (BMS) events.

    BMS occurs when price breaks an **opposing** swing point:
    - Bullish BMS: Price closes above the previous swing **high** (HH break)
    - Bearish BMS: Price closes below the previous swing **low** (LL break)

    Confirmation requires multiple consecutive candle closes beyond the
    broken level.  The exact count depends on the displacement (momentum):
        - Strong displacement  →  2 candle closes  (high conviction)
        - Moderate displacement →  3 candle closes
        - Weak displacement    →  5 candle closes  (needs more proof)

    All pip thresholds are scaled per-timeframe: higher timeframes use
    proportionally larger thresholds; lower timeframes use smaller ones.

    Requirements (Universal Rule 2):
    - Must have displacement (minimum pips threshold, TF-scaled)
    - Must close substantially beyond the level (not just a wick)
    - Must sustain closes beyond the level for N candles
    """

    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_bullish_bms(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[BreakInMarketStructure]:
        """
        Bullish BMS: price breaks above the previous swing HIGH.

        In an uptrend (HH, HL, HH, HL …), when price rises and closes
        above the most recent swing high — creating a new HH — that is
        a bullish BMS.
        """
        bms_events: list[BreakInMarketStructure] = []

        if len(swing_highs) < 1:
            return bms_events

        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)
        candles = sequence.candles
        scale = _tf_scale(sequence.timeframe)

        min_disp = self.config.min_displacement_pips * scale
        strong_disp = self.config.bms_strong_displacement_pips * scale
        moderate_disp = self.config.bms_moderate_displacement_pips * scale
        weak_confirm = self.config.bms_weak_confirm_candles

        for sh in sorted_highs:
            level = sh.price
            break_start = sh.index + 1  # Start scanning AFTER the swing high

            if break_start >= len(candles):
                continue

            # Scan forward for the first candle that closes above the level.
            first_break_idx: int | None = None
            for j in range(break_start, len(candles)):
                if candles[j].close > level:
                    first_break_idx = j
                    break

            if first_break_idx is None:
                continue

            breakout_candle = candles[first_break_idx]

            # Calculate displacement from the broken level to the
            # breakout candle's close.
            displacement = round(
                calculate_pips(
                    level,
                    breakout_candle.close,
                    sequence.symbol,
                ),
                2,
            )

            if displacement < min_disp:
                continue

            # Determine how many consecutive closes above the level are
            # required based on the displacement (momentum).
            required_closes = self._required_confirmation_candles(
                displacement,
                strong_disp,
                moderate_disp,
                weak_confirm,
            )

            # Count consecutive candle closes above the level, starting
            # from (and including) the first breakout candle.
            confirmed_count = 0
            for k in range(first_break_idx, len(candles)):
                if candles[k].close > level:
                    confirmed_count += 1
                else:
                    break  # Streak broken — reset

                if confirmed_count >= required_closes:
                    break

            if confirmed_count < required_closes:
                continue

            # BMS confirmed.
            confirm_candle_idx = first_break_idx + required_closes - 1
            if confirm_candle_idx >= len(candles):
                confirm_candle_idx = len(candles) - 1
            confirm_candle = candles[confirm_candle_idx]

            bms = BreakInMarketStructure(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=confirm_candle.timestamp,
                direction=Direction.BULLISH,
                broken_level=level,
                broken_level_timestamp=sh.timestamp,
                breakout_price=breakout_candle.close,
                candle_index=first_break_idx,
                displacement_pips=displacement,
                confirmed=True,
            )

            bms_events.append(bms)

            self._logger.debug(
                "bullish_bms_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "broken_level": level,
                    "breakout_price": breakout_candle.close,
                    "displacement_pips": displacement,
                    "confirm_candles_required": required_closes,
                    "confirm_candles_actual": confirmed_count,
                    "tf_scale": scale,
                },
            )

        return bms_events

    def detect_bearish_bms(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[BreakInMarketStructure]:
        """
        Bearish BMS: price breaks below the previous swing LOW.

        In a downtrend (LL, LH, LL, LH …), when price drops and closes
        below the most recent swing low — creating a new LL — that is
        a bearish BMS.
        """
        bms_events: list[BreakInMarketStructure] = []

        if len(swing_lows) < 1:
            return bms_events

        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)
        candles = sequence.candles
        scale = _tf_scale(sequence.timeframe)

        min_disp = self.config.min_displacement_pips * scale
        strong_disp = self.config.bms_strong_displacement_pips * scale
        moderate_disp = self.config.bms_moderate_displacement_pips * scale
        weak_confirm = self.config.bms_weak_confirm_candles

        for sl in sorted_lows:
            level = sl.price
            break_start = sl.index + 1

            if break_start >= len(candles):
                continue

            # Scan forward for the first candle that closes below the level.
            first_break_idx: int | None = None
            for j in range(break_start, len(candles)):
                if candles[j].close < level:
                    first_break_idx = j
                    break

            if first_break_idx is None:
                continue

            breakout_candle = candles[first_break_idx]

            displacement = round(
                calculate_pips(
                    breakout_candle.close,
                    level,
                    sequence.symbol,
                ),
                2,
            )

            if displacement < min_disp:
                continue

            required_closes = self._required_confirmation_candles(
                displacement,
                strong_disp,
                moderate_disp,
                weak_confirm,
            )

            confirmed_count = 0
            for k in range(first_break_idx, len(candles)):
                if candles[k].close < level:
                    confirmed_count += 1
                else:
                    break

                if confirmed_count >= required_closes:
                    break

            if confirmed_count < required_closes:
                continue

            confirm_candle_idx = first_break_idx + required_closes - 1
            if confirm_candle_idx >= len(candles):
                confirm_candle_idx = len(candles) - 1
            confirm_candle = candles[confirm_candle_idx]

            bms = BreakInMarketStructure(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=confirm_candle.timestamp,
                direction=Direction.BEARISH,
                broken_level=level,
                broken_level_timestamp=sl.timestamp,
                breakout_price=breakout_candle.close,
                candle_index=first_break_idx,
                displacement_pips=displacement,
                confirmed=True,
            )

            bms_events.append(bms)

            self._logger.debug(
                "bearish_bms_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "broken_level": level,
                    "breakout_price": breakout_candle.close,
                    "displacement_pips": displacement,
                    "confirm_candles_required": required_closes,
                    "confirm_candles_actual": confirmed_count,
                    "tf_scale": scale,
                },
            )

        return bms_events

    def get_latest_bms(
        self,
        bms_events: list[BreakInMarketStructure],
    ) -> BreakInMarketStructure | None:
        if not bms_events:
            return None
        return max(bms_events, key=lambda x: x.timestamp)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _required_confirmation_candles(
        displacement: float,
        strong_threshold: float,
        moderate_threshold: float,
        weak_count: int,
    ) -> int:
        """
        Determine how many consecutive candle closes beyond the broken
        level are required to confirm the BMS.

        The stronger the displacement (momentum), the fewer candles are
        needed — because strong momentum is itself evidence of genuine
        institutional flow.  Weak displacement needs more candles to
        prove it is not a fakeout.

        Returns:
            2 - strong displacement  (≥ strong_threshold pips)
            3 - moderate displacement (≥ moderate_threshold pips)
            weak_count - weak displacement (below moderate threshold)
        """
        if displacement >= strong_threshold:
            return 2
        if displacement >= moderate_threshold:
            return 3
        return weak_count
