from __future__ import annotations

from dataclasses import replace

from engine.rag.constants import Direction, Framework, ScenarioOutcome, SetupFamily
from engine.rag.ingest.loaders.base import LoadedDocument
from engine.rag.ingest.normalizers.base import BaseNormalizer
from engine.shared.exceptions import RAGNormalizationError

_FRAMEWORK_ALIASES: dict[str, str] = {
    "smart money": Framework.SMC,
    "smart money concepts": Framework.SMC,
    "supply and demand": Framework.SND,
    "supply & demand": Framework.SND,
    "s&d": Framework.SND,
    "snd": Framework.SND,
    "smc": Framework.SMC,
    "wyckoff": Framework.WYCKOFF,
}

_DIRECTION_ALIASES: dict[str, str] = {
    "bullish": Direction.LONG,
    "bull": Direction.LONG,
    "buy": Direction.LONG,
    "long": Direction.LONG,
    "bearish": Direction.SHORT,
    "bear": Direction.SHORT,
    "sell": Direction.SHORT,
    "short": Direction.SHORT,
}

_OUTCOME_ALIASES: dict[str, str] = {
    "win": ScenarioOutcome.VALID_WIN,
    "valid_win": ScenarioOutcome.VALID_WIN,
    "loss": ScenarioOutcome.VALID_LOSS,
    "valid_loss": ScenarioOutcome.VALID_LOSS,
    "failed": ScenarioOutcome.FAILED_SETUP,
    "failed_setup": ScenarioOutcome.FAILED_SETUP,
    "edge_case": ScenarioOutcome.EDGE_CASE,
    "edge": ScenarioOutcome.EDGE_CASE,
}


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
        normalized = _FRAMEWORK_ALIASES.get(raw, raw)
        meta["framework"] = normalized
        return meta

    def _normalize_direction(self, meta: dict[str, str]) -> dict[str, str]:
        raw = meta.get("direction", "").strip().lower()
        if not raw:
            raise RAGNormalizationError(
                "Scenario missing direction tag",
                details={"metadata": meta},
            )
        normalized = _DIRECTION_ALIASES.get(raw, raw)
        meta["direction"] = normalized
        return meta

    def _normalize_outcome(self, meta: dict[str, str]) -> dict[str, str]:
        raw = meta.get("outcome", "").strip().lower()
        if not raw:
            raise RAGNormalizationError(
                "Scenario missing outcome tag",
                details={"metadata": meta},
            )
        normalized = _OUTCOME_ALIASES.get(raw, raw)
        meta["outcome"] = normalized
        return meta

    def _normalize_setup_family(self, meta: dict[str, str]) -> dict[str, str]:
        raw = meta.get("setup_family", "").strip().lower()
        if raw:
            normalized = raw.replace(" ", "_").replace("-", "_")
            meta["setup_family"] = normalized
        return meta
