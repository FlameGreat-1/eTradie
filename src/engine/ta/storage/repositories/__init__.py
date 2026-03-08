"""
TA repositories.

Provides async SQLAlchemy repositories for:
- Candles: Historical OHLCV data with cache snapshots and backfill support
- Snapshots: TechnicalSnapshot aggregate persistence and versioning
- Candidates: SMC/SnD candidate output storage and deduplication

All repositories follow repository pattern:
- Clean separation from business logic
- Async/await support for non-blocking I/O
- Transaction management
- Efficient batch operations
- Query optimization with proper indexing

Repository methods:
- create() - Insert new record
- get() - Retrieve by ID
- find() - Query with filters
- update() - Modify existing record
- delete() - Remove record
- bulk_create() - Batch insert
- bulk_update() - Batch modify
"""

from engine.ta.storage.repositories.candle import CandleRepository
from engine.ta.storage.repositories.snapshot import SnapshotRepository
from engine.ta.storage.repositories.candidate import CandidateRepository

__all__ = [
    "CandleRepository",
    "SnapshotRepository",
    "CandidateRepository",
]
