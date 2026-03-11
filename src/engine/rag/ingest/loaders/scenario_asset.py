from __future__ import annotations

import json as json_lib
from pathlib import Path

from engine.rag.constants import SourceFormat, SUPPORTED_IMAGE_FORMATS
from engine.rag.ingest.loaders.base import BaseLoader, LoadedDocument
from engine.shared.exceptions import RAGLoaderError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

_REQUIRED_METADATA_KEYS = frozenset({
    "framework", "setup_family", "direction", "timeframe", "outcome",
})


class ScenarioAssetLoader(BaseLoader):
    @property
    def supported_format(self) -> SourceFormat:
        return SourceFormat.SCENARIO_BUNDLE

    def can_load(self, path: Path) -> bool:
        return path.exists() and path.is_dir()

    async def load(self, path: Path) -> LoadedDocument:
        if not self.can_load(path):
            raise RAGLoaderError(
                f"Scenario bundle directory not found: {path}",
                details={"path": str(path)},
            )

        explanation_path = path / "explanation.md"
        metadata_path = path / "metadata.json"

        if not explanation_path.is_file():
            raise RAGLoaderError(
                f"Missing explanation.md in scenario bundle: {path}",
                details={"path": str(path)},
            )
        if not metadata_path.is_file():
            raise RAGLoaderError(
                f"Missing metadata.json in scenario bundle: {path}",
                details={"path": str(path)},
            )

        try:
            explanation = explanation_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RAGLoaderError(
                f"Failed to read explanation.md: {explanation_path}",
                details={"path": str(explanation_path), "error": str(exc)},
            ) from exc

        if not explanation.strip():
            raise RAGLoaderError(
                f"explanation.md is empty: {explanation_path}",
                details={"path": str(explanation_path)},
            )

        try:
            raw_meta = metadata_path.read_text(encoding="utf-8")
            metadata = json_lib.loads(raw_meta)
        except (OSError, json_lib.JSONDecodeError) as exc:
            raise RAGLoaderError(
                f"Failed to parse metadata.json: {metadata_path}",
                details={"path": str(metadata_path), "error": str(exc)},
            ) from exc

        if not isinstance(metadata, dict):
            raise RAGLoaderError(
                f"metadata.json root must be an object: {metadata_path}",
                details={"path": str(metadata_path)},
            )

        missing_keys = _REQUIRED_METADATA_KEYS - set(metadata.keys())
        if missing_keys:
            raise RAGLoaderError(
                f"metadata.json missing required keys: {sorted(missing_keys)}",
                details={"path": str(metadata_path), "missing": sorted(missing_keys)},
            )

        image_refs: list[str] = []
        for child in sorted(path.iterdir()):
            if child.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                image_refs.append(str(child.relative_to(path)))

        raw_metadata = {k: str(v) for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}
        raw_metadata["image_refs"] = json_lib.dumps(image_refs)
        if "confluence_tags" in metadata and isinstance(metadata["confluence_tags"], list):
            raw_metadata["confluence_tags"] = json_lib.dumps(metadata["confluence_tags"])

        title = metadata.get("title", path.name.replace("_", " ").title())

        logger.info(
            "loaded_scenario_bundle",
            path=str(path),
            title=title,
            image_count=len(image_refs),
            framework=metadata.get("framework"),
            setup_family=metadata.get("setup_family"),
        )

        return LoadedDocument(
            content=explanation,
            source_path=str(path),
            source_format=SourceFormat.SCENARIO_BUNDLE,
            title=title,
            raw_metadata=raw_metadata,
        )
