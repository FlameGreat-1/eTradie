from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Direction, Timeframe
from engine.ta.models.snapshot import TechnicalSnapshot, MultiTimeframeSnapshot
from engine.ta.models.zone import Zone

logger = get_logger(__name__)


class AlignmentService:
    
    def __init__(
        self,
        *,
        require_trend_alignment: bool = True,
        require_zone_nesting: bool = False,
    ) -> None:
        self.require_trend_alignment = require_trend_alignment
        self.require_zone_nesting = require_zone_nesting
        self._logger = get_logger(__name__)
    
    def check_alignment(
        self,
        htf_snapshot: TechnicalSnapshot,
        ltf_snapshot: TechnicalSnapshot,
    ) -> MultiTimeframeSnapshot:
        if htf_snapshot.symbol != ltf_snapshot.symbol:
            raise ValueError(
                f"Symbol mismatch: HTF={htf_snapshot.symbol}, LTF={ltf_snapshot.symbol}"
            )
        
        trends_aligned = self._check_trend_alignment(
            htf_snapshot.trend_direction,
            ltf_snapshot.trend_direction,
        )
        
        zones_nested = self._check_zone_nesting(htf_snapshot, ltf_snapshot)
        
        htf_ltf_aligned = trends_aligned
        
        if self.require_zone_nesting:
            htf_ltf_aligned = htf_ltf_aligned and zones_nested
        
        alignment_metadata = {
            "trends_aligned": trends_aligned,
            "zones_nested": zones_nested,
            "htf_trend": str(htf_snapshot.trend_direction),
            "ltf_trend": str(ltf_snapshot.trend_direction),
            "htf_timeframe": str(htf_snapshot.timeframe),
            "ltf_timeframe": str(ltf_snapshot.timeframe),
        }
        
        multi_snapshot = MultiTimeframeSnapshot(
            symbol=htf_snapshot.symbol,
            timestamp=ltf_snapshot.timestamp,
            htf_snapshot=htf_snapshot,
            ltf_snapshot=ltf_snapshot,
            htf_ltf_aligned=htf_ltf_aligned,
            alignment_metadata=alignment_metadata,
        )
        
        self._logger.info(
            "alignment_checked",
            extra={
                "symbol": htf_snapshot.symbol,
                "htf_timeframe": htf_snapshot.timeframe,
                "ltf_timeframe": ltf_snapshot.timeframe,
                "trends_aligned": trends_aligned,
                "zones_nested": zones_nested,
                "htf_ltf_aligned": htf_ltf_aligned,
            },
        )
        
        return multi_snapshot
    
    def _check_trend_alignment(
        self,
        htf_trend: Direction,
        ltf_trend: Direction,
    ) -> bool:
        if not self.require_trend_alignment:
            return True
        
        if htf_trend == Direction.NEUTRAL or ltf_trend == Direction.NEUTRAL:
            return False
        
        return htf_trend == ltf_trend
    
    def _check_zone_nesting(
        self,
        htf_snapshot: TechnicalSnapshot,
        ltf_snapshot: TechnicalSnapshot,
    ) -> bool:
        htf_zones = self._get_all_zones(htf_snapshot)
        ltf_zones = self._get_all_zones(ltf_snapshot)
        
        if not htf_zones or not ltf_zones:
            return False
        
        nested_count = 0
        
        for ltf_zone in ltf_zones:
            for htf_zone in htf_zones:
                if self._is_zone_nested(ltf_zone, htf_zone):
                    nested_count += 1
                    break
        
        nesting_percentage = (nested_count / len(ltf_zones)) * 100 if ltf_zones else 0
        
        return nesting_percentage >= 50.0
    
    def _get_all_zones(self, snapshot: TechnicalSnapshot) -> list[Zone]:
        zones = []
        
        zones.extend([ob.to_zone() for ob in snapshot.order_blocks])
        zones.extend([fvg.to_zone() for fvg in snapshot.fvgs])
        zones.extend([bb.to_zone() for bb in snapshot.breaker_blocks])
        zones.extend([sz.to_zone() for sz in snapshot.supply_zones])
        zones.extend([dz.to_zone() for dz in snapshot.demand_zones])
        
        return zones
    
    def _is_zone_nested(self, ltf_zone: Zone, htf_zone: Zone) -> bool:
        if ltf_zone.direction != htf_zone.direction:
            return False
        
        return (
            ltf_zone.lower_bound >= htf_zone.lower_bound
            and ltf_zone.upper_bound <= htf_zone.upper_bound
        )
    
    def validate_htf_context(
        self,
        htf_snapshot: TechnicalSnapshot,
        required_direction: Direction,
    ) -> bool:
        if htf_snapshot.trend_direction == Direction.NEUTRAL:
            return False
        
        return htf_snapshot.trend_direction == required_direction
    
    def get_htf_bias(self, htf_snapshot: TechnicalSnapshot) -> Direction:
        return htf_snapshot.trend_direction
