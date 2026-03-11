from __future__ import annotations

from engine.config import RAGConfig
from engine.rag.constants import (
    CoverageResult,
    DocumentType,
    Framework,
)
from engine.rag.models.coverage import CoverageCheck
from engine.rag.models.retrieval import RetrievedChunk
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_COVERAGE_CHECKS_TOTAL

logger = get_logger(__name__)

_RULE_DOC_TYPES: frozenset[str] = frozenset({
    DocumentType.MASTER_RULEBOOK,
    DocumentType.TRADING_STYLE_RULES,
})

_FRAMEWORK_DOC_TYPES: dict[str, str] = {
    DocumentType.SMC_FRAMEWORK: Framework.SMC,
    DocumentType.SND_RULEBOOK: Framework.SND,
    DocumentType.WYCKOFF_GUIDE: Framework.WYCKOFF,
    DocumentType.DXY_FRAMEWORK: Framework.DXY,
    DocumentType.COT_INTERPRETATION_GUIDE: Framework.COT,
    DocumentType.MACRO_TO_PRICE_GUIDE: Framework.MACRO,
}


def check_coverage(
    chunks: list[RetrievedChunk],
    *,
    config: RAGConfig,
    required_framework: str | None = None,
) -> CoverageCheck:
    rule_count = sum(1 for c in chunks if c.doc_type in _RULE_DOC_TYPES)
    framework_count = sum(
        1 for c in chunks if c.doc_type in _FRAMEWORK_DOC_TYPES
    )

    retrieved_doc_types = frozenset(c.doc_type for c in chunks)
    missing_doc_types: set[str] = set()
    missing_frameworks: set[str] = set()
    gaps: list[str] = []

    if rule_count < config.coverage_min_rule_chunks:
        missing_doc_types.update(
            dt for dt in _RULE_DOC_TYPES if dt not in retrieved_doc_types
        )
        gaps.append(
            f"Rule chunks: {rule_count}/{config.coverage_min_rule_chunks} required"
        )

    if framework_count < config.coverage_min_framework_chunks:
        missing_doc_types.update(
            dt for dt in _FRAMEWORK_DOC_TYPES
            if dt not in retrieved_doc_types
        )
        gaps.append(
            f"Framework chunks: {framework_count}/{config.coverage_min_framework_chunks} required"
        )

    if required_framework:
        framework_specific = [
            c for c in chunks
            if _FRAMEWORK_DOC_TYPES.get(c.doc_type) == required_framework
        ]
        if not framework_specific:
            missing_frameworks.add(required_framework)
            gaps.append(
                f"No chunks from framework '{required_framework}'"
            )

    rule_ok = rule_count >= config.coverage_min_rule_chunks
    framework_ok = framework_count >= config.coverage_min_framework_chunks

    if rule_ok and framework_ok and not missing_frameworks:
        result = CoverageResult.SUFFICIENT
    elif rule_ok or framework_ok:
        result = CoverageResult.PARTIAL
    else:
        result = CoverageResult.INSUFFICIENT

    coverage = CoverageCheck(
        result=result,
        rule_chunks_found=rule_count,
        rule_chunks_required=config.coverage_min_rule_chunks,
        framework_chunks_found=framework_count,
        framework_chunks_required=config.coverage_min_framework_chunks,
        missing_doc_types=frozenset(missing_doc_types),
        missing_frameworks=frozenset(missing_frameworks),
        gaps=tuple(gaps),
    )

    RAG_COVERAGE_CHECKS_TOTAL.labels(result=coverage.result).inc()

    logger.info(
        "coverage_check_completed",
        result=coverage.result,
        rule_found=rule_count,
        framework_found=framework_count,
        gaps=len(gaps),
    )

    return coverage
