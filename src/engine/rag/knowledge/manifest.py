from __future__ import annotations

from pathlib import Path

from engine.rag.constants import MANDATORY_KNOWLEDGE_GROUPS
from engine.rag.ingest.manifest import BOOTSTRAP_MANIFEST, ManifestEntry


KNOWLEDGE_REGISTRY: tuple[ManifestEntry, ...] = BOOTSTRAP_MANIFEST


def resolve_asset_path(base_dir: str, asset: ManifestEntry) -> Path:
    """Resolve the full filesystem path for a knowledge asset.

    Uses the asset's relative_path which includes subdirectory structure
    matching the actual knowledge/ directory layout.
    """
    return Path(base_dir) / asset.relative_path


def get_mandatory_assets() -> frozenset[str]:
    return MANDATORY_KNOWLEDGE_GROUPS
