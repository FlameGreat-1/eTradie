from __future__ import annotations

from pathlib import Path


def resolve_asset_path(scenario_dir: Path, ref: str) -> Path:
    resolved = scenario_dir / ref
    if resolved.is_file():
        return resolved
    return scenario_dir / Path(ref).name


def resolve_image_refs(scenario_dir: Path) -> list[str]:
    refs: list[str] = []
    for child in sorted(scenario_dir.iterdir()):
        if child.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            refs.append(child.name)
    return refs
