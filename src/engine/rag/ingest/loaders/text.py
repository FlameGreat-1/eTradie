from __future__ import annotations

from pathlib import Path

from engine.rag.constants import SourceFormat
from engine.rag.ingest.loaders.base import BaseLoader, LoadedDocument
from engine.shared.exceptions import RAGLoaderError
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class TextLoader(BaseLoader):
    @property
    def supported_format(self) -> SourceFormat:
        return SourceFormat.TEXT

    async def load(self, path: Path) -> LoadedDocument:
        if not self.can_load(path):
            raise RAGLoaderError(
                f"Cannot load text file: {path}",
                details={"path": str(path)},
            )
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RAGLoaderError(
                f"Failed to read text file: {path}",
                details={"path": str(path), "error": str(exc)},
            ) from exc

        if not content.strip():
            raise RAGLoaderError(
                f"Text file is empty: {path}",
                details={"path": str(path)},
            )

        title = path.stem.replace("_", " ").title()

        logger.info("loaded_text", path=str(path), title=title)

        return LoadedDocument(
            content=content,
            source_path=str(path),
            source_format=SourceFormat.TEXT,
            title=title,
        )
