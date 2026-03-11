from __future__ import annotations

from engine.config import RAGConfig
from engine.rag.knowledge.bootstrap.seed import seed_knowledge_assets
from engine.rag.knowledge.bootstrap.validator import validate_knowledge_readiness
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
    ) -> None:
        self._config = config
        self._uow = uow_factory
        self._vector_store = vector_store

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
            async with self._uow() as uow:
                await seed_knowledge_assets(
                    document_repo=uow.document_repo,
                    base_dir=self._config.knowledge_base_dir,
                )
        except RAGBootstrapError:
            raise
        except Exception as exc:
            raise RAGBootstrapError(
                f"Failed to seed knowledge assets: {exc}",
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
                RAG_ACTIVE_DOCUMENTS.set(len(docs))
                
                chunk_count = 0
                for doc in docs:
                    chunks = await uow.chunk_repo.get_by_document(doc.id)
                    chunk_count += len(chunks)
                RAG_ACTIVE_CHUNKS.set(chunk_count)
            return ready
