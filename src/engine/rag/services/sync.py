from __future__ import annotations

from uuid import UUID

from engine.rag.storage.repositories.chunk import ChunkRepository
from engine.rag.storage.repositories.document import DocumentRepository
from engine.rag.storage.repositories.document_version import DocumentVersionRepository
from engine.rag.vectorstore.base import BaseVectorStore
from engine.rag.vectorstore.upsert import delete_chunk_vectors
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class SyncService:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        version_repo: DocumentVersionRepository,
        chunk_repo: ChunkRepository,
        vector_store: BaseVectorStore,
        collection: str,
    ) -> None:
        self._document_repo = document_repo
        self._version_repo = version_repo
        self._chunk_repo = chunk_repo
        self._vector_store = vector_store
        self._collection = collection

    async def reconcile_stale_chunks(
        self, document_id: UUID,
    ) -> int:
        active_version = await self._version_repo.get_active(document_id)
        if not active_version:
            return 0

        all_chunks = await self._chunk_repo.get_by_document(document_id)
        stale = [
            c for c in all_chunks
            if c.document_version_id != active_version.id
        ]

        if not stale:
            return 0

        stale_ids = [c.id for c in stale]
        await delete_chunk_vectors(
            store=self._vector_store,
            collection=self._collection,
            chunk_ids=stale_ids,
        )

        for chunk in stale:
            await self._chunk_repo.set_embedding_status([chunk.id], "stale")

        logger.info(
            "stale_chunks_reconciled",
            document_id=str(document_id),
            stale_count=len(stale),
        )

        return len(stale)

    async def full_sync(self) -> int:
        active_docs = await self._document_repo.get_active_documents()
        total_reconciled = 0

        for doc in active_docs:
            count = await self.reconcile_stale_chunks(doc.id)
            total_reconciled += count

        logger.info("full_sync_completed", total_reconciled=total_reconciled)
        return total_reconciled
