from __future__ import annotations

from engine.config import RAGConfig
from engine.rag.vectorstore.base import BaseVectorStore
from engine.rag.vectorstore.chroma import ChromaVectorStore
from engine.shared.exceptions import ConfigurationError


def create_vector_store(*, config: RAGConfig) -> BaseVectorStore:
    provider = config.vectorstore_provider
    if provider == "chroma":
        return ChromaVectorStore(config=config)
    raise ConfigurationError(
        f"Unknown vector store provider: {provider}",
        details={"provider": provider},
    )
