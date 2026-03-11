from __future__ import annotations

from engine.rag.scenarios.config import ScenarioConfig
from engine.rag.scenarios.tags import (
    DIRECTION_TAGS,
    FRAMEWORK_TAGS,
    OUTCOME_TAGS,
    SETUP_FAMILY_TAGS,
    TIMEFRAME_TAGS,
)
from engine.shared.exceptions import RAGScenarioError


def validate_scenario_metadata(
    metadata: dict[str, str],
    *,
    config: ScenarioConfig | None = None,
) -> None:
    framework = metadata.get("framework", "")
    if framework and framework not in FRAMEWORK_TAGS:
        raise RAGScenarioError(
            f"Invalid framework tag: {framework}",
            details={"framework": framework, "allowed": sorted(FRAMEWORK_TAGS)},
        )

    setup_family = metadata.get("setup_family", "")
    if setup_family and setup_family not in SETUP_FAMILY_TAGS:
        raise RAGScenarioError(
            f"Invalid setup_family tag: {setup_family}",
            details={"setup_family": setup_family},
        )

    direction = metadata.get("direction", "")
    if direction and direction not in DIRECTION_TAGS:
        raise RAGScenarioError(
            f"Invalid direction tag: {direction}",
            details={"direction": direction, "allowed": sorted(DIRECTION_TAGS)},
        )

    outcome = metadata.get("outcome", "")
    if outcome and outcome not in OUTCOME_TAGS:
        raise RAGScenarioError(
            f"Invalid outcome tag: {outcome}",
            details={"outcome": outcome, "allowed": sorted(OUTCOME_TAGS)},
        )

    timeframe = metadata.get("timeframe", "")
    if timeframe and timeframe not in TIMEFRAME_TAGS:
        raise RAGScenarioError(
            f"Invalid timeframe tag: {timeframe}",
            details={"timeframe": timeframe, "allowed": sorted(TIMEFRAME_TAGS)},
        )


def validate_scenario_count(
    count: int,
    *,
    config: ScenarioConfig,
) -> None:
    if count < config.min_total_scenarios:
        raise RAGScenarioError(
            f"Insufficient scenarios: {count} < {config.min_total_scenarios} required",
            details={"count": count, "required": config.min_total_scenarios},
        )
