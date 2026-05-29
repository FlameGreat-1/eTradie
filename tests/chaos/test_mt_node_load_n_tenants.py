"""Multi-tenant load tests at N in {10, 50, 100}.

This file is a SKELETON. The full implementation requires:
  - A real K8s cluster (ETRADIE_CHAOS_KUBECONFIG set).
  - An engine HTTP endpoint reachable from the test runner with an
    admin JWT (ETRADIE_CHAOS_ENGINE_URL + ETRADIE_CHAOS_ADMIN_JWT).
  - A load-generator harness that produces the workload mix the
    body comments describe.

What the implementation MUST verify (the CHECKLIST Section 10
contract):

  1. Provisioning at N tenants completes within a bounded SLO:
     N=10  -> 60s
     N=50  -> 180s
     N=100 -> 300s
     (per-tenant readiness gate is 300s; the test asserts the
     ACTUAL elapsed time is well below the worst-case so the
     system has headroom for production sign-up bursts.)

  2. Per-tenant authenticated state stays at >= 99% of polls
     during the soak window. The 1% budget covers the
     watchdog's brief socket-reset cadence on a freshly
     provisioned Pod.

  3. No cross-tenant isolation breach. A SINGLE tenant's metric
     anomaly (RSS spike, CPU soft-cap trip) MUST NOT correlate
     with another tenant's metrics. The test computes Pearson
     correlation across tenant RSS series and asserts |r| < 0.3
     for any pair - i.e. no tenant pair behaves as one workload
     under the hood.

  4. Aggregate engine metrics stay within steady-state bounds:
     etradie_active_user_connections{connection_type="hosted"}
     == N for the duration.
     etradie_hosted_recovery_runs_total{outcome="error"} == 0.
     etradie_broker_request_deadline_exceeded_total rate < 0.01/s.

  5. Tear-down at N tenants completes within bounded SLO:
     N=100 -> 600s (worst-case PVC reclaim + Pod deletion +
     Secret + Service cleanup).
"""
from __future__ import annotations

import os

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.chaos, pytest.mark.slow]


@pytest.mark.parametrize("n_tenants", [10, 50, 100])
async def test_mt_node_n_tenants_steady_state(
    real_cluster_available: bool,
    soak_duration: int,
    n_tenants: int,
):
    """SKELETON. Implementation deferred to the load-test MR."""
    if not real_cluster_available:
        pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set; load tests require a real cluster")
    engine_url = os.environ.get("ETRADIE_CHAOS_ENGINE_URL", "")
    admin_jwt = os.environ.get("ETRADIE_CHAOS_ADMIN_JWT", "")
    if not engine_url or not admin_jwt:
        pytest.skip(
            "ETRADIE_CHAOS_ENGINE_URL + ETRADIE_CHAOS_ADMIN_JWT both required "
            "for multi-tenant load tests"
        )
    pytest.skip(
        f"SKELETON: N={n_tenants} multi-tenant load test "
        "implementation deferred to the load-test follow-up MR"
    )
