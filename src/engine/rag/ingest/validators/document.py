from __future__ import annotations

from engine.rag.constants import DocumentType, SourceFormat
from engine.rag.ingest.loaders.base import LoadedDocument
from engine.shared.exceptions import RAGValidationError

_DOC_TYPE_REQUIRED_FORMATS: dict[str, frozenset[SourceFormat]] = {
    DocumentType.MASTER_RULEBOOK: frozenset({SourceFormat.MARKDOWN}),
    DocumentType.SMC_FRAMEWORK: frozenset({SourceFormat.MARKDOWN}),
    DocumentType.SND_RULEBOOK: frozenset({SourceFormat.MARKDOWN}),
    DocumentType.WYCKOFF_GUIDE: frozenset({SourceFormat.MARKDOWN}),
    DocumentType.DXY_FRAMEWORK: frozenset({SourceFormat.MARKDOWN}),
    DocumentType.COT_INTERPRETATION_GUIDE: frozenset({SourceFormat.MARKDOWN}),
    DocumentType.TRADING_STYLE_RULES: frozenset({SourceFormat.MARKDOWN}),
    DocumentType.MACRO_TO_PRICE_GUIDE: frozenset({SourceFormat.MARKDOWN}),
    DocumentType.CHART_SCENARIO_LIBRARY: frozenset({SourceFormat.MARKDOWN, SourceFormat.SCENARIO_BUNDLE}),
}


def validate_document(
    doc: LoadedDocument,
    *,
    doc_type: str,
    checksum: str,
) -> None:
    if not doc.content.strip():
        raise RAGValidationError(
            "Document content is empty",
            details={"source_path": doc.source_path},
        )

    if not doc.title.strip():
        raise RAGValidationError(
            "Document title is empty",
            details={"source_path": doc.source_path},
        )

    if not checksum:
        raise RAGValidationError(
            "Document checksum is missing",
            details={"source_path": doc.source_path},
        )

    allowed_formats = _DOC_TYPE_REQUIRED_FORMATS.get(doc_type)
    if allowed_formats and doc.source_format not in allowed_formats:
        raise RAGValidationError(
            f"Document format {doc.source_format} not allowed for type {doc_type}",
            details={
                "source_path": doc.source_path,
                "format": doc.source_format,
                "allowed": [str(f) for f in allowed_formats],
            },
        )

    if doc_type != DocumentType.CHART_SCENARIO_LIBRARY and not doc.sections:
        raise RAGValidationError(
            "Rulebook/guide documents must have at least one section heading",
            details={"source_path": doc.source_path, "doc_type": doc_type},
        )
