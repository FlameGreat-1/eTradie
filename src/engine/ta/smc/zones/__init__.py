"""
SMC zone extractors.

Implements the 7 Rules of a Tradeable Order Block:
1. Must sponsor a move that breaks/shifts market structure (BOS/CHOCH)
2. Must have an imbalance/FVG associated with it
3. Must have liquidity or inducement present
4. Must take out an opposing order block
5. Must be located at PREMIUM (sells) or DISCOUNT (buys)
6. Must have imbalance and OB in subsequent timeframe (BPR)
7. Select HTF OBs and refine to LTF for higher probability

All zones are validated against these rules before being marked as tradeable.

Mitigation is handled by ZoneValidator.validate_zone_freshness() which
uses body-threshold analysis to distinguish retests (RTO = entry opportunity)
from true mitigation (body closes through zone).
"""

from engine.ta.smc.zones.breaker import BreakerDetector
from engine.ta.smc.zones.fvg import FVGDetector
from engine.ta.smc.zones.order_block import OrderBlockDetector

__all__ = [
    "OrderBlockDetector",
    "FVGDetector",
    "BreakerDetector",
]
