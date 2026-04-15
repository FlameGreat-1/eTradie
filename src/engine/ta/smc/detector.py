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
from engine.ta.models.liquidity_event import LiquiditySweep
from engine.ta.models.structure_event import BreakInMarketStructure
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

# Default fallback; actual value read from config.sweep_max_candle_distance.
_SWEEP_MAX_CANDLE_DISTANCE_DEFAULT = 10


class SMCDetector:
    """
    SMC orchestration entrypoint.

    Coordinates all SMC pattern detection:
    1. Runs all SMC detectors (BMS, CHOCH, SMS, inducement, turtle soup, AMD)
    2. Extracts zones (OB, FVG, breaker blocks)
    3. Validates zones against 7 OB rules
    4. Validates LTF confirmations (6 requirements) when available
    5. Builds candidates using continuation/reversal/AMD builders
    6. Outputs SMCCandidate models for processor

    Key design principle: the HTF pattern (BMS/SMS + OB + FVG + IDM) IS
    the candidate.  LTF confirmations (CHOCH, LTF BMS, RTO) are evaluated
    when available and stored as metadata on the candidate.  Their absence
    does NOT block candidate creation because:

    - Price may not have returned to the OB yet (RTO pending).
    - The execution engine monitors 24/7 and waits for the RTO + LTF
      confirmation before entering.
    - Blocking candidates here means the execution engine never even
      knows about the setup.

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
        self.amd_detector = AMDDetector(
            config, session_analyzer, dealing_range_analyzer
        )

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
        2. LTF: Refine entry (CHOCH, OB, FVG, sweeps) when available
        3. Validate zone rules
        4. Build candidates with LTF confirmation as metadata
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

        # -- HTF structural detection --
        htf_swing_highs = self.swing_analyzer.detect_swing_highs(htf_sequence)
        htf_swing_lows = self.swing_analyzer.detect_swing_lows(htf_sequence)

        htf_bms_bullish = self.bms_detector.detect_bullish_bms(
            htf_sequence, htf_swing_highs
        )
        htf_bms_bearish = self.bms_detector.detect_bearish_bms(
            htf_sequence, htf_swing_lows
        )

        htf_sms_bullish = self.sms_detector.detect_bullish_sms(
            htf_sequence, htf_swing_lows
        )
        htf_sms_bearish = self.sms_detector.detect_bearish_sms(
            htf_sequence, htf_swing_highs
        )

        # -- LTF structural detection --
        ltf_swing_highs = self.swing_analyzer.detect_swing_highs(ltf_sequence)
        ltf_swing_lows = self.swing_analyzer.detect_swing_lows(ltf_sequence)

        ltf_bms_bullish = self.bms_detector.detect_bullish_bms(
            ltf_sequence, ltf_swing_highs
        )
        ltf_bms_bearish = self.bms_detector.detect_bearish_bms(
            ltf_sequence, ltf_swing_lows
        )

        ltf_choch_bullish = self.choch_detector.detect_bullish_choch(
            ltf_sequence, ltf_swing_highs
        )
        ltf_choch_bearish = self.choch_detector.detect_bearish_choch(
            ltf_sequence, ltf_swing_lows
        )

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

        # -- Also detect FVGs on HTF for cross-timeframe FVG association --
        htf_fvgs = self.fvg_detector.detect_fvgs(htf_sequence)
        all_fvgs = ltf_fvgs + htf_fvgs

        all_inducements = ltf_inducement_bullish + ltf_inducement_bearish

        # -- Detect ALL liquidity sweeps on LTF (not just turtle soup) --
        ltf_all_sweeps = self.sweep_analyzer.detect_sweeps_in_sequence(
            ltf_sequence,
            ltf_swing_highs,
            ltf_swing_lows,
        )
        all_sweeps = ltf_all_sweeps + turtle_soup_long + turtle_soup_short

        # Diagnostic: log all detected structural elements
        self._logger.info(
            "smc_structural_detection_summary",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": str(htf_sequence.timeframe),
                "ltf_timeframe": str(ltf_sequence.timeframe),
                "htf_swing_highs": len(htf_swing_highs),
                "htf_swing_lows": len(htf_swing_lows),
                "htf_bms_bullish": len(htf_bms_bullish),
                "htf_bms_bearish": len(htf_bms_bearish),
                "htf_sms_bullish": len(htf_sms_bullish),
                "htf_sms_bearish": len(htf_sms_bearish),
                "ltf_swing_highs": len(ltf_swing_highs),
                "ltf_swing_lows": len(ltf_swing_lows),
                "ltf_bms_bullish": len(ltf_bms_bullish),
                "ltf_bms_bearish": len(ltf_bms_bearish),
                "ltf_choch_bullish": len(ltf_choch_bullish),
                "ltf_choch_bearish": len(ltf_choch_bearish),
                "ltf_fvgs": len(ltf_fvgs),
                "htf_fvgs": len(htf_fvgs),
                "inducements": len(all_inducements),
                "sweeps": len(all_sweeps),
                "has_retracement": retracement is not None,
                "has_amd_context": amd_context is not None,
            },
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
                    all_fvgs,
                    all_inducements,
                    all_sweeps,
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
                    all_fvgs,
                    all_inducements,
                    retracement,
                    ltf_swing_highs,
                    ltf_swing_lows,
                )
            )

        # Build Turtle Soup Candidates (Pattern 1/6)
        if self.config.enable_turtle_soup:
            candidates.extend(
                self._build_turtle_soup_candidates(
                    ltf_sequence,
                    turtle_soup_long,
                    turtle_soup_short,
                    ltf_swing_highs,
                    ltf_swing_lows,
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
                    all_fvgs,
                    all_inducements,
                    all_sweeps,
                    retracement,
                    ltf_swing_highs,
                    ltf_swing_lows,
                )
            )

        self._logger.info(
            "smc_detection_completed",
            extra={
                "symbol": htf_sequence.symbol,
                "total_candidates": len(candidates),
                "htf_bms_bullish": len(htf_bms_bullish),
                "htf_bms_bearish": len(htf_bms_bearish),
                "htf_sms_bullish": len(htf_sms_bullish),
                "htf_sms_bearish": len(htf_sms_bearish),
                "ltf_bms_bullish": len(ltf_bms_bullish),
                "ltf_bms_bearish": len(ltf_bms_bearish),
                "ltf_choch_bullish": len(ltf_choch_bullish),
                "ltf_choch_bearish": len(ltf_choch_bearish),
                "turtle_soup_long": len(turtle_soup_long),
                "turtle_soup_short": len(turtle_soup_short),
            },
        )

        return candidates

    # ------------------------------------------------------------------
    # Continuation candidates (Pattern 2/7: SH + BMS + RTO)
    # ------------------------------------------------------------------

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
        """Build continuation candidates.

        The HTF BMS is the primary structural requirement.  LTF BMS and
        CHOCH are evaluated when available and stored as metadata.  Their
        absence does NOT block candidate creation because price may not
        have returned to the OB yet.
        """
        candidates = []

        # -- Bullish continuation --
        latest_htf_bms_bullish = self.bms_detector.get_latest_bms(htf_bms_bullish)
        if latest_htf_bms_bullish:
            # Detect OBs from HTF BMS events (the displacement leg)
            for htf_bms in htf_bms_bullish:
                htf_ob = self.ob_detector.detect_bullish_ob(htf_sequence, htf_bms)
                if htf_ob:
                    # LTF confirmations are optional at detection time
                    ltf_choch = self.choch_detector.get_latest_choch(
                        ltf_choch_bullish
                    )
                    ltf_sweep = self._find_relevant_sweep(
                        sweeps, Direction.BULLISH, htf_bms
                    )

                    candidate = self.continuation_builder.build_bullish_continuation(
                        htf_sequence,
                        ltf_sequence,
                        latest_htf_bms_bullish,
                        ltf_sweep,
                        ltf_choch,
                        htf_bms,
                        htf_ob,
                        ltf_fvgs,
                        inducement_events,
                        retracement,
                    )
                    if candidate:
                        candidates.append(candidate)

            # Also check LTF OBs when LTF BMS exists (higher refinement)
            for ltf_bms in ltf_bms_bullish:
                ltf_ob = self.ob_detector.detect_bullish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue

                # Filter out truly mitigated OBs (1B)
                unmitigated = self.mitigation_detector.get_unmitigated_obs(
                    [ltf_ob], ltf_sequence,
                )
                if not unmitigated:
                    continue

                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bullish)
                ltf_sweep = self._find_relevant_sweep(
                    sweeps, Direction.BULLISH, ltf_bms
                )

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

            # Also detect OBs from LTF CHOCH events (1E)
            for ltf_choch_event in ltf_choch_bullish:
                choch_ob = self.ob_detector.detect_ob_from_choch(
                    ltf_sequence, ltf_choch_event,
                )
                if not choch_ob:
                    continue
                if choch_ob.direction != Direction.BULLISH:
                    continue

                ltf_sweep = self._find_relevant_sweep(
                    sweeps, Direction.BULLISH, latest_htf_bms_bullish,
                )

                candidate = self.continuation_builder.build_bullish_continuation(
                    htf_sequence,
                    ltf_sequence,
                    latest_htf_bms_bullish,
                    ltf_sweep,
                    ltf_choch_event,
                    latest_htf_bms_bullish,
                    choch_ob,
                    ltf_fvgs,
                    inducement_events,
                    retracement,
                )
                if candidate:
                    candidates.append(candidate)

            self._logger.info(
                "smc_continuation_bullish_summary",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_bms_count": len(htf_bms_bullish),
                    "ltf_bms_count": len(ltf_bms_bullish),
                    "ltf_choch_count": len(ltf_choch_bullish),
                    "candidates_built": len(
                        [c for c in candidates if c.direction == Direction.BULLISH]
                    ),
                },
            )

        # -- Bearish continuation --
        latest_htf_bms_bearish = self.bms_detector.get_latest_bms(htf_bms_bearish)
        if latest_htf_bms_bearish:
            for htf_bms in htf_bms_bearish:
                htf_ob = self.ob_detector.detect_bearish_ob(htf_sequence, htf_bms)
                if htf_ob:
                    ltf_choch = self.choch_detector.get_latest_choch(
                        ltf_choch_bearish
                    )
                    ltf_sweep = self._find_relevant_sweep(
                        sweeps, Direction.BEARISH, htf_bms
                    )

                    candidate = self.continuation_builder.build_bearish_continuation(
                        htf_sequence,
                        ltf_sequence,
                        latest_htf_bms_bearish,
                        ltf_sweep,
                        ltf_choch,
                        htf_bms,
                        htf_ob,
                        ltf_fvgs,
                        inducement_events,
                        retracement,
                    )
                    if candidate:
                        candidates.append(candidate)

            for ltf_bms in ltf_bms_bearish:
                ltf_ob = self.ob_detector.detect_bearish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue

                # Filter out truly mitigated OBs (1B)
                unmitigated = self.mitigation_detector.get_unmitigated_obs(
                    [ltf_ob], ltf_sequence,
                )
                if not unmitigated:
                    continue

                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bearish)
                ltf_sweep = self._find_relevant_sweep(
                    sweeps, Direction.BEARISH, ltf_bms
                )

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

            # Also detect OBs from LTF CHOCH events (1E)
            for ltf_choch_event in ltf_choch_bearish:
                choch_ob = self.ob_detector.detect_ob_from_choch(
                    ltf_sequence, ltf_choch_event,
                )
                if not choch_ob:
                    continue
                if choch_ob.direction != Direction.BEARISH:
                    continue

                ltf_sweep = self._find_relevant_sweep(
                    sweeps, Direction.BEARISH, latest_htf_bms_bearish,
                )

                candidate = self.continuation_builder.build_bearish_continuation(
                    htf_sequence,
                    ltf_sequence,
                    latest_htf_bms_bearish,
                    ltf_sweep,
                    ltf_choch_event,
                    latest_htf_bms_bearish,
                    choch_ob,
                    ltf_fvgs,
                    inducement_events,
                    retracement,
                )
                if candidate:
                    candidates.append(candidate)

            self._logger.info(
                "smc_continuation_bearish_summary",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_bms_count": len(htf_bms_bearish),
                    "ltf_bms_count": len(ltf_bms_bearish),
                    "ltf_choch_count": len(ltf_choch_bearish),
                    "candidates_built": len(
                        [c for c in candidates if c.direction == Direction.BEARISH]
                    ),
                },
            )

        return candidates

    # ------------------------------------------------------------------
    # Reversal candidates (Pattern 3/8: SMS + BMS + RTO)
    # ------------------------------------------------------------------

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
        ltf_swing_highs: list = None,
        ltf_swing_lows: list = None,
    ) -> list[SMCCandidate]:
        """Build reversal candidates.

        The HTF SMS (failure swing) is the primary structural requirement.
        LTF BMS and CHOCH are evaluated when available.  Their absence
        does NOT block candidate creation.
        """
        candidates = []

        # -- Bullish reversal --
        latest_htf_sms_bullish = self.sms_detector.get_latest_sms(htf_sms_bullish)
        if latest_htf_sms_bullish:
            # Try LTF-refined OBs first (higher precision)
            for ltf_bms in ltf_bms_bullish:
                ltf_ob = self.ob_detector.detect_bullish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue

                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bullish)

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
                    swing_highs=ltf_swing_highs,
                )
                if candidate:
                    candidates.append(candidate)

            # If no LTF BMS yet, build from HTF structure alone
            if not ltf_bms_bullish:
                for htf_sms in htf_sms_bullish:
                    # Use the SMS reversal candle to find an OB on HTF
                    htf_bms_from_sms = self.bms_detector.detect_bullish_bms(
                        htf_sequence, self.swing_analyzer.detect_swing_highs(htf_sequence)
                    )
                    latest_htf_bms = self.bms_detector.get_latest_bms(htf_bms_from_sms)
                    if not latest_htf_bms:
                        continue

                    htf_ob = self.ob_detector.detect_bullish_ob(
                        htf_sequence, latest_htf_bms
                    )
                    if not htf_ob:
                        continue

                    candidate = self.reversal_builder.build_bullish_sms_reversal(
                        htf_sequence,
                        ltf_sequence,
                        latest_htf_sms_bullish,
                        latest_htf_bms,
                        None,  # No LTF CHOCH yet
                        htf_ob,
                        ltf_fvgs,
                        inducement_events,
                        retracement,
                        swing_highs=ltf_swing_highs,
                    )
                    if candidate:
                        candidates.append(candidate)

            self._logger.info(
                "smc_reversal_bullish_summary",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_sms_count": len(htf_sms_bullish),
                    "ltf_bms_count": len(ltf_bms_bullish),
                    "ltf_choch_count": len(ltf_choch_bullish),
                    "candidates_built": len(
                        [c for c in candidates if c.direction == Direction.BULLISH]
                    ),
                },
            )

        # -- Bearish reversal --
        latest_htf_sms_bearish = self.sms_detector.get_latest_sms(htf_sms_bearish)
        if latest_htf_sms_bearish:
            for ltf_bms in ltf_bms_bearish:
                ltf_ob = self.ob_detector.detect_bearish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue

                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bearish)

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
                    swing_lows=ltf_swing_lows,
                )
                if candidate:
                    candidates.append(candidate)

            if not ltf_bms_bearish:
                for htf_sms in htf_sms_bearish:
                    htf_bms_from_sms = self.bms_detector.detect_bearish_bms(
                        htf_sequence, self.swing_analyzer.detect_swing_lows(htf_sequence)
                    )
                    latest_htf_bms = self.bms_detector.get_latest_bms(htf_bms_from_sms)
                    if not latest_htf_bms:
                        continue

                    htf_ob = self.ob_detector.detect_bearish_ob(
                        htf_sequence, latest_htf_bms
                    )
                    if not htf_ob:
                        continue

                    candidate = self.reversal_builder.build_bearish_sms_reversal(
                        htf_sequence,
                        ltf_sequence,
                        latest_htf_sms_bearish,
                        latest_htf_bms,
                        None,  # No LTF CHOCH yet
                        htf_ob,
                        ltf_fvgs,
                        inducement_events,
                        retracement,
                        swing_lows=ltf_swing_lows,
                    )
                    if candidate:
                        candidates.append(candidate)

            self._logger.info(
                "smc_reversal_bearish_summary",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_sms_count": len(htf_sms_bearish),
                    "ltf_bms_count": len(ltf_bms_bearish),
                    "ltf_choch_count": len(ltf_choch_bearish),
                    "candidates_built": len(
                        [c for c in candidates if c.direction == Direction.BEARISH]
                    ),
                },
            )

        return candidates

    # ------------------------------------------------------------------
    # Turtle Soup candidates (Pattern 1/6)
    # ------------------------------------------------------------------

    def _build_turtle_soup_candidates(
        self,
        ltf_sequence: CandleSequence,
        turtle_soup_long: list,
        turtle_soup_short: list,
        ltf_swing_highs: list = None,
        ltf_swing_lows: list = None,
    ) -> list[SMCCandidate]:
        candidates = []

        for sweep in turtle_soup_long:
            candidate = self.reversal_builder.build_turtle_soup_long(
                ltf_sequence,
                sweep,
                swing_highs=ltf_swing_highs,
            )
            if candidate:
                candidates.append(candidate)

        for sweep in turtle_soup_short:
            candidate = self.reversal_builder.build_turtle_soup_short(
                ltf_sequence,
                sweep,
                swing_lows=ltf_swing_lows,
            )
            if candidate:
                candidates.append(candidate)

        return candidates

    # ------------------------------------------------------------------
    # AMD candidates (Pattern 4/9)
    # ------------------------------------------------------------------

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
        ltf_swing_highs: list = None,
        ltf_swing_lows: list = None,
    ) -> list[SMCCandidate]:
        candidates = []

        if amd_context.distribution_direction == Direction.BULLISH:
            for ltf_bms in ltf_bms_bullish:
                ltf_ob = self.ob_detector.detect_bullish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue

                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bullish)
                ltf_sweep = self._find_relevant_sweep(
                    sweeps, Direction.BULLISH, ltf_bms
                )

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
                    swing_highs=ltf_swing_highs,
                )

                if candidate:
                    candidates.append(candidate)

        elif amd_context.distribution_direction == Direction.BEARISH:
            for ltf_bms in ltf_bms_bearish:
                ltf_ob = self.ob_detector.detect_bearish_ob(ltf_sequence, ltf_bms)
                if not ltf_ob:
                    continue

                ltf_choch = self.choch_detector.get_latest_choch(ltf_choch_bearish)
                ltf_sweep = self._find_relevant_sweep(
                    sweeps, Direction.BEARISH, ltf_bms
                )

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
                    swing_lows=ltf_swing_lows,
                )

                if candidate:
                    candidates.append(candidate)

        return candidates

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        bms: BreakInMarketStructure,
    ) -> Optional[LiquiditySweep]:
        """Find a liquidity sweep structurally related to a BMS event.

        Uses candle-index proximity instead of clock time so the
        association works correctly across all timeframes.  A sweep
        that occurs within ``_SWEEP_MAX_CANDLE_DISTANCE`` candles of
        the BMS is considered structurally related.

        Sweeps are conditional events — they don't happen 100% of the
        time.  Returning None is perfectly valid and the builders
        handle it gracefully.
        """
        max_distance = getattr(
            self.config, "sweep_max_candle_distance",
            _SWEEP_MAX_CANDLE_DISTANCE_DEFAULT,
        )
        best_sweep: Optional[LiquiditySweep] = None
        best_distance = max_distance + 1

        for sweep in sweeps:
            if sweep is None:
                continue

            distance = abs(sweep.candle_index - bms.candle_index)
            if distance > max_distance:
                continue

            if direction == Direction.BULLISH and sweep.liquidity_type.value in (
                "SSL", "EQUAL_LOWS", "PDL_SWEEP",
            ):
                if distance < best_distance:
                    best_distance = distance
                    best_sweep = sweep
            elif direction == Direction.BEARISH and sweep.liquidity_type.value in (
                "BSL", "EQUAL_HIGHS", "PDH_SWEEP",
            ):
                if distance < best_distance:
                    best_distance = distance
                    best_sweep = sweep

        return best_sweep
