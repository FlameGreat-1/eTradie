from __future__ import annotations

from engine.rag.constants import METADATA_KEY_DOC_ID, METADATA_KEY_DOC_TYPE
from engine.rag.ingest.chunkers.base import RawChunk
from engine.shared.exceptions import RAGValidationError


def validate_chunks(
    chunks: tuple[RawChunk, ...],
    *,
    min_size: int,
    max_size: int,
) -> None:
    if not chunks:
        raise RAGValidationError("Chunking produced zero chunks")

    seen_hashes: set[str] = set()

    for chunk in chunks:
        if not chunk.content.strip():
            raise RAGValidationError(
                f"Chunk {chunk.chunk_index} has empty content",
                details={"chunk_index": chunk.chunk_index},
            )

        token_count = chunk.token_count_estimate
        if token_count > max_size:
            raise RAGValidationError(
                f"Chunk {chunk.chunk_index} exceeds max size: {token_count} > {max_size}",
                details={"chunk_index": chunk.chunk_index, "tokens": token_count},
            )

        if METADATA_KEY_DOC_ID not in chunk.metadata:
            raise RAGValidationError(
                f"Chunk {chunk.chunk_index} missing {METADATA_KEY_DOC_ID} metadata",
                details={"chunk_index": chunk.chunk_index},
            )

        if METADATA_KEY_DOC_TYPE not in chunk.metadata:
            raise RAGValidationError(
                f"Chunk {chunk.chunk_index} missing {METADATA_KEY_DOC_TYPE} metadata",
                details={"chunk_index": chunk.chunk_index},
            )

        content_hash = chunk.content_hash
        if content_hash in seen_hashes:
            raise RAGValidationError(
                f"Duplicate chunk content detected at index {chunk.chunk_index}",
                details={"chunk_index": chunk.chunk_index, "hash": content_hash},
            )
        seen_hashes.add(content_hash)

        if chunk.parent_chunk_index is not None:
            if chunk.parent_chunk_index >= chunk.chunk_index:
                raise RAGValidationError(
                    f"Chunk {chunk.chunk_index} has invalid parent index {chunk.parent_chunk_index}",
                    details={"chunk_index": chunk.chunk_index},
                )
