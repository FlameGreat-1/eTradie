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
from engine.ta.models.structure_event import (
    BreakInMarketStructure,
    ChangeOfCharacter,
    ShiftInMarketStructure,
)
from engine.ta.models.zone import OrderBlock, FairValueGap
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
        ltf_choch: ChangeOfCharacter,
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
        retracement: Optional[FibonacciRetracement],
        swing_highs: Optional[list[SwingHigh]] = None,
    ) -> Optional[SMCCandidate]:
        if htf_sms.direction != Direction.BULLISH:
            return None

        if ltf_bms.direction != Direction.BULLISH:
            return None

        if ltf_ob.direction != Direction.BULLISH:
            return None

        if not self.zone_validator.validate_all_ob_rules(
            ltf_ob,
            ltf_fvgs,
            [],
            inducement_events,
            retracement,
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
        )

        confluences = self._count_sms_confluences(
            htf_sms,
            ltf_bms,
            ltf_ob,
            ltf_fvgs,
            retracement,
            inducement_events,
        )

        if confluences < self.config.min_confluences:
            return None

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = ltf_ob.midpoint
        stop_loss = ltf_ob.lower_bound - (self.config.ob_sl_buffer_pips * pip_val)
        take_profit = self._find_nearest_bsl_target(
            entry_price, swing_highs or [], pip_val,
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
            choch_detected=True,
            choch_price=ltf_choch.breakout_price,
            choch_timestamp=ltf_choch.timestamp,
            order_block_upper=ltf_ob.upper_bound,
            order_block_lower=ltf_ob.lower_bound,
            order_block_timestamp=ltf_ob.timestamp,
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
            metadata={"confluences": confluences, "pattern_type": "reversal"},
        )

        self._logger.info(
            "bullish_sms_reversal_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
            },
        )

        return candidate

    def build_bearish_sms_reversal(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        htf_sms: ShiftInMarketStructure,
        ltf_bms: BreakInMarketStructure,
        ltf_choch: ChangeOfCharacter,
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
        retracement: Optional[FibonacciRetracement],
        swing_lows: Optional[list[SwingLow]] = None,
    ) -> Optional[SMCCandidate]:
        if htf_sms.direction != Direction.BEARISH:
            return None

        if ltf_bms.direction != Direction.BEARISH:
            return None

        if ltf_ob.direction != Direction.BEARISH:
            return None

        if not self.zone_validator.validate_all_ob_rules(
            ltf_ob,
            ltf_fvgs,
            [],
            inducement_events,
            retracement,
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
        )

        confluences = self._count_sms_confluences(
            htf_sms,
            ltf_bms,
            ltf_ob,
            ltf_fvgs,
            retracement,
            inducement_events,
        )

        if confluences < self.config.min_confluences:
            return None

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = ltf_ob.midpoint
        stop_loss = ltf_ob.upper_bound + (self.config.ob_sl_buffer_pips * pip_val)
        take_profit = self._find_nearest_ssl_target(
            entry_price, swing_lows or [], pip_val,
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
            choch_price=ltf_choch.breakout_price,
            choch_timestamp=ltf_choch.timestamp,
            order_block_upper=ltf_ob.upper_bound,
            order_block_lower=ltf_ob.lower_bound,
            order_block_timestamp=ltf_ob.timestamp,
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
            metadata={"confluences": confluences, "pattern_type": "reversal"},
        )

        self._logger.info(
            "bearish_sms_reversal_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
            },
        )

        return candidate

    def build_turtle_soup_long(
        self,
        ltf_sequence: CandleSequence,
        sweep: LiquiditySweep,
        swing_highs: Optional[list[SwingHigh]] = None,
    ) -> Optional[SMCCandidate]:
        if not sweep.closed_back_inside:
            return None

        if sweep.sweep_pips < self.config.turtle_soup_min_pips:
            return None

        if not self.ltf_validator.validate_session_timing(ltf_sequence):
            return None

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = sweep.swept_level
        stop_loss = sweep.sweep_low - (self.config.turtle_soup_min_sl_pips * pip_val)
        take_profit = self._find_nearest_bsl_target(
            entry_price, swing_highs or [], pip_val,
        )

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
            metadata={"sweep_pips": sweep.sweep_pips, "pattern_type": "turtle_soup"},
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
        if not sweep.closed_back_inside:
            return None

        if sweep.sweep_pips < self.config.turtle_soup_min_pips:
            return None

        if not self.ltf_validator.validate_session_timing(ltf_sequence):
            return None

        pip_val = float(get_pip_value(ltf_sequence.symbol))
        entry_price = sweep.swept_level
        stop_loss = sweep.sweep_high + (self.config.turtle_soup_min_sl_pips * pip_val)
        take_profit = self._find_nearest_ssl_target(
            entry_price, swing_lows or [], pip_val,
        )

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
            metadata={"sweep_pips": sweep.sweep_pips, "pattern_type": "turtle_soup"},
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
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        retracement: Optional[FibonacciRetracement],
        inducement_events: list[InducementEvent],
    ) -> int:
        confluences = 0

        confluences += 1

        confluences += 1

        if any(fvg.direction == ob.direction for fvg in fvgs):
            confluences += 1

        if retracement and self.zone_validator.validate_ob_at_premium_discount(
            ob, retracement
        ):
            confluences += 1

        if any(idm.cleared for idm in inducement_events):
            confluences += 1

        return confluences

    def _find_nearest_bsl_target(
        self,
        entry_price: float,
        swing_highs: list[SwingHigh],
        pip_val: float,
    ) -> float:
        """Find the nearest BSL (swing high) above entry as the TP target.

        Per SMC rules: price runs from liquidity to liquidity.
        TP must always target the next draw on liquidity — the nearest
        opposing swing high (BSL) above the entry for bullish trades.
        If no structural target is found, returns None so the LLM
        can determine the TP independently.
        """
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
    ) -> float:
        """Find the nearest SSL (swing low) below entry as the TP target.

        Per SMC rules: price runs from liquidity to liquidity.
        TP must always target the next draw on liquidity — the nearest
        opposing swing low (SSL) below the entry for bearish trades.
        If no structural target is found, returns None so the LLM
        can determine the TP independently.
        """
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
        """Return the OTE fib level (0.5, 0.618, 0.705, 0.79) closest to price,
        but only if within the configured tolerance. Returns None if no OTE
        level is close enough — never returns 0.0 or 1.0."""
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
