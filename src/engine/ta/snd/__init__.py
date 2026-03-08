"""
Supply and Demand (SnD) Framework - ForViL Trading System.

Implements all 14 SnD patterns with 9 universal rules:
- QML + SR/RS Flip + Fakeout (baseline)
- QML + MPL + SR/RS Flip + Fakeout
- QML + Previous Highs/Lows + MPL + SR/RS Flip + Fakeout (90% Killer Setup)
- QML + Triple Fakeout (highest confluence)
- Fakeout King
- Previous Highs/Lows + Supply/Demand Zone + Fakeout (S.O.P)

All patterns require:
- Marubozu breakout (non-negotiable)
- Previous Highs/Lows (minimum 2 clustered)
- Entry is a zone, not a line
- Top-down timeframe execution (H4/D1 → H1/M30 → M15/M5 → M1)
- Compression adds conviction
- Diamond Fakeout is exhaustion warning
- Fakeout broken by Marubozu = entry imminent
- Multiple fakeout tests = trend strength
- Fibonacci confluence (90% probability add-on)

Outputs SnDCandidate models for processor consumption.
"""

from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detector import SnDDetector

__all__ = [
    "SnDConfig",
    "SnDDetector",
]
