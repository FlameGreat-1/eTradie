from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, CandidatePattern
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.models.candidate import SMCCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.liquidity_event import LiquiditySweep, InducementEvent
from engine.ta.models.structure_event import BreakInMarketStructure, ChangeOfCharacter
from engine.ta.models.zone import OrderBlock, FairValueGap
from engine.ta.smc.builders.fib_leg import select_leg_for_amd
from engine.ta.smc.config import SMCConfig
from engine.ta.smc.detectors.amd import AMDContext, AMDPhase
from engine.ta.smc.validators.zone.validator import ZoneValidator
from engine.ta.smc.validators.ltf.confirmation import LTFConfirmationValidator

logger = get_logger(__name__)


class AMDCandidateBuilder:
    """
    Builds AMD-related SMC candidates.

    Pattern 4/9: Bullish/Bearish AMD
    - Asian session consolidates (Accumulation)
    - London/NY open manipulates price to trap traders (Manipulation)
    - Price reverses hard in true direction (Distribution)

    Entry during Distribution using any of:
    - Simple RTO to Bullish/Bearish OB
    - SH + BMS + RTO
    - SMS + BMS + RTO

    Fibonacci leg (SMC-MIT-003 / Universal Rule 6):
    - The per-candidate leg runs from the Asian-range extreme on the
      manipulation side to the distribution BMS breakout close:
          Bullish: asian_range.low  -> ltf_bms.breakout_price
          Bearish: ltf_bms.breakout_price -> asian_range.high
    - Built via ``smc.builders.fib_leg.select_leg_for_amd``.
    - The ``retracement`` argument on the public methods is a
      deprecated passthrough retained only so SMCDetector can keep
      calling the builder during the staged rollout.  It is NOT
      consumed.
    - No fallback: when ``amd_context.asian_range`` is None the
      per-candidate leg is None and the candidate is emitted with
      fib_level=None and no fib_context in metadata.  We never use a
      global HTF leg.

    LTF confirmations (CHOCH) are evaluated when available and stored
    as metadata.  Their absence does NOT block candidate creation.
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

    def build_bullish_amd(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        amd_context: AMDContext,
        ltf_sweep: Optional[LiquiditySweep],
        ltf_bms: BreakInMarketStructure,
        ltf_choch: Optional[ChangeOfCharacter],
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
        retracement: Optional[FibonacciRetracement] = None,  # deprecated passthrough
        swing_highs: Optional[list[SwingHigh]] = None,
    ) -> Optional[SMCCandidate]:
        """Build an AMD_BULLISH candidate.

        ``retracement`` is a deprecated passthrough and is ignored.
        The true Fibonacci leg is built inline from
        ``amd_context.asian_range.low`` and ``ltf_bms.breakout_price``
        via ``select_leg_for_amd``.
        """
        del retracement  # intentionally unused; see docstring

        if amd_context.phase != AMDPhase.DISTRIBUTION:
            self._logger.debug(
                "amd_not_in_distribution_phase",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "phase": amd_context.phase,
                },
            )
            return None

        if amd_context.distribution_direction != Direction.BULLISH:
            return None

        if ltf_bms.direction != Direction.BULLISH:
            return None

        if ltf_ob.direction != Direction.BULLISH:
            return None

        # Per-candidate Fibonacci leg (SMC-MIT-003).
        asian_range = amd_context.asian_range
        candidate_retracement = select_leg_for_amd(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            asian_range_high=asian_range.high if asian_range else None,
            asian_range_low=asian_range.low if asian_range else None,
            asian_range_start=asian_range.start_time if asian_range else None,
            asian_range_end=asian_range.end_time if asian_range else None,
            ltf_bms=ltf_bms,
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

        # Confluence scoring is informational metadata for the LLM,
        # not a gate.  The LLM performs its own scoring with full
        # macro/Wyckoff/cross-TF context.
        confluences = self._count_amd_confluences(
            amd_context,
            ltf_sweep,
            ltf_bms,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            candidate_retracement,
            inducement_events,
        )

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = ltf_ob.midpoint
        stop_loss = ltf_ob.lower_bound - (self.config.ob_sl_buffer_pips * pip_val)

        if asian_range:
            take_profit = self._find_nearest_bsl_target(
                entry_price, swing_highs or [], pip_val,
            )
            if take_profit is None:
                take_profit = asian_range.high
        else:
            take_profit = self._find_nearest_bsl_target(
                entry_price, swing_highs or [], pip_val,
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
            pattern=CandidatePattern.AMD_BULLISH,
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
            session_context="AMD_DISTRIBUTION",
            metadata=self._build_metadata(
                # pattern_type / amd_phase / manipulation_direction are
                # all derivable from the AMD_BULLISH pattern itself and
                # the session_context="AMD_DISTRIBUTION" flag already set
                # above, so we do not duplicate them here.
                {"confluences": confluences},
                entry_price,
                candidate_retracement,
                sweep=ltf_sweep,
                ob=ltf_ob,
            ),
        )

        self._logger.info(
            "bullish_amd_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "amd_phase": amd_context.phase,
                "ltf_confirmed": ltf_confirmed,
                "has_per_candidate_fib_leg": candidate_retracement is not None,
            },
        )

        return candidate

    def build_bearish_amd(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        amd_context: AMDContext,
        ltf_sweep: Optional[LiquiditySweep],
        ltf_bms: BreakInMarketStructure,
        ltf_choch: Optional[ChangeOfCharacter],
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
        retracement: Optional[FibonacciRetracement] = None,  # deprecated passthrough
        swing_lows: Optional[list[SwingLow]] = None,
    ) -> Optional[SMCCandidate]:
        """Build an AMD_BEARISH candidate.

        ``retracement`` is a deprecated passthrough and is ignored.
        The true Fibonacci leg is built inline from
        ``amd_context.asian_range.high`` and ``ltf_bms.breakout_price``
        via ``select_leg_for_amd``.
        """
        del retracement  # intentionally unused; see docstring

        if amd_context.phase != AMDPhase.DISTRIBUTION:
            self._logger.debug(
                "amd_not_in_distribution_phase",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "phase": amd_context.phase,
                },
            )
            return None

        if amd_context.distribution_direction != Direction.BEARISH:
            return None

        if ltf_bms.direction != Direction.BEARISH:
            return None

        if ltf_ob.direction != Direction.BEARISH:
            return None

        asian_range = amd_context.asian_range
        candidate_retracement = select_leg_for_amd(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            asian_range_high=asian_range.high if asian_range else None,
            asian_range_low=asian_range.low if asian_range else None,
            asian_range_start=asian_range.start_time if asian_range else None,
            asian_range_end=asian_range.end_time if asian_range else None,
            ltf_bms=ltf_bms,
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

        # Confluence scoring is informational metadata for the LLM,
        # not a gate.  The LLM performs its own scoring with full
        # macro/Wyckoff/cross-TF context.
        confluences = self._count_amd_confluences(
            amd_context,
            ltf_sweep,
            ltf_bms,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            candidate_retracement,
            inducement_events,
        )

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = ltf_ob.midpoint
        stop_loss = ltf_ob.upper_bound + (self.config.ob_sl_buffer_pips * pip_val)

        if asian_range:
            take_profit = self._find_nearest_ssl_target(
                entry_price, swing_lows or [], pip_val,
            )
            if take_profit is None:
                take_profit = asian_range.low
        else:
            take_profit = self._find_nearest_ssl_target(
                entry_price, swing_lows or [], pip_val,
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
            pattern=CandidatePattern.AMD_BEARISH,
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
            session_context="AMD_DISTRIBUTION",
            metadata=self._build_metadata(
                # pattern_type / amd_phase / manipulation_direction are
                # all derivable from the AMD_BEARISH pattern itself and
                # the session_context="AMD_DISTRIBUTION" flag already set
                # above, so we do not duplicate them here.
                {"confluences": confluences},
                entry_price,
                candidate_retracement,
                sweep=ltf_sweep,
                ob=ltf_ob,
            ),
        )

        self._logger.info(
            "bearish_amd_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "amd_phase": amd_context.phase,
                "ltf_confirmed": ltf_confirmed,
                "has_per_candidate_fib_leg": candidate_retracement is not None,
            },
        )

        return candidate

    def _count_amd_confluences(
        self,
        amd_context: AMDContext,
        sweep: Optional[LiquiditySweep],
        bms: BreakInMarketStructure,
        choch: Optional[ChangeOfCharacter],
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        retracement: Optional[FibonacciRetracement],
        inducement_events: list[InducementEvent],
    ) -> int:
        """Count all confluences for an AMD candidate.

        ``retracement`` here is the per-candidate leg built in the
        corresponding build_* method; OTE confluence is scored against
        the candidate's own impulse, never against a global leg.
        """
        confluences = 0

        # 1. AMD context (accumulation + manipulation confirmed)
        confluences += 1

        # 2. BMS confirmed in distribution direction
        confluences += 1

        # 3. LTF CHOCH (may not be present yet)
        if choch is not None:
            confluences += 1

        # 4. Liquidity sweep
        if sweep and sweep.closed_back_inside:
            confluences += 1

        # 5. FVG alignment with OB
        if any(fvg.direction == ob.direction for fvg in fvgs):
            confluences += 1

        # 6. Fibonacci / OTE confluence (0-3 points), per-candidate leg
        fib_score = self.zone_validator.score_ob_fib_confluence(ob, retracement)
        if fib_score >= 3:
            confluences += 2  # OTE pocket = strong confluence
        elif fib_score >= 2:
            confluences += 1  # Correct premium/discount zone

        # 7. Inducement cleared
        if any(idm.cleared for idm in inducement_events):
            confluences += 1

        return confluences

    def _find_nearest_bsl_target(
        self,
        entry_price: float,
        swing_highs: list[SwingHigh],
        pip_val: float,
    ) -> Optional[float]:
        """Find the nearest BSL (swing high) above entry as the TP target."""
        candidates = [
            sh.price for sh in swing_highs
            if sh.price > entry_price
        ]
        if candidates:
            return min(candidates)
        return None

    def _find_nearest_ssl_target(
        self,
        entry_price: float,
        swing_lows: list[SwingLow],
        pip_val: float,
    ) -> Optional[float]:
        """Find the nearest SSL (swing low) below entry as the TP target."""
        candidates = [
            sl.price for sl in swing_lows
            if sl.price < entry_price
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

        ``fib_context`` is the structured Fibonacci context from
        ``ZoneValidator.build_fib_context`` measured against the
        **per-candidate** leg (see SMC-MIT-003).  When the
        per-candidate leg is None (e.g. missing Asian range), the
        field is simply omitted — no fabricated value.
        """
        metadata = dict(base)

        fib_context = self.zone_validator.build_fib_context(price, retracement)
        if fib_context is not None:
            metadata["fib_context"] = fib_context

        sweep_context = self.zone_validator.build_sweep_context(sweep, ob)
        if sweep_context is not None:
            metadata["sweep_context"] = sweep_context

        return metadata
