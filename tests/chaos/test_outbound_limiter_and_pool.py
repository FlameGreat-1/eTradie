"""Section 5 (CHECKLIST) tests for OutboundRateLimiter and BrokerClientPool.

All tests are pure in-process (no broker, no DB, no Redis).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest

from engine.shared.exceptions import OutboundRateLimitExceededError
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
from engine.ta.broker.connectivity.outbound_limiter import OutboundRateLimiter
from engine.ta.broker.mt5.client_pool import BrokerClientPool
from engine.ta.constants import Timeframe
from engine.ta.models.candle import Candle, CandleSequence


# ---------------------------------------------------------------------
# OutboundRateLimiter
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_limiter_initial_burst_passes():
    lim = OutboundRateLimiter(provider="zmq", account_id="a", rate_per_second=1.0, burst_size=3)
    # 3 immediate acquisitions succeed (initial burst).
    for _ in range(3):
        assert await lim.try_acquire() is True
    # 4th immediately fails.
    assert await lim.try_acquire() is False


@pytest.mark.asyncio
async def test_limiter_blocks_until_refill_and_raises_on_deadline():
    lim = OutboundRateLimiter(provider="zmq", account_id="a", rate_per_second=100.0, burst_size=1)
    # Drain.
    assert await lim.try_acquire() is True
    # With deadline_secs=0.05 and rate 100/s, a refill is plenty fast.
    decision = await lim.acquire(deadline_secs=2.0)
    assert decision.allowed is True

    # With deadline_secs=0 (one-shot), exhaustion is reported immediately.
    # Drain again first.
    assert await lim.try_acquire() is True
    decision = await lim.acquire(deadline_secs=0)
    assert decision.allowed is False
    assert decision.reason == "exhausted"


@pytest.mark.asyncio
async def test_limiter_raise_if_exhausted():
    lim = OutboundRateLimiter(provider="zmq", account_id="a", rate_per_second=0.5, burst_size=1)
    await lim.try_acquire()  # drain
    with pytest.raises(OutboundRateLimitExceededError):
        await lim.raise_if_exhausted(deadline_secs=0)


@pytest.mark.asyncio
async def test_limiter_concurrent_one_token():
    """Two coroutines, one token left -> exactly one wins."""
    lim = OutboundRateLimiter(provider="zmq", account_id="a", rate_per_second=0.01, burst_size=1)

    results: list[bool] = []

    async def worker():
        results.append(await lim.try_acquire())

    await asyncio.gather(worker(), worker())
    assert sorted(results) == [False, True]


# ---------------------------------------------------------------------
# BrokerClientPool
# ---------------------------------------------------------------------
class _FakeBroker(BrokerBase):
    """Concrete BrokerBase used only to exercise BrokerClientPool wiring.

    The pool closes clients via a duck-typed ``close()`` and never calls
    any data/trading method, so those raise NotImplementedError. Every
    BrokerBase abstract member is implemented so the class is concrete
    and can be instantiated by the factory under test.
    """

    def __init__(self, tag: str) -> None:
        super().__init__(broker_id="fake")
        self.tag = tag
        self.closed = False

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def account_id(self) -> str:
        return self.tag

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
async def test_pool_dedupes_concurrent_first_touch():
    pool = BrokerClientPool(idle_timeout_secs=60.0, sweep_interval_secs=60.0)
    call_count = 0

    async def factory():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)  # yield
        return _FakeBroker("a")

    workers = [pool.get("zmq", "a", factory) for _ in range(50)]
    clients = await asyncio.gather(*workers)

    # Factory invoked exactly once; every caller gets the same instance.
    assert call_count == 1
    assert all(c is clients[0] for c in clients)
    assert pool.size() == 1
    await pool.stop()


@pytest.mark.asyncio
async def test_pool_evicts_idle_entries():
    pool = BrokerClientPool(idle_timeout_secs=0.05, sweep_interval_secs=0.02)

    async def factory():
        return _FakeBroker("a")

    client = await pool.get("zmq", "a", factory)
    assert pool.size() == 1

    await pool.start()
    await asyncio.sleep(0.15)
    assert pool.size() == 0
    assert client.closed is True
    await pool.stop()


@pytest.mark.asyncio
async def test_pool_explicit_evict_closes_client():
    pool = BrokerClientPool(idle_timeout_secs=60.0, sweep_interval_secs=60.0)

    async def factory():
        return _FakeBroker("a")

    client = await pool.get("zmq", "a", factory)
    assert await pool.evict("zmq", "a", reason="explicit") is True
    assert client.closed is True
    assert pool.size() == 0
    await pool.stop()


@pytest.mark.asyncio
async def test_pool_stop_closes_all():
    pool = BrokerClientPool(idle_timeout_secs=60.0, sweep_interval_secs=60.0)

    a = await pool.get("zmq", "a", lambda: _coro(_FakeBroker("a")))
    b = await pool.get("zmq", "b", lambda: _coro(_FakeBroker("b")))
    assert pool.size() == 2

    await pool.stop()
    assert a.closed is True
    assert b.closed is True
    assert pool.size() == 0

    # get() after stop refuses cleanly.
    with pytest.raises(RuntimeError):
        await pool.get("zmq", "c", lambda: _coro(_FakeBroker("c")))


async def _coro(x: Any) -> Any:
    return x
