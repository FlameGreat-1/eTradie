from __future__ import annotations

import re
from abc import ABC, abstractmethod

from engine.rag.ingest.loaders.base import LoadedDocument

_MULTI_WHITESPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINES = re.compile(r"\n{3,}")
_TRAILING_SPACES = re.compile(r" +$", re.MULTILINE)


class BaseNormalizer(ABC):
    @abstractmethod
    def normalize(self, doc: LoadedDocument) -> LoadedDocument:
        ...

    def _clean_whitespace(self, text: str) -> str:
        text = _MULTI_WHITESPACE.sub(" ", text)
        text = _TRAILING_SPACES.sub("", text)
        text = _MULTI_NEWLINES.sub("\n\n", text)
        return text.strip()

    def _normalize_bullets(self, text: str) -> str:
        lines: list[str] = []
        for line in text.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith(("- ", "* ", "+ ")):
                indent = len(line) - len(stripped)
                lines.append(" " * indent + "- " + stripped[2:])
            else:
                lines.append(line)
        return "\n".join(lines)

    def _normalize_headings(self, text: str) -> str:
        lines: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                match = re.match(r"^(#{1,6})\s*(.*?)\s*#*$", stripped)
                if match:
                    lines.append(f"{match.group(1)} {match.group(2)}")
                    continue
            lines.append(line)
        return "\n".join(lines)
