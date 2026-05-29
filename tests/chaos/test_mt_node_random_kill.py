"""Random-kill chaos test for HostedRecoveryService.

This file is a SKELETON. See test_mt_node_load_n_tenants.py for the
shared rationale.

What the implementation MUST verify (the CHECKLIST Section 5 + 8 +
Section 10 contracts):

  - With 20 hosted releases running, randomly kubectl-delete 5
    of them at random intervals during a 10-minute window.
  - HostedRecoveryService MUST re-provision every killed release.
    Total recovery time per killed release MUST be < (unhealthy_
    threshold + reprovision_cooldown + readiness_timeout). With
    default tuning: 600 + 300 + 300 = 1200s worst-case.
  - The surviving 15 releases MUST NOT see any disruption.
    mt_node_ea_authenticated stays at 1 for the entire window
    for those tenants.
  - HostedRecoveryReprovisionsHigh PrometheusRule MUST fire
    after the killing burst (the alert is calibrated for >1/h
    for 2h; the test verifies the metric increment but does NOT
    wait the 2h to verify the alert renders - that is a
    PrometheusRule unit test, not a chaos test).
"""
from __future__ import annotations

import os

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.chaos, pytest.mark.slow]


async def test_random_kill_recovers_within_slo(
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
        "SKELETON: random-kill chaos test implementation deferred to "
        "the load-test follow-up MR"
    )
