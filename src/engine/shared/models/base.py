"""Base Pydantic model for all domain models.

Provides a frozen, immutable base with consistent JSON serialisation
(via ``orjson`` for speed) and a UTC timestamp mixin for audit fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import orjson
from pydantic import BaseModel, ConfigDict, Field


def _orjson_dumps(v: Any, *, default: Any = None) -> str:
    return orjson.dumps(v, default=default).decode()


class FrozenModel(BaseModel):
    """Immutable Pydantic model base used by all domain models.

    - ``frozen=True`` prevents accidental mutation.
    - ``from_attributes=True`` allows construction from ORM objects.
    - Uses ``orjson`` for fast (de)serialisation.
    """

    model_config = ConfigDict(
        frozen=True,
        from_attributes=True,
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()},
        ser_json_bytes="utf8",
    )


class TimestampedModel(FrozenModel):
    """Extends ``FrozenModel`` with a creation timestamp and unique ID.

    Every domain event and analysis record carries these fields for
    audit and correlation.
    """

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
