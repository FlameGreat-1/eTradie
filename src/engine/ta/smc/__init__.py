"""
Smart Money Concepts (SMC) Framework.

Implements all 10 SMC patterns with 12 universal rules:
- Turtle Soup (liquidity sweeps with reversal)
- SH + BMS + RTO (stop hunt + break + retracement)
- SMS + BMS + RTO (shift + break + retracement)
- AMD (accumulation, manipulation, distribution)
- Combined patterns (highest confluence)

All patterns require:
- HTF BMS alignment
- Liquidity taken first
- Retracement to OB/OTE
- Minimum 3 confluences
- Premium/Discount filtering
- Session timing (London/NY)
- LTF confirmation

Outputs SMCCandidate models for processor consumption.
"""

from engine.ta.smc.config import SMCConfig
from engine.ta.smc.detector import SMCDetector

__all__ = [
    "SMCConfig",
    "SMCDetector",
]
