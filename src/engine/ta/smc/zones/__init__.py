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
"""

from engine.ta.smc.zones.order_block import OrderBlockDetector
from engine.ta.smc.zones.fvg import FVGDetector
from engine.ta.smc.zones.breaker import BreakerDetector
from engine.ta.smc.zones.mitigation import MitigationDetector

__all__ = [
    "OrderBlockDetector",
    "FVGDetector",
    "BreakerDetector",
    "MitigationDetector",
]
