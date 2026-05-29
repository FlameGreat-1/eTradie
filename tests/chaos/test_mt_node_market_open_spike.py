"""Single-tenant burst test simulating market-open behaviour.

This file is a SKELETON. See test_mt_node_load_n_tenants.py for the
shared rationale.

What the implementation MUST verify (the CHECKLIST Section 5 +
Section 10 contracts):

  - At market open, a real user's strategy can fire 100+
    TICK_PRICE + ORDER_SEND commands within a 5-second window.
    The OutboundRateLimiter (token bucket; default 10/s rate,
    20 burst) MUST throttle excess commands and the in-flight
    gate (default 4 concurrent on the trading socket) MUST reject
    backlog with HTTP 429.

  - Throttled commands MUST NOT silently disappear. Each
    rejection MUST surface as ProviderTimeoutError (with the
    'in-flight gate exhausted before deadline' detail) OR
    OutboundRateLimitExceededError. The caller can then decide
    whether to retry; the engine MUST NOT execute a half-completed
    trade.

  - No deadlock under sustained burst: after the 5-second window,
    the per-tenant ZmqClient MUST be able to process new
    commands at the configured rate WITHIN 1 second of the
    burst ending. Asserted by sending one TICK_PRICE 1s after
    the burst and expecting a success within the standard
    timeout.
"""
from __future__ import annotations

import os

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.chaos, pytest.mark.slow]


async def test_market_open_burst_throttles_cleanly(
    real_cluster_available: bool,
):
    """SKELETON. Implementation deferred to the load-test MR."""
    if not real_cluster_available:
        pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set")
    engine_url = os.environ.get("ETRADIE_CHAOS_ENGINE_URL", "")
    admin_jwt = os.environ.get("ETRADIE_CHAOS_ADMIN_JWT", "")
    if not engine_url or not admin_jwt:
        pytest.skip("ETRADIE_CHAOS_ENGINE_URL + ETRADIE_CHAOS_ADMIN_JWT required")
    pytest.skip(
        "SKELETON: market-open spike test implementation deferred to "
        "the load-test follow-up MR"
    )
