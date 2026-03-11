from __future__ import annotations

import re
from dataclasses import replace

from engine.rag.ingest.loaders.base import LoadedDocument, LoadedSection
from engine.rag.ingest.normalizers.base import BaseNormalizer

_CURRENCY_ALIASES: dict[str, str] = {
    "dollar": "USD",
    "us dollar": "USD",
    "euro": "EUR",
    "pound": "GBP",
    "sterling": "GBP",
    "yen": "JPY",
    "japanese yen": "JPY",
    "swiss franc": "CHF",
    "aussie": "AUD",
    "australian dollar": "AUD",
    "kiwi": "NZD",
    "new zealand dollar": "NZD",
    "loonie": "CAD",
    "canadian dollar": "CAD",
    "gold": "XAU",
    "silver": "XAG",
}

_EVENT_ALIASES: dict[str, str] = {
    "nfp": "Non-Farm Payrolls",
    "cpi": "Consumer Price Index",
    "ppi": "Producer Price Index",
    "gdp": "Gross Domestic Product",
    "fomc": "FOMC Decision",
    "ecb rate": "ECB Rate Decision",
    "boe rate": "BOE Rate Decision",
    "boj rate": "BOJ Rate Decision",
}

_ALIAS_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _CURRENCY_ALIASES) + r")\b",
    re.IGNORECASE,
)


class MacroNormalizer(BaseNormalizer):
    def normalize(self, doc: LoadedDocument) -> LoadedDocument:
        content = self._normalize_headings(doc.content)
        content = self._normalize_bullets(content)
        content = self._clean_whitespace(content)
        content = self._standardize_currency_refs(content)

        sections = tuple(
            self._normalize_section(s) for s in doc.sections
        )

        return replace(doc, content=content, sections=sections)

    def _normalize_section(self, section: LoadedSection) -> LoadedSection:
        content = self._clean_whitespace(
            self._standardize_currency_refs(
                self._normalize_bullets(section.content)
            )
        )
        subsections = tuple(
            LoadedSection(
                heading=sub.heading,
                level=sub.level,
                content=self._clean_whitespace(
                    self._standardize_currency_refs(
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

    def _standardize_currency_refs(self, text: str) -> str:
        def _replace(m: re.Match) -> str:
            key = m.group(1).lower()
            canonical = _CURRENCY_ALIASES.get(key)
            if canonical:
                return f"{m.group(1)} ({canonical})"
            return m.group(0)
        return _ALIAS_PATTERN.sub(_replace, text)
