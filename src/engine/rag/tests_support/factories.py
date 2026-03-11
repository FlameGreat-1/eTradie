from __future__ import annotations

import uuid
from datetime import UTC, datetime

from engine.rag.constants import (
    ConflictResult,
    CoverageResult,
    Direction,
    DocumentStatus,
    DocumentType,
    EmbeddingStatus,
    Framework,
    RetrievalStrategy,
    ScenarioOutcome,
    SetupFamily,
    SourceFormat,
)
from engine.rag.models.chunk import Chunk
from engine.rag.models.citation import Citation
from engine.rag.models.context_bundle import ContextBundle
from engine.rag.models.coverage import CoverageCheck
from engine.rag.models.document import Document
from engine.rag.models.document_version import DocumentVersion
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.models.scenario import Scenario


def make_document(
    *,
    doc_type: str = DocumentType.MASTER_RULEBOOK,
    title: str = "Test Rulebook",
    source_path: str = "docs/test_rulebook.md",
    status: str = DocumentStatus.ACTIVE,
    checksum: str = "a" * 64,
) -> Document:
    return Document(
        doc_type=doc_type,
        title=title,
        source_path=source_path,
        source_format=SourceFormat.MARKDOWN,
        status=status,
        checksum=checksum,
    )


def make_document_version(
    *,
    document_id: uuid.UUID | None = None,
    version_number: int = 1,
    status: str = DocumentStatus.ACTIVE,
    checksum: str = "b" * 64,
) -> DocumentVersion:
    return DocumentVersion(
        document_id=document_id or uuid.uuid4(),
        version_number=version_number,
        status=status,
        checksum=checksum,
    )


def make_chunk(
    *,
    document_id: uuid.UUID | None = None,
    document_version_id: uuid.UUID | None = None,
    doc_type: str = DocumentType.MASTER_RULEBOOK,
    chunk_index: int = 0,
    content: str = "Test chunk content for retrieval.",
    content_hash: str = "c" * 64,
    token_count: int = 10,
    embedding_status: str = EmbeddingStatus.EMBEDDED,
    section: str | None = "Test Section",
) -> Chunk:
    return Chunk(
        document_id=document_id or uuid.uuid4(),
        document_version_id=document_version_id or uuid.uuid4(),
        doc_type=doc_type,
        chunk_index=chunk_index,
        content=content,
        content_hash=content_hash,
        token_count=token_count,
        embedding_status=embedding_status,
        section=section,
    )


def make_retrieved_chunk(
    *,
    score: float = 0.85,
    rank: int = 0,
    doc_type: str = DocumentType.MASTER_RULEBOOK,
    content: str = "Retrieved rule content.",
    section: str | None = "Rules",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        doc_type=doc_type,
        content=content,
        score=score,
        rank=rank,
        section=section,
    )


def make_scenario(
    *,
    framework: str = Framework.SMC,
    setup_family: str = SetupFamily.ORDER_BLOCK,
    direction: str = Direction.LONG,
    timeframe: str = "H4",
    outcome: str = ScenarioOutcome.VALID_WIN,
    title: str = "Test Scenario",
    explanation_text: str = "Bullish OB setup with displacement.",
) -> Scenario:
    return Scenario(
        document_id=uuid.uuid4(),
        framework=framework,
        setup_family=setup_family,
        direction=direction,
        timeframe=timeframe,
        outcome=outcome,
        title=title,
        explanation_text=explanation_text,
    )


def make_citation(
    *,
    doc_type: str = DocumentType.SMC_FRAMEWORK,
    section: str = "Section 3.2",
    relevance_score: float = 0.9,
) -> Citation:
    return Citation(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        doc_type=doc_type,
        section=section,
        relevance_score=relevance_score,
    )


def make_context_bundle(
    *,
    strategy: str = RetrievalStrategy.HYBRID,
    chunk_count: int = 3,
    scenario_count: int = 1,
) -> ContextBundle:
    chunks = tuple(make_retrieved_chunk(rank=i) for i in range(chunk_count))
    citations = tuple(make_citation() for _ in range(chunk_count))
    scenarios = tuple(make_scenario() for _ in range(scenario_count))

    return ContextBundle(
        strategy_used=strategy,
        retrieved_chunks=chunks,
        citations=citations,
        matched_scenarios=scenarios,
        coverage_result=CoverageResult.SUFFICIENT,
        conflict_result=ConflictResult.NONE_DETECTED,
        total_chunks_considered=chunk_count * 3,
        total_chunks_returned=chunk_count,
    )


def make_coverage_check(
    *,
    result: str = CoverageResult.SUFFICIENT,
    rule_chunks_found: int = 3,
    rule_chunks_required: int = 2,
    framework_chunks_found: int = 2,
    framework_chunks_required: int = 1,
) -> CoverageCheck:
    return CoverageCheck(
        result=result,
        rule_chunks_found=rule_chunks_found,
        rule_chunks_required=rule_chunks_required,
        framework_chunks_found=framework_chunks_found,
        framework_chunks_required=framework_chunks_required,
    )
