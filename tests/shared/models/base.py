from datetime import UTC, datetime
from typing import Optional

import orjson
import pytest
from pydantic import ValidationError

from engine.shared.models.base import FrozenModel, TimestampedModel


class DummyFrozenModel(FrozenModel):
    name: str
    value: int
    optional: Optional[str] = None


class DummyTimestampedModel(TimestampedModel):
    name: str


def test_frozen_model_immutability():
    """Test that FrozenModel instances cannot be modified after creation."""
    model = DummyFrozenModel(name="test", value=42)
    
    assert model.name == "test"
    assert model.value == 42
    
    with pytest.raises(ValidationError):
        model.name = "new_name"


def test_frozen_model_json_serialization():
    """Test that FrozenModel serializes to JSON correctly using orjson parameters."""
    model = DummyFrozenModel(name="test", value=42)
    json_str = model.model_dump_json()
    
    parsed = orjson.loads(json_str)
    assert parsed["name"] == "test"
    assert parsed["value"] == 42
    assert parsed["optional"] is None


def test_frozen_model_whitespace_stripping():
    """Test that strings are automatically stripped of leading/trailing whitespace."""
    model = DummyFrozenModel(name="  test name  \n", value=1)
    assert model.name == "test name"


def test_timestamped_model_initialization():
    """Test that TimestampedModel automatically gets id and created_at."""
    model = DummyTimestampedModel(name="timestamp_test")
    
    assert model.id is not None
    assert isinstance(model.created_at, datetime)
    assert model.created_at.tzinfo == UTC


def test_timestamped_model_explicit_timestamp():
    """Test that explicitly provided timestamps are converted to UTC if naive."""
    naive_dt = datetime(2025, 1, 1, 12, 0, 0)
    model = DummyTimestampedModel(name="explicit", created_at=naive_dt)
    
    assert model.created_at.tzinfo == UTC
    assert model.created_at.year == 2025


def test_timestamped_model_serialization():
    """Test that TimestampedModel serializes timestamps properly."""
    model = DummyTimestampedModel(name="serial_test")
    json_str = model.model_dump_json()
    
    parsed = orjson.loads(json_str)
    assert "id" in parsed
    assert "created_at" in parsed
    # orjson OPT_UTC_Z appends 'Z' for UTC timezone representation
    assert parsed["created_at"].endswith("Z")
