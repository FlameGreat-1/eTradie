from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, CandidatePattern
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
    
    This is Pattern 2 in the ranking (AMD + SH + BMS + RTO = highest confluence after combined Turtle Soup).
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
        ltf_choch: ChangeOfCharacter,
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
        retracement: Optional[FibonacciRetracement],
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
        
        confluences = self._count_amd_confluences(
            amd_context,
            ltf_sweep,
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
        stop_loss = ltf_ob.lower_bound - (10 * pip_val)
        
        if amd_context.asian_range:
            take_profit = amd_context.asian_range.high + (50 * pip_val)
        else:
            take_profit = entry_price + (100 * pip_val)
        
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
            choch_detected=True,
            choch_price=ltf_choch.breakout_price,
            choch_timestamp=ltf_choch.timestamp,
            order_block_upper=ltf_ob.upper_bound,
            order_block_lower=ltf_ob.lower_bound,
            order_block_timestamp=ltf_ob.timestamp,
            liquidity_swept=ltf_sweep is not None,
            swept_level=ltf_sweep.swept_level if ltf_sweep else None,
            sweep_timestamp=ltf_sweep.timestamp if ltf_sweep else None,
            inducement_cleared=len([idm for idm in inducement_events if idm.cleared]) > 0,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            displacement_pips=ltf_bms.displacement_pips,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
            session_context="AMD_DISTRIBUTION",
            metadata={
                "confluences": confluences,
                "pattern_type": "amd",
                "amd_phase": amd_context.phase,
                "manipulation_direction": str(amd_context.manipulation_direction) if amd_context.manipulation_direction else None,
            },
        )
        
        self._logger.info(
            "bullish_amd_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "amd_phase": amd_context.phase,
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
        ltf_choch: ChangeOfCharacter,
        ltf_ob: OrderBlock,
        ltf_fvgs: list[FairValueGap],
        inducement_events: list[InducementEvent],
        retracement: Optional[FibonacciRetracement],
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
        
        confluences = self._count_amd_confluences(
            amd_context,
            ltf_sweep,
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
        stop_loss = ltf_ob.upper_bound + (10 * pip_val)
        
        if amd_context.asian_range:
            take_profit = amd_context.asian_range.low - (50 * pip_val)
        else:
            take_profit = entry_price - (100 * pip_val)
        
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
            choch_detected=True,
            choch_price=ltf_choch.breakout_price,
            choch_timestamp=ltf_choch.timestamp,
            order_block_upper=ltf_ob.upper_bound,
            order_block_lower=ltf_ob.lower_bound,
            order_block_timestamp=ltf_ob.timestamp,
            liquidity_swept=ltf_sweep is not None,
            swept_level=ltf_sweep.swept_level if ltf_sweep else None,
            sweep_timestamp=ltf_sweep.timestamp if ltf_sweep else None,
            inducement_cleared=len([idm for idm in inducement_events if idm.cleared]) > 0,
            ltf_confirmation=True,
            ltf_confirmation_timestamp=ltf_sequence.candles[-1].timestamp,
            displacement_pips=ltf_bms.displacement_pips,
            fib_level=self._get_fib_level(entry_price, retracement) if retracement else None,
            session_context="AMD_DISTRIBUTION",
            metadata={
                "confluences": confluences,
                "pattern_type": "amd",
                "amd_phase": amd_context.phase,
                "manipulation_direction": str(amd_context.manipulation_direction) if amd_context.manipulation_direction else None,
            },
        )
        
        self._logger.info(
            "bearish_amd_candidate_built",
            extra={
                "symbol": candidate.symbol,
                "entry_price": entry_price,
                "confluences": confluences,
                "amd_phase": amd_context.phase,
            },
        )
        
        return candidate
    
    def _count_amd_confluences(
        self,
        amd_context: AMDContext,
        sweep: Optional[LiquiditySweep],
        bms: BreakInMarketStructure,
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        retracement: Optional[FibonacciRetracement],
        inducement_events: list[InducementEvent],
    ) -> int:
        confluences = 0
        
        confluences += 1
        
        confluences += 1
        
        if sweep and sweep.closed_back_inside:
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
