"""Section 5 (CHECKLIST) tests for OutboundRateLimiter and BrokerClientPool.

All tests are pure in-process (no broker, no DB, no Redis).
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from engine.shared.exceptions import OutboundRateLimitExceededError
from engine.ta.broker.base import BrokerBase, BrokerCapabilities
from engine.ta.broker.connectivity.outbound_limiter import OutboundRateLimiter
from engine.ta.broker.mt5.client_pool import BrokerClientPool


# ---------------------------------------------------------------------
# OutboundRateLimiter
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_limiter_initial_burst_passes():
    lim = OutboundRateLimiter(
        provider="zmq", account_id="a", rate_per_second=1.0, burst_size=3
    )
    # 3 immediate acquisitions succeed (initial burst).
    for _ in range(3):
        assert await lim.try_acquire() is True
    # 4th immediately fails.
    assert await lim.try_acquire() is False


@pytest.mark.asyncio
async def test_limiter_blocks_until_refill_and_raises_on_deadline():
    lim = OutboundRateLimiter(
        provider="zmq", account_id="a", rate_per_second=100.0, burst_size=1
    )
    # Drain.
    assert await lim.try_acquire() is True
    # With deadline_secs=0.05 and rate 100/s, a refill is plenty fast.
    decision = await lim.acquire(deadline_secs=0.5)
    assert decision.allowed is True

    # With deadline_secs=0 (one-shot), exhaustion is reported immediately.
    # Drain again first.
    assert await lim.try_acquire() is True
    decision = await lim.acquire(deadline_secs=0)
    assert decision.allowed is False
    assert decision.reason == "exhausted"


@pytest.mark.asyncio
async def test_limiter_raise_if_exhausted():
    lim = OutboundRateLimiter(
        provider="zmq", account_id="a", rate_per_second=0.5, burst_size=1
    )
    await lim.try_acquire()  # drain
    with pytest.raises(OutboundRateLimitExceededError):
        await lim.raise_if_exhausted(deadline_secs=0)


@pytest.mark.asyncio
async def test_limiter_concurrent_one_token():
    """Two coroutines, one token left -> exactly one wins."""
    lim = OutboundRateLimiter(
        provider="zmq", account_id="a", rate_per_second=0.01, burst_size=1
    )

    results: list[bool] = []

    async def worker():
        results.append(await lim.try_acquire())

    await asyncio.gather(worker(), worker())
    assert sorted(results) == [False, True]


# ---------------------------------------------------------------------
# BrokerClientPool
# ---------------------------------------------------------------------
class _FakeBroker(BrokerBase):
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

    # The remaining BrokerBase abstract methods are not exercised here.
    async def capabilities(self) -> BrokerCapabilities:  # type: ignore[override]
        return BrokerCapabilities()


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
