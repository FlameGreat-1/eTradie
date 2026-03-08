"""
SnD marubozu validation.

Validates Marubozu quality and eligibility in SnD context.

Universal Rule 1: Marubozu is Non-Negotiable
- Every breakout of Support or Resistance must be executed by ONE single Marubozu candle
- Full body, no or minimal wicks
- No Marubozu = no valid SR/RS Flip = no valid setup
- This applies to:
  * Initial Clean Breakout (creates SR/RS Flip)
  * Marubozu that breaks the fakeout zone (entry signal)

Marubozu Requirements:
- Body percentage >= 80% (configurable, default 80%)
- Wick percentage <= 10% (configurable, default 10%)
- Must close substantially beyond the level
- Single candle only (no multi-candle breakouts)
"""

from engine.ta.snd.validators.marubozu.validator import MarubozuValidator

__all__ = [
    "MarubozuValidator",
]
