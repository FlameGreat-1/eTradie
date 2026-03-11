from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from engine.config import RAGConfig
from engine.rag.embeddings.base import BaseEmbeddingProvider
from engine.shared.exceptions import RAGEmbeddingProviderError
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class NomicEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, *, config: RAGConfig) -> None:
        self._model_name = config.embedding_model
        self._dims = config.embedding_dimensions
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._model = None

    @property
    def provider_name(self) -> str:
        return "nomic"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dims

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(
                    self._model_name, trust_remote_code=True,
                )
            except ImportError as exc:
                raise RAGEmbeddingProviderError(
                    "sentence-transformers required for nomic provider",
                ) from exc
        return self._model

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [e.tolist() for e in embeddings]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self._executor, self._embed_sync, texts)
        except RAGEmbeddingProviderError:
            raise
        except Exception as exc:
            raise RAGEmbeddingProviderError(
                f"Nomic embedding failed: {exc}",
                details={"model": self._model_name},
            ) from exc

    async def close(self) -> None:
        self._executor.shutdown(wait=False)
