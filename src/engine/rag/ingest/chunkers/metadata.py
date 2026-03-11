from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from engine.rag.constants import (
    METADATA_KEY_CHUNK_HASH,
    METADATA_KEY_CHUNK_INDEX,
    METADATA_KEY_DOC_ID,
    METADATA_KEY_DOC_TYPE,
    METADATA_KEY_DOC_VERSION,
    METADATA_KEY_SECTION,
    METADATA_KEY_SOURCE_PATH,
    METADATA_KEY_SUBSECTION,
    METADATA_KEY_UPDATED_AT,
)
from engine.rag.ingest.chunkers.base import RawChunk


def attach_metadata(
    chunks: tuple[RawChunk, ...],
    *,
    doc_id: UUID,
    doc_type: str,
    doc_version: int,
    source_path: str,
) -> tuple[RawChunk, ...]:
    now_iso = datetime.now(UTC).isoformat()
    enriched: list[RawChunk] = []

    for chunk in chunks:
        meta = dict(chunk.metadata)
        meta[METADATA_KEY_DOC_ID] = str(doc_id)
        meta[METADATA_KEY_DOC_TYPE] = doc_type
        meta[METADATA_KEY_DOC_VERSION] = str(doc_version)
        meta[METADATA_KEY_CHUNK_INDEX] = str(chunk.chunk_index)
        meta[METADATA_KEY_CHUNK_HASH] = chunk.content_hash
        meta[METADATA_KEY_SOURCE_PATH] = source_path
        meta[METADATA_KEY_UPDATED_AT] = now_iso

        if chunk.section:
            meta[METADATA_KEY_SECTION] = chunk.section
        if chunk.subsection:
            meta[METADATA_KEY_SUBSECTION] = chunk.subsection

        enriched.append(RawChunk(
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            section=chunk.section,
            subsection=chunk.subsection,
            hierarchy_level=chunk.hierarchy_level,
            parent_chunk_index=chunk.parent_chunk_index,
            metadata=meta,
        ))

    return tuple(enriched)
