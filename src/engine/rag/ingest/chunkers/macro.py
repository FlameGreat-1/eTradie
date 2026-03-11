from __future__ import annotations

from engine.rag.ingest.chunkers.base import BaseChunker, RawChunk
from engine.rag.ingest.loaders.base import LoadedDocument


class MacroChunker(BaseChunker):
    def chunk(self, doc: LoadedDocument) -> tuple[RawChunk, ...]:
        chunks: list[RawChunk] = []
        idx = 0

        if not doc.sections:
            parts = self._split_by_token_limit(doc.content, max_tokens=self._chunk_size)
            for part in parts:
                chunks.append(RawChunk(
                    content=part,
                    chunk_index=idx,
                    hierarchy_level=0,
                ))
                idx += 1
            merged = self._merge_small_chunks(chunks)
            return self._reindex(merged)

        for section in doc.sections:
            section_text = f"## {section.heading}\n\n{section.content}"

            for sub in section.subsections:
                section_text += f"\n\n### {sub.heading}\n\n{sub.content}"

            parts = self._split_by_token_limit(section_text, max_tokens=self._chunk_size)
            for part in parts:
                chunks.append(RawChunk(
                    content=part,
                    chunk_index=idx,
                    section=section.heading,
                    hierarchy_level=0,
                ))
                idx += 1

        merged = self._merge_small_chunks(chunks)
        return self._reindex(merged)
