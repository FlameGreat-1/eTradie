"""
Timeframe management and HTF/LTF coordination utilities.

Contains:
- manager.py: Timeframe relationship logic, parent/child lookup, synchronization helpers
"""

from engine.ta.common.timeframe.manager import (
    TimeframeManager,
    get_timeframe_relation,
    get_parent_timeframe,
    get_child_timeframe,
    is_htf_of,
    is_ltf_of,
)

__all__ = [
    "TimeframeManager",
    "get_timeframe_relation",
    "get_parent_timeframe",
    "get_child_timeframe",
    "is_htf_of",
    "is_ltf_of",
]
