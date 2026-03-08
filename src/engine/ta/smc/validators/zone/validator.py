from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.constants import Direction, PriceZone
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.liquidity_event import InducementEvent, LiquiditySweep
from engine.ta.models.structure_event import BreakInMarketStructure, ChangeOfCharacter
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.models.zone import OrderBlock, FairValueGap
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class ZoneValidator:
    """
    Validates SMC zones against the 7 Rules of a Tradeable Order Block.
    
    All 7 rules must be satisfied for a zone to be tradeable:
    1. Must sponsor a BOS/CHOCH
    2. Must have FVG associated
    3. Must have liquidity/inducement present
    4. Must take out opposing OB
    5. Must be at Premium (sells) or Discount (buys)
    6. Must have BPR (FVG within FVG, OB within OB on subsequent TF)
    7. Select HTF OBs, refine to LTF
    
    This validator handles rules 2, 3, 5. Rules 1, 4, 6, 7 handled elsewhere.
    """
    
    def __init__(
        self,
        config: SMCConfig,
        fibonacci_analyzer: FibonacciAnalyzer,
    ) -> None:
        self.config = config
        self.fibonacci_analyzer = fibonacci_analyzer
        self._logger = get_logger(__name__)
    
    def validate_ob_has_fvg(
        self,
        ob: OrderBlock,
        fvgs: list[FairValueGap],
    ) -> bool:
        """Rule 2: Must have FVG associated."""
        if not self.config.require_fvg_with_ob:
            return True
        
        for fvg in fvgs:
            if fvg.direction != ob.direction:
                continue
            
            if abs(fvg.timestamp.timestamp() - ob.timestamp.timestamp()) > 3600:
                continue
            
            if ob.lower_bound <= fvg.lower_bound <= ob.upper_bound:
                return True
            
            if ob.lower_bound <= fvg.upper_bound <= ob.upper_bound:
                return True
        
        return False
    
    def validate_ob_has_liquidity(
        self,
        ob: OrderBlock,
        liquidity_sweeps: list[LiquiditySweep],
        inducement_events: list[InducementEvent],
    ) -> bool:
        """Rule 3: Must have liquidity or inducement present."""
        for sweep in liquidity_sweeps:
            if abs(sweep.timestamp.timestamp() - ob.timestamp.timestamp()) < 3600:
                return True
        
        for inducement in inducement_events:
            if inducement.cleared:
                if abs(inducement.cleared_timestamp.timestamp() - ob.timestamp.timestamp()) < 3600:
                    return True
        
        return True
    
    def validate_ob_at_premium_discount(
        self,
        ob: OrderBlock,
        retracement: Optional[FibonacciRetracement],
    ) -> bool:
        """Rule 5: Must be at Premium (sells) or Discount (buys)."""
        if not self.config.require_premium_discount:
            return True
        
        if not retracement:
            return False
        
        ob_midpoint = ob.midpoint
        
        zone = self.fibonacci_analyzer.get_zone_for_price(ob_midpoint, retracement)
        
        if ob.direction == Direction.BULLISH:
            return zone == PriceZone.DISCOUNT
        else:
            return zone == PriceZone.PREMIUM
    
    def validate_zone_freshness(
        self,
        ob: OrderBlock,
        sequence: CandleSequence,
    ) -> bool:
        """Validate zone is unmitigated (fresh)."""
        if ob.mitigated:
            return False
        
        if ob.candle_index >= len(sequence.candles) - 1:
            return True
        
        for i in range(ob.candle_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if ob.direction == Direction.BULLISH:
                if candle.low <= ob.upper_bound:
                    return False
            else:
                if candle.high >= ob.lower_bound:
                    return False
        
        return True
    
    def validate_zone_no_overlap(
        self,
        ob: OrderBlock,
        other_obs: list[OrderBlock],
    ) -> bool:
        """Validate zone does not overlap with other zones."""
        for other_ob in other_obs:
            if other_ob.timestamp == ob.timestamp:
                continue
            
            if ob.overlaps_with(other_ob.to_zone()):
                return False
        
        return True
    
    def validate_all_ob_rules(
        self,
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        liquidity_sweeps: list[LiquiditySweep],
        inducement_events: list[InducementEvent],
        retracement: Optional[FibonacciRetracement],
        sequence: CandleSequence,
        other_obs: list[OrderBlock],
    ) -> bool:
        """Validate all applicable OB rules."""
        if not self.validate_ob_has_fvg(ob, fvgs):
            self._logger.debug(
                "ob_validation_failed_no_fvg",
                extra={
                    "symbol": ob.symbol,
                    "timeframe": ob.timeframe,
                    "ob_timestamp": ob.timestamp.isoformat(),
                },
            )
            return False
        
        if not self.validate_ob_has_liquidity(ob, liquidity_sweeps, inducement_events):
            self._logger.debug(
                "ob_validation_failed_no_liquidity",
                extra={
                    "symbol": ob.symbol,
                    "timeframe": ob.timeframe,
                    "ob_timestamp": ob.timestamp.isoformat(),
                },
            )
            return False
        
        if not self.validate_ob_at_premium_discount(ob, retracement):
            self._logger.debug(
                "ob_validation_failed_not_premium_discount",
                extra={
                    "symbol": ob.symbol,
                    "timeframe": ob.timeframe,
                    "ob_timestamp": ob.timestamp.isoformat(),
                    "direction": str(ob.direction),
                },
            )
            return False
        
        if not self.validate_zone_freshness(ob, sequence):
            self._logger.debug(
                "ob_validation_failed_not_fresh",
                extra={
                    "symbol": ob.symbol,
                    "timeframe": ob.timeframe,
                    "ob_timestamp": ob.timestamp.isoformat(),
                },
            )
            return False
        
        return True
