"""
SnD lower-timeframe validation.

Validates the 4 LTF Confirmation Requirements before entry:
1. Compression at the Zone (CP inside fakeout zone - tight directional candles)
2. Fakeout Broken by Marubozu (single Marubozu breaks fakeout zone)
3. Decision Point (exact candle where price makes final rejection at SR/RS Flip)
4. Fibonacci Alignment (optional but 90% probability - 50%, 61.8%, 70.5%, 79% levels)

All 4 confirmations must be present before a candidate is eligible for entry.

Top-Down Execution (Universal Rule 4):
- HTF (H4/D1): Identify QM structure, QML, Previous Highs/Lows
- Mid TF (H1/M30): Confirm SR/RS Flip zone and fakeout formation
- Lower TF (M15/M5): Confirm Compression inside fakeout zone
- Lowest TF (M1): Find Decision Point - exact rejection candle - entry trigger
"""

from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator

__all__ = [
    "LTFConfirmationValidator",
]
