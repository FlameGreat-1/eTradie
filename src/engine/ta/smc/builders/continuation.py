from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.common.utils.price.stop_loss import compute_structural_stop_loss
from engine.ta.constants import Direction, CandidatePattern
from engine.ta.models.candidate import SMCCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.liquidity_event import LiquiditySweep, InducementEvent
from engine.ta.models.structure_event import BreakInMarketStructure, ChangeOfCharacter
from engine.ta.models.zone import OrderBlock, FairValueGap
from engine.ta.smc.builders.fib_leg import select_leg_for_sh_bms_rto
from engine.ta.smc.config import SMCConfig
from engine.ta.smc.validators.zone.validator import ZoneValidator
from engine.ta.smc.validators.ltf.confirmation import LTFConfirmationValidator

logger = get_logger(__name__)


class ContinuationBuilder:
    """
    Builds continuation-style SMC candidates.

    Pattern 2/7: SH + BMS + RTO (Bullish/Bearish)
    - Stop Hunt (liquidity sweep) above/below key level
    - BMS confirms the SH was real
    - Price retraces to Order Block
    - Entry at OB with SL beyond OB
    - Target: next liquidity draw (SSL/BSL)

    Structural validity gates (hard requirements):
    - HTF BMS alignment (Universal Rule 2)
    - Direction alignment (HTF BMS, LTF BMS, OB must agree)
    - OB passes all zone rules (unmitigated, has FVG, has liquidity)

    Fibonacci leg (SMC-MIT-003 / Universal Rule 6):
    - The leg used for OTE/fib-context scoring is built per-candidate
      from the candidate's own sweep and BMS endpoints via
      ``smc.builders.fib_leg.select_leg_for_sh_bms_rto``.  It is
      direction-matched to the candidate.
    - No fallback: when the sweep is absent the per-candidate leg is
      None and the candidate is emitted with fib_level=None and no
      fib_context in metadata.  We never use a global HTF leg.

    Confluence scoring (informational metadata for the LLM):
    - The confluence count is stored on the candidate so the LLM can
      see how many structural factors are present.  It is NEVER used
      to reject a candidate.  The LLM performs its own scoring with
      full macro/Wyckoff/cross-TF context.

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

    def build_bullish_continuation(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        htf_bms: BreakInMarketStructure,
        ltf_sweep: Optional[LiquiditySweep],
        ltf_choch: Optional[ChangeOfCharacter],
        ltf_bms: BreakInMarketStructure,
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
    ) -> Optional[SMCCandidate]:
        """Build a SH_BMS_RTO_BULLISH candidate.

        The Fibonacci leg for this candidate is built in-method from
        ``ltf_sweep`` and ``ltf_bms`` via
        ``select_leg_for_sh_bms_rto`` and used for every fib-related
        computation below.
        """
        # --- Hard structural gates (objective, binary) ---
        if htf_bms.direction != Direction.BULLISH:
            return None

        if ltf_bms.direction != Direction.BULLISH:
            return None

        if ltf_ob.direction != Direction.BULLISH:
            return None

        # --- Per-candidate Fibonacci leg (SMC-MIT-003) ---
        candidate_retracement = select_leg_for_sh_bms_rto(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            htf_bms=ltf_bms,
            sweep=ltf_sweep,
            is_bullish=True,
        )

        if not self.zone_validator.validate_all_ob_rules(
            ltf_ob,
            ltf_fvgs,
            [ltf_sweep] if ltf_sweep else [],
            inducement_events,
            candidate_retracement,
            ltf_sequence,
            [],
        ):
            return None

        # --- LTF confirmation (execution timing, not detection gate) ---
        current_price = ltf_sequence.candles[-1].close

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sweep,
            ltf_choch,
            ltf_bms,
            ltf_ob,
            inducement_events,
            ltf_sequence,
            current_price,
            ltf_fvgs=ltf_fvgs,
        )

        # --- Confluence scoring (informational metadata for the LLM) ---
        confluences = self._count_confluences(
            htf_bms,
            ltf_bms,
            ltf_sweep,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            candidate_retracement,
            inducement_events,
        )

        # --- Build the candidate ---
        entry_price = ltf_ob.midpoint
        pip_val = float(get_pip_value(ltf_sequence.symbol))
        stop_loss = self._compute_structural_stop_loss(
            ob=ltf_ob,
            direction=Direction.BULLISH,
            protective_level=(
                ltf_sweep.sweep_low if ltf_sweep is not None else None
            ),
        )

        # take_profit is Optional[float] on SMCCandidate by design.  When
        # no swing clears the 1:1 R:R floor we emit None rather than
        # substituting htf_bms.breakout_price, which has no directional
        # guarantee relative to the current entry and produced inverted
        # TPs (bullish candidate, TP below entry) visible in
        # diagnostic_results.json.  Downstream systems (LLM, execution)
        # handle a null TP explicitly; we never fabricate one.
        take_profit = self._find_nearest_bsl_target(
            entry_price,
            self._get_swing_highs_from_sequence(htf_sequence),
            pip_val,
            stop_loss=stop_loss,
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
            pattern=CandidatePattern.SH_BMS_RTO_BULLISH,
            direction=Direction.BULLISH,
            timestamp=ltf_sequence.candles[-1].timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=htf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
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
            liquidity_swept=ltf_sweep is not None,
            swept_level=ltf_sweep.swept_level if ltf_sweep else None,
            sweep_timestamp=ltf_sweep.timestamp if ltf_sweep else None,
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
                sweep=ltf_sweep,
                ob=ltf_ob,
            ),
        )

        self._logger.info(
            "bullish_continuation_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confluences": confluences,
                "ltf_confirmed": ltf_confirmed,
                "has_per_candidate_fib_leg": candidate_retracement is not None,
            },
        )

        return candidate

    def build_bearish_continuation(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        htf_bms: BreakInMarketStructure,
        ltf_sweep: Optional[LiquiditySweep],
        ltf_choch: Optional[ChangeOfCharacter],
        ltf_bms: BreakInMarketStructure,
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
    ) -> Optional[SMCCandidate]:
        """Build a SH_BMS_RTO_BEARISH candidate.

        The Fibonacci leg for this candidate is built in-method from
        ``ltf_sweep`` and ``ltf_bms`` via
        ``select_leg_for_sh_bms_rto`` and used for every fib-related
        computation below.
        """
        # --- Hard structural gates (objective, binary) ---
        if htf_bms.direction != Direction.BEARISH:
            return None

        if ltf_bms.direction != Direction.BEARISH:
            return None

        if ltf_ob.direction != Direction.BEARISH:
            return None

        # --- Per-candidate Fibonacci leg (SMC-MIT-003) ---
        candidate_retracement = select_leg_for_sh_bms_rto(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            htf_bms=ltf_bms,
            sweep=ltf_sweep,
            is_bullish=False,
        )

        if not self.zone_validator.validate_all_ob_rules(
            ltf_ob,
            ltf_fvgs,
            [ltf_sweep] if ltf_sweep else [],
            inducement_events,
            candidate_retracement,
            ltf_sequence,
            [],
        ):
            return None

        # --- LTF confirmation (execution timing, not detection gate) ---
        current_price = ltf_sequence.candles[-1].close

        ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sweep,
            ltf_choch,
            ltf_bms,
            ltf_ob,
            inducement_events,
            ltf_sequence,
            current_price,
            ltf_fvgs=ltf_fvgs,
        )

        # --- Confluence scoring (informational metadata for the LLM) ---
        confluences = self._count_confluences(
            htf_bms,
            ltf_bms,
            ltf_sweep,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            candidate_retracement,
            inducement_events,
        )

        # --- Build the candidate ---
        entry_price = ltf_ob.midpoint
        pip_val = float(get_pip_value(ltf_sequence.symbol))
        stop_loss = self._compute_structural_stop_loss(
            ob=ltf_ob,
            direction=Direction.BEARISH,
            protective_level=(
                ltf_sweep.sweep_high if ltf_sweep is not None else None
            ),
        )

        # take_profit is Optional[float] on SMCCandidate by design.  When
        # no swing clears the 1:1 R:R floor we emit None rather than
        # substituting htf_bms.breakout_price; see the bullish variant
        # above for the full rationale.
        take_profit = self._find_nearest_ssl_target(
            entry_price,
            self._get_swing_lows_from_sequence(htf_sequence),
            pip_val,
            stop_loss=stop_loss,
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
            pattern=CandidatePattern.SH_BMS_RTO_BEARISH,
            direction=Direction.BEARISH,
            timestamp=ltf_sequence.candles[-1].timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_timeframe=htf_sequence.timeframe,
            ltf_timeframe=ltf_sequence.timeframe,
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
            liquidity_swept=ltf_sweep is not None,
            swept_level=ltf_sweep.swept_level if ltf_sweep else None,
            sweep_timestamp=ltf_sweep.timestamp if ltf_sweep else None,
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
                sweep=ltf_sweep,
                ob=ltf_ob,
            ),
        )

        self._logger.info(
            "bearish_continuation_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "ltf_confirmed": ltf_confirmed,
                "has_per_candidate_fib_leg": candidate_retracement is not None,
            },
        )

        return candidate

    def _count_confluences(
        self,
        htf_bms: BreakInMarketStructure,
        ltf_bms: BreakInMarketStructure,
        sweep: Optional[LiquiditySweep],
        choch: Optional[ChangeOfCharacter],
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        retracement: Optional[FibonacciRetracement],
        inducement_events: list[InducementEvent],
    ) -> int:
        """Count all confluences for a continuation candidate.

        This is informational metadata for the LLM.  It is NEVER used
        to gate or reject a candidate.  Every structural element the
        system detects is counted so the LLM has maximum visibility.

        The ``retracement`` passed here is the per-candidate leg
        (see class docstring); Fibonacci confluence is therefore
        scored against the candidate's own impulse.
        """
        confluences = 0

        # 1. HTF BMS alignment (always present for continuation)
        confluences += 1

        # 2. HTF BMS is confirmed (multi-candle confirmation passed)
        if htf_bms.confirmed:
            confluences += 1

        # 3. LTF BMS alignment (structural confirmation on entry TF)
        if ltf_bms.confirmed:
            confluences += 1

        # 4. Liquidity sweep with close-back-inside
        if sweep and sweep.closed_back_inside:
            confluences += 1

        # 5. LTF CHOCH (earliest signal of order flow shift)
        if choch is not None:
            confluences += 1

        # 6. FVG alignment with OB direction
        if any(fvg.direction == ob.direction for fvg in fvgs):
            confluences += 1

        # 7. Fibonacci / OTE confluence (0-2 points), per-candidate leg
        fib_score = self.zone_validator.score_ob_fib_confluence(ob, retracement)
        if fib_score >= 3:
            confluences += 2  # OTE pocket = strong confluence
        elif fib_score >= 2:
            confluences += 1  # Correct premium/discount zone

        # 8. Inducement cleared
        if any(idm.cleared for idm in inducement_events):
            confluences += 1

        # 9. OB displacement strength (strong displacement = institutional)
        if ob.displacement_pips > 0:
            pip_val = float(get_pip_value(ob.symbol))
            displacement_in_pips = ob.displacement_pips / pip_val
            if displacement_in_pips >= self.config.bms_strong_displacement_pips:
                confluences += 1

        # 10. OB is a breaker block (failed OB flipped = stronger zone)
        if ob.is_breaker:
            confluences += 1

        return confluences

    def _find_nearest_bsl_target(
        self,
        entry_price: float,
        swing_highs: list,
        pip_val: float,
        stop_loss: Optional[float] = None,
    ) -> Optional[float]:
        """Find the nearest BSL (swing high) above entry as the TP target.

        Only swings whose distance from ``entry_price`` is at least
        ``config.min_take_profit_rr * |entry_price - stop_loss|`` are
        considered.  When ``stop_loss`` is not supplied the floor is
        skipped (legacy behaviour, used only if a future caller opts
        out explicitly).
        """
        min_reward = 0.0
        if stop_loss is not None:
            sl_distance = abs(entry_price - stop_loss)
            min_reward = sl_distance * self.config.min_take_profit_rr

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
        swing_lows: list,
        pip_val: float,
        stop_loss: Optional[float] = None,
    ) -> Optional[float]:
        """Find the nearest SSL (swing low) below entry as the TP target.

        Only swings whose distance from ``entry_price`` is at least
        ``config.min_take_profit_rr * |entry_price - stop_loss|`` are
        considered.  When ``stop_loss`` is not supplied the floor is
        skipped (legacy behaviour, used only if a future caller opts
        out explicitly).
        """
        min_reward = 0.0
        if stop_loss is not None:
            sl_distance = abs(entry_price - stop_loss)
            min_reward = sl_distance * self.config.min_take_profit_rr

        candidates = [
            sl.price for sl in swing_lows
            if sl.price < entry_price
            and (entry_price - sl.price) >= min_reward
        ]
        if candidates:
            return max(candidates)
        return None

    def _compute_structural_stop_loss(
        self,
        ob: OrderBlock,
        direction: Direction,
        protective_level: Optional[float],
    ) -> float:
        """Compute SL beyond the pattern's REAL structural invalidation.

        ``protective_level`` is the genuine invalidation price for a
        SH_BMS_RTO continuation: the liquidity-sweep extreme
        (``sweep_low`` for longs, ``sweep_high`` for shorts).  The SL
        is seated beyond it via the shared timeframe-aware helper, with
        the OB edge used only as an inner guard.  When no sweep is
        present the OB edge becomes the invalidation anchor (still
        buffered structurally by timeframe).

        The buffer is no longer a flat fraction of the OB range; it is
        the timeframe-scaled structural buffer (see
        ``engine.ta.common.utils.price.stop_loss``).
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

    @staticmethod
    def _get_swing_highs_from_sequence(sequence: CandleSequence) -> list:
        """Extract approximate swing highs from a candle sequence.

        Used as a fallback when explicit swing highs are not passed.
        Identifies local maxima using a simple 3-bar pivot.
        """
        from engine.ta.models.swing import SwingHigh
        highs = []
        candles = sequence.candles
        for i in range(1, len(candles) - 1):
            if candles[i].high > candles[i - 1].high and candles[i].high > candles[i + 1].high:
                highs.append(SwingHigh(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    timestamp=candles[i].timestamp,
                    price=candles[i].high,
                    index=i,
                    strength=1,
                    left_bars=1,
                    right_bars=1,
                ))
        return highs

    @staticmethod
    def _get_swing_lows_from_sequence(sequence: CandleSequence) -> list:
        """Extract approximate swing lows from a candle sequence."""
        from engine.ta.models.swing import SwingLow
        lows = []
        candles = sequence.candles
        for i in range(1, len(candles) - 1):
            if candles[i].low < candles[i - 1].low and candles[i].low < candles[i + 1].low:
                lows.append(SwingLow(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    timestamp=candles[i].timestamp,
                    price=candles[i].low,
                    index=i,
                    strength=1,
                    left_bars=1,
                    right_bars=1,
                ))
        return lows

    def _fib_level_str(
        self,
        price: float,
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[str]:
        """Return the exact retracement percentage the entry price falls on.

        Formatted to 3 decimals (e.g. ``"0.637"``) to stay within the
        existing ``SMCCandidate.fib_level: Optional[str]`` contract.
        Returns ``None`` when no retracement is available or the price
        falls outside the swing leg.  ``retracement`` here is the
        per-candidate leg built in the build_* method.
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

        When the per-candidate leg is None (e.g. missing sweep),
        ``fib_context`` is simply omitted — no fabricated value.
        """
        metadata = dict(base)

        fib_context = self.zone_validator.build_fib_context(price, retracement)
        if fib_context is not None:
            metadata["fib_context"] = fib_context

        sweep_context = self.zone_validator.build_sweep_context(sweep, ob)
        if sweep_context is not None:
            metadata["sweep_context"] = sweep_context

        return metadata
