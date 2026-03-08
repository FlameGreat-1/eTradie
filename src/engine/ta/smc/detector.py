from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.common.analyzers.liquidity import LiquidityAnalyzer
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.analyzers.dealing_range import DealingRangeAnalyzer
from engine.ta.constants import Direction, Timeframe
from engine.ta.models.candle import CandleSequence
from engine.ta.models.candidate import SMCCandidate
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig
from engine.ta.smc.detectors.bms import BMSDetector
from engine.ta.smc.detectors.choch import CHOCHDetector
from engine.ta.smc.detectors.sms import SMSDetector
from engine.ta.smc.detectors.inducement import InducementDetector
from engine.ta.smc.detectors.turtle_soup import TurtleSoupDetector
from engine.ta.smc.detectors.amd import AMDDetector, AMDContext
from engine.ta.smc.zones.fvg import FVGDetector
from engine.ta.smc.zones.order_block import OrderBlockDetector
from engine.ta.smc.zones.breaker import BreakerDetector
from engine.ta.smc.zones.mitigation import MitigationDetector
from engine.ta.smc.validators.zone.validator import ZoneValidator
from engine.ta.smc.validators.ltf.confirmation import LTFConfirmationValidator
from engine.ta.smc.builders.continuation import ContinuationBuilder
from engine.ta.smc.builders.reversal import ReversalBuilder
from engine.ta.smc.builders.amd.candidates import AMDCandidateBuilder

logger = get_logger(__name__)


class SMCDetector:
    """
    SMC orchestration entrypoint.
    
    Coordinates all SMC pattern detection:
    1. Runs all SMC detectors (BMS, CHOCH, SMS, inducement, turtle soup, AMD)
    2. Extracts zones (OB, FVG, breaker blocks)
    3. Validates zones against 7 OB rules
    4. Validates LTF confirmations (6 requirements)
    5. Builds candidates using continuation/reversal/AMD builders
    6. Outputs SMCCandidate models for processor
    
    Enforces all 12 Universal Rules:
    - Liquidity must be taken first
    - Always trade in direction of HTF BMS
    - After BMS always wait for retracement
    - Order Block definition is strict
    - Minimum 3 confluences required
    - OTE adds critical confluence
    - Session timing is confluence
    - AMD context must be known
    - Equal highs/lows are prime liquidity targets
    - High impact news is a liquidity tool
    - Top-down timeframe execution (mandatory)
    - Turtle Soup minimum SL
    """
    
    def __init__(
        self,
        config: SMCConfig,
        candle_analyzer: CandleAnalyzer,
        swing_analyzer: SwingAnalyzer,
        session_analyzer: SessionAnalyzer,
        liquidity_analyzer: LiquidityAnalyzer,
        sweep_analyzer: SweepAnalyzer,
        fibonacci_analyzer: FibonacciAnalyzer,
        dealing_range_analyzer: DealingRangeAnalyzer,
    ) -> None:
        self.config = config
        self.candle_analyzer = candle_analyzer
        self.swing_analyzer = swing_analyzer
        self.session_analyzer = session_analyzer
        self.liquidity_analyzer = liquidity_analyzer
        self.sweep_analyzer = sweep_analyzer
        self.fibonacci_analyzer = fibonacci_analyzer
        self.dealing_range_analyzer = dealing_range_analyzer
        
        self.bms_detector = BMSDetector(config)
        self.choch_detector = CHOCHDetector(config)
        self.sms_detector = SMSDetector(config)
        self.inducement_detector = InducementDetector(config)
        self.turtle_soup_detector = TurtleSoupDetector(config, sweep_analyzer)
        self.amd_detector = AMDDetector(config, session_analyzer, dealing_range_analyzer)
        
        self.fvg_detector = FVGDetector(config, candle_analyzer)
        self.ob_detector = OrderBlockDetector(config)
        self.breaker_detector = BreakerDetector(config)
        self.mitigation_detector = MitigationDetector(config)
        
        self.zone_validator = ZoneValidator(config, fibonacci_analyzer)
        self.ltf_validator = LTFConfirmationValidator(config, session_analyzer)
        
        self.continuation_builder = ContinuationBuilder(
            config,
            self.zone_validator,
            self.ltf_validator,
            fibonacci_analyzer,
        )
        self.reversal_builder = ReversalBuilder(
            config,
            self.zone_validator,
            self.ltf_validator,
            fibonacci_analyzer,
        )
        self.amd_builder = AMDCandidateBuilder(
            config,
            self.zone_validator,
            self.ltf_validator,
            fibonacci_analyzer,
        )
        
        self._logger = get_logger(__name__)
    
    def detect_patterns(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> list[SMCCandidate]:
        """
        Main orchestration method - detects all SMC patterns and builds candidates.
        
        Top-down execution (Universal Rule 11):
        1. HTF: Identify structure (BMS, SMS, swings)
        2. LTF: Refine entry (CHOCH, OB, FVG, sweeps)
        3. Validate all rules
        4. Build candidates
        """
        if not self.config.enabled:
            return []
        
        self._logger.info(
            "smc_detection_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe,
                "ltf_timeframe": ltf_sequence.timeframe,
            },
        )
        
        htf_swing_highs = self.swing_analyzer.detect_swing_highs(htf_sequence)
        htf_swing_lows = self.swing_analyzer.detect_swing_lows(htf_sequence)
        
        htf_bms_bullish = self.bms_detector.detect_bullish_bms(htf_sequence, htf_swing_lows)
        htf_bms_bearish = self.bms_detector.detect_bearish_bms(htf_sequence, htf_swing_highs)
        
        htf_sms_bullish = self.sms_detector.detect_bullish_sms(htf_sequence, htf_swing_lows)
        htf_sms_bearish = self.sms_detector.detect_bearish_sms(htf_sequence, htf_swing_highs)
        
        ltf_swing_highs = self.swing_analyzer.detect_swing_highs(ltf_sequence)
        ltf_swing_lows = self.swing_analyzer.detect_swing_lows(ltf_sequence)
        
        ltf_bms_bullish = self.bms_detector.detect_bullish_bms(ltf_sequence, ltf_swing_lows)
        ltf_bms_bearish = self.bms_detector.detect_bearish_bms(ltf_sequence, ltf_swing_highs)
        
        ltf_choch_bullish = self.choch_detector.detect_bullish_choch(ltf_sequence, ltf_swing_lows)
        ltf_choch_bearish = self.choch_detector.detect_bearish_choch(ltf_sequence, ltf_swing_highs)
        
        ltf_fvgs = self.fvg_detector.detect_fvgs(ltf_sequence)
        
        ltf_inducement_bullish = self.inducement_detector.detect_bullish_inducement(
            ltf_sequence,
            ltf_swing_lows,
        )
        ltf_inducement_bearish = self.inducement_detector.detect_bearish_inducement(
            ltf_sequence,
            ltf_swing_highs,
        )
        
        turtle_soup_long = []
        turtle_soup_short = []
        if self.config.enable_turtle_soup:
            turtle_soup_long = self.turtle_soup_detector.detect_turtle_soup_long(
                ltf_sequence,
                ltf_swing_lows,
            )
            turtle_soup_short = self.turtle_soup_detector.detect_turtle_soup_short(
                ltf_sequence,
                ltf_swing_highs,
            )
        
        amd_context = None
        if self.config.enable_amd:
            amd_context = self.amd_detector.detect_amd_context(ltf_sequence)
        
        retracement = self._create_fibonacci_retracement(
            htf_swing_highs,
            htf_swing_lows,
        )
        
        candidates = []
        
        # Build Continuation Candidates (Pattern 2/7: SH + BMS + RTO)
        if self.config.enable_sh_bms_rto:
            candidates.extend(
                self._build_continuation_candidates(
                    htf_sequence,
                    ltf_sequence,
                    htf_bms_bullish,
                    htf_bms_bearish,
                    ltf_bms_bullish,
                    ltf_bms_bearish,
                    ltf_choch_bullish,
                    ltf_choch_bearish,
                    ltf_fvgs,
                    ltf_inducement_bullish + ltf_inducement_bearish,
                    turtle_soup_long + turtle_soup_short,
                    retracement,
                )
            )
        
        # Build Reversal Candidates (Pattern 3/8: SMS + BMS + RTO)
        if self.config.enable_sms_bms_rto:
            candidates.extend(
                self._build_reversal_candidates(
                    htf_sequence,
                    ltf_sequence,
                    htf_sms_bullish,
                    htf_sms_bearish,
                    ltf_bms_bullish,
                    ltf_bms_bearish,
                    ltf_choch_bullish,
                    ltf_choch_bearish,
                    ltf_fvgs,
                    ltf_inducement_bullish + ltf_inducement_bearish,
                    retracement,
                )
            )
        
        # Build Turtle Soup Candidates (Pattern 1/6)
        if self.config.enable_turtle_soup:
            candidates.extend(
                self._build_turtle_soup_candidates(
                    ltf_sequence,
                    turtle_soup_long,
                    turtle_soup_short,
                )
            )
        
        # Build AMD Candidates (Pattern 4/9)
        if self.config.enable_amd and amd_context:
            candidates.extend(
                self._build_amd_candidates(
                    htf_sequence,
                    ltf_sequence,
                    amd_context,
                    ltf_bms_bullish,
                    ltf_bms_bearish,
                    ltf_choch_bullish,
                    ltf_choch_bearish,
                    ltf_fvgs,
                    ltf_inducement_bullish + ltf_inducement_bearish,
                    turtle_soup_long + turtle_soup_short,
                    retracement,
                )
            )
        
        self._logger.info(
            "smc_detection_completed",
            extra={
                "symbol": htf_sequence.symbol,
                "total_candidates": len(candidates),
                "htf_bms_bullish": len(htf_bms_bullish),
                "htf_bms_bearish": len(htf_bms_bearish),
                "ltf_bms_bullish": len(ltf_bms_bullish),
                "ltf_bms_bearish": len(ltf_bms_bearish),
                "turtle_soup_long": len(turtle_soup_long),
                "turtle_soup_short": len(turtle_soup_short),
            },
        )
        
        return candidates
    
    def _build_continuation_candidates(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        htf_bms_bullish: list,
        htf_bms_bearish: list,
        ltf_bms_bullish: list,
        ltf_bms_bearish: list,
        ltf_choch_bullish: list,
        ltf_choch_bearish: list,
        ltf_fvgs: list,
        inducement_events: list,
        sweeps: list,
        retracement: Optional[FibonacciRetracement],
    ) -> list[SMCCandidate]:
        candidates = []
        
        latest_htf_bms_bullish = self.bms_detector.get_latest_bms(htf_bms_bullish)
        if latest_htf_bms_bullish and ltf_bms_bullish and ltf_choch_bullish:
            for ltf_bms in ltf_bms_bullish:
                ltf_ob = self.ob_detector.detect_bullish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue
                
                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bullish)
                if not ltf_choch:
                    continue
                
                ltf_sweep = self._find_relevant_sweep(sweeps, Direction.BULLISH, ltf_bms)
                
                candidate = self.continuation_builder.build_bullish_continuation(
                    htf_sequence,
                    ltf_sequence,
                    latest_htf_bms_bullish,
                    ltf_sweep,
                    ltf_choch,
                    ltf_bms,
                    ltf_ob,
                    ltf_fvgs,
                    inducement_events,
                    retracement,
                )
                
                if candidate:
                    candidates.append(candidate)
        
        latest_htf_bms_bearish = self.bms_detector.get_latest_bms(htf_bms_bearish)
        if latest_htf_bms_bearish and ltf_bms_bearish and ltf_choch_bearish:
            for ltf_bms in ltf_bms_bearish:
                ltf_ob = self.ob_detector.detect_bearish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue
                
                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bearish)
                if not ltf_choch:
                    continue
                
                ltf_sweep = self._find_relevant_sweep(sweeps, Direction.BEARISH, ltf_bms)
                
                candidate = self.continuation_builder.build_bearish_continuation(
                    htf_sequence,
                    ltf_sequence,
                    latest_htf_bms_bearish,
                    ltf_sweep,
                    ltf_choch,
                    ltf_bms,
                    ltf_ob,
                    ltf_fvgs,
                    inducement_events,
                    retracement,
                )
                
                if candidate:
                    candidates.append(candidate)
        
        return candidates
    
    def _build_reversal_candidates(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        htf_sms_bullish: list,
        htf_sms_bearish: list,
        ltf_bms_bullish: list,
        ltf_bms_bearish: list,
        ltf_choch_bullish: list,
        ltf_choch_bearish: list,
        ltf_fvgs: list,
        inducement_events: list,
        retracement: Optional[FibonacciRetracement],
    ) -> list[SMCCandidate]:
        candidates = []
        
        latest_htf_sms_bullish = self.sms_detector.get_latest_sms(htf_sms_bullish)
        if latest_htf_sms_bullish and ltf_bms_bullish and ltf_choch_bullish:
            for ltf_bms in ltf_bms_bullish:
                ltf_ob = self.ob_detector.detect_bullish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue
                
                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bullish)
                if not ltf_choch:
                    continue
                
                candidate = self.reversal_builder.build_bullish_sms_reversal(
                    htf_sequence,
                    ltf_sequence,
                    latest_htf_sms_bullish,
                    ltf_bms,
                    ltf_choch,
                    ltf_ob,
                    ltf_fvgs,
                    inducement_events,
                    retracement,
                )
                
                if candidate:
                    candidates.append(candidate)
        
        latest_htf_sms_bearish = self.sms_detector.get_latest_sms(htf_sms_bearish)
        if latest_htf_sms_bearish and ltf_bms_bearish and ltf_choch_bearish:
            for ltf_bms in ltf_bms_bearish:
                ltf_ob = self.ob_detector.detect_bearish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue
                
                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bearish)
                if not ltf_choch:
                    continue
                
                candidate = self.reversal_builder.build_bearish_sms_reversal(
                    htf_sequence,
                    ltf_sequence,
                    latest_htf_sms_bearish,
                    ltf_bms,
                    ltf_choch,
                    ltf_ob,
                    ltf_fvgs,
                    inducement_events,
                    retracement,
                )
                
                if candidate:
                    candidates.append(candidate)
        
        return candidates
    
    def _build_turtle_soup_candidates(
        self,
        ltf_sequence: CandleSequence,
        turtle_soup_long: list,
        turtle_soup_short: list,
    ) -> list[SMCCandidate]:
        candidates = []
        
        for sweep in turtle_soup_long:
            candidate = self.reversal_builder.build_turtle_soup_long(
                ltf_sequence,
                sweep,
            )
            if candidate:
                candidates.append(candidate)
        
        for sweep in turtle_soup_short:
            candidate = self.reversal_builder.build_turtle_soup_short(
                ltf_sequence,
                sweep,
            )
            if candidate:
                candidates.append(candidate)
        
        return candidates
    
    def _build_amd_candidates(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        amd_context: AMDContext,
        ltf_bms_bullish: list,
        ltf_bms_bearish: list,
        ltf_choch_bullish: list,
        ltf_choch_bearish: list,
        ltf_fvgs: list,
        inducement_events: list,
        sweeps: list,
        retracement: Optional[FibonacciRetracement],
    ) -> list[SMCCandidate]:
        candidates = []
        
        if amd_context.distribution_direction == Direction.BULLISH:
            for ltf_bms in ltf_bms_bullish:
                ltf_ob = self.ob_detector.detect_bullish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue
                
                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bullish)
                if not ltf_choch:
                    continue
                
                ltf_sweep = self._find_relevant_sweep(sweeps, Direction.BULLISH, ltf_bms)
                
                candidate = self.amd_builder.build_bullish_amd(
                    htf_sequence,
                    ltf_sequence,
                    amd_context,
                    ltf_sweep,
                    ltf_bms,
                    ltf_choch,
                    ltf_ob,
                    ltf_fvgs,
                    inducement_events,
                    retracement,
                )
                
                if candidate:
                    candidates.append(candidate)
        
        elif amd_context.distribution_direction == Direction.BEARISH:
            for ltf_bms in ltf_bms_bearish:
                ltf_ob = self.ob_detector.detect_bearish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue
                
                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bearish)
                if not ltf_choch:
                    continue
                
                ltf_sweep = self._find_relevant_sweep(sweeps, Direction.BEARISH, ltf_bms)
                
                candidate = self.amd_builder.build_bearish_amd(
                    htf_sequence,
                    ltf_sequence,
                    amd_context,
                    ltf_sweep,
                    ltf_bms,
                    ltf_choch,
                    ltf_ob,
                    ltf_fvgs,
                    inducement_events,
                    retracement,
                )
                
                if candidate:
                    candidates.append(candidate)
        
        return candidates
    
    def _create_fibonacci_retracement(
        self,
        swing_highs: list[SwingHigh],
        swing_lows: list[SwingLow],
    ) -> Optional[FibonacciRetracement]:
        if not swing_highs or not swing_lows:
            return None
        
        latest_high = self.swing_analyzer.get_latest_swing_high(swing_highs)
        latest_low = self.swing_analyzer.get_latest_swing_low(swing_lows)
        
        if not latest_high or not latest_low:
            return None
        
        is_bullish = latest_low.timestamp > latest_high.timestamp
        
        return self.fibonacci_analyzer.create_retracement(
            latest_high,
            latest_low,
            is_bullish,
        )
    
    def _find_relevant_sweep(
        self,
        sweeps: list,
        direction: Direction,
        bms: object,
    ) -> Optional[object]:
        for sweep in sweeps:
            if abs(sweep.timestamp.timestamp() - bms.timestamp.timestamp()) < 3600:
                if direction == Direction.BULLISH and sweep.liquidity_type.value in ["SSL", "EQUAL_LOWS"]:
                    return sweep
                elif direction == Direction.BEARISH and sweep.liquidity_type.value in ["BSL", "EQUAL_HIGHS"]:
                    return sweep
        
        return None

