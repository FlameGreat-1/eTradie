from __future__ import annotations

from engine.rag.ingest.chunkers.base import BaseChunker, RawChunk
from engine.rag.ingest.loaders.base import LoadedDocument


class RulebookChunker(BaseChunker):
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
            parent_idx = idx

            if section.subsections:
                section_header = f"## {section.heading}"
                if section.content.strip():
                    section_text = f"{section_header}\n\n{section.content}"
                else:
                    section_text = section_header

                parts = self._split_by_token_limit(section_text, max_tokens=self._chunk_size)
                for part in parts:
                    chunks.append(RawChunk(
                        content=part,
                        chunk_index=idx,
                        section=section.heading,
                        hierarchy_level=0,
                    ))
                    idx += 1

                for sub in section.subsections:
                    sub_text = f"### {sub.heading}\n\n{sub.content}"
                    sub_parts = self._split_by_token_limit(sub_text, max_tokens=self._chunk_size)
                    for part in sub_parts:
                        chunks.append(RawChunk(
                            content=part,
                            chunk_index=idx,
                            section=section.heading,
                            subsection=sub.heading,
                            hierarchy_level=1,
                            parent_chunk_index=parent_idx,
                        ))
                        idx += 1
            else:
                section_text = f"## {section.heading}\n\n{section.content}"
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
