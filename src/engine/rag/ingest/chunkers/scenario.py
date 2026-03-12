from __future__ import annotations

import re

from engine.rag.ingest.chunkers.base import BaseChunker, RawChunk
from engine.rag.ingest.loaders.base import LoadedDocument

_SCENARIO_HEADER_RE = re.compile(
    r"^###\s*SCENARIO_ID:\s*(SCN-\d{3})\s*$",
    re.MULTILINE,
)

_CATEGORY_HEADER_RE = re.compile(
    r"^##\s*\d+\.\s*(.+)$",
    re.MULTILINE,
)


class ScenarioChunker(BaseChunker):
    """Chunks a multi-scenario markdown file into one chunk per scenario.

    The chart_scenarios.md knowledge file contains 38 scenarios (SCN-001
    through SCN-038) organized under category headings. Each scenario is
    a complete reasoning pattern that must be independently retrievable.

    Chunking strategy:
    - Split on ### SCENARIO_ID: SCN-XXX boundaries
    - Each scenario becomes one primary chunk
    - Category heading (e.g., "High Probability Confluence") is preserved
      as the section metadata for filtering
    - If a single scenario exceeds chunk_size, it is split with overlap
    """

    def chunk(self, doc: LoadedDocument) -> tuple[RawChunk, ...]:
        content = doc.content
        chunks: list[RawChunk] = []
        idx = 0

        # Find all scenario boundaries
        scenario_matches = list(_SCENARIO_HEADER_RE.finditer(content))

        if not scenario_matches:
            # Fallback: no SCENARIO_ID headers found, chunk by sections
            return self._chunk_by_sections(doc)

        # Build category map: position -> category name
        category_map = self._build_category_map(content)

        for i, match in enumerate(scenario_matches):
            scenario_id = match.group(1)
            start = match.start()

            # End is either the next scenario header or end of content
            if i + 1 < len(scenario_matches):
                end = scenario_matches[i + 1].start()
            else:
                end = len(content)

            scenario_text = content[start:end].strip()

            # Find which category this scenario belongs to
            category = self._find_category(start, category_map)

            # Build metadata from scenario content
            scenario_meta = {
                "scenario_id": scenario_id,
            }

            # Split if scenario exceeds chunk size
            parts = self._split_by_token_limit(
                scenario_text, max_tokens=self._chunk_size,
            )

            primary_idx = idx
            for part_num, part in enumerate(parts):
                chunks.append(RawChunk(
                    content=part,
                    chunk_index=idx,
                    section=category or "scenarios",
                    subsection=scenario_id,
                    hierarchy_level=0 if part_num == 0 else 1,
                    parent_chunk_index=primary_idx if part_num > 0 else None,
                    metadata=scenario_meta,
                ))
                idx += 1

        if not chunks:
            return self._chunk_by_sections(doc)

        return self._reindex(chunks)

    def _build_category_map(self, content: str) -> list[tuple[int, str]]:
        """Build a sorted list of (position, category_name) from ## headings."""
        categories: list[tuple[int, str]] = []
        for match in _CATEGORY_HEADER_RE.finditer(content):
            categories.append((match.start(), match.group(1).strip()))
        return sorted(categories, key=lambda x: x[0])

    def _find_category(
        self, position: int, category_map: list[tuple[int, str]],
    ) -> str | None:
        """Find the category heading that precedes the given position."""
        result: str | None = None
        for cat_pos, cat_name in category_map:
            if cat_pos <= position:
                result = cat_name
            else:
                break
        return result

    def _chunk_by_sections(self, doc: LoadedDocument) -> tuple[RawChunk, ...]:
        """Fallback chunking when no SCENARIO_ID headers are found."""
        chunks: list[RawChunk] = []
        idx = 0

        if doc.sections:
            for section in doc.sections:
                section_text = f"## {section.heading}\n\n{section.content}"
                for sub in section.subsections:
                    section_text += f"\n\n### {sub.heading}\n\n{sub.content}"

                parts = self._split_by_token_limit(
                    section_text, max_tokens=self._chunk_size,
                )
                for part in parts:
                    chunks.append(RawChunk(
                        content=part,
                        chunk_index=idx,
                        section=section.heading,
                        hierarchy_level=0,
                    ))
                    idx += 1
        else:
            parts = self._split_by_token_limit(
                doc.content, max_tokens=self._chunk_size,
            )
            for part in parts:
                chunks.append(RawChunk(
                    content=part,
                    chunk_index=idx,
                    hierarchy_level=0,
                ))
                idx += 1

        merged = self._merge_small_chunks(chunks)
        return self._reindex(merged)
