"""
Shared TA services for snapshot building and timeframe alignment.

Services:
- SnapshotBuilder: Constructs TechnicalSnapshot from broker data and analyzer outputs
- AlignmentService: Validates HTF/LTF directional consistency and zone nesting
"""

from engine.ta.common.services.snapshot.builder import SnapshotBuilder
from engine.ta.common.services.alignment.service import AlignmentService

__all__ = [
    "SnapshotBuilder",
    "AlignmentService",
]
