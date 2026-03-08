"""
Snapshot building service.

Constructs normalized TechnicalSnapshot from:
- Broker candle data
- Common analyzer outputs (swings, sessions, liquidity, etc.)
- Framework-specific detections (SMC/SnD)
"""

from engine.ta.common.services.snapshot.builder import SnapshotBuilder

__all__ = [
    "SnapshotBuilder",
]
