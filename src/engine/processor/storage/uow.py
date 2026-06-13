from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from engine.processor.storage.repositories.analysis_repository import AnalysisRepository
from engine.processor.storage.repositories.audit_repository import AuditRepository
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class ProcessorUnitOfWork:
    """
    Scoped unit of work for the Analysis Processor.

    Ensures that every analysis request has its own transactionally
    safe session and correctly initialized repositories.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._ctx: AbstractAsyncContextManager[AsyncSession] | None = None
        self._session: AsyncSession | None = None
        self._analysis_repo: AnalysisRepository | None = None
        self._audit_repo: AuditRepository | None = None

    @property
    def analysis_repo(self) -> AnalysisRepository:
        if self._analysis_repo is None:
            raise RuntimeError("ProcessorUnitOfWork used outside its async context")
        return self._analysis_repo

    @property
    def audit_repo(self) -> AuditRepository:
        if self._audit_repo is None:
            raise RuntimeError("ProcessorUnitOfWork used outside its async context")
        return self._audit_repo

    async def __aenter__(self) -> ProcessorUnitOfWork:
        self._ctx = self._db.session()
        session = await self._ctx.__aenter__()
        self._session = session

        self._analysis_repo = AnalysisRepository(session)
        self._audit_repo = AuditRepository(session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._ctx is not None:
            await self._ctx.__aexit__(exc_type, exc_val, exc_tb)


ProcessorUOWFactory = Callable[[], ProcessorUnitOfWork]


def processor_uow_factory(db: DatabaseManager) -> ProcessorUOWFactory:
    """Return a callable that creates ``ProcessorUnitOfWork`` instances."""

    def _factory() -> ProcessorUnitOfWork:
        return ProcessorUnitOfWork(db)

    return _factory
