"""Integration tests for DatabaseManager against real PostgreSQL."""

import pytest

from tests.integration.conftest import skip_no_db

pytestmark = [pytest.mark.integration, skip_no_db]


@pytest.mark.asyncio
async def test_health_check_passes(db_manager):
    """DatabaseManager.health_check() returns True with live PostgreSQL."""
    result = await db_manager.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_session_executes_query(db_manager):
    """Write session can execute a simple query."""
    from sqlalchemy import text

    async with db_manager.session() as session:
        result = await session.execute(text("SELECT 1 AS val"))
        row = result.one()
        assert row.val == 1


@pytest.mark.asyncio
async def test_read_session_executes_query(db_manager):
    """Read session can execute SELECT queries."""
    from sqlalchemy import text

    async with db_manager.read_session() as session:
        result = await session.execute(text("SELECT current_database() AS db"))
        row = result.one()
        assert row.db is not None
        assert len(row.db) > 0


@pytest.mark.asyncio
async def test_session_rollback_on_error(db_manager):
    """Session rolls back on exception."""
    from sqlalchemy import text

    try:
        async with db_manager.session() as session:
            await session.execute(text("SELECT 1"))
            raise ValueError("Intentional test error")
    except ValueError:
        pass  # Expected

    # Verify the connection is still usable after rollback.
    async with db_manager.read_session() as session:
        result = await session.execute(text("SELECT 1 AS val"))
        assert result.one().val == 1


@pytest.mark.asyncio
async def test_pool_metrics_update(db_manager):
    """Pool metrics update without error."""
    db_manager.update_pool_metrics()
    # No assertion needed - just verify it doesn't raise.
