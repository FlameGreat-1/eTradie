from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.rag.constants import DocumentType, MANDATORY_KNOWLEDGE_GROUPS, SourceFormat


@dataclass(frozen=True, slots=True)
class KnowledgeAsset:
    doc_type: DocumentType
    title: str
    filename: str
    source_format: SourceFormat


KNOWLEDGE_REGISTRY: tuple[KnowledgeAsset, ...] = (
    KnowledgeAsset(DocumentType.MASTER_RULEBOOK, "Master Rulebook", "master_rulebook.md", SourceFormat.MARKDOWN),
    KnowledgeAsset(DocumentType.SMC_FRAMEWORK, "SMC Framework", "smc_framework.md", SourceFormat.MARKDOWN),
    KnowledgeAsset(DocumentType.SND_RULEBOOK, "Supply & Demand Rulebook", "snd_rulebook.md", SourceFormat.MARKDOWN),
    KnowledgeAsset(DocumentType.WYCKOFF_GUIDE, "Wyckoff Phase Guide", "wyckoff_guide.md", SourceFormat.MARKDOWN),
    KnowledgeAsset(DocumentType.DXY_FRAMEWORK, "DXY Analysis Framework", "dxy_framework.md", SourceFormat.MARKDOWN),
    KnowledgeAsset(DocumentType.COT_INTERPRETATION_GUIDE, "COT Interpretation Guide", "cot_guide.md", SourceFormat.MARKDOWN),
    KnowledgeAsset(DocumentType.TRADING_STYLE_RULES, "Trading Style Rules", "trading_style_rules.md", SourceFormat.MARKDOWN),
    KnowledgeAsset(DocumentType.MACRO_TO_PRICE_GUIDE, "Macro-to-Price Relationship Guide", "macro_to_price_guide.md", SourceFormat.MARKDOWN),
)


def resolve_asset_path(base_dir: str, asset: KnowledgeAsset) -> Path:
    return Path(base_dir) / asset.filename


def get_mandatory_assets() -> frozenset[DocumentType]:
    return MANDATORY_KNOWLEDGE_GROUPS
