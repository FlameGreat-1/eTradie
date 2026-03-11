from __future__ import annotations

from engine.rag.ingest.chunkers.base import BaseChunker, RawChunk
from engine.rag.ingest.loaders.base import LoadedDocument


class ScenarioChunker(BaseChunker):
    """Each scenario produces one primary retrievable chunk per RAG.md Section 4."""

    def chunk(self, doc: LoadedDocument) -> tuple[RawChunk, ...]:
        chunks: list[RawChunk] = []
        idx = 0

        primary_content = doc.content.strip()
        primary_metadata = dict(doc.raw_metadata)

        parts = self._split_by_token_limit(primary_content, max_tokens=self._chunk_size)

        chunks.append(RawChunk(
            content=parts[0],
            chunk_index=idx,
            section="scenario_primary",
            hierarchy_level=0,
            metadata=primary_metadata,
        ))
        idx += 1

        for supplemental in parts[1:]:
            chunks.append(RawChunk(
                content=supplemental,
                chunk_index=idx,
                section="scenario_supplemental",
                hierarchy_level=1,
                parent_chunk_index=0,
                metadata=primary_metadata,
            ))
            idx += 1

        return self._reindex(chunks)
