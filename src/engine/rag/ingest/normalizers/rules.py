from __future__ import annotations

import re
from dataclasses import replace

from engine.rag.ingest.loaders.base import LoadedDocument, LoadedSection
from engine.rag.ingest.normalizers.base import BaseNormalizer

_NUMBERED_RULE_RE = re.compile(r"^(\d+)\.\s+")
_RULE_ID_RE = re.compile(r"\b(Rule\s+[A-Z]+-\d+)\b", re.IGNORECASE)


class RulesNormalizer(BaseNormalizer):
    def normalize(self, doc: LoadedDocument) -> LoadedDocument:
        content = self._normalize_headings(doc.content)
        content = self._normalize_bullets(content)
        content = self._clean_whitespace(content)
        content = self._standardize_rule_references(content)

        sections = tuple(
            self._normalize_section(s) for s in doc.sections
        )

        return replace(doc, content=content, sections=sections)

    def _normalize_section(self, section: LoadedSection) -> LoadedSection:
        content = self._normalize_bullets(section.content)
        content = self._clean_whitespace(content)
        content = self._standardize_rule_references(content)

        subsections = tuple(
            LoadedSection(
                heading=sub.heading,
                level=sub.level,
                content=self._clean_whitespace(
                    self._standardize_rule_references(
                        self._normalize_bullets(sub.content)
                    )
                ),
                subsections=sub.subsections,
            )
            for sub in section.subsections
        )

        return LoadedSection(
            heading=section.heading,
            level=section.level,
            content=content,
            subsections=subsections,
        )

    def _standardize_rule_references(self, text: str) -> str:
        def _upper_rule(m: re.Match) -> str:
            parts = m.group(1).split()
            return f"{parts[0]} {parts[1].upper()}"
        return _RULE_ID_RE.sub(_upper_rule, text)
