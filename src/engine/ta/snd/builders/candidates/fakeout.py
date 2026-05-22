from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, CandidatePattern
from engine.ta.models.candidate import SnDCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.snd.builders.levels import compute_trade_levels
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detectors.fakeouts import FakeoutTest
from engine.ta.snd.detectors.previous_levels import PreviousHighsLows
from engine.ta.snd.validators.marubozu.validator import MarubozuValidator
from engine.ta.constants import Direction, CandidatePattern, OTE_LEVELS, FIBONACCI_VALUES

from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator
import datetime

logger = get_logger(__name__)

class FakeoutCandidateBuilder:
    """
    Builds fakeout-driven SnD candidates.

    Fakeout patterns are the foundation of SnD trading:
    - Fakeout King: Multiple fakeout tests (R1, R2, R3, R4 or S1, S2, S3, S4)
    - S.O.P: Previous Highs/Lows + Supply/Demand Zone + Fakeout
    - Triple Fakeout: 3+ fakeout tests at same zone (highest confluence)

    Requirements:
    - Minimum 1 fakeout test (Universal Rule 7)
    - More tests = stronger zone (Universal Rule 8)
    - Compression inside fakeout zone (Universal Rule 5)
    - Fakeout broken by Marubozu (Universal Rule 7)
    - Decision Point identified on LTF
    - Fibonacci alignment (optional but 90% probability)
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

    def build_fakeout_king_short(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        sr_flip_level: float,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: Optional[int],
        previous_highs: Optional[PreviousHighsLows],
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SnDCandidate]:
        if len(fakeout_tests) < self.config.min_fakeout_tests:
            return None

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BEARISH,
            sr_flip_level,
            retracement,
        )

        confluences = self._count_fakeout_confluences(
            fakeout_tests,
            previous_highs,
            retracement,
            sr_flip_level,
        )

        # Universal Rule 1: Validate Marubozu on breakout candle
        marubozu_valid, marubozu_ts = self._validate_marubozu(
            ltf_sequence, breakout_candle_index, Direction.BEARISH
        )
        
        # Fakeout-king entries sit at the SR flip; the flip level is the
        # SL anchor (no separate structural extreme).
        levels = compute_trade_levels(
            symbol=ltf_sequence.symbol,
            direction=Direction.BEARISH,
            entry_price=sr_flip_level,
            structural_extreme=None,
            sl_buffer_pips=self.config.previous_level_tolerance_pips,
            logger_event_prefix="fakeout_king_short",
        )
        if levels is None:
            return None

        entry_price = levels.entry_price
        stop_loss = levels.stop_loss
        take_profit = levels.take_profit

        pattern = (
            CandidatePattern.FAKEOUT_KING
            if len(fakeout_tests) >= 3
            else CandidatePattern.SOP
        )

        candidate = SnDCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=pattern,
            direction=Direction.BEARISH,
            timestamp=ltf_sequence.candles[-1].timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=htf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
            sr_flip_detected=True,
            sr_flip_price=sr_flip_level,
            fakeout_detected=len(fakeout_tests) > 0,
            fakeout_level=fakeout_tests[-1].level if fakeout_tests else None,
            fakeout_timestamp=fakeout_tests[-1].timestamp if fakeout_tests else None,
            compression_detected=self._check_compression(
                ltf_sequence, fakeout_tests,
            ),
            marubozu_detected=marubozu_valid,
            marubozu_timestamp=marubozu_ts,
            previous_highs_count=previous_highs.touch_count if previous_highs else 0,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            fib_level=(
                self._get_fib_level(entry_price, retracement) if retracement else None
            ),
            metadata={
                "confluences": confluences,
                "pattern_type": "fakeout_king" if len(fakeout_tests) >= 3 else "sop",
            },
        )

        self._logger.info(
            "fakeout_king_short_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "fakeout_count": len(fakeout_tests),
                "confluences": confluences,
            },
        )

        return candidate

    def build_fakeout_king_long(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        rs_flip_level: float,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: Optional[int],
        previous_lows: Optional[PreviousHighsLows],
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SnDCandidate]:
        if len(fakeout_tests) < self.config.min_fakeout_tests:
            return None

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BULLISH,
            rs_flip_level,
            retracement,
        )

        confluences = self._count_fakeout_confluences(
            fakeout_tests,
            previous_lows,
            retracement,
            rs_flip_level,
        )

        # Universal Rule 1: Validate Marubozu on breakout candle
        marubozu_valid, marubozu_ts = self._validate_marubozu(
            ltf_sequence, breakout_candle_index, Direction.BULLISH
        )

        # Fakeout-king entries sit at the RS flip; the flip level is the
        # SL anchor (no separate structural extreme).
        levels = compute_trade_levels(
            symbol=ltf_sequence.symbol,
            direction=Direction.BULLISH,
            entry_price=rs_flip_level,
            structural_extreme=None,
            sl_buffer_pips=self.config.previous_level_tolerance_pips,
            logger_event_prefix="fakeout_king_long",
        )
        if levels is None:
            return None

        entry_price = levels.entry_price
        stop_loss = levels.stop_loss
        take_profit = levels.take_profit

        pattern = (
            CandidatePattern.FAKEOUT_KING
            if len(fakeout_tests) >= 3
            else CandidatePattern.SOP
        )

        candidate = SnDCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=pattern,
            direction=Direction.BULLISH,
            timestamp=ltf_sequence.candles[-1].timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=htf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
            rs_flip_detected=True,
            rs_flip_price=rs_flip_level,
            fakeout_detected=len(fakeout_tests) > 0,
            fakeout_level=fakeout_tests[-1].level if fakeout_tests else None,
            fakeout_timestamp=fakeout_tests[-1].timestamp if fakeout_tests else None,
            compression_detected=self._check_compression(
                ltf_sequence, fakeout_tests,
            ),
            marubozu_detected=marubozu_valid,
            marubozu_timestamp=marubozu_ts,
            previous_lows_count=previous_lows.touch_count if previous_lows else 0,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            fib_level=(
                self._get_fib_level(entry_price, retracement) if retracement else None
            ),
            metadata={
                "confluences": confluences,
                "pattern_type": "fakeout_king" if len(fakeout_tests) >= 3 else "sop",
            },
        )

        self._logger.info(
            "fakeout_king_long_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "fakeout_count": len(fakeout_tests),
                "confluences": confluences,
            },
        )

        return candidate

    def _count_fakeout_confluences(
        self,
        fakeout_tests: list[FakeoutTest],
        previous_levels: Optional[PreviousHighsLows],
        retracement: Optional[FibonacciRetracement],
        zone_price: float,
    ) -> int:
        confluences = 0

        confluences += len(fakeout_tests)

        if previous_levels and previous_levels.touch_count >= 2:
            confluences += previous_levels.touch_count

        if retracement:
            if self.ltf_validator.check_fibonacci_alignment(zone_price, retracement):
                confluences += 2

        if any(test.is_diamond_fakeout for test in fakeout_tests):
            confluences += 1

        return confluences

    def _check_compression(
        self,
        sequence: CandleSequence,
        fakeout_tests: list[FakeoutTest],
    ) -> bool:
        """Check if real compression exists at the fakeout zone."""
        if not fakeout_tests:
            return False
        return self.ltf_validator.validate_compression_at_zone(
            sequence, fakeout_tests,
        )

    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[str]:
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
        breakout_candle_index: Optional[int],
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
