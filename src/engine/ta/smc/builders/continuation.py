from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.constants import Direction, CandidatePattern
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
    - Liquidity taken first (Universal Rule 1)
    - Retracement to OB (Universal Rule 3)
    - OB at Premium/Discount (Universal Rule 6)
    - Session timing (Universal Rule 7)
    - Minimum 3 confluences (Universal Rule 5)
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
        ltf_sweep: LiquiditySweep,
        ltf_choch: ChangeOfCharacter,
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
            [ltf_sweep],
            inducement_events,
            retracement,
            ltf_sequence,
            [],
        ):
            return None
        
        current_price = ltf_sequence.candles[-1].close
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sweep,
            ltf_choch,
            ltf_bms,
            ltf_ob,
            inducement_events,
            ltf_sequence,
            current_price,
        ):
            return None
        
        confluences = self._count_confluences(
            htf_bms,
            ltf_sweep,
            ltf_ob,
            ltf_fvgs,
            retracement,
            inducement_events,
        )
        
        if confluences < self.config.min_confluences:
            self._logger.debug(
                "bullish_continuation_insufficient_confluences",
                extra={
                    "symbol": ltf_sequence.symbol,
                    "confluences": confluences,
                    "required": self.config.min_confluences,
                },
            )
            return None
        
        entry_price = ltf_ob.midpoint
        stop_loss = ltf_ob.lower_bound - (0.0010)
        take_profit = htf_bms.breakout_price
        
        candidate = SMCCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.SH_BMS_RTO,
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
            choch_detected=True,
            choch_price=ltf_choch.breakout_price,
            choch_timestamp=ltf_choch.timestamp,
            order_block_upper=ltf_ob.upper_bound,
            order_block_lower=ltf_ob.lower_bound,
            order_block_timestamp=ltf_ob.timestamp,
            liquidity_swept=True,
            swept_level=ltf_sweep.swept_level,
            sweep_timestamp=ltf_sweep.timestamp,
            inducement_cleared=len([idm for idm in inducement_events if idm.cleared]) > 0,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            displacement_pips=ltf_bms.displacement_pips,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
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
            },
        )
        
        return candidate
    
    def build_bearish_continuation(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
        htf_bms: BreakInMarketStructure,
        ltf_sweep: LiquiditySweep,
        ltf_choch: ChangeOfCharacter,
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
            [ltf_sweep],
            inducement_events,
            retracement,
            ltf_sequence,
            [],
        ):
            return None
        
        current_price = ltf_sequence.candles[-1].close
        
        if not self.ltf_validator.validate_all_ltf_confirmations(
            ltf_sweep,
            ltf_choch,
            ltf_bms,
            ltf_ob,
            inducement_events,
            ltf_sequence,
            current_price,
        ):
            return None
        
        confluences = self._count_confluences(
            htf_bms,
            ltf_sweep,
            ltf_ob,
            ltf_fvgs,
            retracement,
            inducement_events,
        )
        
        if confluences < self.config.min_confluences:
            return None
        
        entry_price = ltf_ob.midpoint
        stop_loss = ltf_ob.upper_bound + (0.0010)
        take_profit = htf_bms.breakout_price
        
        candidate = SMCCandidate(
            symbol=ltf_sequence.symbol,
            timeframe=ltf_sequence.timeframe,
            pattern=CandidatePattern.SH_BMS_RTO,
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
            choch_detected=True,
            choch_price=ltf_choch.breakout_price,
            choch_timestamp=ltf_choch.timestamp,
            order_block_upper=ltf_ob.upper_bound,
            order_block_lower=ltf_ob.lower_bound,
            order_block_timestamp=ltf_ob.timestamp,
            liquidity_swept=True,
            swept_level=ltf_sweep.swept_level,
            sweep_timestamp=ltf_sweep.timestamp,
            inducement_cleared=len([idm for idm in inducement_events if idm.cleared]) > 0,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            displacement_pips=ltf_bms.displacement_pips,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
            metadata={"confluences": confluences},
        )
        
        self._logger.info(
            "bearish_continuation_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
            },
        )
        
        return candidate
    
    def _count_confluences(
        self,
        htf_bms: BreakInMarketStructure,
        sweep: LiquiditySweep,
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        retracement: Optional[FibonacciRetracement],
        inducement_events: list[InducementEvent],
    ) -> int:
        confluences = 0
        
        confluences += 1
        
        if sweep.closed_back_inside:
            confluences += 1
        
        if any(fvg.direction == ob.direction for fvg in fvgs):
            confluences += 1
        
        if retracement and self.zone_validator.validate_ob_at_premium_discount(ob, retracement):
            confluences += 1
        
        if any(idm.cleared for idm in inducement_events):
            confluences += 1
        
        return confluences
    
    def _get_fib_level(
        self,
        price: float,
        retracement: FibonacciRetracement,
    ) -> Optional[str]:
        nearest_level = self.fibonacci_analyzer.get_nearest_fib_level(price, retracement)
        return str(nearest_level) if nearest_level else None
