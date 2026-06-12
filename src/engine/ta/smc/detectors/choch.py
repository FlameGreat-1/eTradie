from engine.shared.logging import get_logger
from engine.ta.constants import Direction, Timeframe
from engine.ta.models.candle import CandleSequence
from engine.ta.models.structure_event import ChangeOfCharacter
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class CHOCHDetector:
    """
    Detects Change of Character (CHOCH) events.

    CHOCH is the initial signal of a shift in order flow -- earlier and
    smaller than BMS.

    CHOCH occurs when price breaks an **opposing internal** swing point:
    - Bullish CHOCH: Price closes above a minor/internal swing **high**
      that is NOT a major structural pivot.  In a downtrend this is the
      first sign of buyer strength -- the internal highs are being broken.
    - Bearish CHOCH: Price closes below a minor/internal swing **low**
      that is NOT a major structural pivot.  In an uptrend this is the
      first sign of seller strength -- the internal lows are being broken.

    Swing strength filtering:
      The SwingAnalyzer calculates strength by counting how many of the
      previous N candles are below/above the swing point (capped at 10).
      With left_bars=5 and right_bars=5, most swing points naturally
      reach strength 8-10.  Only the very strongest structural pivots
      (strength 9-10) are excluded from CHOCH detection.  Swing points
      with strength <= choch_max_swing_strength (default 8) are valid
      internal/minor swings for CHOCH purposes.

    Confirmation requires dynamic consecutive candle closes based on the
    timeframe, so higher timeframes require more closes to avoid fakeouts:
        - M1, M5   -> 1 candle close (aggressive LTF)
        - M15, M30 -> 2 candle closes
        - H1+      -> 3 candle closes

    Sequence: CHOCH appears first -> BMS confirms -> entry on RTO to OB.
    """

    # Default max swing strength for CHOCH candidates.  Swing points
    # with strength ABOVE this value are considered major structural
    # pivots and are excluded -- only internal/minor swings qualify.
    DEFAULT_CHOCH_MAX_SWING_STRENGTH = 8

    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._choch_max_strength = getattr(config, "choch_max_swing_strength", self.DEFAULT_CHOCH_MAX_SWING_STRENGTH)
        self._logger = get_logger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_bullish_choch(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[ChangeOfCharacter]:
        """
        Bullish CHOCH: price breaks above a minor/internal swing HIGH.

        In a downtrend (LL, LH, LL, LH ...), when price closes above one
        of the recent internal swing highs, it signals that selling
        pressure is fading -- the first "change of character."
        """
        choch_events: list[ChangeOfCharacter] = []

        if not swing_highs:
            return choch_events

        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)
        candles = sequence.candles

        required_closes = self._get_required_confirmations(sequence.timeframe)

        for sh in sorted_highs:
            # Only use internal/minor swing highs -- exclude the strongest
            # structural pivots which represent major swing points, not
            # the internal structure breaks that CHOCH targets.
            if sh.strength > self._choch_max_strength:
                continue

            level = sh.price
            break_start = sh.index + 1

            if break_start >= len(candles):
                continue

            # Scan forward for the first candle that closes above the internal swing high.
            first_break_idx: int | None = None
            for j in range(break_start, len(candles)):
                if candles[j].close > level:
                    first_break_idx = j
                    break

            if first_break_idx is None:
                continue

            breakout_candle = candles[first_break_idx]

            # Count consecutive candle closes above the internal level
            confirmed_count = 0
            for k in range(first_break_idx, len(candles)):
                if candles[k].close > level:
                    confirmed_count += 1
                else:
                    break

                if confirmed_count >= required_closes:
                    break

            if confirmed_count < required_closes:
                continue

            # CHOCH confirmed
            confirm_candle_idx = first_break_idx + required_closes - 1
            if confirm_candle_idx >= len(candles):
                confirm_candle_idx = len(candles) - 1
            confirm_candle = candles[confirm_candle_idx]

            choch = ChangeOfCharacter(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=confirm_candle.timestamp,
                direction=Direction.BULLISH,
                broken_level=level,
                broken_level_timestamp=sh.timestamp,
                breakout_price=breakout_candle.close,
                candle_index=first_break_idx,
                is_minor=sh.strength <= 5,
            )

            choch_events.append(choch)

            self._logger.debug(
                "bullish_choch_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "broken_level": level,
                    "breakout_price": breakout_candle.close,
                    "swing_strength": sh.strength,
                    "max_strength_threshold": self._choch_max_strength,
                    "confirm_candles_required": required_closes,
                },
            )

        return choch_events

    def detect_bearish_choch(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[ChangeOfCharacter]:
        """
        Bearish CHOCH: price breaks below a minor/internal swing LOW.

        In an uptrend (HH, HL, HH, HL ...), when price closes below one
        of the recent internal swing lows, it signals that buying
        pressure is fading -- the first "change of character."
        """
        choch_events: list[ChangeOfCharacter] = []

        if not swing_lows:
            return choch_events

        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)
        candles = sequence.candles

        required_closes = self._get_required_confirmations(sequence.timeframe)

        for sl in sorted_lows:
            # Only use internal/minor swing lows -- exclude the strongest
            # structural pivots which represent major swing points, not
            # the internal structure breaks that CHOCH targets.
            if sl.strength > self._choch_max_strength:
                continue

            level = sl.price
            break_start = sl.index + 1

            if break_start >= len(candles):
                continue

            # Scan forward for the first candle that closes below the internal swing low.
            first_break_idx: int | None = None
            for j in range(break_start, len(candles)):
                if candles[j].close < level:
                    first_break_idx = j
                    break

            if first_break_idx is None:
                continue

            breakout_candle = candles[first_break_idx]

            # Count consecutive candle closes below the internal level
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

            # CHOCH confirmed
            confirm_candle_idx = first_break_idx + required_closes - 1
            if confirm_candle_idx >= len(candles):
                confirm_candle_idx = len(candles) - 1
            confirm_candle = candles[confirm_candle_idx]

            choch = ChangeOfCharacter(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=confirm_candle.timestamp,
                direction=Direction.BEARISH,
                broken_level=level,
                broken_level_timestamp=sl.timestamp,
                breakout_price=breakout_candle.close,
                candle_index=first_break_idx,
                is_minor=sl.strength <= 5,
            )

            choch_events.append(choch)

            self._logger.debug(
                "bearish_choch_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "broken_level": level,
                    "breakout_price": breakout_candle.close,
                    "swing_strength": sl.strength,
                    "max_strength_threshold": self._choch_max_strength,
                    "confirm_candles_required": required_closes,
                },
            )

        return choch_events

    def get_latest_choch(
        self,
        choch_events: list[ChangeOfCharacter],
    ) -> ChangeOfCharacter | None:
        if not choch_events:
            return None
        return max(choch_events, key=lambda x: x.timestamp)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _get_required_confirmations(timeframe: Timeframe) -> int:
        """
        Dynamically scale the required candle closes for CHOCH confirmation
        based on the timeframe. Higher timeframes require more closes to
        prevent getting faked out by a single wicky candle.
        """
        if timeframe in [Timeframe.M1, Timeframe.M5]:
            return 1
        if timeframe in [Timeframe.M15, Timeframe.M30]:
            return 2
        return 3
