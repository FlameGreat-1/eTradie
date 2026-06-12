"""Section 5 (CHECKLIST) test for the Container -> BrokerClientPool path.

Proves the per-key construction lock in BrokerClientPool actually
de-duplicates concurrent first-touches when invoked through the
pool API directly. Container.load_user_broker integration is exercised
the same way but requires DB plumbing; here we hit the pool directly.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest

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
from engine.ta.broker.mt5.client_pool import BrokerClientPool
from engine.ta.constants import Timeframe
from engine.ta.models.candle import Candle, CandleSequence


class _StubBroker(BrokerBase):
    """Concrete BrokerBase used only to exercise BrokerClientPool wiring.

    The pool closes clients via a duck-typed ``close()`` and never calls
    any data/trading method, so those raise NotImplementedError. Every
    BrokerBase abstract member is implemented so the class is concrete
    and can be instantiated by the factory under test.
    """

    def __init__(self) -> None:
        super().__init__(broker_id="stub")
        self.closed = False

    @property
    def provider_name(self) -> str:
        return "stub"

    @property
    def account_id(self) -> str:
        return "acct"

    async def close(self) -> None:
        self.closed = True

    async def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities()

    async def get_all_symbol_names(self) -> list[str]:
        raise NotImplementedError

    async def get_all_symbols(self) -> list[dict]:
        raise NotImplementedError

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        count: int | None = None,
    ) -> CandleSequence:
        raise NotImplementedError

    async def fetch_latest_candle(self, symbol: str, timeframe: Timeframe) -> Candle:
        raise NotImplementedError

    async def get_symbol_info(self, symbol: str) -> dict:
        raise NotImplementedError

    async def validate_symbol(self, symbol: str) -> bool:
        raise NotImplementedError

    async def health_check(self) -> bool:
        raise NotImplementedError

    async def get_account_info(self) -> AccountInfo:
        raise NotImplementedError

    async def get_positions(self) -> list[PositionInfo]:
        raise NotImplementedError

    async def get_history(self, days: int = 30) -> list[HistoryDealInfo]:
        raise NotImplementedError

    async def get_pending_orders(self) -> list[PendingOrderInfo]:
        raise NotImplementedError

    async def get_position(self, ticket: str) -> PositionInfo:
        raise NotImplementedError

    async def get_tick_price(self, symbol: str) -> TickPrice:
        raise NotImplementedError

    async def place_order(
        self,
        *,
        symbol: str,
        direction: str,
        order_type: str,
        price: float,
        stop_loss: float,
        take_profit: float,
        lot_size: float,
        comment: str = "",
    ) -> OrderResult:
        raise NotImplementedError

    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    async def modify_position(self, *, ticket: str, stop_loss: float, take_profit: float) -> bool:
        raise NotImplementedError

    async def close_partial(self, *, ticket: str, volume: float) -> dict[str, Any]:
        raise NotImplementedError

    async def close_position(self, ticket: str) -> dict[str, Any]:
        raise NotImplementedError

    async def shutdown(self) -> None:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_pool_collapses_concurrent_first_touch():
    pool = BrokerClientPool(idle_timeout_secs=60.0, sweep_interval_secs=60.0)

    calls = 0

    async def factory():
        nonlocal calls
        calls += 1
        # Force a yield so concurrent callers actually race.
        await asyncio.sleep(0)
        return _StubBroker()

    workers = [pool.get("zmq-ea", "127.0.0.1:5555", factory) for _ in range(50)]
    clients = await asyncio.gather(*workers)

    assert calls == 1
    assert all(c is clients[0] for c in clients)
    assert pool.size() == 1

    await pool.stop()
    assert clients[0].closed is True


@pytest.mark.asyncio
async def test_pool_evict_closes_client():
    pool = BrokerClientPool(idle_timeout_secs=60.0, sweep_interval_secs=60.0)

    async def factory():
        return _StubBroker()

    client = await pool.get("zmq-ea", "127.0.0.1:5555", factory)
    assert pool.size() == 1
    assert await pool.evict("zmq-ea", "127.0.0.1:5555", reason="explicit") is True
    assert client.closed is True
    assert pool.size() == 0
    await pool.stop()
