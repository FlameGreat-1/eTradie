from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.compression import CompressionAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import calculate_pips
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence, Candle
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detectors.fakeouts import FakeoutTest

logger = get_logger(__name__)


class LTFConfirmationValidator:
    """
    Validates LTF confirmation requirements for SnD candidate eligibility.
    
    4 LTF Confirmations (all required):
    1. Compression at the Zone - tight directional candles inside fakeout zone
    2. Fakeout Broken by Marubozu - single Marubozu breaks fakeout zone
    3. Decision Point - exact candle where price makes final rejection
    4. Fibonacci Alignment - 50%, 61.8%, 70.5%, 79% level aligns with zone (optional but 90% probability)
    
    No entry without all required confirmations.
    
    Top-Down Execution:
    - HTF: QM structure, QML, Previous Highs/Lows
    - Mid TF: SR/RS Flip zone, fakeout formation
    - Lower TF (M15/M5): Compression confirmation
    - Lowest TF (M1): Decision Point identification
    """
    
    def __init__(
        self,
        config: SnDConfig,
        compression_analyzer: CompressionAnalyzer,
        fibonacci_analyzer: FibonacciAnalyzer,
    ) -> None:
        self.config = config
        self.compression_analyzer = compression_analyzer
        self.fibonacci_analyzer = fibonacci_analyzer
        self._logger = get_logger(__name__)
    
    def validate_compression_at_zone(
        self,
        sequence: CandleSequence,
        fakeout_tests: list[FakeoutTest],
    ) -> bool:
        """
        Confirmation 1: Compression at the Zone.
        
        Price must show Compression (CP) inside the SR/RS Flip zone:
        - Small, tight, directional candles
        - Collecting orders
        - Confirms price is stalling at zone
        - Building for next move
        """
        if not fakeout_tests:
            return False
        
        last_fakeout = fakeout_tests[-1]
        
        if last_fakeout.candle_index < self.config.compression_min_candles:
            return False
        
        start_index = max(0, last_fakeout.candle_index - self.config.compression_min_candles)
        end_index = last_fakeout.candle_index + 1
        
        compression_candles = sequence.candles[start_index:end_index]
        
        is_compressed = self.compression_analyzer.is_compression(
            compression_candles,
            sequence.symbol,
        )
        
        if not is_compressed:
            self._logger.debug(
                "ltf_validation_failed_no_compression",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                },
            )
            return False
        
        return True
    
    def validate_fakeout_broken_by_marubozu(
        self,
        breakout_candle_index: Optional[int],
    ) -> bool:
        """
        Confirmation 2: Fakeout Broken by Marubozu.
        
        A single Marubozu candle must break through the fakeout zone.
        This is the signal that the Supply/Demand zone (QML/QMH) is directly ahead.
        Be ready - do not wait until price is already inside the zone.
        """
        if breakout_candle_index is None:
            self._logger.debug("ltf_validation_failed_no_marubozu_breakout")
            return False
        
        return True
    
    def validate_decision_point(
        self,
        sequence: CandleSequence,
        fakeout_tests: list[FakeoutTest],
        direction: Direction,
    ) -> Optional[Candle]:
        """
        Confirmation 3: Decision Point.
        
        On M15/M5/M1, identify the exact candle where price makes its final rejection
        at the SR/RS Flip level. This is the Decision Point - the specific candle
        where price touches the internal support/resistance of the fakeout and rejects.
        
        This is the entry trigger - the moment the Decision Point candle closes, you enter.
        """
        if not fakeout_tests:
            self._logger.debug("ltf_validation_failed_no_fakeouts")
            return None
        
        last_fakeout = fakeout_tests[-1]
        
        if last_fakeout.candle_index >= len(sequence.candles):
            return None
        
        decision_candle = sequence.candles[last_fakeout.candle_index]
        
        if direction == Direction.BULLISH:
            if decision_candle.low <= last_fakeout.level and decision_candle.close > last_fakeout.level:
                return decision_candle
        
        else:
            if decision_candle.high >= last_fakeout.level and decision_candle.close < last_fakeout.level:
                return decision_candle
        
        self._logger.debug(
            "ltf_validation_failed_no_decision_point",
            extra={
                "symbol": sequence.symbol,
                "timeframe": sequence.timeframe,
            },
        )
        
        return None
    
    def validate_fibonacci_alignment(
        self,
        zone_price: float,
        retracement: Optional[FibonacciRetracement],
    ) -> bool:
        """
        Confirmation 4: Fibonacci Alignment (Optional but 90% Probability).
        
        If the 50%, 61.8%, 70.5% or 79% Fibonacci retracement level aligns exactly
        with the identified Supply/Demand zone (QML, SR Flip level) - this adds
        a critical extra confluence and pushes the setup to 90% high probability.
        
        Fibonacci alone is meaningless in this system - it only counts when it lands
        precisely on an already valid zone.
        """
        if not self.config.require_fibonacci_confluence:
            return True
        
        if not retracement:
            return False
        
        nearest_level = self.fibonacci_analyzer.get_nearest_fib_level(zone_price, retracement)
        
        if not nearest_level:
            return False
        
        level_price = self.fibonacci_analyzer.get_fib_level_price(nearest_level, retracement)
        
        if not level_price:
            return False
        
        price_diff_pips = calculate_pips(
            zone_price,
            level_price,
            retracement.symbol,
        )
        
        if abs(price_diff_pips) > self.config.fibonacci_tolerance_pips:
            self._logger.debug(
                "ltf_validation_failed_fibonacci_not_aligned",
                extra={
                    "zone_price": zone_price,
                    "fib_level": str(nearest_level),
                    "fib_price": level_price,
                    "diff_pips": price_diff_pips,
                },
            )
            return False
        
        return True
    
    def validate_all_ltf_confirmations(
        self,
        sequence: CandleSequence,
        fakeout_tests: list[FakeoutTest],
        breakout_candle_index: Optional[int],
        direction: Direction,
        zone_price: float,
        retracement: Optional[FibonacciRetracement],
    ) -> bool:
        """Validate all 4 LTF confirmations."""
        if not self.validate_compression_at_zone(sequence, fakeout_tests):
            return False
        
        if not self.validate_fakeout_broken_by_marubozu(breakout_candle_index):
            return False
        
        decision_point = self.validate_decision_point(sequence, fakeout_tests, direction)
        if not decision_point:
            return False
        
        if not self.validate_fibonacci_alignment(zone_price, retracement):
            return False
        
        return True
