from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    min_scenarios_per_framework: int = 3
    min_total_scenarios: int = 20
    required_outcomes: frozenset[str] = frozenset({"valid_win", "valid_loss", "failed_setup"})
    max_image_size_mb: float = 10.0
    supported_image_formats: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp", ".svg"})
