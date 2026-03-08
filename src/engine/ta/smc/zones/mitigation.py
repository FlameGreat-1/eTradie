from typing import Optional
from datetime import datetime

from engine.shared.logging import get_logger
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.zone import OrderBlock, FairValueGap
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class MitigationDetector:
    """
    Detects mitigation/retest interactions with SMC zones.
    
    Mitigation occurs when:
    - Price returns to an OB and touches/enters the zone
    - Price fills an FVG (partially or fully)
    - The zone has been "used" by institutions
    
    Mitigated zones are weaker and less likely to hold on subsequent tests.
    Unmitigated zones are fresh and have higher probability.
    
    This is critical for OB Rule validation - fresh zones are preferred.
    """
    
    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def check_ob_mitigation(
        self,
        ob: OrderBlock,
        sequence: CandleSequence,
    ) -> tuple[bool, Optional[datetime]]:
        if ob.candle_index >= len(sequence.candles) - 1:
            return False, None
        
        for i in range(ob.candle_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if ob.direction == Direction.BULLISH:
                if candle.low <= ob.upper_bound and candle.low >= ob.lower_bound:
                    return True, candle.timestamp
                
                if candle.high >= ob.lower_bound and candle.low <= ob.lower_bound:
                    return True, candle.timestamp
            
            else:
                if candle.high >= ob.lower_bound and candle.high <= ob.upper_bound:
                    return True, candle.timestamp
                
                if candle.low <= ob.upper_bound and candle.high >= ob.upper_bound:
                    return True, candle.timestamp
        
        return False, None
    
    def check_fvg_mitigation(
        self,
        fvg: FairValueGap,
        sequence: CandleSequence,
    ) -> tuple[bool, Optional[datetime], float]:
        if fvg.candle_index >= len(sequence.candles) - 1:
            return False, None, 0.0
        
        for i in range(fvg.candle_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            
            if candle.low <= fvg.lower_bound and candle.high >= fvg.upper_bound:
                return True, candle.timestamp, 100.0
            
            if fvg.lower_bound <= candle.low <= fvg.upper_bound:
                fill_percentage = ((candle.high - fvg.lower_bound) / fvg.range_size) * 100.0
                return True, candle.timestamp, fill_percentage
            
            if fvg.lower_bound <= candle.high <= fvg.upper_bound:
                fill_percentage = ((fvg.upper_bound - candle.low) / fvg.range_size) * 100.0
                return True, candle.timestamp, fill_percentage
        
        return False, None, 0.0
    
    def get_unmitigated_obs(
        self,
        obs: list[OrderBlock],
        sequence: CandleSequence,
    ) -> list[OrderBlock]:
        unmitigated = []
        
        for ob in obs:
            mitigated, _ = self.check_ob_mitigation(ob, sequence)
            
            if not mitigated:
                unmitigated.append(ob)
        
        return unmitigated
    
    def get_unfilled_fvgs(
        self,
        fvgs: list[FairValueGap],
        sequence: CandleSequence,
    ) -> list[FairValueGap]:
        unfilled = []
        
        for fvg in fvgs:
            filled, _, fill_pct = self.check_fvg_mitigation(fvg, sequence)
            
            if not filled or fill_pct < 50.0:
                unfilled.append(fvg)
        
        return unfilled
