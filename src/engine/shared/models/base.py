# shared/models/base.py

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):

    model_config = ConfigDict(
        frozen=True,
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=False,
        validate_assignment=True,
        arbitrary_types_allowed=False,
        str_strip_whitespace=True,
    )

    def model_dump_json(self, **kwargs: Any) -> str:
        import orjson
        return orjson.dumps(
            self.model_dump(**kwargs),
            option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z,
        ).decode()


class TimestampedModel(FrozenModel):

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def model_post_init(self, __context: Any) -> None:
        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=UTC))

