from __future__ import annotations

from uuid import UUID

from engine.rag.embeddings.pipeline import EmbeddingPipeline
from engine.rag.storage.repositories.chunk import ChunkRepository
from engine.rag.storage.repositories.reembed_queue import ReembedQueueRepository
from engine.rag.vectorstore.base import BaseVectorStore
from engine.rag.vectorstore.upsert import upsert_chunk_vectors
from engine.shared.exceptions import RAGError
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class ReembedService:
    def __init__(
        self,
        *,
        reembed_repo: ReembedQueueRepository,
        chunk_repo: ChunkRepository,
        embedding_pipeline: EmbeddingPipeline,
        vector_store: BaseVectorStore,
        collection: str,
    ) -> None:
        self._reembed_repo = reembed_repo
        self._chunk_repo = chunk_repo
        self._embedding_pipeline = embedding_pipeline
        self._vector_store = vector_store
        self._collection = collection

    async def process_pending(self, *, limit: int = 50) -> int:
        pending = await self._reembed_repo.get_pending(limit=limit)
        if not pending:
            return 0

        processed = 0
        for item in pending:
            try:
                await self._reembed_repo.mark_processing(item.id)
                await self._process_item(item.document_id, item.chunk_id)
                await self._reembed_repo.mark_completed(item.id)
                processed += 1
            except Exception as exc:
                logger.error(
                    "reembed_failed",
                    queue_id=str(item.id),
                    error=str(exc),
                )
                await self._reembed_repo.mark_failed(
                    item.id, error_message=str(exc),
                )

        logger.info("reembed_batch_completed", processed=processed, total=len(pending))
        return processed

    async def _process_item(
        self, document_id: UUID, chunk_id: UUID | None,
    ) -> None:
        if chunk_id:
            chunks = [c for c in await self._chunk_repo.get_by_document(document_id) if c.id == chunk_id]
        else:
            chunks = list(await self._chunk_repo.get_by_document(document_id))

        if not chunks:
            return

        contents = [c.metadata.get("content", "") for c in chunks]
        results = await self._embedding_pipeline.embed_chunks(chunks, contents)

        if results:
            chunk_ids = [r[0] for r in results]
            embeddings = [r[1] for r in results]
            documents = contents[:len(results)]
            metadatas = [c.metadata for c in chunks[:len(results)]]

            await upsert_chunk_vectors(
                store=self._vector_store,
                collection=self._collection,
                chunk_ids=chunk_ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
