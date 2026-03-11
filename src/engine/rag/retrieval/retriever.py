from __future__ import annotations

import time
from uuid import UUID

from engine.config import RAGConfig
from engine.rag.embeddings.base import BaseEmbeddingProvider
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.vectorstore.base import BaseVectorStore, VectorSearchResult
from engine.rag.vectorstore.filters import build_where_filter
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_DOCUMENTS_RETRIEVED, RAG_QUERY_DURATION, RAG_QUERY_TOTAL

logger = get_logger(__name__)


class Retriever:
    def __init__(
        self,
        *,
        config: RAGConfig,
        vector_store: BaseVectorStore,
        embedding_provider: BaseEmbeddingProvider,
    ) -> None:
        self._config = config
        self._store = vector_store
        self._embedder = embedding_provider

    async def retrieve(
        self,
        query_text: str,
        *,
        collection: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        doc_types: list[str] | None = None,
        frameworks: list[str] | None = None,
        setup_families: list[str] | None = None,
        directions: list[str] | None = None,
        timeframes: list[str] | None = None,
        styles: list[str] | None = None,
        scenario_outcomes: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        effective_top_k = top_k or self._config.retrieval_top_k
        effective_threshold = score_threshold if score_threshold is not None else self._config.retrieval_score_threshold

        start = time.monotonic()

        query_embedding = await self._embedder.embed_single(query_text)

        where = build_where_filter(
            doc_types=doc_types,
            frameworks=frameworks,
            setup_families=setup_families,
            directions=directions,
            timeframes=timeframes,
            styles=styles,
            scenario_outcomes=scenario_outcomes,
        )

        raw_results = await self._store.query(
            collection,
            query_embedding=query_embedding,
            top_k=effective_top_k,
            where=where,
        )

        filtered = [
            r for r in raw_results if r.score >= effective_threshold
        ]

        chunks = self._to_retrieved_chunks(filtered)

        elapsed = time.monotonic() - start
        RAG_QUERY_TOTAL.labels(collection=collection, status="success").inc()
        RAG_QUERY_DURATION.labels(collection=collection).observe(elapsed)
        RAG_DOCUMENTS_RETRIEVED.labels(collection=collection).observe(len(chunks))

        logger.info(
            "retrieval_completed",
            collection=collection,
            query_length=len(query_text),
            candidates=len(raw_results),
            returned=len(chunks),
            threshold=effective_threshold,
            elapsed_s=round(elapsed, 3),
        )

        return chunks

    def _to_retrieved_chunks(
        self, results: list[VectorSearchResult],
    ) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        for rank, result in enumerate(results):
            try:
                chunk_id = UUID(result.chunk_id)
                doc_id = UUID(result.metadata.get("doc_id", result.chunk_id))
            except ValueError:
                continue

            chunks.append(RetrievedChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                doc_type=result.metadata.get("doc_type", ""),
                content=result.content,
                score=result.score,
                rank=rank,
                section=result.metadata.get("section"),
                subsection=result.metadata.get("subsection"),
                metadata=result.metadata,
            ))
        return chunks
