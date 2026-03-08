from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.zone import SupplyZone, DemandZone
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class SupplyDemandDetector:
    """
    Detects Supply and Demand zones and their exact boundaries.
    
    Supply Zone (for sells):
    - Upper boundary: QML level
    - Lower boundary: SR Flip level
    - Entry is inside this zone, not at a single line (Universal Rule 3)
    - Zone must be at Premium price (if Fibonacci required)
    
    Demand Zone (for buys):
    - Upper boundary: RS Flip level
    - Lower boundary: QMH level
    - Entry is inside this zone, not at a single line (Universal Rule 3)
    - Zone must be at Discount price (if Fibonacci required)
    
    The zone represents where institutional orders are located.
    Price must reach this zone before entry is valid.
    """
    
    def __init__(self, config: SnDConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def create_supply_zone(
        self,
        sequence: CandleSequence,
        qml_level: float,
        qml_timestamp: object,
        sr_flip_level: float,
        sr_flip_timestamp: object,
    ) -> SupplyZone:
        upper_bound = max(qml_level, sr_flip_level)
        lower_bound = min(qml_level, sr_flip_level)
        
        supply_zone = SupplyZone(
            symbol=sequence.symbol,
            timeframe=sequence.timeframe,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            timestamp=sr_flip_timestamp,
            qml_level=qml_level,
            qml_timestamp=qml_timestamp,
            sr_flip_level=sr_flip_level,
            sr_flip_timestamp=sr_flip_timestamp,
            is_valid=True,
        )
        
        self._logger.debug(
            "supply_zone_created",
            extra={
                "symbol": sequence.symbol,
                "timeframe": sequence.timeframe,
                "upper_bound": upper_bound,
                "lower_bound": lower_bound,
                "qml_level": qml_level,
                "sr_flip_level": sr_flip_level,
            },
        )
        
        return supply_zone
    
    def create_demand_zone(
        self,
        sequence: CandleSequence,
        qmh_level: float,
        qmh_timestamp: object,
        rs_flip_level: float,
        rs_flip_timestamp: object,
    ) -> DemandZone:
        upper_bound = max(qmh_level, rs_flip_level)
        lower_bound = min(qmh_level, rs_flip_level)
        
        demand_zone = DemandZone(
            symbol=sequence.symbol,
            timeframe=sequence.timeframe,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            timestamp=rs_flip_timestamp,
            qmh_level=qmh_level,
            qmh_timestamp=qmh_timestamp,
            rs_flip_level=rs_flip_level,
            rs_flip_timestamp=rs_flip_timestamp,
            is_valid=True,
        )
        
        self._logger.debug(
            "demand_zone_created",
            extra={
                "symbol": sequence.symbol,
                "timeframe": sequence.timeframe,
                "upper_bound": upper_bound,
                "lower_bound": lower_bound,
                "qmh_level": qmh_level,
                "rs_flip_level": rs_flip_level,
            },
        )
        
        return demand_zone
    
    def check_price_in_supply_zone(
        self,
        supply_zone: SupplyZone,
        current_price: float,
    ) -> bool:
        return supply_zone.lower_bound <= current_price <= supply_zone.upper_bound
    
    def check_price_in_demand_zone(
        self,
        demand_zone: DemandZone,
        current_price: float,
    ) -> bool:
        return demand_zone.lower_bound <= current_price <= demand_zone.upper_bound
