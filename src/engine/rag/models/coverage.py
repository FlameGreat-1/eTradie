from __future__ import annotations

from pydantic import Field

from engine.rag.constants import CoverageResult, DocumentType, Framework
from engine.shared.models.base import FrozenModel


class CoverageCheck(FrozenModel):
    result: CoverageResult
    rule_chunks_found: int = Field(ge=0)
    rule_chunks_required: int = Field(ge=0)
    framework_chunks_found: int = Field(ge=0)
    framework_chunks_required: int = Field(ge=0)
    missing_doc_types: frozenset[DocumentType] = Field(default_factory=frozenset)
    missing_frameworks: frozenset[Framework] = Field(default_factory=frozenset)
    gaps: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def is_sufficient(self) -> bool:
        return self.result == CoverageResult.SUFFICIENT
