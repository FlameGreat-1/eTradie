"""Integration tests for /internal/broker/* FastAPI endpoints.

Uses a mock BrokerBase injected into the app Container to test the
full HTTP handler chain without requiring a real MetaApi/ZMQ connection.
Verifies response JSON shapes match what Go services expect.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Deterministic JWT for broker integration tests
_BROKER_TEST_JWT_SECRET = "test-secret-key-for-jwt-signing-must-be-long-enough-64chars-ok"


def _broker_test_jwt() -> str:
    now = int(time.time())
    payload = {
        "sub": "broker-test-user",
        "username": "brokertest",
        "role": "etradie",
        "iss": "etradie",
        "iat": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, _BROKER_TEST_JWT_SECRET, algorithm="HS256")


from engine.ta.broker.base import (
    AccountInfo,
    BrokerBase,
    BrokerCapabilities,
    HistoryDealInfo,
    OrderResult,
    PendingOrderInfo,
    PositionInfo,
    TickPrice,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Mock broker implementing all BrokerBase abstract methods
# ---------------------------------------------------------------------------


class MockBroker(BrokerBase):
    """In-memory mock broker for endpoint testing."""

    def __init__(self) -> None:
        super().__init__(broker_id="mock")
        self._balance = 10000.0
        self._positions: list[PositionInfo] = [
            PositionInfo(
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.1000,
                current_price=1.1050,
                stop_loss=1.0950,
                take_profit=1.1200,
                volume=0.10,
                profit=50.0,
                ticket="12345",
                comment="test-analysis",
                open_time=1700000000,
            ),
        ]
        self._orders: list[PendingOrderInfo] = [
            PendingOrderInfo(
                symbol="GBPUSD",
                order_type=2,
                price=1.2500,
                stop_loss=1.2450,
                take_profit=1.2600,
                volume=0.05,
                ticket="67890",
                comment="test-limit",
                open_time=1700001000,
            ),
        ]
        self._next_order_id = 99999

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def account_id(self) -> str:
        return "mock-account-0001"

    async def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities()

    async def get_all_symbol_names(self) -> list[str]:
        return ["EURUSD", "GBPUSD"]

    async def get_all_symbols(self) -> list[dict]:
        return [
            {"name": "EURUSD", "description": "Euro vs US Dollar", "path": "Forex\\Majors"},
            {"name": "GBPUSD", "description": "Great Britain Pound vs US Dollar", "path": "Forex\\Majors"},
        ]

    async def fetch_candles(self, symbol, timeframe, start_time=None, end_time=None, count=None):
        raise NotImplementedError

    async def fetch_latest_candle(self, symbol, timeframe):
        raise NotImplementedError

    async def get_symbol_info(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "description": f"{symbol} pair",
            "point": 0.00001,
            "digits": 5,
            "spread": 12,
            "trade_contract_size": 100000,
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01,
            "trade_tick_value": 10.0,
            "trade_tick_size": 0.00001,
        }

    async def validate_symbol(self, symbol: str) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    async def get_account_info(self) -> AccountInfo:
        return AccountInfo(
            balance=self._balance,
            equity=self._balance + 50.0,
            margin=100.0,
            free_margin=self._balance - 50.0,
            currency="USD",
        )

    async def get_positions(self) -> list[PositionInfo]:
        return list(self._positions)

    async def get_history(self, days: int = 30) -> list[HistoryDealInfo]:
        return [
            HistoryDealInfo(
                ticket="55501",
                position_id="12345",
                symbol="EURUSD",
                direction="BUY",
                volume=0.10,
                price=1.1000,
                profit=50.0,
                commission=-0.7,
                swap=0.0,
                time=1699990000,
                comment="closed-deal",
            ),
        ]

    async def get_pending_orders(self) -> list[PendingOrderInfo]:
        return list(self._orders)

    async def get_position(self, ticket: str) -> PositionInfo:
        for p in self._positions:
            if p.ticket == ticket:
                return p
        raise Exception(f"Position {ticket} not found")

    async def get_tick_price(self, symbol: str) -> TickPrice:
        return TickPrice(bid=1.1050, ask=1.1052, time=1700002000)

    async def place_order(
        self, *, symbol, direction, order_type, price, stop_loss, take_profit, lot_size, comment=""
    ) -> OrderResult:
        self._next_order_id += 1
        status = "FILLED" if order_type.upper() == "MARKET" else "PLACED"
        return OrderResult(order_id=self._next_order_id, price=price or 1.1050, status=status, error="")

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def modify_position(self, *, ticket, stop_loss, take_profit) -> bool:
        return True

    async def close_partial(self, *, ticket, volume) -> dict[str, Any]:
        return {"success": True, "close_price": 1.1055}

    async def close_position(self, ticket: str) -> dict[str, Any]:
        return {"success": True, "close_price": 1.1060}


# ---------------------------------------------------------------------------
# App fixture with mock broker injected
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_broker() -> MockBroker:
    return MockBroker()


@pytest_asyncio.fixture
async def client(mock_broker):
    """FastAPI test client with mock broker injected into Container."""
    import os

    env_overrides = {
        "AUTH_JWT_SECRET": _BROKER_TEST_JWT_SECRET,
        "AUTH_ISSUER": "etradie",
        "APP_ENV": "testing",
    }
    # Patch Container so it doesn't try to connect to real DB/Redis/broker
    with patch.dict(os.environ, env_overrides), patch("engine.main.Container") as MockContainer:
        container = MagicMock()
        container.mt5_client = mock_broker
        container.load_user_broker = AsyncMock(return_value=mock_broker)
        container.cache = AsyncMock()
        container.cache.health_check = AsyncMock(return_value=True)
        container.cache.set = AsyncMock()
        container.db = AsyncMock()
        container.db.health_check = AsyncMock(return_value=True)
        container.scheduler = MagicMock()
        container.scheduler.start = MagicMock()
        container.shutdown = AsyncMock()
        MockContainer.return_value = container

        from engine.main import create_app

        app = create_app()
        # Manually set container on app state (lifespan won't run in test)
        app.state.container = container

        auth_headers = {"Authorization": f"Bearer {_broker_test_jwt()}"}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as ac:
            yield ac


# ---------------------------------------------------------------------------
# Account info
# ---------------------------------------------------------------------------


class TestAccountInfo:
    @pytest.mark.asyncio
    async def test_returns_balance_fields(self, client):
        resp = await client.get("/internal/broker/account_info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["balance"] == 10000.0
        assert data["equity"] == 10050.0
        assert data["margin"] == 100.0
        assert data["margin_free"] == 9950.0
        assert data["currency"] == "USD"


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


class TestPositions:
    @pytest.mark.asyncio
    async def test_returns_position_list(self, client):
        resp = await client.get("/internal/broker/positions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        p = data[0]
        assert p["symbol"] == "EURUSD"
        assert p["type"] == 0  # BUY
        assert p["price_open"] == 1.1000
        assert p["price_current"] == 1.1050
        assert p["sl"] == 1.0950
        assert p["tp"] == 1.1200
        assert p["volume"] == 0.10
        assert p["profit"] == 50.0
        assert p["ticket"] == 12345
        assert p["comment"] == "test-analysis"


# ---------------------------------------------------------------------------
# Pending orders
# ---------------------------------------------------------------------------


class TestPendingOrders:
    @pytest.mark.asyncio
    async def test_returns_order_list(self, client):
        resp = await client.get("/internal/broker/pending_orders")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        o = data[0]
        assert o["symbol"] == "GBPUSD"
        assert o["type"] == 2  # BUY_LIMIT
        assert o["price_open"] == 1.2500
        assert o["ticket"] == 67890


# ---------------------------------------------------------------------------
# Symbol info
# ---------------------------------------------------------------------------


class TestSymbolInfo:
    @pytest.mark.asyncio
    async def test_returns_instrument_metadata(self, client):
        resp = await client.get("/internal/broker/symbol_info?symbol=EURUSD")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "EURUSD"
        assert data["digits"] == 5
        assert data["trade_contract_size"] == 100000
        assert data["trade_tick_value"] == 10.0
        assert data["trade_tick_size"] == 0.00001

    @pytest.mark.asyncio
    async def test_missing_symbol_returns_400(self, client):
        resp = await client.get("/internal/broker/symbol_info")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tick price
# ---------------------------------------------------------------------------


class TestTickPrice:
    @pytest.mark.asyncio
    async def test_returns_bid_ask(self, client):
        resp = await client.get("/internal/broker/tick_price?symbol=EURUSD")
        assert resp.status_code == 200
        data = resp.json()
        assert data["bid"] == 1.1050
        assert data["ask"] == 1.1052
        assert data["time"] == 1700002000

    @pytest.mark.asyncio
    async def test_missing_symbol_returns_400(self, client):
        resp = await client.get("/internal/broker/tick_price")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Single position
# ---------------------------------------------------------------------------


class TestPosition:
    @pytest.mark.asyncio
    async def test_returns_position_by_ticket(self, client):
        resp = await client.get("/internal/broker/position?ticket=12345")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "EURUSD"
        assert data["type"] == 0
        assert data["ticket"] == 12345

    @pytest.mark.asyncio
    async def test_missing_ticket_returns_400(self, client):
        resp = await client.get("/internal/broker/position")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Place order
# ---------------------------------------------------------------------------


class TestPlaceOrder:
    @pytest.mark.asyncio
    async def test_market_order(self, client):
        resp = await client.post(
            "/internal/broker/place_order",
            json={
                "symbol": "EURUSD",
                "direction": "BUY",
                "order_type": "MARKET",
                "price": 0,
                "stop_loss": 1.0950,
                "take_profit": 1.1200,
                "lot_size": 0.10,
                "comment": "test",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] > 0
        assert data["status"] == "FILLED"
        assert data["error"] == ""

    @pytest.mark.asyncio
    async def test_limit_order(self, client):
        resp = await client.post(
            "/internal/broker/place_order",
            json={
                "symbol": "GBPUSD",
                "direction": "SELL",
                "order_type": "LIMIT",
                "price": 1.2600,
                "stop_loss": 1.2650,
                "take_profit": 1.2500,
                "lot_size": 0.05,
                "comment": "test-limit",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "PLACED"

    @pytest.mark.asyncio
    async def test_missing_symbol_returns_400(self, client):
        resp = await client.post(
            "/internal/broker/place_order",
            json={
                "direction": "BUY",
                "order_type": "MARKET",
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Cancel order
# ---------------------------------------------------------------------------


class TestCancelOrder:
    @pytest.mark.asyncio
    async def test_cancel_success(self, client):
        resp = await client.post(
            "/internal/broker/cancel_order",
            json={
                "order_id": "67890",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["error"] == ""


# ---------------------------------------------------------------------------
# Modify position
# ---------------------------------------------------------------------------


class TestModifyPosition:
    @pytest.mark.asyncio
    async def test_modify_success(self, client):
        resp = await client.post(
            "/internal/broker/modify_position",
            json={
                "ticket": "12345",
                "stop_loss": 1.1000,
                "take_profit": 1.1300,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_missing_ticket_returns_400(self, client):
        resp = await client.post(
            "/internal/broker/modify_position",
            json={
                "stop_loss": 1.1000,
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Close partial
# ---------------------------------------------------------------------------


class TestClosePartial:
    @pytest.mark.asyncio
    async def test_partial_close_success(self, client):
        resp = await client.post(
            "/internal/broker/close_partial",
            json={
                "ticket": "12345",
                "volume": 0.05,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["close_price"] == 1.1055

    @pytest.mark.asyncio
    async def test_zero_volume_returns_400(self, client):
        resp = await client.post(
            "/internal/broker/close_partial",
            json={
                "ticket": "12345",
                "volume": 0,
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Close position
# ---------------------------------------------------------------------------


class TestClosePosition:
    @pytest.mark.asyncio
    async def test_close_success(self, client):
        resp = await client.post(
            "/internal/broker/close_position",
            json={
                "ticket": "12345",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["close_price"] == 1.1060

    @pytest.mark.asyncio
    async def test_missing_ticket_returns_400(self, client):
        resp = await client.post("/internal/broker/close_position", json={})
        assert resp.status_code == 400
