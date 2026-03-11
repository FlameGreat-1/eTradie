from __future__ import annotations

from engine.config import RAGConfig
from engine.rag.vectorstore.base import BaseVectorStore
from engine.shared.logging import get_logger

logger = get_logger(__name__)


async def bootstrap_collections(
    *, store: BaseVectorStore, config: RAGConfig,
) -> None:
    dimensions = config.embedding_dimensions

    await store.create_collection(
        config.collection_documents, dimensions=dimensions,
    )
    logger.info(
        "collection_bootstrapped",
        collection=config.collection_documents,
        dimensions=dimensions,
    )

    await store.create_collection(
        config.collection_scenarios, dimensions=dimensions,
    )
    logger.info(
        "collection_bootstrapped",
        collection=config.collection_scenarios,
        dimensions=dimensions,
    )
