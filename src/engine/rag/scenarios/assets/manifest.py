from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScenarioManifestEntry:
    scenario_dir: Path
    explanation_path: Path
    metadata_path: Path
    image_paths: tuple[Path, ...] = ()


def build_scenario_manifest(scenario_root: Path) -> list[ScenarioManifestEntry]:
    if not scenario_root.is_dir():
        return []

    entries: list[ScenarioManifestEntry] = []
    for child in sorted(scenario_root.iterdir()):
        if not child.is_dir():
            continue

        explanation = child / "explanation.md"
        metadata = child / "metadata.json"

        if not explanation.is_file() or not metadata.is_file():
            continue

        images = tuple(
            sorted(
                f for f in child.iterdir()
                if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}
            )
        )

        entries.append(ScenarioManifestEntry(
            scenario_dir=child,
            explanation_path=explanation,
            metadata_path=metadata,
            image_paths=images,
        ))

    return entries
