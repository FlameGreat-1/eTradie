from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration

@pytest.fixture
async def client():
    with patch("engine.main.Container") as MC:
        c = MagicMock()
        c.mt5_client = MagicMock()
        c.cache = AsyncMock()
        c.cache.health_check = AsyncMock(return_value=True)
        c.cache.set = AsyncMock()
        c.db = AsyncMock()
        c.db.health_check = AsyncMock(return_value=True)
        c.scheduler = MagicMock()
        c.scheduler.start = MagicMock()
        c.shutdown = AsyncMock()
        MC.return_value = c
        from engine.main import create_app
        app = create_app()
        app.state.container = c
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

class TestHealth:
    @pytest.mark.asyncio
    async def test_returns_ok(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_is_json(self, client):
        r = await client.get("/health")
        assert r.headers["content-type"].startswith("application/json")
