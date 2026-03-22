from __future__ import annotations
from pathlib import Path

from engine.config import RAGConfig
from engine.rag.constants import CollectionName
from engine.rag.knowledge.bootstrap.seed import seed_knowledge_assets
from engine.rag.knowledge.bootstrap.validator import validate_knowledge_readiness
from engine.rag.storage.uow import RAGUnitOfWorkFactory
from engine.rag.vectorstore.base import BaseVectorStore
from engine.rag.vectorstore.collections import bootstrap_collections
from engine.shared.exceptions import RAGBootstrapError
from engine.rag.ingest.pipeline import IngestPipeline
from engine.rag.services.reembed import ReembedService
from engine.rag.services.versioning import VersioningService
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
                        source_format=doc.source_format,
                        title=doc.title,
                    )
                    
                    # After chunking, we MUST activate the version to move it
                    # out of draft status and enqueue it for embedding.
                    async with self._uow() as uow:
                        latest_version = await uow.version_repo.get_latest(doc.id)
                    
                    if latest_version:
                        await self._versioning.activate_version(doc.id, latest_version.id)
                
                # After all are chunked and activated, trigger the actual embedding process
                await self._reembed_service.process_pending()
        except RAGBootstrapError:
            raise
        except Exception as exc:
            raise RAGBootstrapError(
                f"Failed to bootstrap knowledge assets: {exc}",
                details={"error": str(exc)},
            ) from exc

        logger.info("rag_bootstrap_completed")

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
