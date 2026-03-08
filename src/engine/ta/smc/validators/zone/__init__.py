"""
SMC zone validation.

Validates the 7 Rules of a Tradeable Order Block:
1. Must sponsor a BOS/CHOCH
2. Must have FVG associated
3. Must have liquidity/inducement present
4. Must take out opposing OB
5. Must be at Premium (sells) or Discount (buys)
6. Must have BPR (FVG within FVG, OB within OB on subsequent TF)
7. Select HTF OBs, refine to LTF

Also validates:
- Zone freshness (unmitigated preferred)
- Zone overlap (avoid overlapping zones)
- Displacement context (minimum displacement requirement)
- Invalidation state (zone still valid)
"""

from engine.ta.smc.validators.zone.validator import ZoneValidator

__all__ = [
    "ZoneValidator",
]
