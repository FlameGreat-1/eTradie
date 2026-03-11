from __future__ import annotations

from dataclasses import dataclass

from engine.rag.constants import SUPPORTED_IMAGE_FORMATS


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    min_scenarios_per_framework: int = 3
    min_total_scenarios: int = 20
    required_outcomes: frozenset[str] = frozenset({"valid_win", "valid_loss", "failed_setup"})
    max_image_size_mb: float = 10.0
    supported_image_formats: frozenset[str] = SUPPORTED_IMAGE_FORMATS
