from __future__ import annotations

import json as json_lib
from pathlib import Path

from engine.rag.constants import SourceFormat
from engine.rag.ingest.loaders.base import BaseLoader, LoadedDocument
from engine.shared.exceptions import RAGLoaderError
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class JsonLoader(BaseLoader):
    @property
    def supported_format(self) -> SourceFormat:
        return SourceFormat.JSON

    async def load(self, path: Path) -> LoadedDocument:
        if not self.can_load(path):
            raise RAGLoaderError(
                f"Cannot load JSON file: {path}",
                details={"path": str(path)},
            )
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RAGLoaderError(
                f"Failed to read JSON file: {path}",
                details={"path": str(path), "error": str(exc)},
            ) from exc

        try:
            data = json_lib.loads(raw)
        except json_lib.JSONDecodeError as exc:
            raise RAGLoaderError(
                f"Invalid JSON in file: {path}",
                details={"path": str(path), "error": str(exc)},
            ) from exc

        if not isinstance(data, dict):
            raise RAGLoaderError(
                f"JSON root must be an object: {path}",
                details={"path": str(path), "type": type(data).__name__},
            )

        content = json_lib.dumps(data, indent=2, ensure_ascii=False)
        title = data.get("title", path.stem.replace("_", " ").title())
        raw_metadata = {
            k: str(v) for k, v in data.items()
            if isinstance(v, (str, int, float, bool))
        }

        logger.info("loaded_json", path=str(path), title=title)

        return LoadedDocument(
            content=content,
            source_path=str(path),
            source_format=SourceFormat.JSON,
            title=title,
            raw_metadata=raw_metadata,
        )
