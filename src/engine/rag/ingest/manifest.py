from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.rag.constants import DocumentType, SourceFormat


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    doc_type: DocumentType
    relative_path: str
    source_format: SourceFormat
    title: str


BOOTSTRAP_MANIFEST: tuple[ManifestEntry, ...] = (
    ManifestEntry(
        doc_type=DocumentType.MASTER_RULEBOOK,
        relative_path="master_rulebook.md",
        source_format=SourceFormat.MARKDOWN,
        title="Trading System Master Rulebook",
    ),
    ManifestEntry(
        doc_type=DocumentType.SMC_FRAMEWORK,
        relative_path="frameworks/smc_framework.md",
        source_format=SourceFormat.MARKDOWN,
        title="Smart Money Concepts Framework",
    ),
    ManifestEntry(
        doc_type=DocumentType.SND_RULEBOOK,
        relative_path="frameworks/snd_framework.md",
        source_format=SourceFormat.MARKDOWN,
        title="Supply and Demand Framework",
    ),
    ManifestEntry(
        doc_type=DocumentType.WYCKOFF_GUIDE,
        relative_path="frameworks/wyckoff_guide.md",
        source_format=SourceFormat.MARKDOWN,
        title="Wyckoff Market Cycle Guide",
    ),
    ManifestEntry(
        doc_type=DocumentType.DXY_FRAMEWORK,
        relative_path="frameworks/dxy_framework.md",
        source_format=SourceFormat.MARKDOWN,
        title="DXY Market Influence Framework",
    ),
    ManifestEntry(
        doc_type=DocumentType.COT_INTERPRETATION_GUIDE,
        relative_path="frameworks/cot_interpretation.md",
        source_format=SourceFormat.MARKDOWN,
        title="Commitment of Traders Interpretation Guide",
    ),
    ManifestEntry(
        doc_type=DocumentType.TRADING_STYLE_RULES,
        relative_path="trading_rules/trading_style_rules.md",
        source_format=SourceFormat.MARKDOWN,
        title="Trading Style and Operational Rules",
    ),
    ManifestEntry(
        doc_type=DocumentType.MACRO_TO_PRICE_GUIDE,
        relative_path="frameworks/macro_to_price.md",
        source_format=SourceFormat.MARKDOWN,
        title="Macro to Price Translation Guide",
    ),
    ManifestEntry(
        doc_type=DocumentType.CHART_SCENARIO_LIBRARY,
        relative_path="scenarios/chart_scenarios.md",
        source_format=SourceFormat.MARKDOWN,
        title="Chart Scenario Library",
    ),
)

SCENARIO_DIR_NAME = "scenarios"


def resolve_manifest_path(base_dir: str, entry: ManifestEntry) -> Path:
    """Resolve the full filesystem path for a manifest entry.

    Uses the entry's relative_path which includes subdirectory structure
    matching the actual knowledge/ directory layout.
    """
    return Path(base_dir) / entry.relative_path


def resolve_scenario_dirs(base_dir: str) -> list[Path]:
    """Find scenario bundle directories (for future multi-directory scenario support)."""
    scenario_root = Path(base_dir) / SCENARIO_DIR_NAME
    if not scenario_root.is_dir():
        return []
    return sorted(
        d for d in scenario_root.iterdir()
        if d.is_dir() and (d / "explanation.md").is_file()
    )
