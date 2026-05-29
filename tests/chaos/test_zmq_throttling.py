"""Section 5 (CHECKLIST) chaos tests for ZmqClient throttling primitives.

These tests exercise the OutboundRateLimiter + in-flight gate +
request-deadline propagation at the ZmqClient._request boundary by
stubbing _send_recv_async. No ZMQ socket, no broker, no DB.
"""
from __future__ import annotations

import asyncio
import time as _time
from typing import Any

import pytest

from engine.shared.exceptions import (
    OutboundRateLimitExceededError,
    ProviderTimeoutError,
)
from engine.ta.broker.connectivity.outbound_limiter import OutboundRateLimiter
from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.zmq.client import ZmqClient


def _make_client(
    *,
    rate: float = 5.0,
    burst: int = 5,
    inflight: int = 2,
    outbound_limit_deadline_secs: float = 0.0,
) -> ZmqClient:
    config = MT5Config.model_construct(
        enabled=True,
        provider="native",
        metaapi_token="",
        metaapi_account_id="",
        metaapi_base_url="",
        zmq_host="127.0.0.1",
        zmq_port=5555,
        zmq_auth_token="t",
        terminal_path=None,
        account=0,
        password="",
        server="",
        timeout_seconds=5,
        max_retries=0,
        retry_delay_seconds=0,
        connection_timeout_seconds=5,
        max_candles_per_request=1000,
        enable_tick_data=False,
        magic_number=0,
    )
    return ZmqClient(
        config=config,
        auth_token="t",
        outbound_limiter=OutboundRateLimiter(
            provider="zmq-test",
            account_id="acct",
            rate_per_second=rate,
            burst_size=burst,
        ),
        inflight_limit=inflight,
        outbound_limit_deadline_secs=outbound_limit_deadline_secs,
    )


@pytest.mark.asyncio
async def test_outbound_limiter_rejects_after_burst_exhausted():
    """Burst exhausted with deadline=0 -> OutboundRateLimitExceededError."""
    client = _make_client(rate=1.0, burst=3, outbound_limit_deadline_secs=0.0)

    # Stub the actual ZMQ I/O so _request_inner is a no-op.
    async def fake_inner(req: dict[str, Any], *, request_deadline_secs=None):
        return {"ok": True}

    client._request_inner = fake_inner  # type: ignore[assignment]
    # Mark the client as 'initialised' so _request_inner is not called via
    # the normal connect path. _request itself owns the gating logic.
    client._initialized = True

    # First 3 calls fit the burst.
    for _ in range(3):
        out = await client._request({"command": "PING"})
        assert out == {"ok": True}

    # 4th raises - bucket empty + deadline_secs=0.
    with pytest.raises(OutboundRateLimitExceededError):
        await client._request({"command": "PING"})


@pytest.mark.asyncio
async def test_inflight_gate_serialises_concurrent_calls():
    """With inflight_limit=2 and a 100ms stub, 10 concurrent calls
    take at least 0.5s wall time and never exceed 2 in flight."""
    client = _make_client(rate=10000.0, burst=10000, inflight=2)

    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    async def fake_inner(req: dict[str, Any], *, request_deadline_secs=None):
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        try:
            await asyncio.sleep(0.1)
            return {"ok": True}
        finally:
            async with lock:
                in_flight -= 1

    client._request_inner = fake_inner  # type: ignore[assignment]
    client._initialized = True

    start = _time.monotonic()
    await asyncio.gather(*[client._request({"command": "PING"}) for _ in range(10)])
    elapsed = _time.monotonic() - start

    assert peak <= 2, f"in-flight gate breached: peak={peak}"
    assert elapsed >= 0.4, f"gate did not serialise; elapsed={elapsed:.3f}s"


@pytest.mark.asyncio
async def test_inflight_gate_rejects_when_deadline_elapses():
    """With inflight_limit=1, a slow first call + short deadline on the
    second call surfaces ProviderTimeoutError."""
    client = _make_client(rate=10000.0, burst=10000, inflight=1)

    async def slow_inner(req: dict[str, Any], *, request_deadline_secs=None):
        await asyncio.sleep(0.5)
        return {"ok": True}

    client._request_inner = slow_inner  # type: ignore[assignment]
    client._initialized = True

    async def fast_caller():
        # Tiny deadline: bounce off the gate before the slow caller releases.
        return await client._request(
            {"command": "PING"}, request_deadline_secs=0.05
        )

    slow = asyncio.create_task(client._request({"command": "PING"}))
    # Give the slow caller time to acquire the gate.
    await asyncio.sleep(0.01)
    with pytest.raises(ProviderTimeoutError):
        await fast_caller()

    # Let the slow caller finish so it does not leak.
    await slow
