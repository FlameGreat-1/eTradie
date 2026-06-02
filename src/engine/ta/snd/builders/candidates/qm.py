from datetime import datetime
from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, CandidatePattern, OTE_LEVELS, FIBONACCI_VALUES
from engine.ta.models.candidate import SnDCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.zone import QuasiModoLevel, MiniPriceLevel
from engine.ta.snd.builders.levels import compute_trade_levels
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detectors.fakeouts import FakeoutTest
from engine.ta.snd.detectors.previous_levels import PreviousHighsLows
from engine.ta.snd.validators.marubozu.validator import MarubozuValidator
from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator

logger = get_logger(__name__)


class QMCandidateBuilder:
    """
    Builds QM/QML/QMH-driven SnD candidates.

    QM patterns are the core of SnD trading:
    1. QML + SR Flip + Fakeout (baseline)
    2. QML + MPL + SR Flip + Fakeout
    3. QML + Previous Highs + MPL + SR Flip + Fakeout (Type 1 - 90% Killer Setup)
    4. QML + Previous Highs + MPL + SR Flip + Fakeout (Type 2 - 90% Killer Setup)
    5. QML + Triple Fakeout (highest confluence)

    Requirements:
    - QML must be valid (H → HH → break of H)
    - SR/RS Flip must be created by Marubozu
    - Minimum 1 fakeout test
    - Previous Highs/Lows (minimum 2 touches) for 90% setups
    - MPL adds extra confluence
    - Fibonacci alignment = 90% probability
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

    def build_qml_baseline_short(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        qml: QuasiModoLevel,
        sr_flip_level: float,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: Optional[int],
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SnDCandidate]:
        if not qml.is_valid:
            return None

        if len(fakeout_tests) < self.config.min_fakeout_tests:
            return None

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BEARISH,
            qml.level,
            retracement,
        )

        confluences = self._count_qml_confluences(
            qml,
            fakeout_tests,
            None,
            None,
            retracement,
        )

        # Universal Rule 1: Validate Marubozu on breakout candle
        marubozu_valid, marubozu_ts = self._validate_marubozu(
            ltf_sequence, breakout_candle_index, Direction.BEARISH
        )

        # SL above the structural extreme (HH that formed the QM pattern).
        # All level geometry is delegated to compute_trade_levels which
        # uses the broker-aware pip utilities and enforces positivity +
        # direction-correct ordering.
        levels = compute_trade_levels(
            symbol=ltf_sequence.symbol,
            direction=Direction.BEARISH,
            entry_price=qml.level,
            structural_extreme=qml.hh_price,
            sl_buffer_pips=self.config.previous_level_tolerance_pips,
            timeframe=ltf_sequence.timeframe,
            logger_event_prefix="qml_baseline_short",
        )
        if levels is None:
            return None

        entry_price = levels.entry_price
        stop_loss = levels.stop_loss
        take_profit = levels.take_profit

        candidate = SnDCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.QML_BASELINE,
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
            marubozu_detected=marubozu_valid,
            marubozu_timestamp=marubozu_ts,
            compression_detected=self._check_compression(
                ltf_sequence, fakeout_tests,
            ),
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            fib_level=(
                self._get_fib_level(entry_price, retracement) if retracement else None
            ),
            metadata={"confluences": confluences, "pattern_type": "qml_baseline"},
        )

        self._logger.info(
            "qml_baseline_short_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "marubozu_detected": marubozu_valid,
            },
        )

        return candidate

    def build_qml_killer_setup_short(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        qml: QuasiModoLevel,
        sr_flip_level: float,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: Optional[int],
        previous_highs: PreviousHighsLows,
        mpl: Optional[MiniPriceLevel],
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SnDCandidate]:
        if not qml.is_valid:
            return None

        if previous_highs.touch_count < self.config.min_previous_touches:
            return None

        if len(fakeout_tests) < self.config.min_fakeout_tests:
            return None

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BEARISH,
            qml.level,
            retracement,
        )

        confluences = self._count_qml_confluences(
            qml,
            fakeout_tests,
            previous_highs,
            mpl,
            retracement,
        )

        # Universal Rule 1: Validate Marubozu on breakout candle
        marubozu_valid, marubozu_ts = self._validate_marubozu(
            ltf_sequence, breakout_candle_index, Direction.BEARISH
        )

        # SL above the structural extreme (HH that formed the QM pattern).
        levels = compute_trade_levels(
            symbol=ltf_sequence.symbol,
            direction=Direction.BEARISH,
            entry_price=qml.level,
            structural_extreme=qml.hh_price,
            sl_buffer_pips=self.config.previous_level_tolerance_pips,
            timeframe=ltf_sequence.timeframe,
            logger_event_prefix="qml_killer_short",
        )
        if levels is None:
            return None

        entry_price = levels.entry_price
        stop_loss = levels.stop_loss
        take_profit = levels.take_profit

        pattern_type = (
            CandidatePattern.QML_KILLER_TYPE1
            if mpl and mpl.is_type1
            else CandidatePattern.QML_KILLER_TYPE2
        )

        candidate = SnDCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=pattern_type,
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
            marubozu_detected=marubozu_valid,
            marubozu_timestamp=marubozu_ts,
            compression_detected=self._check_compression(
                ltf_sequence, fakeout_tests,
            ),
            previous_highs_count=previous_highs.touch_count,
            mpl_detected=mpl is not None,
            mpl_price=mpl.level if mpl else None,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            fib_level=(
                self._get_fib_level(entry_price, retracement) if retracement else None
            ),
            metadata={
                "confluences": confluences,
                "pattern_type": (
                    "qml_killer_type1" if mpl and mpl.is_type1 else "qml_killer_type2"
                ),
                "is_90_percent_setup": True,
            },
        )

        self._logger.info(
            "qml_killer_setup_short_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "previous_highs_count": previous_highs.touch_count,
                "has_mpl": mpl is not None,
                "marubozu_detected": marubozu_valid,
            },
        )

        return candidate

    def build_qmh_baseline_long(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        qmh: QuasiModoLevel,
        rs_flip_level: float,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: Optional[int],
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SnDCandidate]:
        if not qmh.is_valid:
            return None

        if len(fakeout_tests) < self.config.min_fakeout_tests:
            return None

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BULLISH,
            qmh.level,
            retracement,
        )

        confluences = self._count_qmh_confluences(
            qmh,
            fakeout_tests,
            None,
            None,
            retracement,
        )

        # Universal Rule 1: Validate Marubozu on breakout candle
        marubozu_valid, marubozu_ts = self._validate_marubozu(
            ltf_sequence, breakout_candle_index, Direction.BULLISH
        )

        # SL below the structural extreme (LL that formed the QM pattern).
        levels = compute_trade_levels(
            symbol=ltf_sequence.symbol,
            direction=Direction.BULLISH,
            entry_price=qmh.level,
            structural_extreme=qmh.ll_price,
            sl_buffer_pips=self.config.previous_level_tolerance_pips,
            timeframe=ltf_sequence.timeframe,
            logger_event_prefix="qmh_baseline_long",
        )
        if levels is None:
            return None

        entry_price = levels.entry_price
        stop_loss = levels.stop_loss
        take_profit = levels.take_profit

        candidate = SnDCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.QMH_BASELINE,
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
            marubozu_detected=marubozu_valid,
            marubozu_timestamp=marubozu_ts,
            compression_detected=self._check_compression(
                ltf_sequence, fakeout_tests,
            ),
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            fib_level=(
                self._get_fib_level(entry_price, retracement) if retracement else None
            ),
            metadata={"confluences": confluences, "pattern_type": "qmh_baseline"},
        )

        self._logger.info(
            "qmh_baseline_long_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "marubozu_detected": marubozu_valid,
            },
        )

        return candidate

    def build_qmh_killer_setup_long(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        qmh: QuasiModoLevel,
        rs_flip_level: float,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: Optional[int],
        previous_lows: PreviousHighsLows,
        mpl: Optional[MiniPriceLevel],
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SnDCandidate]:
        if not qmh.is_valid:
            return None

        if previous_lows.touch_count < self.config.min_previous_touches:
            return None

        if len(fakeout_tests) < self.config.min_fakeout_tests:
            return None

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BULLISH,
            qmh.level,
            retracement,
        )

        confluences = self._count_qmh_confluences(
            qmh,
            fakeout_tests,
            previous_lows,
            mpl,
            retracement,
        )

        # Universal Rule 1: Validate Marubozu on breakout candle
        marubozu_valid, marubozu_ts = self._validate_marubozu(
            ltf_sequence, breakout_candle_index, Direction.BULLISH
        )

        # SL below the structural extreme (LL that formed the QM pattern).
        levels = compute_trade_levels(
            symbol=ltf_sequence.symbol,
            direction=Direction.BULLISH,
            entry_price=qmh.level,
            structural_extreme=qmh.ll_price,
            sl_buffer_pips=self.config.previous_level_tolerance_pips,
            timeframe=ltf_sequence.timeframe,
            logger_event_prefix="qmh_killer_long",
        )
        if levels is None:
            return None

        entry_price = levels.entry_price
        stop_loss = levels.stop_loss
        take_profit = levels.take_profit

        pattern_type = (
            CandidatePattern.QMH_KILLER_TYPE1
            if mpl and mpl.is_type1
            else CandidatePattern.QMH_KILLER_TYPE2
        )

        candidate = SnDCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=pattern_type,
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
            marubozu_detected=marubozu_valid,
            marubozu_timestamp=marubozu_ts,
            compression_detected=self._check_compression(
                ltf_sequence, fakeout_tests,
            ),
            previous_lows_count=previous_lows.touch_count,
            mpl_detected=mpl is not None,
            mpl_price=mpl.level if mpl else None,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            fib_level=(
                self._get_fib_level(entry_price, retracement) if retracement else None
            ),
            metadata={
                "confluences": confluences,
                "pattern_type": (
                    "qmh_killer_type1" if mpl and mpl.is_type1 else "qmh_killer_type2"
                ),
                "is_90_percent_setup": True,
            },
        )

        self._logger.info(
            "qmh_killer_setup_long_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "previous_lows_count": previous_lows.touch_count,
                "has_mpl": mpl is not None,
                "marubozu_detected": marubozu_valid,
            },
        )

        return candidate

    def _count_qml_confluences(
        self,
        qml: QuasiModoLevel,
        fakeout_tests: list[FakeoutTest],
        previous_highs: Optional[PreviousHighsLows],
        mpl: Optional[MiniPriceLevel],
        retracement: Optional[FibonacciRetracement],
    ) -> int:
        confluences = 1

        confluences += len(fakeout_tests)

        if previous_highs and previous_highs.touch_count >= 2:
            confluences += previous_highs.touch_count

        if mpl:
            confluences += 2 if mpl.is_type1 else 1

        if retracement:
            if self.ltf_validator.check_fibonacci_alignment(qml.level, retracement):
                confluences += 2

        return confluences

    def _count_qmh_confluences(
        self,
        qmh: QuasiModoLevel,
        fakeout_tests: list[FakeoutTest],
        previous_lows: Optional[PreviousHighsLows],
        mpl: Optional[MiniPriceLevel],
        retracement: Optional[FibonacciRetracement],
    ) -> int:
        confluences = 1

        confluences += len(fakeout_tests)

        if previous_lows and previous_lows.touch_count >= 2:
            confluences += previous_lows.touch_count

        if mpl:
            confluences += 2 if mpl.is_type1 else 1

        if retracement:
            if self.ltf_validator.check_fibonacci_alignment(qmh.level, retracement):
                confluences += 2

        return confluences

    def _check_compression(
        self,
        sequence: CandleSequence,
        fakeout_tests: list[FakeoutTest],
    ) -> bool:
        """Check if real compression exists at the fakeout zone."""
        if not fakeout_tests:
            return False
        last_fakeout = fakeout_tests[-1]
        return self.ltf_validator.validate_compression_at_zone(
            sequence, fakeout_tests,
        )

    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[str]:
        """Return the OTE fib level (0.5, 0.618, 0.705, 0.79) closest to price,
        but only if within the configured tolerance. Returns None if no OTE
        level is close enough — never returns 0.0 or 1.0."""
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
    ) -> tuple[bool, Optional["datetime"]]:
        """Validate whether the breakout candle is a valid Marubozu.

        Returns (is_valid, timestamp) tuple.
        """
        if breakout_candle_index is None:
            return False, None

        if breakout_candle_index >= len(sequence.candles):
            return False, None

        candle = sequence.candles[breakout_candle_index]

        if direction == Direction.BEARISH:
            is_valid = self.marubozu_validator.validate_bearish_marubozu(candle)
        else:
            is_valid = self.marubozu_validator.validate_bullish_marubozu(candle)

        return is_valid, candle.timestamp if is_valid else None
