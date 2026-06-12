from __future__ import annotations

from collections.abc import Callable

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
        self._ctx = None
        self._session = None
        self.analysis_repo: AnalysisRepository | None = None
        self.audit_repo: AuditRepository | None = None

    async def __aenter__(self) -> ProcessorUnitOfWork:
        self._ctx = self._db.session()
        self._session = await self._ctx.__aenter__()

        self.analysis_repo = AnalysisRepository(self._session)
        self.audit_repo = AuditRepository(self._session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._ctx.__aexit__(exc_type, exc_val, exc_tb)


ProcessorUOWFactory = Callable[[], ProcessorUnitOfWork]


def processor_uow_factory(db: DatabaseManager) -> ProcessorUOWFactory:
    """Return a callable that creates ``ProcessorUnitOfWork`` instances."""

    def _factory() -> ProcessorUnitOfWork:
        return ProcessorUnitOfWork(db)

    return _factory
