"""Tests for the credential re-wrap maintenance service.

Uses an in-memory fake DatabaseManager that implements exactly the
surface CredentialRewrapService depends on:

  - read_session() / session() as async context managers,
  - session.execute(text(sql), params) supporting the keyset SELECT
    (WHERE id > :cursor ORDER BY id ASC LIMIT :limit) and the per-row
    UPDATE the service issues.

The focus is the accounting contract from the Tier 3 audit: a dry run
must report the same rewrapped_rows / rewrapped_columns a live run
would, and must write nothing.
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager

import pytest

from engine.shared.crypto import (
    active_key_version,
    encrypt_credential,
    key_version_of,
    needs_rewrap,
)
from engine.shared.crypto.credential_cipher import reset_cipher_for_tests
from engine.shared.crypto.rewrap_service import CredentialRewrapService

_KEY_V1 = "rewrap-test-kek-v1"
_KEY_V2 = "rewrap-test-kek-v2"


# ---------------------------------------------------------------------------
# In-memory fake DatabaseManager
# ---------------------------------------------------------------------------

_SELECT_RE = re.compile(
    r"SELECT\s+(?P<cols>.+?)\s+FROM\s+(?P<table>\w+)\s*(?P<where>WHERE\s+\w+\s*>\s*:cursor)?\s*ORDER BY",
    re.IGNORECASE | re.DOTALL,
)
_UPDATE_RE = re.compile(r"UPDATE\s+(?P<table>\w+)\s+SET\s+(?P<set>.+?)\s+WHERE", re.IGNORECASE | re.DOTALL)


class _FakeResult:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, store: dict[str, list[dict]]) -> None:
        self._store = store
        self.write_count = 0

    async def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        m = _SELECT_RE.search(sql)
        if m:
            return self._do_select(m, params)
        m = _UPDATE_RE.search(sql)
        if m:
            self._do_update(m, sql, params)
            return _FakeResult([])
        raise AssertionError(f"unexpected SQL in fake session: {sql!r}")

    def _do_select(self, m, params) -> _FakeResult:
        table = m.group("table")
        cols = [c.strip() for c in m.group("cols").split(",")]
        rows = sorted(self._store[table], key=lambda r: r["id"])
        if m.group("where"):
            cursor = params["cursor"]
            rows = [r for r in rows if str(r["id"]) > cursor]
        limit = params["limit"]
        page = rows[:limit]
        projected = [{c: r.get(c) for c in cols} for r in page]
        return _FakeResult(projected)

    def _do_update(self, m, sql, params) -> None:
        table = m.group("table")
        row_id = params["__row_id"]
        target = next(r for r in self._store[table] if str(r["id"]) == str(row_id))
        # Apply every :param that maps to a real column name.
        for col in ("mt5_password_encrypted", "ea_auth_token_encrypted", "api_key_encrypted"):
            if col in params:
                target[col] = params[col]
        target["key_version"] = params["__key_version"]
        self.write_count += 1


class _FakeDB:
    """Implements the DatabaseManager surface the service uses."""

    def __init__(self, store: dict[str, list[dict]]) -> None:
        self._store = store
        self.session_obj = _FakeSession(store)

    @property
    def write_count(self) -> int:
        return self.session_obj.write_count

    @asynccontextmanager
    async def read_session(self, **_kwargs):
        yield self.session_obj

    @asynccontextmanager
    async def session(self, **_kwargs):
        yield self.session_obj


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def single_kek(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("BROKER_ENCRYPTION_KEY", _KEY_V1)
    monkeypatch.delenv("BROKER_ENCRYPTION_KEY_V2", raising=False)
    reset_cipher_for_tests()
    yield
    reset_cipher_for_tests()


def _legacy_token(raw_kek: str, plaintext: str) -> str:
    import base64
    import hashlib

    from cryptography.fernet import Fernet

    digest = hashlib.sha256(raw_kek.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest)).encrypt(plaintext.encode()).decode()


def _new_store_with_legacy_rows() -> dict[str, list[dict]]:
    """broker_connections with two legacy-ciphertext rows (one of which
    has both encrypted columns populated) + one llm_connections legacy
    row. All need re-wrapping to v2."""
    return {
        "broker_connections": [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "mt5_password_encrypted": _legacy_token(_KEY_V1, "pw-1"),
                "ea_auth_token_encrypted": _legacy_token(_KEY_V1, "ea-1"),
                "key_version": None,
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "mt5_password_encrypted": _legacy_token(_KEY_V1, "pw-2"),
                "ea_auth_token_encrypted": None,
                "key_version": None,
            },
        ],
        "llm_connections": [
            {
                "id": "00000000-0000-0000-0000-0000000000aa",
                "api_key_encrypted": _legacy_token(_KEY_V1, "api-1"),
                "key_version": None,
            },
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDryRunAccounting:
    @pytest.mark.asyncio
    async def test_dry_run_reports_rows_and_columns_and_writes_nothing(self, single_kek):
        db = _FakeDB(_new_store_with_legacy_rows())
        service = CredentialRewrapService(db, batch_size=200)

        stats = await service.run(dry_run=True)

        # 3 rows scanned, all 3 stale -> 3 rewrapped_rows; columns =
        # 2 (row 1) + 1 (row 2) + 1 (llm) = 4.
        assert stats.scanned_rows == 3
        assert stats.rewrapped_rows == 3
        assert stats.rewrapped_columns == 4
        assert stats.failed_columns == 0
        assert db.write_count == 0  # dry run writes nothing

    @pytest.mark.asyncio
    async def test_dry_run_matches_live_run(self, single_kek):
        dry = await CredentialRewrapService(_FakeDB(_new_store_with_legacy_rows())).run(
            dry_run=True
        )
        live = await CredentialRewrapService(_FakeDB(_new_store_with_legacy_rows())).run(
            dry_run=False
        )
        assert dry.scanned_rows == live.scanned_rows
        assert dry.rewrapped_rows == live.rewrapped_rows
        assert dry.rewrapped_columns == live.rewrapped_columns
        assert dry.per_table == live.per_table


class TestLiveRun:
    @pytest.mark.asyncio
    async def test_live_run_persists_and_stamps_active_version(self, single_kek):
        store = _new_store_with_legacy_rows()
        db = _FakeDB(store)
        stats = await CredentialRewrapService(db).run(dry_run=False)

        assert stats.rewrapped_rows == 3
        assert db.write_count == 3
        active = active_key_version()
        for row in store["broker_connections"] + store["llm_connections"]:
            assert row["key_version"] == active
            for col in ("mt5_password_encrypted", "ea_auth_token_encrypted", "api_key_encrypted"):
                ct = row.get(col)
                if ct:
                    assert not needs_rewrap(ct)
                    assert key_version_of(ct) == active

    @pytest.mark.asyncio
    async def test_second_live_run_is_a_noop(self, single_kek):
        store = _new_store_with_legacy_rows()
        await CredentialRewrapService(_FakeDB(store)).run(dry_run=False)
        db2 = _FakeDB(store)
        stats2 = await CredentialRewrapService(db2).run(dry_run=False)
        assert stats2.scanned_rows == 3
        assert stats2.rewrapped_rows == 0
        assert stats2.rewrapped_columns == 0
        assert db2.write_count == 0

    @pytest.mark.asyncio
    async def test_per_table_totals_equal_aggregate(self, single_kek):
        stats = await CredentialRewrapService(_FakeDB(_new_store_with_legacy_rows())).run(
            dry_run=False
        )
        agg_rows = sum(t["rewrapped_rows"] for t in stats.per_table.values())
        agg_cols = sum(t["rewrapped_columns"] for t in stats.per_table.values())
        assert agg_rows == stats.rewrapped_rows
        assert agg_cols == stats.rewrapped_columns


class TestPagination:
    @pytest.mark.asyncio
    async def test_scans_every_row_across_batches(self, single_kek):
        store = _new_store_with_legacy_rows()
        # batch_size 1 forces multiple keyset pages per table.
        stats = await CredentialRewrapService(_FakeDB(store), batch_size=1).run(
            dry_run=True
        )
        assert stats.scanned_rows == 3
        assert stats.rewrapped_rows == 3
        assert stats.rewrapped_columns == 4
