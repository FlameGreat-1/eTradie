import datetime
from typing import Any, Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import (
    FIBONACCI_VALUES,
    OTE_LEVELS,
    CandidatePattern,
    Direction,
)
from engine.ta.models.candidate import SnDCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.zone import QuasiModoLevel
from engine.ta.snd.builders.levels import compute_trade_levels
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detectors.fakeouts import FakeoutTest
from engine.ta.snd.detectors.previous_levels import PreviousHighsLows
from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator
from engine.ta.snd.validators.marubozu.validator import MarubozuValidator

logger = get_logger(__name__)


class ContinuationCandidateBuilder:
    """
    Builds continuation-style SnD candidates (where explicitly allowed).

    SnD Continuation is LIMITED and only valid when:
    - Existing trend is confirmed by multiple QM structures
    - Previous Highs/Lows show clear directional bias
    - Fakeout tests confirm trend continuation (not reversal)
    - Compression shows continuation setup (not exhaustion)

    This is NOT the same as SMC continuation patterns.
    SnD continuation requires existing QM structure + fakeout confirmation.

    Use cases:
    - Trend continuation after pullback to SR/RS Flip zone
    - Multiple QM structures in same direction
    - Fakeout tests confirm trend is intact
    """

    def __init__(
        self,
        config: SnDConfig,
        marubozu_validator: MarubozuValidator,
        ltf_validator: LTFConfirmationValidator,
        fibonacci_analyzer: FibonacciAnalyzer,
    ) -> None:
        self.config = config
        self.marubozu_validator = marubozu_validator
        self.ltf_validator = ltf_validator
        self.fibonacci_analyzer = fibonacci_analyzer
        self._logger = get_logger(__name__)

    def build_continuation_short(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        qml: QuasiModoLevel,
        sr_flip_level: float,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: int | None,
        previous_highs: PreviousHighsLows | None,
        retracement: FibonacciRetracement | None,
    ) -> SnDCandidate | None:
        """
        Build bearish continuation candidate.

        Requirements:
        - Valid QML structure
        - SR Flip zone established
        - Minimum 2 fakeout tests (confirms trend continuation)
        - Previous Highs present (confirms directional bias)
        - LTF confirmations met
        """
        if not qml.is_valid:
            return None

        if len(fakeout_tests) < 2:
            self._logger.debug(
                "continuation_short_insufficient_fakeouts",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "fakeout_count": len(fakeout_tests),
                },
            )
            return None

        if not previous_highs or previous_highs.touch_count < 2:
            self._logger.debug(
                "continuation_short_no_previous_highs",
                extra={"symbol": ltf_sequence.symbol},
            )
            return None

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BEARISH,
            qml.level,
            retracement,
        )

        confluences = self._count_continuation_confluences(
            qml,
            fakeout_tests,
            previous_highs,
            retracement,
        )

        # Universal Rule 1: Validate Marubozu on breakout candle
        marubozu_valid, marubozu_ts = self._validate_marubozu(ltf_sequence, breakout_candle_index, Direction.BEARISH)

        # Continuation entries sit at the SR flip; no separate structural
        # extreme - the flip level itself is the SL anchor.
        levels = compute_trade_levels(
            symbol=ltf_sequence.symbol,
            direction=Direction.BEARISH,
            entry_price=sr_flip_level,
            structural_extreme=None,
            sl_buffer_pips=self.config.previous_level_tolerance_pips,
            timeframe=ltf_sequence.timeframe,
            logger_event_prefix="continuation_short",
        )
        if levels is None:
            return None

        entry_price = levels.entry_price
        stop_loss = levels.stop_loss
        take_profit = levels.take_profit

        candidate = SnDCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.SND_CONTINUATION,
            direction=Direction.BEARISH,
            timestamp=ltf_sequence.candles[-1].timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=htf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
            qml_detected=True,
            qml_price=qml.level,
            qml_timestamp=qml.timestamp,
            sr_flip_detected=True,
            sr_flip_price=sr_flip_level,
            fakeout_detected=len(fakeout_tests) > 0,
            fakeout_level=fakeout_tests[-1].level if fakeout_tests else None,
            fakeout_timestamp=fakeout_tests[-1].timestamp if fakeout_tests else None,
            compression_detected=self._check_compression(
                ltf_sequence,
                fakeout_tests,
            ),
            marubozu_detected=marubozu_valid,
            marubozu_timestamp=marubozu_ts,
            previous_highs_count=previous_highs.touch_count,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(ltf_sequence.candles[-1].timestamp if ltf_confirmed else None),
            fib_level=(self._get_fib_level(entry_price, retracement) if retracement else None),
            metadata={
                "confluences": confluences,
                "pattern_type": "snd_continuation",
            },
        )

        self._logger.info(
            "continuation_short_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
            },
        )

        return candidate

    def build_continuation_long(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        qmh: QuasiModoLevel,
        rs_flip_level: float,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: int | None,
        previous_lows: PreviousHighsLows | None,
        retracement: FibonacciRetracement | None,
    ) -> SnDCandidate | None:
        """
        Build bullish continuation candidate.

        Requirements:
        - Valid QMH structure
        - RS Flip zone established
        - Minimum 2 fakeout tests (confirms trend continuation)
        - Previous Lows present (confirms directional bias)
        - LTF confirmations met
        """
        if not qmh.is_valid:
            return None

        if len(fakeout_tests) < 2:
            self._logger.debug(
                "continuation_long_insufficient_fakeouts",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "fakeout_count": len(fakeout_tests),
                },
            )
            return None

        if not previous_lows or previous_lows.touch_count < 2:
            self._logger.debug(
                "continuation_long_no_previous_lows",
                extra={"symbol": ltf_sequence.symbol},
            )
            return None

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BULLISH,
            qmh.level,
            retracement,
        )

        confluences = self._count_continuation_confluences(
            qmh,
            fakeout_tests,
            previous_lows,
            retracement,
        )

        # Universal Rule 1: Validate Marubozu on breakout candle
        marubozu_valid, marubozu_ts = self._validate_marubozu(ltf_sequence, breakout_candle_index, Direction.BULLISH)

        # Continuation entries sit at the RS flip; no separate structural
        # extreme - the flip level itself is the SL anchor.
        levels = compute_trade_levels(
            symbol=ltf_sequence.symbol,
            direction=Direction.BULLISH,
            entry_price=rs_flip_level,
            structural_extreme=None,
            sl_buffer_pips=self.config.previous_level_tolerance_pips,
            timeframe=ltf_sequence.timeframe,
            logger_event_prefix="continuation_long",
        )
        if levels is None:
            return None

        entry_price = levels.entry_price
        stop_loss = levels.stop_loss
        take_profit = levels.take_profit

        candidate = SnDCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.SND_CONTINUATION,
            direction=Direction.BULLISH,
            timestamp=ltf_sequence.candles[-1].timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=htf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
            qml_detected=True,
            qml_price=qmh.level,
            qml_timestamp=qmh.timestamp,
            rs_flip_detected=True,
            rs_flip_price=rs_flip_level,
            fakeout_detected=len(fakeout_tests) > 0,
            fakeout_level=fakeout_tests[-1].level if fakeout_tests else None,
            fakeout_timestamp=fakeout_tests[-1].timestamp if fakeout_tests else None,
            compression_detected=self._check_compression(
                ltf_sequence,
                fakeout_tests,
            ),
            marubozu_detected=marubozu_valid,
            marubozu_timestamp=marubozu_ts,
            previous_lows_count=previous_lows.touch_count,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(ltf_sequence.candles[-1].timestamp if ltf_confirmed else None),
            fib_level=(self._get_fib_level(entry_price, retracement) if retracement else None),
            metadata={
                "confluences": confluences,
                "pattern_type": "snd_continuation",
            },
        )

        self._logger.info(
            "continuation_long_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
            },
        )

        return candidate

    def _count_continuation_confluences(
        self,
        qm_level: QuasiModoLevel,
        fakeout_tests: list[FakeoutTest],
        previous_levels: PreviousHighsLows | None,
        retracement: FibonacciRetracement | None,
    ) -> int:
        confluences = 1

        confluences += len(fakeout_tests)

        if previous_levels and previous_levels.touch_count >= 2:
            confluences += previous_levels.touch_count

        if retracement and self.ltf_validator.check_fibonacci_alignment(qm_level.level, retracement):
            confluences += 2

        return confluences

    def _check_compression(
        self,
        sequence: CandleSequence,
        fakeout_tests: list[Any],
    ) -> bool:
        """Check if real compression exists at the fakeout zone."""
        if not fakeout_tests:
            return False
        return self.ltf_validator.validate_compression_at_zone(
            sequence,
            fakeout_tests,
        )

    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> str | None:
        pip_val = float(get_pip_value(retracement.symbol))
        tolerance = self.config.fibonacci_tolerance_pips * pip_val

        best_level = None
        best_distance = float("inf")

        for level in OTE_LEVELS:
            level_price = retracement.get_level_price(level)
            distance = abs(price - level_price)
            if distance <= tolerance and distance < best_distance:
                best_distance = distance
                best_level = level

        if best_level is None:
            return None

        return str(FIBONACCI_VALUES[best_level])

    def _validate_marubozu(
        self,
        sequence: CandleSequence,
        breakout_candle_index: int | None,
        direction: Direction,
    ) -> tuple[bool, Optional["datetime.datetime"]]:
        if breakout_candle_index is None or breakout_candle_index >= len(sequence.candles):
            return False, None

        candle = sequence.candles[breakout_candle_index]

        if direction == Direction.BEARISH:
            is_valid = self.marubozu_validator.validate_bearish_marubozu(candle)
        else:
            is_valid = self.marubozu_validator.validate_bullish_marubozu(candle)

        return is_valid, candle.timestamp if is_valid else None
