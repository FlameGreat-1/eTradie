"""
SMC lower-timeframe validation.

Validates the 6 LTF Confirmation Requirements before entry:
1. Liquidity has been taken (Stop Hunt completed)
2. CHOCH on LTF (first sign of order flow shift)
3. BMS confirmed on LTF (reversal direction confirmed)
4. Price returns to LTF Order Block (RTO - entry point)
5. Session timing (London/NY opens)
6. Inducement has been cleared (internal highs/lows swept)

All 6 confirmations must be present before a candidate is eligible for entry.
"""

from engine.ta.smc.validators.ltf.confirmation import LTFConfirmationValidator

__all__ = [
    "LTFConfirmationValidator",
]
