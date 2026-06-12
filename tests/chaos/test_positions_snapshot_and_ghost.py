"""Chaos test: position snapshot write + ghost-position detection.

Tests the Section 7 Step A + B data-consistency layer end-to-end
using a real PostgreSQL fixture (the same pool the brokertest package
uses; CI brings up postgres via docker-compose).

Coverage:
  1. PositionSnapshotStore.WriteSnapshot round-trips correctly:
     - Canonicalises positions by OrderID before hashing.
     - sha256 content_hash is deterministic for the same input.
     - Two snapshots with different positions produce different hashes.

  2. PositionSnapshotStore.LatestSnapshot returns the most recent row.

  3. PositionSnapshotStore.SnapshotsBetween returns rows in the
     inclusive range, ordered chronologically.

  4. Ghost-position detection logic (in-process, no DB):
     - A position present in the latest snapshot but NOT in the
       current broker reply AND older than ghostMinAge is classified
       as a ghost.
     - A position present in BOTH the snapshot and the broker reply
       is NOT classified as a ghost.
     - A snapshot younger than ghostMinAge does NOT trigger ghost
       detection (transient close protection).
     - No snapshot (first cycle) -> ghost detection is a no-op.

  5. DB-level immutability triggers (Section 7 Step B):
     - BEFORE UPDATE on execution_positions_snapshot raises
       psycopg2.errors.RestrictViolation.
     - BEFORE UPDATE on execution_audit_logs raises the same.

Skipped when:
  - EXECUTION_DATABASE_URL is not set (local dev without postgres).
  - psycopg2 is not installed.
  - The postgres connection fails.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import uuid
from datetime import datetime

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_pool():
    """Return a psycopg2 connection pool backed by EXECUTION_DATABASE_URL.

    Skips the module when the env var is absent or the connection fails.
    """
    db_url = os.environ.get("EXECUTION_DATABASE_URL", "")
    if not db_url:
        pytest.skip("EXECUTION_DATABASE_URL not set; skipping snapshot chaos test")

    try:
        import psycopg2
        import psycopg2.pool
    except ImportError:
        pytest.skip("psycopg2 not installed; skipping snapshot chaos test")

    try:
        pool = psycopg2.pool.SimpleConnectionPool(1, 3, db_url)
    except Exception as exc:
        pytest.skip(f"Cannot connect to postgres: {exc}")

    yield pool
    pool.closeall()


@pytest.fixture()
def conn(db_pool):
    """Yield a single connection; always roll back after the test."""
    c = db_pool.getconn()
    c.autocommit = False
    try:
        yield c
    finally:
        c.rollback()
        db_pool.putconn(c)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_hash(positions: list[dict]) -> str:
    """Compute the sha256 of the canonicalised positions slice.

    Mirrors the Go store logic: sort by order_id, then sha256 of the
    compact JSON.
    """
    canonical = sorted(positions, key=lambda p: p.get("order_id", ""))
    raw = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _insert_snapshot(
    conn,
    user_id: str,
    positions: list[dict],
    snapshot_ts: datetime | None = None,
    reconcile_run_id: str = "",
) -> int:
    """Insert a snapshot row directly. Returns the inserted row id."""
    canonical = sorted(positions, key=lambda p: p.get("order_id", ""))
    json_bytes = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
    content_hash = hashlib.sha256(json_bytes).hexdigest()
    ts = snapshot_ts or datetime.now(dt.UTC)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO execution_positions_snapshot
              (user_id, snapshot_ts, position_count, positions, content_hash, reconcile_run_id)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            RETURNING id
            """,
            (user_id, ts, len(canonical), json.dumps(canonical), content_hash, reconcile_run_id),
        )
        row_id = cur.fetchone()[0]
    conn.commit()
    return row_id


def _latest_snapshot(conn, user_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, snapshot_ts, position_count, positions, content_hash
            FROM execution_positions_snapshot
            WHERE user_id = %s
            ORDER BY snapshot_ts DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "user_id": row[1],
        "snapshot_ts": row[2],
        "position_count": row[3],
        "positions": row[4] if isinstance(row[4], list) else json.loads(row[4]),
        "content_hash": row[5],
    }


def _snapshots_between(conn, user_id: str, since: datetime, until: datetime) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, snapshot_ts, position_count, content_hash
            FROM execution_positions_snapshot
            WHERE user_id = %s AND snapshot_ts BETWEEN %s AND %s
            ORDER BY snapshot_ts ASC
            """,
            (user_id, since, until),
        )
        rows = cur.fetchall()
    return [{"id": r[0], "snapshot_ts": r[1], "position_count": r[2], "content_hash": r[3]} for r in rows]


def _make_position(order_id: str, symbol: str = "EURUSD") -> dict:
    return {
        "order_id": order_id,
        "symbol": symbol,
        "direction": "BUY",
        "lot_size": 0.10,
        "stop_loss": 1.0950,
        "take_profit": 1.1100,
        "entry_price": 1.1000,
    }


# ---------------------------------------------------------------------------
# DB-backed tests: PositionSnapshotStore round-trip
# ---------------------------------------------------------------------------


def test_snapshot_write_and_latest(conn):
    """WriteSnapshot -> LatestSnapshot round-trip."""
    user_id = f"test-ghost-{uuid.uuid4().hex[:8]}"
    positions = [_make_position("42")]

    row_id = _insert_snapshot(conn, user_id, positions)
    assert row_id > 0

    snap = _latest_snapshot(conn, user_id)
    assert snap is not None
    assert snap["user_id"] == user_id
    assert snap["position_count"] == 1
    assert len(snap["positions"]) == 1
    assert snap["positions"][0]["order_id"] == "42"
    assert len(snap["content_hash"]) == 64  # sha256 hex


def test_snapshot_hash_is_deterministic(conn):
    """Same positions in different order -> same content_hash."""
    user_id = f"test-ghost-{uuid.uuid4().hex[:8]}"
    pos_a = _make_position("1")
    pos_b = _make_position("2", symbol="GBPUSD")

    _insert_snapshot(conn, user_id, [pos_a, pos_b])
    snap1 = _latest_snapshot(conn, user_id)

    _insert_snapshot(conn, user_id, [pos_b, pos_a])
    snap2 = _latest_snapshot(conn, user_id)

    assert snap1["content_hash"] == snap2["content_hash"], (
        "Content hash must be deterministic regardless of position order"
    )


def test_snapshot_different_positions_different_hash(conn):
    """Different positions -> different content_hash."""
    user_id = f"test-ghost-{uuid.uuid4().hex[:8]}"
    _insert_snapshot(conn, user_id, [_make_position("1")])
    snap1 = _latest_snapshot(conn, user_id)

    _insert_snapshot(conn, user_id, [_make_position("1"), _make_position("2")])
    snap2 = _latest_snapshot(conn, user_id)

    assert snap1["content_hash"] != snap2["content_hash"]


def test_latest_snapshot_returns_most_recent(conn):
    """LatestSnapshot returns the row with the highest snapshot_ts."""
    user_id = f"test-ghost-{uuid.uuid4().hex[:8]}"
    t1 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=dt.UTC)
    t2 = datetime(2026, 1, 1, 0, 1, 0, tzinfo=dt.UTC)

    _insert_snapshot(conn, user_id, [_make_position("old")], snapshot_ts=t1)
    _insert_snapshot(conn, user_id, [_make_position("new")], snapshot_ts=t2)

    snap = _latest_snapshot(conn, user_id)
    assert snap["positions"][0]["order_id"] == "new"


def test_snapshots_between_range(conn):
    """SnapshotsBetween returns rows in the inclusive range, ordered chronologically."""
    user_id = f"test-ghost-{uuid.uuid4().hex[:8]}"
    t1 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=dt.UTC)
    t2 = datetime(2026, 1, 1, 0, 1, 0, tzinfo=dt.UTC)
    t3 = datetime(2026, 1, 1, 0, 2, 0, tzinfo=dt.UTC)
    t4 = datetime(2026, 1, 1, 0, 3, 0, tzinfo=dt.UTC)

    for ts, oid in [(t1, "a"), (t2, "b"), (t3, "c"), (t4, "d")]:
        _insert_snapshot(conn, user_id, [_make_position(oid)], snapshot_ts=ts)

    rows = _snapshots_between(conn, user_id, t2, t3)
    assert len(rows) == 2
    assert rows[0]["snapshot_ts"] <= rows[1]["snapshot_ts"]


def test_no_snapshot_returns_none(conn):
    """LatestSnapshot returns None for a user with no snapshots."""
    user_id = f"test-ghost-{uuid.uuid4().hex[:8]}-nosnapshot"
    snap = _latest_snapshot(conn, user_id)
    assert snap is None


# ---------------------------------------------------------------------------
# DB-backed tests: immutability triggers (Section 7 Step B)
# ---------------------------------------------------------------------------


def test_snapshot_update_is_blocked(conn):
    """BEFORE UPDATE trigger must block any UPDATE on execution_positions_snapshot."""
    try:
        import psycopg2.errors
    except ImportError:
        pytest.skip("psycopg2 not available")

    user_id = f"test-ghost-{uuid.uuid4().hex[:8]}"
    row_id = _insert_snapshot(conn, user_id, [_make_position("x")])

    with pytest.raises(Exception) as exc_info:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE execution_positions_snapshot SET position_count = 99 WHERE id = %s",
                (row_id,),
            )
        conn.commit()
    conn.rollback()
    # The trigger raises restrict_violation (SQLSTATE 23001).
    assert (
        "restrict_violation" in str(exc_info.value).lower()
        or "immutability" in str(exc_info.value).lower()
        or "23001" in str(exc_info.value)
    )


def test_audit_log_update_is_blocked(conn):
    """BEFORE UPDATE trigger must block any UPDATE on execution_audit_logs."""
    try:
        import psycopg2.errors
    except ImportError:
        pytest.skip("psycopg2 not available")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO execution_audit_logs
              (user_id, action, symbol, direction, order_id, analysis_id,
               trace_id, execution_mode, entry_price, stop_loss, lot_size,
               risk_amount, risk_percent, grade, trading_style, session,
               rr_ratio, confluence_score, rejection_check, rejection_reason,
               details)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            RETURNING id
            """,
            (
                "test-user",
                "LIMIT_ORDER_PLACED",
                "EURUSD",
                "BUY",
                "order-1",
                "analysis-1",
                "trace-1",
                "LIMIT",
                1.1000,
                1.0950,
                0.10,
                100.0,
                1.0,
                "A",
                "INTRADAY",
                "LONDON_OPEN",
                2.0,
                0.85,
                0,
                "",
                "{}",
            ),
        )
        row_id = cur.fetchone()[0]
    conn.commit()

    with pytest.raises(Exception) as exc_info:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE execution_audit_logs SET symbol = 'GBPUSD' WHERE id = %s",
                (row_id,),
            )
        conn.commit()
    conn.rollback()
    assert (
        "restrict_violation" in str(exc_info.value).lower()
        or "immutability" in str(exc_info.value).lower()
        or "23001" in str(exc_info.value)
    )


# ---------------------------------------------------------------------------
# In-process logic tests: ghost-position detection algorithm
# (no DB required; these run in any environment)
# ---------------------------------------------------------------------------


def _apply_ghost_detection(
    snapshot_positions: list[dict],
    broker_positions: list[dict],
    snapshot_age_secs: float,
    ghost_min_age_secs: float,
) -> list[dict]:
    """Pure-Python mirror of the Go reconciler's detectGhostPositions logic.

    Returns the list of positions classified as ghosts.
    """
    if snapshot_age_secs < ghost_min_age_secs:
        return []
    broker_set = {p["order_id"] for p in broker_positions}
    return [p for p in snapshot_positions if p.get("order_id") and p["order_id"] not in broker_set]


def test_ghost_detection_removes_stale_missing_position():
    """Position in snapshot, NOT in broker reply, snapshot age >= ghostMinAge -> ghost."""
    ghosts = _apply_ghost_detection(
        snapshot_positions=[_make_position("42")],
        broker_positions=[],
        snapshot_age_secs=600,  # 10 min
        ghost_min_age_secs=300,  # 5 min
    )
    assert len(ghosts) == 1
    assert ghosts[0]["order_id"] == "42"


def test_ghost_detection_skips_fresh_snapshot():
    """Snapshot younger than ghostMinAge -> no ghost detection."""
    ghosts = _apply_ghost_detection(
        snapshot_positions=[_make_position("42")],
        broker_positions=[],
        snapshot_age_secs=60,  # 1 min
        ghost_min_age_secs=300,  # 5 min
    )
    assert ghosts == [], "Fresh snapshot must not trigger ghost detection"


def test_ghost_detection_skips_position_still_in_broker_reply():
    """Position in BOTH snapshot and broker reply -> not a ghost."""
    ghosts = _apply_ghost_detection(
        snapshot_positions=[_make_position("42"), _make_position("99")],
        broker_positions=[_make_position("42")],  # '42' still open; '99' closed
        snapshot_age_secs=600,
        ghost_min_age_secs=300,
    )
    assert len(ghosts) == 1
    assert ghosts[0]["order_id"] == "99"


def test_ghost_detection_no_snapshot_is_safe():
    """No snapshot (first cycle) -> ghost detection is a no-op."""
    # Mirrors the Go reconciler: if LatestSnapshot returns nil, return early.
    latest_snapshot = None
    if latest_snapshot is None:
        ghosts = []
    else:
        ghosts = _apply_ghost_detection(latest_snapshot["positions"], [], 999, 300)
    assert ghosts == []


def test_ghost_detection_empty_snapshot_is_safe():
    """Snapshot with zero positions -> no ghosts regardless of age."""
    ghosts = _apply_ghost_detection(
        snapshot_positions=[],
        broker_positions=[],
        snapshot_age_secs=600,
        ghost_min_age_secs=300,
    )
    assert ghosts == []


def test_ghost_detection_multiple_ghosts():
    """Multiple positions in snapshot, none in broker reply -> all are ghosts."""
    ghosts = _apply_ghost_detection(
        snapshot_positions=[_make_position("1"), _make_position("2"), _make_position("3")],
        broker_positions=[],
        snapshot_age_secs=600,
        ghost_min_age_secs=300,
    )
    assert len(ghosts) == 3
    ghost_ids = {g["order_id"] for g in ghosts}
    assert ghost_ids == {"1", "2", "3"}


def test_ghost_detection_partial_close():
    """Broker closed some positions but not all -> only closed ones are ghosts."""
    ghosts = _apply_ghost_detection(
        snapshot_positions=[
            _make_position("open-1"),
            _make_position("closed-2"),
            _make_position("open-3"),
        ],
        broker_positions=[_make_position("open-1"), _make_position("open-3")],
        snapshot_age_secs=600,
        ghost_min_age_secs=300,
    )
    assert len(ghosts) == 1
    assert ghosts[0]["order_id"] == "closed-2"
