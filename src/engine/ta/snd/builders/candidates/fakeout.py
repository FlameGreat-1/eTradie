from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.constants import Direction, CandidatePattern
from engine.ta.models.candidate import SnDCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detectors.fakeouts import FakeoutTest
from engine.ta.snd.detectors.previous_levels import PreviousHighsLows
from engine.ta.snd.validators.marubozu.validator import MarubozuValidator
from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator

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
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BEARISH,
            sr_flip_level,
            retracement,
        ):
            return None
        
        confluences = self._count_fakeout_confluences(
            fakeout_tests,
            previous_highs,
            retracement,
            sr_flip_level,
        )
        
        entry_price = sr_flip_level
        stop_loss = sr_flip_level + (0.0020)
        take_profit = sr_flip_level - (0.0100)
        
        pattern = CandidatePattern.FAKEOUT_KING if len(fakeout_tests) >= 3 else CandidatePattern.SOP
        
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
            sr_flip_level=sr_flip_level,
            fakeout_count=len(fakeout_tests),
            has_compression=True,
            has_previous_highs=previous_highs is not None,
            previous_highs_count=previous_highs.touch_count if previous_highs else 0,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
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
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sequence,
            fakeout_tests,
            breakout_candle_index,
            Direction.BULLISH,
            rs_flip_level,
            retracement,
        ):
            return None
        
        confluences = self._count_fakeout_confluences(
            fakeout_tests,
            previous_lows,
            retracement,
            rs_flip_level,
        )
        
        entry_price = rs_flip_level
        stop_loss = rs_flip_level - (0.0020)
        take_profit = rs_flip_level + (0.0100)
        
        pattern = CandidatePattern.FAKEOUT_KING if len(fakeout_tests) >= 3 else CandidatePattern.SOP
        
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
            rs_flip_level=rs_flip_level,
            fakeout_count=len(fakeout_tests),
            has_compression=True,
            has_previous_lows=previous_lows is not None,
            previous_lows_count=previous_lows.touch_count if previous_lows else 0,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
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
            if self.ltf_validator.validate_fibonacci_alignment(zone_price, retracement):
                confluences += 2
        
        if any(test.is_diamond_fakeout for test in fakeout_tests):
            confluences += 1
        
        return confluences
    
    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[str]:
        nearest_level = self.fibonacci_analyzer.get_nearest_fib_level(price, retracement)
        return str(nearest_level) if nearest_level else None
