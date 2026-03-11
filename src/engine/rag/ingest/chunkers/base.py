from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from engine.rag.ingest.loaders.base import LoadedDocument


@dataclass(frozen=True, slots=True)
class RawChunk:
    content: str
    chunk_index: int
    section: str | None = None
    subsection: str | None = None
    hierarchy_level: int = 0
    parent_chunk_index: int | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    @property
    def token_count_estimate(self) -> int:
        return max(1, len(self.content.split()))


class BaseChunker(ABC):
    def __init__(self, *, chunk_size: int, chunk_overlap: int, min_size: int, max_size: int) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._min_size = min_size
        self._max_size = max_size

    @abstractmethod
    def chunk(self, doc: LoadedDocument) -> tuple[RawChunk, ...]:
        ...

    def _split_by_token_limit(self, text: str, *, max_tokens: int) -> list[str]:
        words = text.split()
        if len(words) <= max_tokens:
            return [text]

        parts: list[str] = []
        start = 0
        while start < len(words):
            end = min(start + max_tokens, len(words))
            parts.append(" ".join(words[start:end]))
            start = end - self._chunk_overlap if end < len(words) else end
        return parts

    def _merge_small_chunks(self, chunks: list[RawChunk]) -> list[RawChunk]:
        if not chunks:
            return []

        merged: list[RawChunk] = []
        buffer: RawChunk | None = None

        for chunk in chunks:
            if chunk.token_count_estimate < self._min_size:
                if buffer is None:
                    buffer = chunk
                else:
                    combined_content = buffer.content + "\n\n" + chunk.content
                    buffer = RawChunk(
                        content=combined_content,
                        chunk_index=buffer.chunk_index,
                        section=buffer.section,
                        subsection=buffer.subsection,
                        hierarchy_level=buffer.hierarchy_level,
                        parent_chunk_index=buffer.parent_chunk_index,
                        metadata=buffer.metadata,
                    )
            else:
                if buffer is not None:
                    combined_content = buffer.content + "\n\n" + chunk.content
                    merged.append(RawChunk(
                        content=combined_content,
                        chunk_index=buffer.chunk_index,
                        section=buffer.section,
                        subsection=buffer.subsection,
                        hierarchy_level=buffer.hierarchy_level,
                        parent_chunk_index=buffer.parent_chunk_index,
                        metadata=buffer.metadata,
                    ))
                    buffer = None
                else:
                    merged.append(chunk)

        if buffer is not None:
            if merged:
                last = merged[-1]
                combined_content = last.content + "\n\n" + buffer.content
                merged[-1] = RawChunk(
                    content=combined_content,
                    chunk_index=last.chunk_index,
                    section=last.section,
                    subsection=last.subsection,
                    hierarchy_level=last.hierarchy_level,
                    parent_chunk_index=last.parent_chunk_index,
                    metadata=last.metadata,
                )
            else:
                merged.append(buffer)

        return merged

    def _reindex(self, chunks: list[RawChunk]) -> tuple[RawChunk, ...]:
        return tuple(
            RawChunk(
                content=c.content,
                chunk_index=i,
                section=c.section,
                subsection=c.subsection,
                hierarchy_level=c.hierarchy_level,
                parent_chunk_index=c.parent_chunk_index,
                metadata=c.metadata,
            )
            for i, c in enumerate(chunks)
        )
