"""
SnD validation helpers.

Validators enforce:
- Marubozu quality (Universal Rule 1 - non-negotiable)
- 4 LTF Confirmation Requirements (all must be met before entry)
- Premium/Discount filtering (mandatory if enabled)
- Fibonacci confluence validation (90% probability add-on)
- Previous Highs/Lows minimum requirement (2+ touches)
- Compression presence (adds conviction)
- Diamond Fakeout detection (exhaustion warning)

No candidate is generated unless all validation rules pass.
"""

from engine.ta.snd.validators.marubozu.validator import MarubozuValidator
from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator

__all__ = [
    "MarubozuValidator",
    "LTFConfirmationValidator",
]
