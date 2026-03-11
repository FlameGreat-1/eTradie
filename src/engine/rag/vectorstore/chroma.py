from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import chromadb
from chromadb.config import Settings as ChromaSettings

from engine.config import RAGConfig
from engine.rag.vectorstore.base import BaseVectorStore, VectorSearchResult
from engine.shared.exceptions import (
    RAGVectorStoreConnectionError,
    RAGVectorStoreError,
    RAGVectorStoreUpsertError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_VECTORSTORE_OPS_DURATION, RAG_VECTORSTORE_OPS_TOTAL

logger = get_logger(__name__)


class ChromaVectorStore(BaseVectorStore):
    def __init__(self, *, config: RAGConfig) -> None:
        self._config = config
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._client: chromadb.HttpClient | None = None

    def _get_client(self) -> chromadb.HttpClient:
        if self._client is None:
            settings = ChromaSettings(
                anonymized_telemetry=False,
            )
            kwargs: dict = {
                "host": self._config.chroma_host,
                "port": self._config.chroma_port,
                "settings": settings,
            }
            if self._config.chroma_ssl:
                kwargs["ssl"] = True
            if self._config.chroma_auth_token:
                kwargs["headers"] = {
                    "Authorization": f"Bearer {self._config.chroma_auth_token}",
                }
            try:
                self._client = chromadb.HttpClient(**kwargs)
                self._client.heartbeat()
            except Exception as exc:
                self._client = None
                raise RAGVectorStoreConnectionError(
                    f"Failed to connect to ChromaDB at {self._config.chroma_host}:{self._config.chroma_port}",
                    details={"error": str(exc)},
                ) from exc
        return self._client

    def _run_sync(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(self._executor, lambda: fn(*args, **kwargs))

    async def create_collection(self, name: str, *, dimensions: int) -> None:
        import time
        start = time.monotonic()
        try:
            client = self._get_client()
            await self._run_sync(
                client.get_or_create_collection,
                name=name,
                metadata={"hnsw:space": "cosine", "dimensions": dimensions},
            )
            elapsed = time.monotonic() - start
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="create_collection", collection=name, status="success").inc()
            RAG_VECTORSTORE_OPS_DURATION.labels(operation="create_collection", collection=name).observe(elapsed)
            logger.info("chroma_collection_created", collection=name, dimensions=dimensions)
        except RAGVectorStoreConnectionError:
            raise
        except Exception as exc:
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="create_collection", collection=name, status="error").inc()
            raise RAGVectorStoreError(
                f"Failed to create collection {name}",
                details={"error": str(exc)},
            ) from exc

    async def delete_collection(self, name: str) -> None:
        try:
            client = self._get_client()
            await self._run_sync(client.delete_collection, name=name)
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="delete_collection", collection=name, status="success").inc()
        except Exception as exc:
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="delete_collection", collection=name, status="error").inc()
            raise RAGVectorStoreError(
                f"Failed to delete collection {name}",
                details={"error": str(exc)},
            ) from exc

    async def upsert(
        self,
        collection: str,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None:
        if not ids:
            return

        import time
        start = time.monotonic()
        try:
            client = self._get_client()
            col = await self._run_sync(client.get_collection, name=collection)
            await self._run_sync(
                col.upsert,
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            elapsed = time.monotonic() - start
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="upsert", collection=collection, status="success").inc()
            RAG_VECTORSTORE_OPS_DURATION.labels(operation="upsert", collection=collection).observe(elapsed)
            logger.info("chroma_upsert", collection=collection, count=len(ids), elapsed_s=round(elapsed, 3))
        except Exception as exc:
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="upsert", collection=collection, status="error").inc()
            raise RAGVectorStoreUpsertError(
                f"Failed to upsert {len(ids)} vectors into {collection}",
                details={"error": str(exc), "count": len(ids)},
            ) from exc

    async def delete(self, collection: str, *, ids: list[str]) -> None:
        if not ids:
            return
        try:
            client = self._get_client()
            col = await self._run_sync(client.get_collection, name=collection)
            await self._run_sync(col.delete, ids=ids)
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="delete", collection=collection, status="success").inc()
        except Exception as exc:
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="delete", collection=collection, status="error").inc()
            raise RAGVectorStoreError(
                f"Failed to delete {len(ids)} vectors from {collection}",
                details={"error": str(exc)},
            ) from exc

    async def query(
        self,
        collection: str,
        *,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        import time
        start = time.monotonic()
        try:
            client = self._get_client()
            col = await self._run_sync(client.get_collection, name=collection)

            query_kwargs: dict = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                query_kwargs["where"] = where

            raw = await self._run_sync(col.query, **query_kwargs)

            elapsed = time.monotonic() - start
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="query", collection=collection, status="success").inc()
            RAG_VECTORSTORE_OPS_DURATION.labels(operation="query", collection=collection).observe(elapsed)

            results: list[VectorSearchResult] = []
            if raw and raw.get("ids") and raw["ids"][0]:
                ids_list = raw["ids"][0]
                distances = raw.get("distances", [[]])[0]
                documents = raw.get("documents", [[]])[0]
                metadatas = raw.get("metadatas", [[]])[0]

                for i, chunk_id in enumerate(ids_list):
                    distance = distances[i] if i < len(distances) else 1.0
                    score = max(0.0, 1.0 - distance)
                    results.append(VectorSearchResult(
                        chunk_id=chunk_id,
                        score=score,
                        metadata=metadatas[i] if i < len(metadatas) else {},
                        content=documents[i] if i < len(documents) else "",
                    ))

            return results

        except RAGVectorStoreConnectionError:
            raise
        except Exception as exc:
            RAG_VECTORSTORE_OPS_TOTAL.labels(operation="query", collection=collection, status="error").inc()
            raise RAGVectorStoreError(
                f"Failed to query collection {collection}",
                details={"error": str(exc)},
            ) from exc

    async def count(self, collection: str) -> int:
        try:
            client = self._get_client()
            col = await self._run_sync(client.get_collection, name=collection)
            return await self._run_sync(col.count)
        except Exception as exc:
            raise RAGVectorStoreError(
                f"Failed to count collection {collection}",
                details={"error": str(exc)},
            ) from exc

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            heartbeat = await self._run_sync(client.heartbeat)
            return heartbeat is not None
        except Exception:
            return False

    async def close(self) -> None:
        self._executor.shutdown(wait=False)
        self._client = None
