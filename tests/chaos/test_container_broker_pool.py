"""Section 5 (CHECKLIST) test for the Container -> BrokerClientPool path.

Proves the per-key construction lock in BrokerClientPool actually
de-duplicates concurrent first-touches when invoked through the
pool API directly. Container.load_user_broker integration is exercised
the same way but requires DB plumbing; here we hit the pool directly.
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from engine.ta.broker.base import BrokerBase, BrokerCapabilities
from engine.ta.broker.mt5.client_pool import BrokerClientPool


class _StubBroker(BrokerBase):
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

    async def capabilities(self) -> BrokerCapabilities:  # type: ignore[override]
        return BrokerCapabilities()


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
