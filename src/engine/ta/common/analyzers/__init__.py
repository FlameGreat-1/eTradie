"""
Shared deterministic analyzers for pattern detection.

These analyzers are framework-agnostic and used by both SMC and SnD:
- Candle classification and displacement detection
- Swing point detection with configurable strength
- Session boundary identification
- Liquidity pool mapping (BSL/SSL)
- Sweep detection logic
- Fibonacci retracement calculations
- Dealing range construction
- Marubozu detection
- Compression/expansion detection

All analyzers are pure functions or stateless classes.
"""

from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.common.analyzers.liquidity import LiquidityAnalyzer
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.analyzers.dealing_range import DealingRangeAnalyzer
from engine.ta.common.analyzers.marubozu import MarubozuAnalyzer
from engine.ta.common.analyzers.compression import CompressionAnalyzer

__all__ = [
    "CandleAnalyzer",
    "SwingAnalyzer",
    "SessionAnalyzer",
    "LiquidityAnalyzer",
    "SweepAnalyzer",
    "FibonacciAnalyzer",
    "DealingRangeAnalyzer",
    "MarubozuAnalyzer",
    "CompressionAnalyzer",
]
