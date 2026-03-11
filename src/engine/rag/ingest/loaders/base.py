from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from engine.rag.constants import SourceFormat


@dataclass(frozen=True, slots=True)
class LoadedDocument:
    content: str
    source_path: str
    source_format: SourceFormat
    title: str
    sections: tuple[LoadedSection, ...] = ()
    raw_metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LoadedSection:
    heading: str
    level: int
    content: str
    subsections: tuple[LoadedSection, ...] = ()


class BaseLoader(ABC):
    @property
    @abstractmethod
    def supported_format(self) -> SourceFormat:
        ...

    @abstractmethod
    async def load(self, path: Path) -> LoadedDocument:
        ...

    def can_load(self, path: Path) -> bool:
        return path.exists() and path.is_file()
