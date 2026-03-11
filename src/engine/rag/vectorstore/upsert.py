from __future__ import annotations

from uuid import UUID

from engine.rag.vectorstore.base import BaseVectorStore
from engine.shared.logging import get_logger

logger = get_logger(__name__)


async def upsert_chunk_vectors(
    *,
    store: BaseVectorStore,
    collection: str,
    chunk_ids: list[UUID],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, str]],
    batch_size: int = 100,
) -> int:
    if not chunk_ids:
        return 0

    total = 0
    str_ids = [str(cid) for cid in chunk_ids]

    for start in range(0, len(str_ids), batch_size):
        end = start + batch_size
        await store.upsert(
            collection,
            ids=str_ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
        batch_count = min(batch_size, len(str_ids) - start)
        total += batch_count
        logger.info(
            "vectorstore_batch_upserted",
            collection=collection,
            batch_count=batch_count,
            total_so_far=total,
        )

    return total


async def delete_chunk_vectors(
    *,
    store: BaseVectorStore,
    collection: str,
    chunk_ids: list[UUID],
    batch_size: int = 100,
) -> int:
    if not chunk_ids:
        return 0

    total = 0
    str_ids = [str(cid) for cid in chunk_ids]

    for start in range(0, len(str_ids), batch_size):
        end = start + batch_size
        await store.delete(collection, ids=str_ids[start:end])
        batch_count = min(batch_size, len(str_ids) - start)
        total += batch_count

    logger.info(
        "vectorstore_vectors_deleted",
        collection=collection,
        total=total,
    )
    return total
