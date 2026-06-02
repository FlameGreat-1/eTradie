from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.common.utils.price.stop_loss import (
    compute_structural_stop_loss,
    resolve_min_tp_rr,
)
from engine.ta.constants import Direction, CandidatePattern
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.models.candidate import SMCCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.liquidity_event import LiquiditySweep, InducementEvent
from engine.ta.models.structure_event import (
    BreakInMarketStructure,
    ChangeOfCharacter,
    ShiftInMarketStructure,
)
from engine.ta.models.zone import OrderBlock, FairValueGap
from engine.ta.smc.builders.fib_leg import (
    select_leg_for_sms_bms_rto,
)
from engine.ta.smc.config import SMCConfig
from engine.ta.smc.validators.zone.validator import ZoneValidator
from engine.ta.smc.validators.ltf.confirmation import LTFConfirmationValidator

logger = get_logger(__name__)


class ReversalBuilder:
    """
    Builds reversal-style SMC candidates.

    Pattern 3/8: SMS + BMS + RTO (Bullish/Bearish Reversal)
    - Price in trend fails to break last swing high/low (SMS - Failure Swing)
    - BMS confirms trend exhaustion and reversal
    - Price retraces to Order Block
    - Entry at OB with SL beyond OB
    - Target: next liquidity draw

    Pattern 1/6: Turtle Soup (Standard)
    - Price raids BSL/SSL zone
    - Sweeps 5-20+ pips above/below level
    - Single candle closes back inside
    - Entry against sweep
    - Minimum 10 pip SL (Universal Rule 12)

    Pattern 5/10: Turtle Soup + SH + BMS + RTO (Combined - Highest Confluence)
    - Turtle Soup sweep also creates BMS
    - Price retraces to OB
    - Both setups confirm simultaneously

    Fibonacci leg (SMC-MIT-003 / Universal Rule 6):
    - Every build_* method constructs its own per-candidate leg from
      the candidate's structural endpoints, direction-matched:
        SMS reversal  -> select_leg_for_sms_bms_rto
                         (htf_sms.failed_level <-> ltf_bms.breakout_price)
        Turtle soup L -> select_leg_for_turtle_soup_long
                         (sweep.swept_level -> nearest swing high above)
        Turtle soup S -> select_leg_for_turtle_soup_short
                         (nearest swing low below -> sweep.swept_level)
    - No fallback: when endpoints are missing the per-candidate leg
      is None and the candidate is emitted with fib_level=None and
      no fib_context in metadata.  We never use a global HTF leg.

    LTF confirmations (CHOCH, LTF BMS, RTO) are evaluated when
    available and stored as metadata.  Their absence does NOT block
    candidate creation.
    """

    def __init__(
        self,
        config: SMCConfig,
        zone_validator: ZoneValidator,
        ltf_validator: LTFConfirmationValidator,
        fibonacci_analyzer: FibonacciAnalyzer,
    ) -> None:
        self.config = config
        self.zone_validator = zone_validator
        self.ltf_validator = ltf_validator
        self.fibonacci_analyzer = fibonacci_analyzer
        self._logger = get_logger(__name__)

    def build_bullish_sms_reversal(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        htf_sms: ShiftInMarketStructure,
        ltf_bms: BreakInMarketStructure,
        ltf_choch: Optional[ChangeOfCharacter],
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
        swing_highs: Optional[list[SwingHigh]] = None,
    ) -> Optional[SMCCandidate]:
        """Build an SMS_BMS_RTO_BULLISH candidate.

        The Fibonacci leg for this candidate is built inline from
        ``htf_sms`` + ``ltf_bms`` via ``select_leg_for_sms_bms_rto``.
        """
        if htf_sms.direction != Direction.BULLISH:
            return None

        if ltf_bms.direction != Direction.BULLISH:
            return None

        if ltf_ob.direction != Direction.BULLISH:
            return None

        candidate_retracement = select_leg_for_sms_bms_rto(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            htf_sms=htf_sms,
            ltf_bms=ltf_bms,
            is_bullish=True,
        )

        if not self.zone_validator.validate_all_ob_rules(
            ltf_ob,
            ltf_fvgs,
            [],
            inducement_events,
            candidate_retracement,
            ltf_sequence,
            [],
        ):
            return None

        current_price = ltf_sequence.candles[-1].close

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            None,  # No sweep required for reversal
            ltf_choch,
            ltf_bms,
            ltf_ob,
            inducement_events,
            ltf_sequence,
            current_price,
            ltf_fvgs=ltf_fvgs,
        )

        confluences = self._count_sms_confluences(
            htf_sms,
            ltf_bms,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            candidate_retracement,
            inducement_events,
        )

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = ltf_ob.midpoint
        stop_loss = self._compute_structural_stop_loss(
            ob=ltf_ob,
            direction=Direction.BULLISH,
            protective_level=htf_sms.failed_level,
        )
        take_profit = self._find_nearest_bsl_target(
            entry_price, swing_highs or [], pip_val,
            stop_loss=stop_loss,
            min_tp_rr=resolve_min_tp_rr(ltf_ob.timeframe),
        )

        associated_fvg = self.zone_validator.get_associated_fvg(ltf_ob, ltf_fvgs)

        relevant_idm = self.zone_validator.select_relevant_inducement(
            ltf_ob,
            Direction.BULLISH,
            inducement_events,
            bms_breakout_price=ltf_bms.breakout_price,
        )

        candidate = SMCCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.SMS_BMS_RTO_BULLISH,
            direction=Direction.BULLISH,
            timestamp=ltf_sequence.candles[-1].timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=htf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
            sms_detected=True,
            sms_price=htf_sms.failed_level,
            sms_timestamp=htf_sms.timestamp,
            bms_detected=True,
            bms_price=ltf_bms.breakout_price,
            bms_timestamp=ltf_bms.timestamp,
            choch_detected=ltf_choch is not None,
            choch_price=ltf_choch.breakout_price if ltf_choch else None,
            choch_timestamp=ltf_choch.timestamp if ltf_choch else None,
            order_block_upper=ltf_ob.upper_bound,
            order_block_lower=ltf_ob.lower_bound,
            order_block_timestamp=ltf_ob.timestamp,
            fvg_upper=associated_fvg.upper_bound if associated_fvg else None,
            fvg_lower=associated_fvg.lower_bound if associated_fvg else None,
            fvg_timestamp=associated_fvg.timestamp if associated_fvg else None,
            inducement_cleared=relevant_idm is not None,
            inducement_level=relevant_idm.inducement_level if relevant_idm else None,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            displacement_pips=ltf_bms.displacement_pips,
            fib_level=self._fib_level_str(entry_price, candidate_retracement),
            metadata=self._build_metadata(
                {"confluences": confluences},
                entry_price,
                candidate_retracement,
            ),
        )

        self._logger.info(
            "bullish_sms_reversal_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "ltf_confirmed": ltf_confirmed,
                "has_per_candidate_fib_leg": candidate_retracement is not None,
            },
        )

        return candidate

    def build_bearish_sms_reversal(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        htf_sms: ShiftInMarketStructure,
        ltf_bms: BreakInMarketStructure,
        ltf_choch: Optional[ChangeOfCharacter],
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
        swing_lows: Optional[list[SwingLow]] = None,
    ) -> Optional[SMCCandidate]:
        """Build an SMS_BMS_RTO_BEARISH candidate.

        The Fibonacci leg for this candidate is built inline from
        ``htf_sms`` + ``ltf_bms`` via ``select_leg_for_sms_bms_rto``.
        """
        if htf_sms.direction != Direction.BEARISH:
            return None

        if ltf_bms.direction != Direction.BEARISH:
            return None

        if ltf_ob.direction != Direction.BEARISH:
            return None

        candidate_retracement = select_leg_for_sms_bms_rto(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            htf_sms=htf_sms,
            ltf_bms=ltf_bms,
            is_bullish=False,
        )

        if not self.zone_validator.validate_all_ob_rules(
            ltf_ob,
            ltf_fvgs,
            [],
            inducement_events,
            candidate_retracement,
            ltf_sequence,
            [],
        ):
            return None

        current_price = ltf_sequence.candles[-1].close

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            None,
            ltf_choch,
            ltf_bms,
            ltf_ob,
            inducement_events,
            ltf_sequence,
            current_price,
            ltf_fvgs=ltf_fvgs,
        )

        confluences = self._count_sms_confluences(
            htf_sms,
            ltf_bms,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            candidate_retracement,
            inducement_events,
        )

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = ltf_ob.midpoint
        stop_loss = self._compute_structural_stop_loss(
            ob=ltf_ob,
            direction=Direction.BEARISH,
            protective_level=htf_sms.failed_level,
        )
        take_profit = self._find_nearest_ssl_target(
            entry_price, swing_lows or [], pip_val,
            stop_loss=stop_loss,
            min_tp_rr=resolve_min_tp_rr(ltf_ob.timeframe),
        )

        associated_fvg = self.zone_validator.get_associated_fvg(ltf_ob, ltf_fvgs)

        relevant_idm = self.zone_validator.select_relevant_inducement(
            ltf_ob,
            Direction.BEARISH,
            inducement_events,
            bms_breakout_price=ltf_bms.breakout_price,
        )

        candidate = SMCCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.SMS_BMS_RTO_BEARISH,
            direction=Direction.BEARISH,
            timestamp=ltf_sequence.candles[-1].timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=htf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
            sms_detected=True,
            sms_price=htf_sms.failed_level,
            sms_timestamp=htf_sms.timestamp,
            bms_detected=True,
            bms_price=ltf_bms.breakout_price,
            bms_timestamp=ltf_bms.timestamp,
            choch_detected=True,
            choch_price=ltf_choch.breakout_price if ltf_choch else None,
            choch_timestamp=ltf_choch.timestamp if ltf_choch else None,
            order_block_upper=ltf_ob.upper_bound,
            order_block_lower=ltf_ob.lower_bound,
            order_block_timestamp=ltf_ob.timestamp,
            fvg_upper=associated_fvg.upper_bound if associated_fvg else None,
            fvg_lower=associated_fvg.lower_bound if associated_fvg else None,
            fvg_timestamp=associated_fvg.timestamp if associated_fvg else None,
            inducement_cleared=relevant_idm is not None,
            inducement_level=relevant_idm.inducement_level if relevant_idm else None,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            displacement_pips=ltf_bms.displacement_pips,
            fib_level=self._fib_level_str(entry_price, candidate_retracement),
            metadata=self._build_metadata(
                {"confluences": confluences},
                entry_price,
                candidate_retracement,
            ),
        )

        self._logger.info(
            "bearish_sms_reversal_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "ltf_confirmed": ltf_confirmed,
                "has_per_candidate_fib_leg": candidate_retracement is not None,
            },
        )

        return candidate

    def build_turtle_soup_long(
        self,
        ltf_sequence: CandleSequence,
        sweep: LiquiditySweep,
        swing_highs: Optional[list[SwingHigh]] = None,
    ) -> Optional[SMCCandidate]:
        """Build a TURTLE_SOUP_LONG candidate.

        Per-candidate fib leg is drawn from the swept SSL level up to
        the nearest opposing swing high (via
        ``select_leg_for_turtle_soup_long``).  When no such swing
        high is available, ``fib_context`` is omitted from metadata
        — no fabricated leg.
        """
        if not sweep.closed_back_inside:
            return None

        if sweep.sweep_pips < self.config.turtle_soup_min_pips:
            return None

        if not self.ltf_validator.validate_session_timing(ltf_sequence):
            return None

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = sweep.swept_level
        # SL beyond the swept extreme (the real invalidation of a turtle
        # soup), using the timeframe-aware structural buffer.  The turtle
        # minimum is preserved as an additional floor.
        structural_sl = compute_structural_stop_loss(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            direction=Direction.BULLISH,
            invalidation_level=sweep.sweep_low,
        )
        turtle_min_sl = sweep.sweep_low - (
            self.config.turtle_soup_min_sl_pips * pip_val
        )
        stop_loss = min(structural_sl, turtle_min_sl)
        take_profit = self._find_nearest_bsl_target(
            entry_price, swing_highs or [], pip_val,
            stop_loss=stop_loss,
            min_tp_rr=resolve_min_tp_rr(ltf_sequence.timeframe),
        )

        # Turtle Soup fib context is trivial by construction
        # (entry_price == sweep.swept_level == leg anchor => 1.0).
        # See commit message for rationale; we deliberately emit no
        # fib_context and no fib_level on this pattern.
        turtle_metadata: dict = {}
        sweep_context = self.zone_validator.build_sweep_context(sweep, ob=None)
        if sweep_context is not None:
            turtle_metadata["sweep_context"] = sweep_context

        candidate = SMCCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.TURTLE_SOUP_LONG,
            direction=Direction.BULLISH,
            timestamp=sweep.timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=ltf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
            liquidity_swept=True,
            swept_level=sweep.swept_level,
            sweep_timestamp=sweep.timestamp,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=sweep.timestamp,
            fib_level=None,
            metadata=turtle_metadata,
        )

        self._logger.info(
            "turtle_soup_long_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "sweep_pips": sweep.sweep_pips,
            },
        )

        return candidate

    def build_turtle_soup_short(
        self,
        ltf_sequence: CandleSequence,
        sweep: LiquiditySweep,
        swing_lows: Optional[list[SwingLow]] = None,
    ) -> Optional[SMCCandidate]:
        """Build a TURTLE_SOUP_SHORT candidate.

        Per-candidate fib leg is drawn from the nearest opposing
        swing low up to the swept BSL level (via
        ``select_leg_for_turtle_soup_short``).  When no such swing
        low is available, ``fib_context`` is omitted from metadata.
        """
        if not sweep.closed_back_inside:
            return None

        if sweep.sweep_pips < self.config.turtle_soup_min_pips:
            return None

        if not self.ltf_validator.validate_session_timing(ltf_sequence):
            return None

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = sweep.swept_level
        # SL beyond the swept extreme (the real invalidation of a turtle
        # soup), using the timeframe-aware structural buffer.  The turtle
        # minimum is preserved as an additional floor.
        structural_sl = compute_structural_stop_loss(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            direction=Direction.BEARISH,
            invalidation_level=sweep.sweep_high,
        )
        turtle_min_sl = sweep.sweep_high + (
            self.config.turtle_soup_min_sl_pips * pip_val
        )
        stop_loss = max(structural_sl, turtle_min_sl)
        take_profit = self._find_nearest_ssl_target(
            entry_price, swing_lows or [], pip_val,
            stop_loss=stop_loss,
            min_tp_rr=resolve_min_tp_rr(ltf_sequence.timeframe),
        )

        # Turtle Soup fib context is trivial by construction
        # (entry_price == sweep.swept_level == leg anchor => 1.0).
        # See commit message for rationale; we deliberately emit no
        # fib_context and no fib_level on this pattern.
        turtle_metadata: dict = {}
        sweep_context = self.zone_validator.build_sweep_context(sweep, ob=None)
        if sweep_context is not None:
            turtle_metadata["sweep_context"] = sweep_context

        candidate = SMCCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.TURTLE_SOUP_SHORT,
            direction=Direction.BEARISH,
            timestamp=sweep.timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=ltf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
            liquidity_swept=True,
            swept_level=sweep.swept_level,
            sweep_timestamp=sweep.timestamp,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=sweep.timestamp,
            fib_level=None,
            metadata=turtle_metadata,
        )

        self._logger.info(
            "turtle_soup_short_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "sweep_pips": sweep.sweep_pips,
            },
        )

        return candidate

    def _count_sms_confluences(
        self,
        sms: ShiftInMarketStructure,
        bms: BreakInMarketStructure,
        choch: Optional[ChangeOfCharacter],
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        retracement: Optional[FibonacciRetracement],
        inducement_events: list[InducementEvent],
    ) -> int:
        """Count all confluences for a reversal candidate.

        Informational metadata for the LLM.  It is NEVER used to
        gate or reject a candidate.  ``retracement`` here is the
        per-candidate leg built in the corresponding build_* method.
        """
        confluences = 0

        # 1. HTF SMS (failure swing) detected
        confluences += 1

        # 2. BMS detected
        confluences += 1

        # 3. BMS is confirmed (multi-candle confirmation passed)
        if bms.confirmed:
            confluences += 1

        # 4. LTF CHOCH (earliest signal of order flow shift)
        if choch is not None:
            confluences += 1

        # 5. FVG alignment with OB direction
        if any(fvg.direction == ob.direction for fvg in fvgs):
            confluences += 1

        # 6. Fibonacci / OTE confluence (0-2 points), per-candidate leg
        fib_score = self.zone_validator.score_ob_fib_confluence(ob, retracement)
        if fib_score >= 3:
            confluences += 2  # OTE pocket = strong confluence
        elif fib_score >= 2:
            confluences += 1  # Correct premium/discount zone

        # 7. Inducement cleared
        if any(idm.cleared for idm in inducement_events):
            confluences += 1

        # 8. OB displacement strength (strong displacement = institutional)
        if ob.displacement_pips > 0:
            pip_val = float(get_pip_value(ob.symbol))
            displacement_in_pips = ob.displacement_pips / pip_val
            if displacement_in_pips >= self.config.bms_strong_displacement_pips:
                confluences += 1

        # 9. OB is a breaker block (failed OB flipped = stronger zone)
        if ob.is_breaker:
            confluences += 1

        return confluences

    def _compute_structural_stop_loss(
        self,
        ob: OrderBlock,
        direction: Direction,
        protective_level: Optional[float],
    ) -> float:
        """Compute SL beyond the pattern's REAL structural invalidation.

        For an SMS reversal ``protective_level`` is ``htf_sms.failed_
        level`` -- the swing the market failed to break, i.e. the true
        invalidation.  The SL is seated beyond it via the shared
        timeframe-aware helper, with the OB edge as an inner guard.
        When ``protective_level`` is None the OB edge becomes the
        anchor (still buffered structurally by timeframe).
        """
        invalidation_level = (
            protective_level
            if protective_level is not None
            else (
                ob.lower_bound
                if direction == Direction.BULLISH
                else ob.upper_bound
            )
        )
        ob_inner_edge = (
            ob.lower_bound if direction == Direction.BULLISH else ob.upper_bound
        )
        return compute_structural_stop_loss(
            symbol=ob.symbol,
            timeframe=ob.timeframe,
            direction=direction,
            invalidation_level=invalidation_level,
            ob_inner_edge=ob_inner_edge,
        )

    def _find_nearest_bsl_target(
        self,
        entry_price: float,
        swing_highs: list[SwingHigh],
        pip_val: float,
        stop_loss: Optional[float] = None,
        min_tp_rr: Optional[float] = None,
    ) -> Optional[float]:
        """Find the nearest BSL (swing high) above entry as the TP target.

        Only swings whose distance from ``entry_price`` is at least
        ``min_tp_rr * |entry_price - stop_loss|`` are considered, where
        ``min_tp_rr`` is the timeframe-resolved reward-to-risk MULTIPLE
        (never below the rulebook's lowest style minimum).  Falls back
        to ``config.min_take_profit_rr`` when not supplied.
        """
        rr = min_tp_rr if min_tp_rr is not None else self.config.min_take_profit_rr
        min_reward = 0.0
        if stop_loss is not None:
            sl_distance = abs(entry_price - stop_loss)
            min_reward = sl_distance * rr

        candidates = [
            sh.price for sh in swing_highs
            if sh.price > entry_price
            and (sh.price - entry_price) >= min_reward
        ]
        if candidates:
            return min(candidates)
        return None

    def _find_nearest_ssl_target(
        self,
        entry_price: float,
        swing_lows: list[SwingLow],
        pip_val: float,
        stop_loss: Optional[float] = None,
        min_tp_rr: Optional[float] = None,
    ) -> Optional[float]:
        """Find the nearest SSL (swing low) below entry as the TP target.

        Only swings whose distance from ``entry_price`` is at least
        ``min_tp_rr * |entry_price - stop_loss|`` are considered, where
        ``min_tp_rr`` is the timeframe-resolved reward-to-risk MULTIPLE
        (never below the rulebook's lowest style minimum).  Falls back
        to ``config.min_take_profit_rr`` when not supplied.
        """
        rr = min_tp_rr if min_tp_rr is not None else self.config.min_take_profit_rr
        min_reward = 0.0
        if stop_loss is not None:
            sl_distance = abs(entry_price - stop_loss)
            min_reward = sl_distance * rr

        candidates = [
            sl.price for sl in swing_lows
            if sl.price < entry_price
            and (entry_price - sl.price) >= min_reward
        ]
        if candidates:
            return max(candidates)
        return None

    def _fib_level_str(
        self,
        price: float,
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[str]:
        """Return the exact retracement percentage the entry price falls on,
        formatted to 3 decimals.  Returns None when no retracement is
        available or the price falls outside the swing leg.  ``retracement``
        is the per-candidate leg built inline in the build_* methods.
        """
        context = self.zone_validator.build_fib_context(price, retracement)
        if context is None:
            return None
        return f"{context['percentage']:.3f}"

    def _build_metadata(
        self,
        base: dict,
        price: float,
        retracement: Optional[FibonacciRetracement],
        sweep: Optional[LiquiditySweep] = None,
        ob: Optional[OrderBlock] = None,
    ) -> dict:
        """Attach fib_context and sweep_context to the metadata dict.

        The returned dict always contains ``base`` plus, when the
        corresponding inputs are available:

        - ``fib_context`` — structured Fibonacci context from
          ``ZoneValidator.build_fib_context`` (see SMC-MIT-003),
          measured against the **per-candidate** leg.
        - ``sweep_context`` — structured liquidity-sweep context from
          ``ZoneValidator.build_sweep_context`` (see SMC-LIQ-003).

        When the per-candidate leg is None (e.g. missing SMS or BMS
        endpoint), ``fib_context`` is simply omitted — no fabricated
        value.
        """
        metadata = dict(base)

        fib_context = self.zone_validator.build_fib_context(price, retracement)
        if fib_context is not None:
            metadata["fib_context"] = fib_context

        sweep_context = self.zone_validator.build_sweep_context(sweep, ob)
        if sweep_context is not None:
            metadata["sweep_context"] = sweep_context

        return metadata
