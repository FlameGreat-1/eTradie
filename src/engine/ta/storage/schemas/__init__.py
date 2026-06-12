"""
TA ORM/database schemas.

Defines SQLAlchemy models for:
- Candle: OHLCV data storage
- Snapshot: TechnicalSnapshot aggregate storage
- Candidate: SMC/SnD candidate output storage

All schemas use:
- UUID primary keys
- Timestamp indexing
- Symbol/timeframe composite indexes
- JSON fields for metadata
- Immutable historical records
"""

from engine.ta.storage.schemas.broker_symbol import BrokerSymbolSchema
from engine.ta.storage.schemas.candidate import CandidateSchema
from engine.ta.storage.schemas.candle import CandleSchema
from engine.ta.storage.schemas.snapshot import SnapshotSchema

__all__ = [
    "CandleSchema",
    "SnapshotSchema",
    "CandidateSchema",
    "BrokerSymbolSchema",
]
