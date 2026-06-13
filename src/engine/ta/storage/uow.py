from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger
from engine.ta.storage.repositories.broker_symbol import BrokerSymbolRepository
from engine.ta.storage.repositories.candidate import CandidateRepository
from engine.ta.storage.repositories.candle import CandleRepository
from engine.ta.storage.repositories.snapshot import SnapshotRepository

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
        self._ctx: AbstractAsyncContextManager[AsyncSession] | None = None
        self._session: AsyncSession | None = None
        self._candle_repo: CandleRepository | None = None
        self._snapshot_repo: SnapshotRepository | None = None
        self._candidate_repo: CandidateRepository | None = None
        self._broker_symbol_repo: BrokerSymbolRepository | None = None

    @property
    def candle_repo(self) -> CandleRepository:
        if self._candle_repo is None:
            raise RuntimeError("TAUnitOfWork used outside its async context")
        return self._candle_repo

    @property
    def snapshot_repo(self) -> SnapshotRepository:
        if self._snapshot_repo is None:
            raise RuntimeError("TAUnitOfWork used outside its async context")
        return self._snapshot_repo

    @property
    def candidate_repo(self) -> CandidateRepository:
        if self._candidate_repo is None:
            raise RuntimeError("TAUnitOfWork used outside its async context")
        return self._candidate_repo

    @property
    def broker_symbol_repo(self) -> BrokerSymbolRepository:
        if self._broker_symbol_repo is None:
            raise RuntimeError("TAUnitOfWork used outside its async context")
        return self._broker_symbol_repo

    async def __aenter__(self) -> TAUnitOfWork:
        self._ctx = self._db.session()
        session = await self._ctx.__aenter__()
        self._session = session

        self._candle_repo = CandleRepository(session)
        self._snapshot_repo = SnapshotRepository(session)
        self._candidate_repo = CandidateRepository(session)
        self._broker_symbol_repo = BrokerSymbolRepository(session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._ctx is not None:
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
        self._ctx: AbstractAsyncContextManager[AsyncSession] | None = None
        self._session: AsyncSession | None = None
        self._candle_repo: CandleRepository | None = None
        self._snapshot_repo: SnapshotRepository | None = None
        self._candidate_repo: CandidateRepository | None = None
        self._broker_symbol_repo: BrokerSymbolRepository | None = None

    @property
    def candle_repo(self) -> CandleRepository:
        if self._candle_repo is None:
            raise RuntimeError("TAReadUnitOfWork used outside its async context")
        return self._candle_repo

    @property
    def snapshot_repo(self) -> SnapshotRepository:
        if self._snapshot_repo is None:
            raise RuntimeError("TAReadUnitOfWork used outside its async context")
        return self._snapshot_repo

    @property
    def candidate_repo(self) -> CandidateRepository:
        if self._candidate_repo is None:
            raise RuntimeError("TAReadUnitOfWork used outside its async context")
        return self._candidate_repo

    @property
    def broker_symbol_repo(self) -> BrokerSymbolRepository:
        if self._broker_symbol_repo is None:
            raise RuntimeError("TAReadUnitOfWork used outside its async context")
        return self._broker_symbol_repo

    async def __aenter__(self) -> TAReadUnitOfWork:
        self._ctx = self._db.read_session()
        session = await self._ctx.__aenter__()
        self._session = session

        self._candle_repo = CandleRepository(session)
        self._snapshot_repo = SnapshotRepository(session)
        self._candidate_repo = CandidateRepository(session)
        self._broker_symbol_repo = BrokerSymbolRepository(session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._ctx is not None:
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
