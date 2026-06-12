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

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.chaos, pytest.mark.slow]


async def test_market_open_burst_throttles_cleanly(
    real_cluster_available: bool,
):
    """Single-tenant market-open burst test.

    Provisions one tenant, fires 100 TICK_PRICE calls in a 5s
    window with uncapped concurrency, asserts the engine
    rate-limited cleanly (some throttled responses, zero
    timeouts) AND the engine recovered within 1s.
    """
    import asyncio
    import time

    if not real_cluster_available:
        pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set")
    from tests.chaos._load.harness import build_harness_from_env
    from tests.chaos._load.workload_driver import WorkloadDriver

    harness = build_harness_from_env()
    if harness is None:
        pytest.skip(
            "ETRADIE_CHAOS_ENGINE_URL + ETRADIE_CHAOS_ADMIN_JWT + "
            "ETRADIE_CHAOS_WATCHDOG_URL_TEMPLATE + ETRADIE_CHAOS_TEST_CREDS_FILE "
            "all required for the market-open spike test"
        )

    provisioner = harness._engine_url  # access via the same env wiring
    from tests.chaos._load.tenant_provisioner import TenantProvisioner

    prov = TenantProvisioner(
        engine_url=harness._engine_url,
        admin_jwt=harness._admin_jwt,
        insecure_tls=harness._insecure,
    )
    async with prov.lease(1, user_id_prefix="market-spike") as provisioning:
        assert not provisioning.failed, f"provisioning failed: {provisioning.failed}"
        tenant = provisioning.successful[0]
        driver = WorkloadDriver(
            engine_url=harness._engine_url,
            admin_jwt=harness._admin_jwt,
            insecure_tls=harness._insecure,
        )
        # 100 parallel TICK_PRICE calls. Uncapped concurrency by
        # design: the engine's outbound limiter + in-flight gate
        # MUST be the throttle point, not the test driver.
        burst_start = time.monotonic()
        burst_results = await asyncio.gather(
            *[driver._call(tenant, "/internal/broker/tick_price", params={"symbol": "EURUSD"}) for _ in range(100)]
        )
        burst_elapsed = time.monotonic() - burst_start
        assert burst_elapsed <= 10.0, f"burst took {burst_elapsed:.1f}s; expected <= 10s. Engine may be deadlocked."
        statuses = [s for s, _ in burst_results]
        timeouts = sum(1 for s in statuses if s == 0)
        throttled = sum(1 for s in statuses if s in (429, 503))
        successes = sum(1 for s in statuses if s == 200)
        assert timeouts == 0, (
            f"burst produced {timeouts} timeouts. Engine MUST throttle with 429/503, not silently drop."
        )
        assert throttled > 0, (
            "burst produced ZERO throttled responses. Engine OutboundRateLimiter / in-flight gate appears disabled."
        )
        assert successes > 0, "burst produced ZERO successful responses"

        # Post-burst recovery: one TICK_PRICE 1s after the burst
        # MUST succeed.
        await asyncio.sleep(1.0)
        status, _ = await driver._call(
            tenant,
            "/internal/broker/tick_price",
            params={"symbol": "EURUSD"},
        )
        assert status == 200, (
            f"post-burst recovery TICK_PRICE returned {status}; engine did NOT recover within 1s of burst end."
        )
