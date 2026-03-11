from __future__ import annotations

from dataclasses import dataclass

from engine.config import RAGConfig
from engine.rag.vectorstore.base import BaseVectorStore
from engine.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class VectorStoreHealthStatus:
    connected: bool
    documents_collection_count: int
    scenarios_collection_count: int
    error: str | None = None


async def check_vectorstore_health(
    *, store: BaseVectorStore, config: RAGConfig,
) -> VectorStoreHealthStatus:
    try:
        connected = await store.health_check()
        if not connected:
            return VectorStoreHealthStatus(
                connected=False,
                documents_collection_count=0,
                scenarios_collection_count=0,
                error="ChromaDB heartbeat failed",
            )

        doc_count = await store.count(config.collection_documents)
        scenario_count = await store.count(config.collection_scenarios)

        logger.info(
            "vectorstore_health_ok",
            documents=doc_count,
            scenarios=scenario_count,
        )

        return VectorStoreHealthStatus(
            connected=True,
            documents_collection_count=doc_count,
            scenarios_collection_count=scenario_count,
        )
    except Exception as exc:
        logger.error("vectorstore_health_failed", error=str(exc))
        return VectorStoreHealthStatus(
            connected=False,
            documents_collection_count=0,
            scenarios_collection_count=0,
            error=str(exc),
        )
