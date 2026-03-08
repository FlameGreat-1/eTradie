from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.constants import Direction, CandidatePattern
from engine.ta.models.candidate import SnDCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.zone import QuasiModoLevel
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detectors.fakeouts import FakeoutTest
from engine.ta.snd.detectors.previous_levels import PreviousHighsLows
from engine.ta.snd.validators.marubozu.validator import MarubozuValidator
from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator

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
        breakout_candle_index: Optional[int],
        previous_highs: Optional[PreviousHighsLows],
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SnDCandidate]:
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
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BEARISH,
            qml.level,
            retracement,
        ):
            return None
        
        confluences = self._count_continuation_confluences(
            qml,
            fakeout_tests,
            previous_highs,
            retracement,
        )
        
        entry_price = sr_flip_level
        stop_loss = sr_flip_level + (0.0020)
        take_profit = qml.level - (0.0050)
        
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
            qml_level=qml.level,
            qml_timestamp=qml.timestamp,
            sr_flip_level=sr_flip_level,
            fakeout_count=len(fakeout_tests),
            has_compression=True,
            has_previous_highs=True,
            previous_highs_count=previous_highs.touch_count,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
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
        breakout_candle_index: Optional[int],
        previous_lows: Optional[PreviousHighsLows],
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SnDCandidate]:
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
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BULLISH,
            qmh.level,
            retracement,
        ):
            return None
        
        confluences = self._count_continuation_confluences(
            qmh,
            fakeout_tests,
            previous_lows,
            retracement,
        )
        
        entry_price = rs_flip_level
        stop_loss = rs_flip_level - (0.0020)
        take_profit = qmh.level + (0.0050)
        
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
            qmh_level=qmh.level,
            qmh_timestamp=qmh.timestamp,
            rs_flip_level=rs_flip_level,
            fakeout_count=len(fakeout_tests),
            has_compression=True,
            has_previous_lows=True,
            previous_lows_count=previous_lows.touch_count,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
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
        previous_levels: Optional[PreviousHighsLows],
        retracement: Optional[FibonacciRetracement],
    ) -> int:
        confluences = 1
        
        confluences += len(fakeout_tests)
        
        if previous_levels and previous_levels.touch_count >= 2:
            confluences += previous_levels.touch_count
        
        if retracement:
            if self.ltf_validator.validate_fibonacci_alignment(qm_level.level, retracement):
                confluences += 2
        
        return confluences
    
    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[str]:
        nearest_level = self.fibonacci_analyzer.get_nearest_fib_level(price, retracement)
        return str(nearest_level) if nearest_level else None
