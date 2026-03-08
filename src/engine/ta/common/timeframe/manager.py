from typing import Optional

from engine.shared.exceptions import ConfigurationError
from engine.ta.constants import Timeframe, TimeframeRelation, TIMEFRAME_MINUTES


class TimeframeManager:
    
    _HIERARCHY: list[Timeframe] = [
        Timeframe.M1,
        Timeframe.M5,
        Timeframe.M15,
        Timeframe.M30,
        Timeframe.H1,
        Timeframe.H4,
        Timeframe.D1,
        Timeframe.W1,
        Timeframe.MN1,
    ]
    
    def __init__(self) -> None:
        self._hierarchy_index = {tf: idx for idx, tf in enumerate(self._HIERARCHY)}
    
    def get_relation(self, tf1: Timeframe, tf2: Timeframe) -> TimeframeRelation:
        idx1 = self._hierarchy_index.get(tf1)
        idx2 = self._hierarchy_index.get(tf2)
        
        if idx1 is None or idx2 is None:
            return TimeframeRelation.UNRELATED
        
        if idx1 == idx2:
            return TimeframeRelation.SAME
        
        if idx1 > idx2:
            return TimeframeRelation.PARENT
        
        return TimeframeRelation.CHILD
    
    def get_parent(self, timeframe: Timeframe, steps: int = 1) -> Optional[Timeframe]:
        if steps < 1:
            raise ConfigurationError(
                "Steps must be at least 1",
                details={"steps": steps},
            )
        
        idx = self._hierarchy_index.get(timeframe)
        
        if idx is None:
            return None
        
        parent_idx = idx + steps
        
        if parent_idx >= len(self._HIERARCHY):
            return None
        
        return self._HIERARCHY[parent_idx]
    
    def get_child(self, timeframe: Timeframe, steps: int = 1) -> Optional[Timeframe]:
        if steps < 1:
            raise ConfigurationError(
                "Steps must be at least 1",
                details={"steps": steps},
            )
        
        idx = self._hierarchy_index.get(timeframe)
        
        if idx is None:
            return None
        
        child_idx = idx - steps
        
        if child_idx < 0:
            return None
        
        return self._HIERARCHY[child_idx]
    
    def is_htf_of(self, potential_htf: Timeframe, reference: Timeframe) -> bool:
        relation = self.get_relation(potential_htf, reference)
        return relation == TimeframeRelation.PARENT
    
    def is_ltf_of(self, potential_ltf: Timeframe, reference: Timeframe) -> bool:
        relation = self.get_relation(potential_ltf, reference)
        return relation == TimeframeRelation.CHILD
    
    def get_minutes(self, timeframe: Timeframe) -> int:
        minutes = TIMEFRAME_MINUTES.get(timeframe)
        
        if minutes is None:
            raise ConfigurationError(
                f"Unknown timeframe: {timeframe}",
                details={"timeframe": timeframe},
            )
        
        return minutes
    
    def calculate_candle_count(
        self,
        source_tf: Timeframe,
        target_tf: Timeframe,
    ) -> int:
        source_minutes = self.get_minutes(source_tf)
        target_minutes = self.get_minutes(target_tf)
        
        if target_minutes < source_minutes:
            raise ConfigurationError(
                "Target timeframe must be >= source timeframe",
                details={
                    "source_tf": source_tf,
                    "target_tf": target_tf,
                    "source_minutes": source_minutes,
                    "target_minutes": target_minutes,
                },
            )
        
        if target_minutes % source_minutes != 0:
            raise ConfigurationError(
                "Target timeframe must be a multiple of source timeframe",
                details={
                    "source_tf": source_tf,
                    "target_tf": target_tf,
                    "source_minutes": source_minutes,
                    "target_minutes": target_minutes,
                },
            )
        
        return target_minutes // source_minutes


_manager: Optional[TimeframeManager] = None


def _get_manager() -> TimeframeManager:
    global _manager
    
    if _manager is None:
        _manager = TimeframeManager()
    
    return _manager


def get_timeframe_relation(tf1: Timeframe, tf2: Timeframe) -> TimeframeRelation:
    return _get_manager().get_relation(tf1, tf2)


def get_parent_timeframe(timeframe: Timeframe, steps: int = 1) -> Optional[Timeframe]:
    return _get_manager().get_parent(timeframe, steps)


def get_child_timeframe(timeframe: Timeframe, steps: int = 1) -> Optional[Timeframe]:
    return _get_manager().get_child(timeframe, steps)


def is_htf_of(potential_htf: Timeframe, reference: Timeframe) -> bool:
    return _get_manager().is_htf_of(potential_htf, reference)


def is_ltf_of(potential_ltf: Timeframe, reference: Timeframe) -> bool:
    return _get_manager().is_ltf_of(potential_ltf, reference)
