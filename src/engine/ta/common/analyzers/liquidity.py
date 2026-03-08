from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import is_within_tolerance
from engine.ta.constants import LiquidityType
from engine.ta.models.candle import CandleSequence
from engine.ta.models.liquidity_event import LiquidityPool, EqualHighsLows
from engine.ta.models.swing import SwingHigh, SwingLow

logger = get_logger(__name__)


class LiquidityAnalyzer:
    
    def __init__(
        self,
        *,
        equal_tolerance_pips: float = 2.0,
        min_touches: int = 2,
        clustering_distance_pips: float = 5.0,
    ) -> None:
        self.equal_tolerance_pips = equal_tolerance_pips
        self.min_touches = min_touches
        self.clustering_distance_pips = clustering_distance_pips
    
    def detect_bsl(
        self,
        swing_highs: list[SwingHigh],
    ) -> list[LiquidityPool]:
        bsl_pools = []
        
        for swing_high in swing_highs:
            pool = LiquidityPool(
                symbol=swing_high.symbol,
                timeframe=swing_high.timeframe,
                liquidity_type=LiquidityType.BSL,
                price_level=swing_high.price,
                timestamp=swing_high.timestamp,
                strength=swing_high.strength,
                touch_count=1,
            )
            bsl_pools.append(pool)
        
        return bsl_pools
    
    def detect_ssl(
        self,
        swing_lows: list[SwingLow],
    ) -> list[LiquidityPool]:
        ssl_pools = []
        
        for swing_low in swing_lows:
            pool = LiquidityPool(
                symbol=swing_low.symbol,
                timeframe=swing_low.timeframe,
                liquidity_type=LiquidityType.SSL,
                price_level=swing_low.price,
                timestamp=swing_low.timestamp,
                strength=swing_low.strength,
                touch_count=1,
            )
            ssl_pools.append(pool)
        
        return ssl_pools
    
    def detect_equal_highs(
        self,
        swing_highs: list[SwingHigh],
    ) -> list[EqualHighsLows]:
        equal_highs_groups = []
        
        processed_indices = set()
        
        for i, swing_high in enumerate(swing_highs):
            if i in processed_indices:
                continue
            
            group_timestamps = [swing_high.timestamp]
            group_indices = [swing_high.index]
            
            for j in range(i + 1, len(swing_highs)):
                if j in processed_indices:
                    continue
                
                other_swing = swing_highs[j]
                
                if is_within_tolerance(
                    swing_high.price,
                    other_swing.price,
                    self.equal_tolerance_pips,
                    swing_high.symbol,
                ):
                    group_timestamps.append(other_swing.timestamp)
                    group_indices.append(other_swing.index)
                    processed_indices.add(j)
            
            if len(group_timestamps) >= self.min_touches:
                equal_highs = EqualHighsLows(
                    symbol=swing_high.symbol,
                    timeframe=swing_high.timeframe,
                    liquidity_type=LiquidityType.EQUAL_HIGHS,
                    price_level=swing_high.price,
                    timestamps=group_timestamps,
                    tolerance_pips=self.equal_tolerance_pips,
                    candle_indices=group_indices,
                )
                equal_highs_groups.append(equal_highs)
                processed_indices.add(i)
        
        return equal_highs_groups
    
    def detect_equal_lows(
        self,
        swing_lows: list[SwingLow],
    ) -> list[EqualHighsLows]:
        equal_lows_groups = []
        
        processed_indices = set()
        
        for i, swing_low in enumerate(swing_lows):
            if i in processed_indices:
                continue
            
            group_timestamps = [swing_low.timestamp]
            group_indices = [swing_low.index]
            
            for j in range(i + 1, len(swing_lows)):
                if j in processed_indices:
                    continue
                
                other_swing = swing_lows[j]
                
                if is_within_tolerance(
                    swing_low.price,
                    other_swing.price,
                    self.equal_tolerance_pips,
                    swing_low.symbol,
                ):
                    group_timestamps.append(other_swing.timestamp)
                    group_indices.append(other_swing.index)
                    processed_indices.add(j)
            
            if len(group_timestamps) >= self.min_touches:
                equal_lows = EqualHighsLows(
                    symbol=swing_low.symbol,
                    timeframe=swing_low.timeframe,
                    liquidity_type=LiquidityType.EQUAL_LOWS,
                    price_level=swing_low.price,
                    timestamps=group_timestamps,
                    tolerance_pips=self.equal_tolerance_pips,
                    candle_indices=group_indices,
                )
                equal_lows_groups.append(equal_lows)
                processed_indices.add(i)
        
        return equal_lows_groups
    
    def cluster_liquidity_pools(
        self,
        pools: list[LiquidityPool],
    ) -> list[list[LiquidityPool]]:
        if not pools:
            return []
        
        sorted_pools = sorted(pools, key=lambda p: p.price_level)
        
        clusters = []
        current_cluster = [sorted_pools[0]]
        
        for i in range(1, len(sorted_pools)):
            current_pool = sorted_pools[i]
            previous_pool = sorted_pools[i - 1]
            
            if is_within_tolerance(
                current_pool.price_level,
                previous_pool.price_level,
                self.clustering_distance_pips,
                current_pool.symbol,
            ):
                current_cluster.append(current_pool)
            else:
                clusters.append(current_cluster)
                current_cluster = [current_pool]
        
        if current_cluster:
            clusters.append(current_cluster)
        
        return clusters
    
    def get_nearest_liquidity(
        self,
        current_price: float,
        pools: list[LiquidityPool],
        above: bool = True,
    ) -> Optional[LiquidityPool]:
        if not pools:
            return None
        
        if above:
            above_pools = [p for p in pools if p.price_level > current_price]
            if not above_pools:
                return None
            return min(above_pools, key=lambda p: abs(p.price_level - current_price))
        else:
            below_pools = [p for p in pools if p.price_level < current_price]
            if not below_pools:
                return None
            return min(below_pools, key=lambda p: abs(p.price_level - current_price))
    
    def calculate_liquidity_draw(
        self,
        current_price: float,
        target_pool: LiquidityPool,
    ) -> float:
        from engine.ta.common.utils.price.math import calculate_pips
        
        return calculate_pips(
            current_price,
            target_pool.price_level,
            target_pool.symbol,
        )
