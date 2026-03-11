from __future__ import annotations

from engine.rag.knowledge.policies import enforce_mandatory_assets
from engine.rag.storage.repositories.document import DocumentRepository
from engine.shared.exceptions import RAGKnowledgeBaseError
from engine.shared.logging import get_logger

logger = get_logger(__name__)


async def validate_knowledge_readiness(
    *,
    document_repo: DocumentRepository,
) -> bool:
    active_types = await document_repo.get_active_doc_types()
    active_set = set(active_types)

    try:
        enforce_mandatory_assets(active_set)
    except RAGKnowledgeBaseError as exc:
        logger.warning(
            "knowledge_not_ready",
            error=str(exc),
        )
        return False

    logger.info("knowledge_ready", active_types=sorted(active_set))
    return True
