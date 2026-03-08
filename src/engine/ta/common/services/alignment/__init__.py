"""
Timeframe alignment service.

Validates HTF/LTF directional consistency and zone nesting.
Ensures multi-timeframe confluence before candidate generation.
"""

from engine.ta.common.services.alignment.service import AlignmentService

__all__ = [
    "AlignmentService",
]
