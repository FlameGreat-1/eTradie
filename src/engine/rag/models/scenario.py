from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import Field

from engine.rag.constants import Direction, Framework, ScenarioOutcome, SetupFamily
from engine.shared.models.base import TimestampedModel


class Scenario(TimestampedModel):
    document_id: UUID
    framework: Framework
    setup_family: SetupFamily
    direction: Direction
    timeframe: str = Field(min_length=1, max_length=10)
    outcome: ScenarioOutcome
    title: str = Field(min_length=1, max_length=512)
    explanation_text: str = Field(min_length=1)
    image_refs: tuple[str, ...] = Field(default_factory=tuple)
    confluence_tags: frozenset[str] = Field(default_factory=frozenset)
    style_tags: frozenset[str] = Field(default_factory=frozenset)
    linked_chunk_ids: tuple[UUID, ...] = Field(default_factory=tuple)
    metadata: dict[str, str] = Field(default_factory=dict)
    is_active: bool = True
    notes: Optional[str] = None
