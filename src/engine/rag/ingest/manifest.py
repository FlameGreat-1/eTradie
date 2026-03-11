from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.rag.constants import DocumentType, SourceFormat


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    doc_type: DocumentType
    filename: str
    source_format: SourceFormat
    title: str


BOOTSTRAP_MANIFEST: tuple[ManifestEntry, ...] = (
    ManifestEntry(
        doc_type=DocumentType.MASTER_RULEBOOK,
        filename="master_rulebook.md",
        source_format=SourceFormat.MARKDOWN,
        title="Master Rulebook",
    ),
    ManifestEntry(
        doc_type=DocumentType.SMC_FRAMEWORK,
        filename="smc_framework.md",
        source_format=SourceFormat.MARKDOWN,
        title="SMC Framework",
    ),
    ManifestEntry(
        doc_type=DocumentType.SND_RULEBOOK,
        filename="snd_rulebook.md",
        source_format=SourceFormat.MARKDOWN,
        title="Supply & Demand Rulebook",
    ),
    ManifestEntry(
        doc_type=DocumentType.WYCKOFF_GUIDE,
        filename="wyckoff_guide.md",
        source_format=SourceFormat.MARKDOWN,
        title="Wyckoff Phase Guide",
    ),
    ManifestEntry(
        doc_type=DocumentType.DXY_FRAMEWORK,
        filename="dxy_framework.md",
        source_format=SourceFormat.MARKDOWN,
        title="DXY Analysis Framework",
    ),
    ManifestEntry(
        doc_type=DocumentType.COT_INTERPRETATION_GUIDE,
        filename="cot_guide.md",
        source_format=SourceFormat.MARKDOWN,
        title="COT Interpretation Guide",
    ),
    ManifestEntry(
        doc_type=DocumentType.TRADING_STYLE_RULES,
        filename="trading_style_rules.md",
        source_format=SourceFormat.MARKDOWN,
        title="Trading Style Rules",
    ),
    ManifestEntry(
        doc_type=DocumentType.MACRO_TO_PRICE_GUIDE,
        filename="macro_to_price_guide.md",
        source_format=SourceFormat.MARKDOWN,
        title="Macro-to-Price Relationship Guide",
    ),
)

SCENARIO_DIR_NAME = "chart_scenarios"


def resolve_manifest_path(base_dir: str, entry: ManifestEntry) -> Path:
    return Path(base_dir) / entry.filename


def resolve_scenario_dirs(base_dir: str) -> list[Path]:
    scenario_root = Path(base_dir) / SCENARIO_DIR_NAME
    if not scenario_root.is_dir():
        return []
    return sorted(
        d for d in scenario_root.iterdir()
        if d.is_dir() and (d / "explanation.md").is_file()
    )
