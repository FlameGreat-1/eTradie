from __future__ import annotations

from dataclasses import replace

from engine.rag.ingest.loaders.base import LoadedDocument
from engine.rag.ingest.normalizers.base import BaseNormalizer
from engine.rag.ingest.normalizers.taxonomy import (
    resolve_direction,
    resolve_framework,
    resolve_outcome,
)
from engine.shared.exceptions import RAGNormalizationError


class ScenariosNormalizer(BaseNormalizer):
    def normalize(self, doc: LoadedDocument) -> LoadedDocument:
        content = self._clean_whitespace(doc.content)
        content = self._normalize_bullets(content)

        metadata = dict(doc.raw_metadata)
        metadata = self._normalize_framework(metadata)
        metadata = self._normalize_direction(metadata)
        metadata = self._normalize_outcome(metadata)
        metadata = self._normalize_setup_family(metadata)

        return replace(doc, content=content, raw_metadata=metadata)

    def _normalize_framework(self, meta: dict[str, str]) -> dict[str, str]:
        raw = meta.get("framework", "").strip().lower()
        if not raw:
            raise RAGNormalizationError(
                "Scenario missing framework tag",
                details={"metadata": meta},
            )
        normalized = resolve_framework(raw) or raw
        meta["framework"] = normalized
        return meta

    def _normalize_direction(self, meta: dict[str, str]) -> dict[str, str]:
        raw = meta.get("direction", "").strip().lower()
        if not raw:
            raise RAGNormalizationError(
                "Scenario missing direction tag",
                details={"metadata": meta},
            )
        normalized = resolve_direction(raw) or raw
        meta["direction"] = normalized
        return meta

    def _normalize_outcome(self, meta: dict[str, str]) -> dict[str, str]:
        raw = meta.get("outcome", "").strip().lower()
        if not raw:
            raise RAGNormalizationError(
                "Scenario missing outcome tag",
                details={"metadata": meta},
            )
        normalized = resolve_outcome(raw) or raw
        meta["outcome"] = normalized
        return meta

    def _normalize_setup_family(self, meta: dict[str, str]) -> dict[str, str]:
        raw = meta.get("setup_family", "").strip().lower()
        if raw:
            normalized = raw.replace(" ", "_").replace("-", "_")
            meta["setup_family"] = normalized
        return meta
