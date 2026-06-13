from __future__ import annotations

from pathlib import Path

from engine.config import RAGConfig
from engine.rag.constants import CollectionName
from engine.rag.ingest.pipeline import IngestPipeline
from engine.rag.knowledge.bootstrap.seed import seed_knowledge_assets
from engine.rag.knowledge.bootstrap.validator import validate_knowledge_readiness
from engine.rag.services.reembed import ReembedService
from engine.rag.services.versioning import VersioningService
from engine.rag.storage.uow import RAGUnitOfWorkFactory
from engine.rag.vectorstore.base import BaseVectorStore
from engine.rag.vectorstore.collections import bootstrap_collections
from engine.shared.exceptions import RAGBootstrapError
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_ACTIVE_CHUNKS, RAG_ACTIVE_DOCUMENTS

logger = get_logger(__name__)


class BootstrapService:
    def __init__(
        self,
        *,
        config: RAGConfig,
        uow_factory: RAGUnitOfWorkFactory,
        vector_store: BaseVectorStore,
        ingest_pipeline: IngestPipeline,
        reembed_service: ReembedService,
        versioning_service: VersioningService,
    ) -> None:
        self._config = config
        self._uow = uow_factory
        self._vector_store = vector_store
        self._ingest_pipeline = ingest_pipeline
        self._reembed_service = reembed_service
        self._versioning = versioning_service

    async def bootstrap(self) -> None:
        logger.info("rag_bootstrap_starting")

        try:
            await bootstrap_collections(
                store=self._vector_store,
                config=self._config,
            )
        except Exception as exc:
            raise RAGBootstrapError(
                f"Failed to bootstrap vector store collections: {exc}",
                details={"error": str(exc)},
            ) from exc

        try:
            logger.info("bootstrap_seeding_started")
            async with self._uow() as uow:
                # First, ensure new assets from manifest are in the DB
                await seed_knowledge_assets(
                    document_repo=uow.document_repo,
                    base_dir=self._config.knowledge_base_dir,
                )
                logger.info("bootstrap_seeding_completed")

                # Now, find ALL documents that are still in 'draft' status
                # (either newly seeded or from a previous failed/partial run)
                all_drafts = await uow.document_repo.get_by_status("draft")
                logger.info("bootstrap_drafts_found", count=len(all_drafts))

            if all_drafts:
                logger.info("ingesting_pending_drafts", count=len(all_drafts))
                for doc in all_drafts:
                    await self._ingest_pipeline.ingest(
                        path=Path(doc.source_path),
                        doc_type=doc.doc_type,
                        source_format=SourceFormat(doc.source_format),
                        title=doc.title,
                    )

                    # After chunking, we MUST activate the version to move it
                    # out of draft status and enqueue it for embedding.
                    async with self._uow() as uow:
                        latest_version = await uow.version_repo.get_latest(doc.id)

                    if latest_version:
                        await self._versioning.activate_version(doc.id, latest_version.id)

                # After all are chunked and activated, trigger the actual embedding process
                await self._drain_reembed_queue()

        except RAGBootstrapError:
            raise
        except Exception as exc:
            raise RAGBootstrapError(
                f"Failed to bootstrap knowledge assets: {exc}",
                details={"error": str(exc)},
            ) from exc

        # Reconcile ChromaDB with PostgreSQL to handle volume loss/reset.
        await self._reconcile_vectorstore()

        logger.info("rag_bootstrap_completed")

    async def _reconcile_vectorstore(self) -> None:
        """Detect and repair ChromaDB/PostgreSQL drift.

        Compares the number of vectors in ChromaDB against the number
        of active embedded chunks in PostgreSQL. If ChromaDB is empty
        or significantly behind, re-enqueues all active document chunks
        for embedding.

        This handles:
        - ChromaDB volume loss or recreation
        - Container rebuild without persistent volume
        - Partial embedding failures from previous runs
        - Any state where PostgreSQL and ChromaDB are out of sync

        The operation is idempotent: ChromaDB upsert overwrites existing
        vectors with identical content, so running this when data already
        exists has negligible cost.
        """
        try:
            chroma_count = await self._vector_store.count(self._config.collection_documents)
        except Exception as exc:
            logger.warning(
                "reconcile_chroma_count_failed",
                error=str(exc),
            )
            return

        async with self._uow() as uow:
            active_docs = await uow.document_repo.get_active_documents()
            if not active_docs:
                logger.info("reconcile_no_active_documents")
                return

            # Count all chunks belonging to active documents.
            pg_chunk_count = 0
            for doc in active_docs:
                chunks = await uow.chunk_repo.get_by_document(doc.id)
                pg_chunk_count += len(chunks)

        if pg_chunk_count == 0:
            logger.info("reconcile_no_chunks_in_postgres")
            return

        # If ChromaDB has at least 90% of the expected chunks, consider it healthy.
        # This threshold accounts for minor timing differences during concurrent writes.
        threshold = int(pg_chunk_count * 0.9)

        if chroma_count >= threshold:
            logger.info(
                "reconcile_vectorstore_healthy",
                chroma_count=chroma_count,
                pg_chunk_count=pg_chunk_count,
            )
            return

        # ChromaDB is behind. Re-enqueue all active documents for embedding.
        logger.warning(
            "reconcile_vectorstore_drift_detected",
            chroma_count=chroma_count,
            pg_chunk_count=pg_chunk_count,
            threshold=threshold,
        )

        enqueued = 0
        async with self._uow() as uow:
            for doc in active_docs:
                if doc.active_version_id is None:
                    continue
                # Check if this document already has a pending reembed entry.
                existing = await uow.reembed_queue_repo.get_by_document(doc.id)
                has_pending = any(r.status in ("pending", "running", "retrying") for r in existing)
                if has_pending:
                    continue

                await uow.reembed_queue_repo.enqueue(
                    document_id=doc.id,
                    document_version_id=doc.active_version_id,
                    reason="vectorstore_reconciliation",
                )
                enqueued += 1

        if enqueued > 0:
            logger.info(
                "reconcile_documents_enqueued_for_reembed",
                enqueued=enqueued,
            )
            await self._drain_reembed_queue()
            logger.info("reconcile_reembed_completed")
        else:
            logger.info("reconcile_no_documents_needed_reembed")

    async def _drain_reembed_queue(self) -> None:
        """Process the reembed queue until it is fully drained.

        The ReembedService.process_pending() processes items in batches.
        This method calls it repeatedly until no more pending items remain,
        ensuring all enqueued documents are fully embedded into ChromaDB.
        """
        total_processed = 0
        while True:
            batch_count = await self._reembed_service.process_pending(limit=100)
            if batch_count == 0:
                break
            total_processed += batch_count

        if total_processed > 0:
            logger.info(
                "reembed_queue_drained",
                total_processed=total_processed,
            )

    async def check_readiness(self) -> bool:
        async with self._uow() as uow:
            ready = await validate_knowledge_readiness(
                document_repo=uow.document_repo,
            )
            if ready:
                docs = await uow.document_repo.get_active_documents()

                # Group by doc_type and set labels correctly to avoid ValueError
                counts: dict[str, int] = {}
                for d in docs:
                    counts[d.doc_type] = counts.get(d.doc_type, 0) + 1

                for dt, count in counts.items():
                    RAG_ACTIVE_DOCUMENTS.labels(doc_type=dt).set(count)

                chunk_total = 0
                for doc in docs:
                    chunks = await uow.chunk_repo.get_by_document(doc.id)
                    chunk_total += len(chunks)
                RAG_ACTIVE_CHUNKS.labels(collection=CollectionName.DOCUMENTS).set(chunk_total)
            return ready
