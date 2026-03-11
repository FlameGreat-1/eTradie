from __future__ import annotations

from engine.config import RAGConfig
from engine.rag.embeddings.base import BaseEmbeddingProvider
from engine.rag.embeddings.nomic import NomicEmbeddingProvider
from engine.rag.embeddings.openai import OpenAIEmbeddingProvider
from engine.rag.embeddings.sentence_transformers import SentenceTransformersProvider
from engine.shared.exceptions import ConfigurationError
from engine.shared.http import HttpClient


def create_embedding_provider(
    *, config: RAGConfig, http_client: HttpClient,
) -> BaseEmbeddingProvider:
    provider = config.embedding_provider

    if provider == "openai":
        if not config.openai_api_key:
            raise ConfigurationError(
                "RAG_OPENAI_API_KEY required for openai embedding provider",
            )
        return OpenAIEmbeddingProvider(config=config, http_client=http_client)

    if provider == "nomic":
        return NomicEmbeddingProvider(config=config)

    if provider == "sentence_transformers":
        return SentenceTransformersProvider(config=config)

    raise ConfigurationError(
        f"Unknown embedding provider: {provider}",
        details={"provider": provider},
    )
