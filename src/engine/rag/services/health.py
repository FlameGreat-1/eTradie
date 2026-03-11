from __future__ import annotations

from dataclasses import dataclass

from engine.config import RAGConfig
from engine.rag.embeddings.base import BaseEmbeddingProvider
from engine.rag.vectorstore.base import BaseVectorStore
from engine.rag.vectorstore.health import VectorStoreHealthStatus, check_vectorstore_health
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RAGHealthStatus:
    vectorstore: VectorStoreHealthStatus
    database_connected: bool
    embedding_provider_ready: bool
    overall_healthy: bool


class HealthService:
    def __init__(
        self,
        *,
        config: RAGConfig,
        vector_store: BaseVectorStore,
        db: DatabaseManager,
        embedding_provider: BaseEmbeddingProvider,
    ) -> None:
        self._config = config
        self._vector_store = vector_store
        self._db = db
        self._embedding_provider = embedding_provider

    async def check(self) -> RAGHealthStatus:
        vs_health = await check_vectorstore_health(
            store=self._vector_store, config=self._config,
        )

        db_ok = False
        try:
            db_ok = await self._db.health_check()
        except Exception:
            pass

        embed_ok = False
        try:
            test_vec = await self._embedding_provider.embed_single("health check")
            embed_ok = len(test_vec) == self._embedding_provider.dimensions
        except Exception:
            pass

        overall = vs_health.connected and db_ok and embed_ok

        status = RAGHealthStatus(
            vectorstore=vs_health,
            database_connected=db_ok,
            embedding_provider_ready=embed_ok,
            overall_healthy=overall,
        )

        if overall:
            logger.info("rag_health_ok")
        else:
            logger.warning(
                "rag_health_degraded",
                vectorstore=vs_health.connected,
                database=db_ok,
                embedding=embed_ok,
            )

        return status
