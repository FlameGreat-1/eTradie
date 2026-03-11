from __future__ import annotations

import hashlib
from uuid import UUID

from engine.config import RAGConfig
from engine.rag.embeddings.base import BaseEmbeddingProvider
from engine.rag.embeddings.validator import validate_embeddings
from engine.rag.storage.repositories.chunk import ChunkRepository
from engine.rag.storage.schemas.chunk import ChunkRow
from engine.shared.exceptions import RAGEmbeddingError
from engine.shared.logging import get_logger
from engine.shared.metrics import (
    RAG_EMBEDDING_BATCH_SIZE,
    RAG_EMBEDDING_DURATION,
    RAG_EMBEDDING_TOTAL,
)

logger = get_logger(__name__)


class EmbeddingPipeline:
    def __init__(
        self,
        *,
        config: RAGConfig,
        provider: BaseEmbeddingProvider,
        chunk_repo: ChunkRepository,
    ) -> None:
        self._config = config
        self._provider = provider
        self._chunk_repo = chunk_repo
        self._batch_size = config.embedding_batch_size

    async def embed_pending_chunks(
        self, *, limit: int = 500,
    ) -> list[tuple[UUID, list[float]]]:
        pending = await self._chunk_repo.get_pending_embedding(limit=limit)
        if not pending:
            return []

        results: list[tuple[UUID, list[float]]] = []

        for batch_start in range(0, len(pending), self._batch_size):
            batch = pending[batch_start:batch_start + self._batch_size]
            batch_results = await self._embed_batch(batch)
            results.extend(batch_results)

        return results

    async def embed_chunks(
        self, chunks: list[ChunkRow], contents: list[str],
    ) -> list[tuple[UUID, list[float]]]:
        if len(chunks) != len(contents):
            raise RAGEmbeddingError(
                f"Chunk/content count mismatch: {len(chunks)} vs {len(contents)}",
            )

        results: list[tuple[UUID, list[float]]] = []

        for batch_start in range(0, len(chunks), self._batch_size):
            batch_chunks = chunks[batch_start:batch_start + self._batch_size]
            batch_texts = contents[batch_start:batch_start + self._batch_size]

            import time
            start = time.monotonic()

            vectors = await self._provider.embed_batch(batch_texts)

            elapsed = time.monotonic() - start
            RAG_EMBEDDING_DURATION.labels(model=self._provider.model_name).observe(elapsed)
            RAG_EMBEDDING_BATCH_SIZE.labels(model=self._provider.model_name).observe(len(batch_texts))

            validate_embeddings(
                vectors,
                expected_count=len(batch_texts),
                expected_dimensions=self._provider.dimensions,
            )

            chunk_ids = [c.id for c in batch_chunks]
            await self._chunk_repo.set_embedding_status(chunk_ids, "embedded")

            for chunk_row, vector in zip(batch_chunks, vectors):
                results.append((chunk_row.id, vector))

            RAG_EMBEDDING_TOTAL.labels(
                model=self._provider.model_name, status="success",
            ).inc(len(batch_texts))

            logger.info(
                "embedding_batch_completed",
                batch_size=len(batch_texts),
                elapsed_s=round(elapsed, 3),
            )

        return results

    async def _embed_batch(
        self, chunk_rows: list[ChunkRow] | tuple[ChunkRow, ...],
    ) -> list[tuple[UUID, list[float]]]:
        texts = [row.metadata.get("content", "") for row in chunk_rows]

        import time
        start = time.monotonic()

        vectors = await self._provider.embed_batch(texts)

        elapsed = time.monotonic() - start
        RAG_EMBEDDING_DURATION.labels(model=self._provider.model_name).observe(elapsed)
        RAG_EMBEDDING_BATCH_SIZE.labels(model=self._provider.model_name).observe(len(texts))

        validate_embeddings(
            vectors,
            expected_count=len(texts),
            expected_dimensions=self._provider.dimensions,
        )

        chunk_ids = [row.id for row in chunk_rows]
        await self._chunk_repo.set_embedding_status(chunk_ids, "embedded")

        results: list[tuple[UUID, list[float]]] = []
        for row, vector in zip(chunk_rows, vectors):
            results.append((row.id, vector))

        RAG_EMBEDDING_TOTAL.labels(
            model=self._provider.model_name, status="success",
        ).inc(len(texts))

        return results

    @staticmethod
    def compute_vector_hash(vector: list[float]) -> str:
        raw = ",".join(f"{v:.8f}" for v in vector)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
