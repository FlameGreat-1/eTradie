from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, CandidatePattern, OTE_LEVELS, FIBONACCI_VALUES
from engine.ta.models.candidate import SMCCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.liquidity_event import LiquiditySweep, InducementEvent
from engine.ta.models.structure_event import BreakInMarketStructure, ChangeOfCharacter
from engine.ta.models.zone import OrderBlock, FairValueGap
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

    Requirements:
    - HTF BMS alignment (Universal Rule 2)
    - Liquidity taken first (Universal Rule 1) - when available
    - Retracement to OB (Universal Rule 3) - checked at execution time
    - OTE adds confluence (Universal Rule 6) - scored, not gated
    - Session timing (Universal Rule 7) - checked at execution time
    - Minimum 3 confluences (Universal Rule 5)

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
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SMCCandidate]:
        if htf_bms.direction != Direction.BULLISH:
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

        # LTF confirmation is evaluated when available but does NOT
        # block candidate creation.  The execution engine waits for
        # RTO + LTF confirmation before entering.
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

        confluences = self._count_confluences(
            htf_bms,
            ltf_sweep,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            retracement,
            inducement_events,
        )

        if confluences < self.config.min_confluences:
            self._logger.info(
                "bullish_continuation_insufficient_confluences",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "confluences": confluences,
                    "required": self.config.min_confluences,
                    "ob_upper": ltf_ob.upper_bound,
                    "ob_lower": ltf_ob.lower_bound,
                    "has_sweep": ltf_sweep is not None,
                    "has_choch": ltf_choch is not None,
                    "has_retracement": retracement is not None,
                },
            )
            return None

        entry_price = ltf_ob.midpoint
        pip_val = float(get_pip_value(ltf_sequence.symbol))
        stop_loss = ltf_ob.lower_bound - (self.config.ob_sl_buffer_pips * pip_val)
        take_profit = htf_bms.breakout_price

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
            metadata={"confluences": confluences},
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
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[SMCCandidate]:
        if htf_bms.direction != Direction.BEARISH:
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

        confluences = self._count_confluences(
            htf_bms,
            ltf_sweep,
            ltf_choch,
            ltf_ob,
            ltf_fvgs,
            retracement,
            inducement_events,
        )

        if confluences < self.config.min_confluences:
            self._logger.info(
                "bearish_continuation_insufficient_confluences",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "confluences": confluences,
                    "required": self.config.min_confluences,
                    "ob_upper": ltf_ob.upper_bound,
                    "ob_lower": ltf_ob.lower_bound,
                    "has_sweep": ltf_sweep is not None,
                    "has_choch": ltf_choch is not None,
                    "has_retracement": retracement is not None,
                },
            )
            return None

        entry_price = ltf_ob.midpoint
        pip_val = float(get_pip_value(ltf_sequence.symbol))
        stop_loss = ltf_ob.upper_bound + (self.config.ob_sl_buffer_pips * pip_val)
        take_profit = htf_bms.breakout_price

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
            metadata={"confluences": confluences},
        )

        self._logger.info(
            "bearish_continuation_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "ltf_confirmed": ltf_confirmed,
            },
        )

        return candidate

    def _count_confluences(
        self,
        htf_bms: BreakInMarketStructure,
        sweep: Optional[LiquiditySweep],
        choch: Optional[ChangeOfCharacter],
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        retracement: Optional[FibonacciRetracement],
        inducement_events: list[InducementEvent],
    ) -> int:
        """Count all confluences for a continuation candidate.

        Each confluence is an independent piece of evidence that the
        setup is valid.  The minimum is 3 (Universal Rule 5).
        """
        confluences = 0

        # 1. HTF BMS alignment (always present for continuation)
        confluences += 1

        # 2. Liquidity sweep (conditional - doesn't happen 100%)
        if sweep and sweep.closed_back_inside:
            confluences += 1

        # 3. LTF CHOCH (may not be present yet if RTO hasn't happened)
        if choch is not None:
            confluences += 1

        # 4. FVG alignment with OB
        if any(fvg.direction == ob.direction for fvg in fvgs):
            confluences += 1

        # 5. Fibonacci / OTE confluence (0-3 points)
        fib_score = self.zone_validator.score_ob_fib_confluence(ob, retracement)
        if fib_score >= 3:
            confluences += 2  # OTE pocket = strong confluence
        elif fib_score >= 2:
            confluences += 1  # Correct premium/discount zone

        # 6. Inducement cleared
        if any(idm.cleared for idm in inducement_events):
            confluences += 1

        return confluences

    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[str]:
        """Return the OTE fib level (0.5, 0.618, 0.705, 0.79) closest to price,
        but only if within the configured tolerance. Returns None if no OTE
        level is close enough."""
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
