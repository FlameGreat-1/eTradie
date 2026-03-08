"""
TA persistence layer.

Provides database repositories for:
- Candles: Historical OHLCV data with cache snapshots
- Snapshots: Persisted TechnicalSnapshot aggregates (all detected primitives)
- Candidates: Deterministic SMC/SnD candidate outputs ready for processor

All repositories use SQLAlchemy ORM with async support.
Schemas are defined separately for clean separation of concerns.

Storage layer enforces:
- Immutable historical data (candles never modified after insert)
- Snapshot versioning (track changes over time)
- Candidate deduplication (same pattern not stored twice)
- Efficient querying (indexed by symbol, timeframe, timestamp)
"""

from engine.ta.storage.repositories.candle import CandleRepository
from engine.ta.storage.repositories.snapshot import SnapshotRepository
from engine.ta.storage.repositories.candidate import CandidateRepository

__all__ = [
    "CandleRepository",
    "SnapshotRepository",
    "CandidateRepository",
]
