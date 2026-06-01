"""Read-through durability tests for the macro collector base class.

Production module: src/engine/macro/collectors/base.py

These verify the fix for the regression where a Redis cache miss on the
analysis hot path produced an EMPTY macro dataset (COT vanished from the
LLM input) because every collector's _read_from_db returned None.

The fix: on a cache miss the base reads the durable last-good snapshot
from macro_snapshots and rehydrates it via cache_model, so the dataset
is always the last good enriched value, never empty, with no API call.

All infrastructure (Redis, Postgres) is faked; the snapshot repository is
patched where BaseCollector imports it.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import BaseModel

from engine.macro.collectors import base as base_module
from engine.macro.collectors.base import BaseCollector


# ── Fakes ───────────────────────────────────────────────────────────────


class _FakeCache:
    """Cache that always misses on get and records set() calls."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], Any] = {}

    async def get(self, namespace: str, key: str) -> Any | None:
        return self.store.get((namespace, key))

    async def set(self, namespace: str, key: str, value: Any, ttl: int) -> None:
        self.store[(namespace, key)] = value


class _FakeSession:
    pass


class _FakeDB:
    """DatabaseManager stand-in exposing session()/read_session()."""

    @asynccontextmanager
    async def read_session(self, **_kw):
        yield _FakeSession()

    @asynccontextmanager
    async def session(self, **_kw):
        yield _FakeSession()


class _SampleDataSet(BaseModel):
    """Minimal stand-in for a collector dataset with a collected_at."""

    value: int = 0
    collected_at: datetime = datetime(2026, 6, 1, tzinfo=UTC)


class _ModelCollector(BaseCollector):
    """Concrete collector backed by a Pydantic cache_model."""

    collector_name = "sample"
    cache_namespace = "sample"
    cache_model = _SampleDataSet

    def __init__(self, providers, cache, db, *, do_collect_value: int = 99) -> None:
        super().__init__(providers, cache, db)
        self._do_collect_value = do_collect_value

    async def _do_collect(self) -> _SampleDataSet:
        return _SampleDataSet(value=self._do_collect_value)

    def _empty_dataset(self) -> _SampleDataSet:
        return _SampleDataSet(value=0)


class _DictCollector(BaseCollector):
    """Concrete collector that returns a raw dict (cache_model unset)."""

    collector_name = "dictlike"
    cache_namespace = "dictlike"
    cache_model = None

    async def _do_collect(self) -> dict[str, Any]:
        return {"hello": "world", "collected_at": "2026-06-01T00:00:00+00:00"}

    def _empty_dataset(self) -> dict[str, Any]:
        return {}


class _FakeSnapshotRepo:
    """Patched MacroSnapshotRepository: serves a fixed payload + records writes."""

    payload_by_namespace: dict[str, dict[str, Any]] = {}
    upserts: list[tuple[str, dict[str, Any]]] = []

    def __init__(self, _session) -> None:
        pass

    async def get_payload(self, namespace: str) -> dict[str, Any] | None:
        return type(self).payload_by_namespace.get(namespace)

    async def upsert_payload(self, namespace, payload, collected_at) -> None:
        type(self).upserts.append((namespace, payload))


@pytest.fixture(autouse=True)
def _patch_snapshot_repo(monkeypatch):
    _FakeSnapshotRepo.payload_by_namespace = {}
    _FakeSnapshotRepo.upserts = []
    monkeypatch.setattr(
        base_module, "MacroSnapshotRepository", _FakeSnapshotRepo
    )
    yield


# ── Tests ───────────────────────────────────────────────────────────────


async def test_cache_miss_serves_last_good_snapshot_not_empty():
    """Cache miss + persisted snapshot -> rehydrated dataset, never empty."""
    _FakeSnapshotRepo.payload_by_namespace = {
        "sample": {"value": 42, "collected_at": "2026-06-01T00:00:00+00:00"}
    }
    c = _ModelCollector([], _FakeCache(), _FakeDB())

    result = await c.collect()

    assert isinstance(result, _SampleDataSet)
    assert result.value == 42  # last-good snapshot, NOT the empty value 0


async def test_cache_miss_dict_collector_returns_raw_snapshot():
    """cache_model unset (sentiment): raw snapshot dict is returned as-is."""
    _FakeSnapshotRepo.payload_by_namespace = {
        "dictlike": {"hello": "persisted"}
    }
    c = _DictCollector([], _FakeCache(), _FakeDB())

    result = await c.collect()

    assert result == {"hello": "persisted"}


async def test_cold_start_no_snapshot_falls_back_to_empty():
    """No cache, no snapshot -> _empty_dataset() exactly once."""
    c = _ModelCollector([], _FakeCache(), _FakeDB())

    result = await c.collect()

    assert isinstance(result, _SampleDataSet)
    assert result.value == 0  # empty fallback


async def test_force_refresh_persists_snapshot():
    """refresh() (force) runs _do_collect and persists the snapshot."""
    c = _ModelCollector([], _FakeCache(), _FakeDB(), do_collect_value=7)

    result = await c.refresh()

    assert isinstance(result, _SampleDataSet)
    assert result.value == 7
    assert any(
        ns == "sample" and payload.get("value") == 7
        for ns, payload in _FakeSnapshotRepo.upserts
    )


def test_cot_empty_dataset_is_valid():
    """COTCollector._empty_dataset() must construct a valid COTDataSet.

    Regression guard: the old implementation passed reports=/sources=,
    which are not fields of COTDataSet.
    """
    from engine.macro.collectors.cot.collector import COTCollector
    from engine.macro.models.collector.cot import COTDataSet

    empty = COTCollector.__new__(COTCollector)._empty_dataset()
    assert isinstance(empty, COTDataSet)
    assert empty.latest_positions == []
    assert empty.has_tff_data is False
