from __future__ import annotations

from engine.rag.ingest.loaders.base import LoadedDocument
from engine.shared.exceptions import RAGValidationError

_REQUIRED_SCENARIO_KEYS = frozenset({
    "framework", "setup_family", "direction", "timeframe", "outcome",
})


def validate_scenario(doc: LoadedDocument) -> None:
    if not doc.content.strip():
        raise RAGValidationError(
            "Scenario explanation text is empty",
            details={"source_path": doc.source_path},
        )

    missing = _REQUIRED_SCENARIO_KEYS - set(doc.raw_metadata.keys())
    if missing:
        raise RAGValidationError(
            f"Scenario missing required metadata: {sorted(missing)}",
            details={
                "source_path": doc.source_path,
                "missing": sorted(missing),
            },
        )

    for key in _REQUIRED_SCENARIO_KEYS:
        val = doc.raw_metadata.get(key, "")
        if not str(val).strip():
            raise RAGValidationError(
                f"Scenario metadata '{key}' is blank",
                details={"source_path": doc.source_path, "key": key},
            )
