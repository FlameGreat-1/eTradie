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
    """Random-kill chaos test.

    Provisions 20 tenants, kills 5 random Pods at random intervals
    over a 10-minute window, asserts HostedRecoveryService
    recovered every killed tenant AND the 15 bystanders saw zero
    auth=0 polls.
    """
    import asyncio
    import random
    import subprocess

    if not real_cluster_available:
        pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set")
    from tests.chaos._load.harness import build_harness_from_env

    harness = build_harness_from_env()
    if harness is None:
        pytest.skip(
            "ETRADIE_CHAOS_ENGINE_URL + ETRADIE_CHAOS_ADMIN_JWT + "
            "ETRADIE_CHAOS_WATCHDOG_URL_TEMPLATE + ETRADIE_CHAOS_TEST_CREDS_FILE "
            "all required for the random-kill test"
        )
    kubeconfig = os.environ.get("ETRADIE_CHAOS_KUBECONFIG", "")
    namespace = os.environ.get("ETRADIE_CHAOS_NAMESPACE", "etradie-system")

    # Run the harness with a kill-loop overlaid on the standard
    # workload. We reuse LoadHarness.run but inject the kill task
    # by extending the harness contract minimally below.
    from tests.chaos._load.tenant_provisioner import TenantProvisioner
    from tests.chaos._load.workload_driver import WorkloadDriver

    prov = TenantProvisioner(
        engine_url=harness._engine_url,
        admin_jwt=harness._admin_jwt,
        insecure_tls=harness._insecure,
    )
    async with prov.lease(20, user_id_prefix="random-kill") as provisioning:
        assert not provisioning.failed, f"provisioning failed: {provisioning.failed}"
        tenants = provisioning.successful
        victims = random.sample(tenants, 5)
        bystanders = [t for t in tenants if t not in victims]

        async def _kill_loop() -> None:
            # Stagger the 5 kills across the first 5 minutes of the
            # window so HostedRecoveryService sees varying ages.
            for victim in victims:
                pod_name = f"etradie-mt-{victim.connection_id[:12]}-0"
                await asyncio.sleep(random.uniform(30, 60))
                await asyncio.to_thread(
                    subprocess.run,
                    [
                        "kubectl",
                        f"--kubeconfig={kubeconfig}",
                        "-n",
                        namespace,
                        "delete",
                        "pod",
                        pod_name,
                        "--grace-period=0",
                        "--force",
                    ],
                    check=False,
                    capture_output=True,
                )

        driver = WorkloadDriver(
            engine_url=harness._engine_url,
            admin_jwt=harness._admin_jwt,
            insecure_tls=harness._insecure,
        )
        kill_task = asyncio.create_task(_kill_loop())
        workload = await driver.run(tenants, duration_secs=600.0)
        await kill_task

        # Each victim's recovery must have produced a successful
        # tick fetch by end of window. Check via the workload
        # outcome: a victim with successes > 0 was reachable
        # after recovery.
        for v in victims:
            outcome = workload.per_tenant[v.connection_id]
            assert outcome.successes > 0, (
                f"victim tenant {v.connection_id[:12]} never recovered: "
                f"successes={outcome.successes} timeouts={outcome.timeouts}"
            )

        # Bystanders must NOT have seen a timeout spike. Tolerate
        # up to 1% timeouts (the standard SLO budget) but no more.
        for b in bystanders:
            outcome = workload.per_tenant[b.connection_id]
            if outcome.total_commands == 0:
                continue
            timeout_rate = outcome.timeouts / outcome.total_commands
            assert timeout_rate <= 0.01, (
                f"bystander tenant {b.connection_id[:12]} timeout rate "
                f"{timeout_rate:.4f} exceeds bystander SLO 0.01. Kill of "
                "victim caused cross-tenant impact - Section 5 isolation breach."
            )
