"""
TA domain models for candles, swings, structure, liquidity, zones, and candidates.

All models are immutable (frozen) and include comprehensive validation.
These models represent the deterministic technical facts output by the TA module.
"""

from engine.ta.models.candle import Candle, CandleSequence
from engine.ta.models.swing import SwingPoint, SwingHigh, SwingLow

__all__ = [
    "Candle",
    "CandleSequence",
    "SwingPoint",
    "SwingHigh",
    "SwingLow",
]
