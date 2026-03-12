from __future__ import annotations

import hashlib
import time
from pathlib import Path
from uuid import UUID

from engine.config import RAGConfig
from engine.rag.constants import DocumentType, SourceFormat
from engine.rag.ingest.chunkers.base import BaseChunker, RawChunk
from engine.rag.ingest.chunkers.framework import FrameworkChunker
from engine.rag.ingest.chunkers.macro import MacroChunker
from engine.rag.ingest.chunkers.metadata import attach_metadata
from engine.rag.ingest.chunkers.rulebook import RulebookChunker
from engine.rag.ingest.chunkers.scenario import ScenarioChunker
from engine.rag.ingest.loaders.base import BaseLoader, LoadedDocument
from engine.rag.ingest.loaders.docx import DocxLoader
from engine.rag.ingest.loaders.json import JsonLoader
from engine.rag.ingest.loaders.markdown import MarkdownLoader
from engine.rag.ingest.loaders.scenario_asset import ScenarioAssetLoader
from engine.rag.ingest.loaders.text import TextLoader
from engine.rag.ingest.normalizers.macro import MacroNormalizer
from engine.rag.ingest.normalizers.rules import RulesNormalizer
from engine.rag.ingest.normalizers.scenarios import ScenariosNormalizer
from engine.rag.ingest.validators.chunk import validate_chunks
from engine.rag.ingest.validators.document import validate_document
from engine.rag.ingest.validators.scenario import validate_scenario
from engine.rag.storage.uow import RAGUnitOfWork, RAGUnitOfWorkFactory
from engine.rag.storage.schemas.chunk import ChunkRow
from engine.rag.storage.schemas.document import DocumentRow
from engine.rag.storage.schemas.document_version import DocumentVersionRow
from engine.rag.storage.schemas.ingest_job import IngestJobRow
from engine.shared.exceptions import RAGIngestError
from engine.shared.logging import get_logger
from engine.shared.metrics import (
    RAG_CHUNKS_GENERATED,
    RAG_INGEST_DURATION,
    RAG_INGEST_TOTAL,
)

logger = get_logger(__name__)

_LOADER_MAP: dict[SourceFormat, type[BaseLoader]] = {
    SourceFormat.MARKDOWN: MarkdownLoader,
    SourceFormat.TEXT: TextLoader,
    SourceFormat.DOCX: DocxLoader,
    SourceFormat.JSON: JsonLoader,
    SourceFormat.SCENARIO_BUNDLE: ScenarioAssetLoader,
}

_FRAMEWORK_DOC_TYPES = frozenset({
    DocumentType.SMC_FRAMEWORK,
    DocumentType.SND_RULEBOOK,
    DocumentType.WYCKOFF_GUIDE,
    DocumentType.DXY_FRAMEWORK,
    DocumentType.COT_INTERPRETATION_GUIDE,
})

_MACRO_DOC_TYPES = frozenset({
    DocumentType.MACRO_TO_PRICE_GUIDE,
})

_RULEBOOK_DOC_TYPES = frozenset({
    DocumentType.MASTER_RULEBOOK,
    DocumentType.TRADING_STYLE_RULES,
})


class IngestPipeline:
    def __init__(
        self,
        *,
        config: RAGConfig,
        uow_factory: RAGUnitOfWorkFactory,
    ) -> None:
        self._config = config
        self._uow = uow_factory

        self._rules_normalizer = RulesNormalizer()
        self._macro_normalizer = MacroNormalizer()
        self._scenarios_normalizer = ScenariosNormalizer()

    async def ingest(
        self,
        *,
        path: Path,
        doc_type: str,
        source_format: SourceFormat,
        title: str,
    ) -> UUID:

        start = time.monotonic()

        try:
            loader = self._resolve_loader(source_format)
            loaded = await loader.load(path)

            checksum = self._compute_checksum(loaded.content)

            validate_document(loaded, doc_type=doc_type, checksum=checksum)
            if (
                doc_type == DocumentType.CHART_SCENARIO_LIBRARY
                and source_format == SourceFormat.SCENARIO_BUNDLE
            ):
                validate_scenario(loaded)

            loaded = self._normalize(loaded, doc_type)

            async with self._uow() as uow:
                doc_row = await self._ensure_document(
                    uow, loaded, doc_type=doc_type, source_format=source_format, title=title, checksum=checksum,
                )

                existing_version = await uow.version_repo.get_by_checksum(
                    doc_row.id, checksum,
                )
                if existing_version:
                    logger.info(
                        "ingest_skipped_unchanged",
                        doc_id=str(doc_row.id),
                        checksum=checksum,
                    )
                    RAG_INGEST_TOTAL.labels(doc_type=doc_type, status="skipped").inc()
                    return doc_row.id

                version_row = await self._create_version(uow, doc_row, checksum)

                job_row = await self._create_ingest_job(uow, doc_row, version_row)
                await uow.ingest_job_repo.mark_running(job_row.id)

                chunker = self._resolve_chunker(doc_type)
                raw_chunks = chunker.chunk(loaded)

                raw_chunks = attach_metadata(
                    raw_chunks,
                    doc_id=doc_row.id,
                    doc_type=doc_type,
                    doc_version=version_row.version_number,
                    source_path=str(path),
                )

                validate_chunks(
                    raw_chunks,
                    min_size=self._config.chunk_min_size,
                    max_size=self._config.chunk_max_size,
                )

                await uow.chunk_repo.delete_by_document_version(version_row.id)

                chunk_rows = await self._persist_chunks(uow, raw_chunks, doc_row, version_row)

                await uow.ingest_job_repo.mark_completed(
                    job_row.id,
                    chunks_created=len(chunk_rows),
                    embeddings_created=0,
                )

            elapsed = time.monotonic() - start
            RAG_INGEST_TOTAL.labels(doc_type=doc_type, status="success").inc()
            RAG_INGEST_DURATION.labels(doc_type=doc_type).observe(elapsed)
            RAG_CHUNKS_GENERATED.labels(doc_type=doc_type, chunker=type(chunker).__name__).inc(len(chunk_rows))

            logger.info(
                "ingest_completed",
                doc_id=str(doc_row.id),
                version=version_row.version_number,
                chunks=len(chunk_rows),
                elapsed_s=round(elapsed, 3),
            )

            return doc_row.id

        except RAGIngestError:
            RAG_INGEST_TOTAL.labels(doc_type=doc_type, status="failed").inc()
            raise
        except Exception as exc:
            RAG_INGEST_TOTAL.labels(doc_type=doc_type, status="failed").inc()
            raise RAGIngestError(
                f"Ingest failed for {path}: {exc}",
                details={"path": str(path), "doc_type": doc_type},
            ) from exc

    def _resolve_loader(self, source_format: SourceFormat) -> BaseLoader:
        loader_cls = _LOADER_MAP.get(source_format)
        if not loader_cls:
            raise RAGIngestError(
                f"No loader for format: {source_format}",
                details={"format": source_format},
            )
        return loader_cls()

    def _resolve_chunker(self, doc_type: str) -> BaseChunker:
        kwargs = {
            "chunk_size": self._config.chunk_size,
            "chunk_overlap": self._config.chunk_overlap,
            "min_size": self._config.chunk_min_size,
            "max_size": self._config.chunk_max_size,
        }
        if doc_type in _RULEBOOK_DOC_TYPES:
            return RulebookChunker(**kwargs)
        if doc_type in _FRAMEWORK_DOC_TYPES:
            return FrameworkChunker(**kwargs)
        if doc_type in _MACRO_DOC_TYPES:
            return MacroChunker(**kwargs)
        if doc_type == DocumentType.CHART_SCENARIO_LIBRARY:
            return ScenarioChunker(**kwargs)
        return RulebookChunker(**kwargs)

    def _normalize(self, doc: LoadedDocument, doc_type: str) -> LoadedDocument:
        if (
            doc_type == DocumentType.CHART_SCENARIO_LIBRARY
            and doc.source_format == SourceFormat.SCENARIO_BUNDLE
        ):
            return self._scenarios_normalizer.normalize(doc)
        if doc_type in _MACRO_DOC_TYPES:
            return self._macro_normalizer.normalize(doc)
        return self._rules_normalizer.normalize(doc)

    def _compute_checksum(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _ensure_document(
        self,
        uow: RAGUnitOfWork,
        loaded: LoadedDocument,
        *,
        doc_type: str,
        source_format: SourceFormat,
        title: str,
        checksum: str,
    ) -> DocumentRow:
        existing = await uow.document_repo.get_by_source_path(loaded.source_path)
        if existing:
            return existing

        row = DocumentRow(
            doc_type=doc_type,
            title=title,
            source_path=loaded.source_path,
            source_format=source_format,
            status="draft",
            checksum=checksum,
            framework_tags=list(loaded.raw_metadata.get("framework_tags", [])),
            metadata={},
        )
        return await uow.document_repo.add(row)

    async def _create_version(
        self, uow: RAGUnitOfWork, doc_row: DocumentRow, checksum: str,
    ) -> DocumentVersionRow:
        latest = await uow.version_repo.get_latest(doc_row.id)
        next_number = (latest.version_number + 1) if latest else 1

        row = DocumentVersionRow(
            document_id=doc_row.id,
            version_number=next_number,
            status="draft",
            checksum=checksum,
        )
        return await uow.version_repo.add(row)

    async def _create_ingest_job(
        self, uow: RAGUnitOfWork, doc_row: DocumentRow, version_row: DocumentVersionRow,
    ) -> IngestJobRow:
        row = IngestJobRow(
            document_id=doc_row.id,
            document_version_id=version_row.id,
            status="pending",
            max_retries=self._config.ingest_retry_max,
        )
        return await uow.ingest_job_repo.add(row)

    async def _persist_chunks(
        self,
        uow: RAGUnitOfWork,
        raw_chunks: tuple[RawChunk, ...],
        doc_row: DocumentRow,
        version_row: DocumentVersionRow,
    ) -> list[ChunkRow]:
        rows: list[ChunkRow] = []
        for chunk in raw_chunks:
            row = ChunkRow(
                document_id=doc_row.id,
                document_version_id=version_row.id,
                doc_type=doc_row.doc_type,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_hash=chunk.content_hash,
                token_count=chunk.token_count_estimate,
                embedding_status="pending",
                section=chunk.section,
                subsection=chunk.subsection,
                hierarchy_level=chunk.hierarchy_level,
                metadata=chunk.metadata,
            )
            created = await uow.chunk_repo.add(row)
            rows.append(created)
        return rows
