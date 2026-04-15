from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, CandidatePattern, OTE_LEVELS, FIBONACCI_VALUES
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.models.candidate import SMCCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.liquidity_event import LiquiditySweep, InducementEvent
from engine.ta.models.structure_event import BreakInMarketStructure, ChangeOfCharacter
from engine.ta.models.zone import OrderBlock, FairValueGap
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
        retracement: Optional[FibonacciRetracement],
        swing_highs: Optional[list[SwingHigh]] = None,
    ) -> Optional[SMCCandidate]:
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

        if not self.zone_validator.validate_all_ob_rules(
            ltf_ob,
            ltf_fvgs,
            [ltf_sweep] if ltf_sweep else [],
            inducement_events,
            retracement,
            ltf_sequence,
            [],
        ):
            return None

        current_price = ltf_sequence.candles[-1].close

        ltf_confirmed = False
        if ltf_sweep and ltf_choch:
            ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
                ltf_sweep,
                ltf_choch,
                ltf_bms,
                ltf_ob,
                inducement_events,
                ltf_sequence,
                current_price,
            )

        confluences = self._count_amd_confluences(
            amd_context,
            ltf_sweep,
            ltf_bms,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            retracement,
            inducement_events,
        )

        if confluences < self.config.min_confluences:
            self._logger.info(
                "bullish_amd_insufficient_confluences",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "confluences": confluences,
                    "required": self.config.min_confluences,
                    "has_sweep": ltf_sweep is not None,
                    "has_choch": ltf_choch is not None,
                },
            )
            return None

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = ltf_ob.midpoint
        stop_loss = ltf_ob.lower_bound - (self.config.ob_sl_buffer_pips * pip_val)

        if amd_context.asian_range:
            take_profit = self._find_nearest_bsl_target(
                entry_price, swing_highs or [], pip_val,
            )
            if take_profit is None:
                take_profit = amd_context.asian_range.high
        else:
            take_profit = self._find_nearest_bsl_target(
                entry_price, swing_highs or [], pip_val,
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
            liquidity_swept=ltf_sweep is not None,
            swept_level=ltf_sweep.swept_level if ltf_sweep else None,
            sweep_timestamp=ltf_sweep.timestamp if ltf_sweep else None,
            inducement_cleared=len([idm for idm in inducement_events if idm.cleared])
            > 0,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            displacement_pips=ltf_bms.displacement_pips,
            fib_level=(
                self._get_fib_level(entry_price, retracement) if retracement else None
            ),
            session_context="AMD_DISTRIBUTION",
            metadata={
                "confluences": confluences,
                "pattern_type": "amd",
                "amd_phase": amd_context.phase,
                "manipulation_direction": (
                    str(amd_context.manipulation_direction)
                    if amd_context.manipulation_direction
                    else None
                ),
            },
        )

        self._logger.info(
            "bullish_amd_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "amd_phase": amd_context.phase,
                "ltf_confirmed": ltf_confirmed,
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
        retracement: Optional[FibonacciRetracement],
        swing_lows: Optional[list[SwingLow]] = None,
    ) -> Optional[SMCCandidate]:
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

        if not self.zone_validator.validate_all_ob_rules(
            ltf_ob,
            ltf_fvgs,
            [ltf_sweep] if ltf_sweep else [],
            inducement_events,
            retracement,
            ltf_sequence,
            [],
        ):
            return None

        current_price = ltf_sequence.candles[-1].close

        ltf_confirmed = False
        if ltf_sweep and ltf_choch:
            ltf_confirmed = self.ltf_validator.validate_all_ltf_confirmations(
                ltf_sweep,
                ltf_choch,
                ltf_bms,
                ltf_ob,
                inducement_events,
                ltf_sequence,
                current_price,
            )

        confluences = self._count_amd_confluences(
            amd_context,
            ltf_sweep,
            ltf_bms,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            retracement,
            inducement_events,
        )

        if confluences < self.config.min_confluences:
            self._logger.info(
                "bearish_amd_insufficient_confluences",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "confluences": confluences,
                    "required": self.config.min_confluences,
                    "has_sweep": ltf_sweep is not None,
                    "has_choch": ltf_choch is not None,
                },
            )
            return None

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = ltf_ob.midpoint
        stop_loss = ltf_ob.upper_bound + (self.config.ob_sl_buffer_pips * pip_val)

        if amd_context.asian_range:
            take_profit = self._find_nearest_ssl_target(
                entry_price, swing_lows or [], pip_val,
            )
            if take_profit is None:
                take_profit = amd_context.asian_range.low
        else:
            take_profit = self._find_nearest_ssl_target(
                entry_price, swing_lows or [], pip_val,
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
            liquidity_swept=ltf_sweep is not None,
            swept_level=ltf_sweep.swept_level if ltf_sweep else None,
            sweep_timestamp=ltf_sweep.timestamp if ltf_sweep else None,
            inducement_cleared=len([idm for idm in inducement_events if idm.cleared])
            > 0,
            ltf_confirmation=ltf_confirmed,
            ltf_confirmation_timestamp=(
                ltf_sequence.candles[-1].timestamp if ltf_confirmed else None
            ),
            displacement_pips=ltf_bms.displacement_pips,
            fib_level=(
                self._get_fib_level(entry_price, retracement) if retracement else None
            ),
            session_context="AMD_DISTRIBUTION",
            metadata={
                "confluences": confluences,
                "pattern_type": "amd",
                "amd_phase": amd_context.phase,
                "manipulation_direction": (
                    str(amd_context.manipulation_direction)
                    if amd_context.manipulation_direction
                    else None
                ),
            },
        )

        self._logger.info(
            "bearish_amd_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "amd_phase": amd_context.phase,
                "ltf_confirmed": ltf_confirmed,
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
        """Count all confluences for an AMD candidate."""
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

        # 6. Fibonacci / OTE confluence (0-3 points)
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

    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[str]:
        """Return the OTE fib level closest to price within tolerance."""
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
