from __future__ import annotations

from typing import Callable

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
        self._ctx = None
        self._session = None

    async def __aenter__(self) -> RAGUnitOfWork:
        self._ctx = self._db.session()
        self._session = await self._ctx.__aenter__()

        self.document_repo = DocumentRepository(self._session)
        self.version_repo = DocumentVersionRepository(self._session)
        self.chunk_repo = ChunkRepository(self._session)
        self.scenario_repo = ScenarioRepository(self._session)
        self.ingest_job_repo = IngestJobRepository(self._session)
        self.retrieval_log_repo = RetrievalLogRepository(self._session)
        self.citation_log_repo = CitationLogRepository(self._session)
        self.reembed_queue_repo = ReembedQueueRepository(self._session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._ctx.__aexit__(exc_type, exc_val, exc_tb)


RAGUnitOfWorkFactory = Callable[[], RAGUnitOfWork]


def rag_uow_factory(db: DatabaseManager) -> RAGUnitOfWorkFactory:
    """Return a callable that creates ``RAGUnitOfWork`` instances."""

    def _factory() -> RAGUnitOfWork:
        return RAGUnitOfWork(db)

    return _factory
