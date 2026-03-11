from __future__ import annotations

import asyncio
import random
import time

from engine.config import RAGConfig
from engine.rag.embeddings.base import BaseEmbeddingProvider
from engine.shared.exceptions import RAGEmbeddingProviderError
from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_EMBEDDING_DURATION, RAG_EMBEDDING_TOTAL

logger = get_logger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, *, config: RAGConfig, http_client: HttpClient) -> None:
        self._config = config
        self._http = http_client
        self._api_key = config.openai_api_key
        self._base_url = config.openai_embedding_base_url.rstrip("/")
        self._model = config.embedding_model
        self._dims = config.embedding_dimensions
        self._max_retries = config.embedding_max_retries
        self._timeout = config.embedding_timeout_seconds

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dims

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        url = f"{self._base_url}/embeddings"
        payload = {
            "input": texts,
            "model": self._model,
            "dimensions": self._dims,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):

            start = time.monotonic()
            try:
                response = await self._http.post(
                    url,
                    json_body=payload,
                    headers=headers,
                    timeout_override=self._timeout,
                    provider_name="openai_embedding",
                    category="embedding",
                )
                elapsed = time.monotonic() - start
                RAG_EMBEDDING_DURATION.labels(model=self._model).observe(elapsed)
                RAG_EMBEDDING_TOTAL.labels(model=self._model, status="success").inc()

                data = response.get("data", [])
                sorted_data = sorted(data, key=lambda x: x["index"])
                vectors = [item["embedding"] for item in sorted_data]

                if len(vectors) != len(texts):
                    raise RAGEmbeddingProviderError(
                        f"Expected {len(texts)} embeddings, got {len(vectors)}",
                        details={"expected": len(texts), "got": len(vectors)},
                    )

                return vectors

            except RAGEmbeddingProviderError:
                raise
            except Exception as exc:
                last_exc = exc
                RAG_EMBEDDING_TOTAL.labels(model=self._model, status="error").inc()
                logger.warning(
                    "openai_embedding_retry",
                    attempt=attempt,
                    max_retries=self._max_retries,
                    error=str(exc),
                )
                if attempt < self._max_retries:
                    backoff = min(2 ** attempt + random.uniform(0, 1), 30.0)
                    await asyncio.sleep(backoff)

        raise RAGEmbeddingProviderError(
            f"OpenAI embedding failed after {self._max_retries} attempts",
            details={"last_error": str(last_exc)},
        )

    async def close(self) -> None:
        pass
