from __future__ import annotations

from engine.config import RAGConfig
from engine.rag.knowledge.bootstrap.seed import seed_knowledge_assets
from engine.rag.knowledge.bootstrap.validator import validate_knowledge_readiness
from engine.rag.storage.repositories.document import DocumentRepository
from engine.rag.vectorstore.base import BaseVectorStore
from engine.rag.vectorstore.collections import bootstrap_collections
from engine.shared.exceptions import RAGBootstrapError
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class BootstrapService:
    def __init__(
        self,
        *,
        config: RAGConfig,
        document_repo: DocumentRepository,
        vector_store: BaseVectorStore,
    ) -> None:
        self._config = config
        self._document_repo = document_repo
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
            await seed_knowledge_assets(
                document_repo=self._document_repo,
                base_dir=self._config.knowledge_base_dir,
            )
        except Exception as exc:
            raise RAGBootstrapError(
                f"Failed to seed knowledge assets: {exc}",
                details={"error": str(exc)},
            ) from exc

        logger.info("rag_bootstrap_completed")

    async def check_readiness(self) -> bool:
        return await validate_knowledge_readiness(
            document_repo=self._document_repo,
        )
