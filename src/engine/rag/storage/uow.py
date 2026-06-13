from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from engine.rag.storage.repositories.chunk import ChunkRepository
from engine.rag.storage.repositories.citation_log import CitationLogRepository
from engine.rag.storage.repositories.document import DocumentRepository
from engine.rag.storage.repositories.document_version import DocumentVersionRepository
from engine.rag.storage.repositories.ingest_job import IngestJobRepository
from engine.rag.storage.repositories.reembed_queue import ReembedQueueRepository
from engine.rag.storage.repositories.retrieval_log import RetrievalLogRepository
from engine.rag.storage.repositories.scenario import ScenarioRepository
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class RAGUnitOfWork:
    """
    Scoped unit of work that owns a single session and all 8 RAG repositories.

    Usage::

        async with uow_factory() as uow:
            doc = await uow.document_repo.get_by_id(doc_id)
            await uow.chunk_repo.add(chunk)
            # auto-commit on success, rollback on error, close always
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._ctx: AbstractAsyncContextManager[AsyncSession] | None = None
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> RAGUnitOfWork:
        self._ctx = self._db.session()
        session = await self._ctx.__aenter__()
        self._session = session

        self.document_repo = DocumentRepository(session)
        self.version_repo = DocumentVersionRepository(session)
        self.chunk_repo = ChunkRepository(session)
        self.scenario_repo = ScenarioRepository(session)
        self.ingest_job_repo = IngestJobRepository(session)
        self.retrieval_log_repo = RetrievalLogRepository(session)
        self.citation_log_repo = CitationLogRepository(session)
        self.reembed_queue_repo = ReembedQueueRepository(session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if self._ctx is not None:
                await self._ctx.__aexit__(exc_type, exc_val, exc_tb)
        finally:
            self._ctx = None
            self._session = None


RAGUnitOfWorkFactory = Callable[[], RAGUnitOfWork]


def rag_uow_factory(db: DatabaseManager) -> RAGUnitOfWorkFactory:
    """Return a callable that creates ``RAGUnitOfWork`` instances."""

    def _factory() -> RAGUnitOfWork:
        return RAGUnitOfWork(db)

    return _factory
