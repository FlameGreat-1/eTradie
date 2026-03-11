from __future__ import annotations

import re
from pathlib import Path

from engine.rag.constants import SourceFormat
from engine.rag.ingest.loaders.base import BaseLoader, LoadedDocument, LoadedSection
from engine.shared.exceptions import RAGLoaderError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownLoader(BaseLoader):
    @property
    def supported_format(self) -> SourceFormat:
        return SourceFormat.MARKDOWN

    async def load(self, path: Path) -> LoadedDocument:
        if not self.can_load(path):
            raise RAGLoaderError(
                f"Cannot load markdown file: {path}",
                details={"path": str(path)},
            )
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RAGLoaderError(
                f"Failed to read markdown file: {path}",
                details={"path": str(path), "error": str(exc)},
            ) from exc

        if not content.strip():
            raise RAGLoaderError(
                f"Markdown file is empty: {path}",
                details={"path": str(path)},
            )

        title = self._extract_title(content, path)
        sections = self._parse_sections(content)

        logger.info(
            "loaded_markdown",
            path=str(path),
            title=title,
            section_count=len(sections),
        )

        return LoadedDocument(
            content=content,
            source_path=str(path),
            source_format=SourceFormat.MARKDOWN,
            title=title,
            sections=sections,
        )

    def _extract_title(self, content: str, path: Path) -> str:
        for match in _HEADING_RE.finditer(content):
            if len(match.group(1)) == 1:
                return match.group(2).strip()
        return path.stem.replace("_", " ").title()

    def _parse_sections(self, content: str) -> tuple[LoadedSection, ...]:
        lines = content.split("\n")
        sections: list[LoadedSection] = []
        current_heading: str | None = None
        current_level: int = 0
        current_lines: list[str] = []
        subsection_buffer: list[tuple[str, int, list[str]]] = []

        def _flush() -> None:
            nonlocal current_heading, current_lines, subsection_buffer
            if current_heading is not None:
                subsections = tuple(
                    LoadedSection(
                        heading=sh, level=sl, content="\n".join(sc).strip(),
                    )
                    for sh, sl, sc in subsection_buffer
                )
                sections.append(LoadedSection(
                    heading=current_heading,
                    level=current_level,
                    content="\n".join(current_lines).strip(),
                    subsections=subsections,
                ))
                current_lines = []
                subsection_buffer = []

        for line in lines:
            heading_match = _HEADING_RE.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                if level <= 2:
                    _flush()
                    current_heading = heading_text
                    current_level = level
                    current_lines = []
                    subsection_buffer = []
                else:
                    if subsection_buffer:
                        pass
                    subsection_buffer.append((heading_text, level, []))
            else:
                if subsection_buffer:
                    subsection_buffer[-1][2].append(line)
                else:
                    current_lines.append(line)

        _flush()
        return tuple(sections)
