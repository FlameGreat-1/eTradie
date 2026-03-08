from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.constants import Direction, CandidatePattern
from engine.ta.models.candidate import SnDCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.zone import QuasiModoLevel, MiniPriceLevel
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
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BEARISH,
            qml.level,
            retracement,
        ):
            return None
        
        confluences = self._count_qml_confluences(
            qml,
            fakeout_tests,
            None,
            None,
            retracement,
        )
        
        entry_price = qml.level
        stop_loss = qml.level + (0.0020)
        take_profit = qml.level - (0.0100)
        
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
            qml_level=qml.level,
            qml_timestamp=qml.timestamp,
            sr_flip_level=sr_flip_level,
            fakeout_count=len(fakeout_tests),
            has_compression=True,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
            metadata={"confluences": confluences, "pattern_type": "qml_baseline"},
        )
        
        self._logger.info(
            "qml_baseline_short_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
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
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BEARISH,
            qml.level,
            retracement,
        ):
            return None
        
        confluences = self._count_qml_confluences(
            qml,
            fakeout_tests,
            previous_highs,
            mpl,
            retracement,
        )
        
        entry_price = qml.level
        stop_loss = qml.level + (0.0020)
        take_profit = qml.level - (0.0100)
        
        pattern_type = CandidatePattern.QML_KILLER_TYPE1 if mpl and mpl.is_type1 else CandidatePattern.QML_KILLER_TYPE2
        
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
            qml_level=qml.level,
            qml_timestamp=qml.timestamp,
            sr_flip_level=sr_flip_level,
            fakeout_count=len(fakeout_tests),
            has_compression=True,
            has_previous_highs=True,
            previous_highs_count=previous_highs.touch_count,
            has_mpl=mpl is not None,
            mpl_level=mpl.level if mpl else None,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
            metadata={
                "confluences": confluences,
                "pattern_type": "qml_killer_type1" if mpl and mpl.is_type1 else "qml_killer_type2",
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
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BULLISH,
            qmh.level,
            retracement,
        ):
            return None
        
        confluences = self._count_qmh_confluences(
            qmh,
            fakeout_tests,
            None,
            None,
            retracement,
        )
        
        entry_price = qmh.level
        stop_loss = qmh.level - (0.0020)
        take_profit = qmh.level + (0.0100)
        
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
            qmh_level=qmh.level,
            qmh_timestamp=qmh.timestamp,
            rs_flip_level=rs_flip_level,
            fakeout_count=len(fakeout_tests),
            has_compression=True,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
            metadata={"confluences": confluences, "pattern_type": "qmh_baseline"},
        )
        
        self._logger.info(
            "qmh_baseline_long_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
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
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BULLISH,
            qmh.level,
            retracement,
        ):
            return None
        
        confluences = self._count_qmh_confluences(
            qmh,
            fakeout_tests,
            previous_lows,
            mpl,
            retracement,
        )
        
        entry_price = qmh.level
        stop_loss = qmh.level - (0.0020)
        take_profit = qmh.level + (0.0100)
        
        pattern_type = CandidatePattern.QMH_KILLER_TYPE1 if mpl and mpl.is_type1 else CandidatePattern.QMH_KILLER_TYPE2
        
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
            qmh_level=qmh.level,
            qmh_timestamp=qmh.timestamp,
            rs_flip_level=rs_flip_level,
            fakeout_count=len(fakeout_tests),
            has_compression=True,
            has_previous_lows=True,
            previous_lows_count=previous_lows.touch_count,
            has_mpl=mpl is not None,
            mpl_level=mpl.level if mpl else None,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
            metadata={
                "confluences": confluences,
                "pattern_type": "qmh_killer_type1" if mpl and mpl.is_type1 else "qmh_killer_type2",
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
            if self.ltf_validator.validate_fibonacci_alignment(qml.level, retracement):
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
            if self.ltf_validator.validate_fibonacci_alignment(qmh.level, retracement):
                confluences += 2
        
        return confluences
    
    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[str]:
        nearest_level = self.fibonacci_analyzer.get_nearest_fib_level(price, retracement)
        return str(nearest_level) if nearest_level else None
