"""Integration tests for TA repositories against real PostgreSQL.

Requires PostgreSQL running with migrations applied.
Run: docker compose up -d postgres && make db-migrate
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from tests.integration.conftest import skip_no_db

pytestmark = [pytest.mark.integration, skip_no_db]


# ---------------------------------------------------------------------------
# SnapshotRepository
# ---------------------------------------------------------------------------


class TestSnapshotRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_by_id(self, db_manager):
        """Create a snapshot and retrieve it by ID."""
        from engine.ta.storage.repositories.snapshot import SnapshotRepository

        async with db_manager.session() as session:
            repo = SnapshotRepository(session)
            now = datetime.now(UTC)
            symbol = f"EURUSD_{uuid4().hex[:6]}"

            snapshot = await repo.create(
                user_id="test_user_id_123",
                symbol=symbol,
                timeframe="H4",
                timestamp=now,
                swing_highs={"highs": [{"price": 1.1050, "index": 10}]},
                swing_lows={"lows": [{"price": 1.0950, "index": 5}]},
                bms_events={},
                choch_events={},
                sms_events={},
                order_blocks={"blocks": [{"upper": 1.1020, "lower": 1.1000}]},
                fair_value_gaps={},
                breaker_blocks={},
                liquidity_sweeps={},
                inducement_events={},
                qm_levels={},
                sr_flips={},
                rs_flips={},
                previous_levels={},
                mpl_levels={},
                fakeout_tests={},
                supply_zones={},
                demand_zones={},
                fibonacci_retracements={},
                dealing_ranges={},
            )

            assert snapshot.id is not None
            assert snapshot.symbol == symbol
            assert snapshot.timeframe == "H4"
            assert snapshot.version == 1

            fetched = await repo.get_by_id(snapshot.id)
            assert fetched is not None
            assert fetched.symbol == symbol
            assert fetched.swing_highs["highs"][0]["price"] == 1.1050

    @pytest.mark.asyncio
    async def test_get_latest_snapshot(self, db_manager):
        """get_latest_snapshot returns the most recent by timestamp."""
        from engine.ta.storage.repositories.snapshot import SnapshotRepository

        async with db_manager.session() as session:
            repo = SnapshotRepository(session)
            symbol = f"GBPUSD_{uuid4().hex[:6]}"
            base = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
            empty = {}

            await repo.create(
                user_id="test_user_id_123",
                symbol=symbol, timeframe="D1", timestamp=base,
                swing_highs=empty, swing_lows=empty, bms_events=empty,
                choch_events=empty, sms_events=empty, order_blocks=empty,
                fair_value_gaps=empty, breaker_blocks=empty,
                liquidity_sweeps=empty, inducement_events=empty,
                qm_levels=empty, sr_flips=empty, rs_flips=empty,
                previous_levels=empty, mpl_levels=empty, fakeout_tests=empty,
                supply_zones=empty, demand_zones=empty,
                fibonacci_retracements=empty, dealing_ranges=empty,
            )
            await repo.create(
                user_id="test_user_id_123",
                symbol=symbol, timeframe="D1",
                timestamp=base + timedelta(hours=4),
                swing_highs=empty, swing_lows=empty, bms_events=empty,
                choch_events=empty, sms_events=empty, order_blocks=empty,
                fair_value_gaps=empty, breaker_blocks=empty,
                liquidity_sweeps=empty, inducement_events=empty,
                qm_levels=empty, sr_flips=empty, rs_flips=empty,
                previous_levels=empty, mpl_levels=empty, fakeout_tests=empty,
                supply_zones=empty, demand_zones=empty,
                fibonacci_retracements=empty, dealing_ranges=empty,
            )

            latest = await repo.get_latest_snapshot(symbol, "D1", user_id="test_user_id_123")
            assert latest is not None
            assert latest.timestamp == base + timedelta(hours=4)

    @pytest.mark.asyncio
    async def test_version_auto_increments(self, db_manager):
        """Each new snapshot for same symbol/tf increments version."""
        from engine.ta.storage.repositories.snapshot import SnapshotRepository

        async with db_manager.session() as session:
            repo = SnapshotRepository(session)
            empty = {}
            symbol = f"USDJPY_{uuid4().hex[:6]}"
            ts = datetime(2024, 7, 1, 8, 0, tzinfo=UTC)

            s1 = await repo.create(
                user_id="test_user_id_123",
                symbol=symbol, timeframe="H1", timestamp=ts,
                swing_highs=empty, swing_lows=empty, bms_events=empty,
                choch_events=empty, sms_events=empty, order_blocks=empty,
                fair_value_gaps=empty, breaker_blocks=empty,
                liquidity_sweeps=empty, inducement_events=empty,
                qm_levels=empty, sr_flips=empty, rs_flips=empty,
                previous_levels=empty, mpl_levels=empty, fakeout_tests=empty,
                supply_zones=empty, demand_zones=empty,
                fibonacci_retracements=empty, dealing_ranges=empty,
            )
            s2 = await repo.create(
                user_id="test_user_id_123",
                symbol=symbol, timeframe="H1",
                timestamp=ts + timedelta(hours=1),
                swing_highs=empty, swing_lows=empty, bms_events=empty,
                choch_events=empty, sms_events=empty, order_blocks=empty,
                fair_value_gaps=empty, breaker_blocks=empty,
                liquidity_sweeps=empty, inducement_events=empty,
                qm_levels=empty, sr_flips=empty, rs_flips=empty,
                previous_levels=empty, mpl_levels=empty, fakeout_tests=empty,
                supply_zones=empty, demand_zones=empty,
                fibonacci_retracements=empty, dealing_ranges=empty,
            )

            assert s1.version == 1
            assert s2.version == 2

    @pytest.mark.asyncio
    async def test_get_snapshot_count(self, db_manager):
        """Count snapshots for a symbol/timeframe."""
        from engine.ta.storage.repositories.snapshot import SnapshotRepository

        async with db_manager.session() as session:
            repo = SnapshotRepository(session)
            empty = {}
            unique_symbol = f"TEST{uuid4().hex[:6].upper()}"

            for i in range(3):
                await repo.create(
                    user_id="test_user_id_123",
                    symbol=unique_symbol, timeframe="M15",
                    timestamp=datetime(2024, 8, 1, i, 0, tzinfo=UTC),
                    swing_highs=empty, swing_lows=empty, bms_events=empty,
                    choch_events=empty, sms_events=empty, order_blocks=empty,
                    fair_value_gaps=empty, breaker_blocks=empty,
                    liquidity_sweeps=empty, inducement_events=empty,
                    qm_levels=empty, sr_flips=empty, rs_flips=empty,
                    previous_levels=empty, mpl_levels=empty, fakeout_tests=empty,
                    supply_zones=empty, demand_zones=empty,
                    fibonacci_retracements=empty, dealing_ranges=empty,
                )

            count = await repo.get_snapshot_count(unique_symbol, "M15", user_id="test_user_id_123")
            assert count == 3

    @pytest.mark.asyncio
    async def test_delete_by_id(self, db_manager):
        """Delete snapshot and verify it's gone."""
        from engine.ta.storage.repositories.snapshot import SnapshotRepository

        async with db_manager.session() as session:
            repo = SnapshotRepository(session)
            empty = {}

            snapshot = await repo.create(
                user_id="test_user_id_123",
                symbol="XAUUSD", timeframe="W1",
                timestamp=datetime(2024, 9, 1, tzinfo=UTC),
                swing_highs=empty, swing_lows=empty, bms_events=empty,
                choch_events=empty, sms_events=empty, order_blocks=empty,
                fair_value_gaps=empty, breaker_blocks=empty,
                liquidity_sweeps=empty, inducement_events=empty,
                qm_levels=empty, sr_flips=empty, rs_flips=empty,
                previous_levels=empty, mpl_levels=empty, fakeout_tests=empty,
                supply_zones=empty, demand_zones=empty,
                fibonacci_retracements=empty, dealing_ranges=empty,
            )

            deleted = await repo.delete_by_id(snapshot.id)
            assert deleted is True

            fetched = await repo.get_by_id(snapshot.id)
            assert fetched is None
