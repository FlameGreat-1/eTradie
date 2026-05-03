from __future__ import annotations

from typing import Callable, Optional

from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger
from engine.ta.storage.repositories.candle import CandleRepository
from engine.ta.storage.repositories.candidate import CandidateRepository
from engine.ta.storage.repositories.snapshot import SnapshotRepository
from engine.ta.storage.repositories.broker_symbol import BrokerSymbolRepository

logger = get_logger(__name__)


class TAUnitOfWork:
    """
    Scoped unit of work for the TA engine.

    Ensures that every TA operation (candle fetch, snapshot persist,
    candidate persist) has its own transactionally safe session and
    correctly initialized repositories.

    Usage::

        async with ta_uow_factory() as uow:
            candles = await uow.candle_repo.find_by_time_range(...)
            await uow.snapshot_repo.create(...)
            # auto-commit on success, rollback on error, close always
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._ctx = None
        self._session = None
        self.candle_repo: Optional[CandleRepository] = None
        self.snapshot_repo: Optional[SnapshotRepository] = None
        self.candidate_repo: Optional[CandidateRepository] = None
        self.broker_symbol_repo: Optional[BrokerSymbolRepository] = None

    async def __aenter__(self) -> TAUnitOfWork:
        self._ctx = self._db.session()
        self._session = await self._ctx.__aenter__()

        self.candle_repo = CandleRepository(self._session)
        self.snapshot_repo = SnapshotRepository(self._session)
        self.candidate_repo = CandidateRepository(self._session)
        self.broker_symbol_repo = BrokerSymbolRepository(self._session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._ctx.__aexit__(exc_type, exc_val, exc_tb)


class TAReadUnitOfWork:
    """
    Read-only scoped unit of work for the TA engine.

    Uses read_session() (no auto-commit) for query-only operations
    like candle lookups in the orchestrator's fetch sequence.

    Usage::

        async with ta_read_uow_factory() as uow:
            candles = await uow.candle_repo.find_by_time_range(...)
            # no commit, session closed on exit
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._ctx = None
        self._session = None
        self.candle_repo: Optional[CandleRepository] = None
        self.snapshot_repo: Optional[SnapshotRepository] = None
        self.candidate_repo: Optional[CandidateRepository] = None
        self.broker_symbol_repo: Optional[BrokerSymbolRepository] = None

    async def __aenter__(self) -> TAReadUnitOfWork:
        self._ctx = self._db.read_session()
        self._session = await self._ctx.__aenter__()

        self.candle_repo = CandleRepository(self._session)
        self.snapshot_repo = SnapshotRepository(self._session)
        self.candidate_repo = CandidateRepository(self._session)
        self.broker_symbol_repo = BrokerSymbolRepository(self._session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._ctx.__aexit__(exc_type, exc_val, exc_tb)


TAUOWFactory = Callable[[], TAUnitOfWork]
TAReadUOWFactory = Callable[[], TAReadUnitOfWork]


def ta_uow_factory(db: DatabaseManager) -> TAUOWFactory:
    """Return a callable that creates ``TAUnitOfWork`` instances."""

    def _factory() -> TAUnitOfWork:
        return TAUnitOfWork(db)

    return _factory


def ta_read_uow_factory(db: DatabaseManager) -> TAReadUOWFactory:
    """Return a callable that creates ``TAReadUnitOfWork`` instances."""

    def _factory() -> TAReadUnitOfWork:
        return TAReadUnitOfWork(db)

    return _factory
