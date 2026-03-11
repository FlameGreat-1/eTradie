from __future__ import annotations

from engine.rag.knowledge.manifest import KNOWLEDGE_REGISTRY, resolve_asset_path
from engine.rag.storage.repositories.document import DocumentRepository
from engine.rag.storage.schemas.document import DocumentRow
from engine.shared.logging import get_logger

logger = get_logger(__name__)


async def seed_knowledge_assets(
    *,
    document_repo: DocumentRepository,
    base_dir: str,
) -> list[DocumentRow]:
    seeded: list[DocumentRow] = []

    for asset in KNOWLEDGE_REGISTRY:
        existing = await document_repo.get_by_doc_type(asset.doc_type)
        if existing:
            logger.info("seed_skipped_exists", doc_type=asset.doc_type)
            continue

        path = resolve_asset_path(base_dir, asset)

        row = DocumentRow(
            doc_type=asset.doc_type,
            title=asset.title,
            source_path=str(path),
            source_format=asset.source_format,
            status="draft",
            checksum="",
            framework_tags=[],
            metadata={},
        )
        created = await document_repo.add(row)
        seeded.append(created)

        logger.info(
            "seed_created",
            doc_type=asset.doc_type,
            title=asset.title,
            source_path=str(path),
        )

    return seeded
