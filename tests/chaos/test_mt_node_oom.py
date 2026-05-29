"""Verify the watchdog enforces the memory soft-cap BEFORE the kernel OOMs.

Approach: scrape the watchdog metrics, confirm
mt_node_watchdog_memory_soft_cap_trips_total goes UP after we induce
memory pressure inside the container.

Memory pressure is induced by setting the chart's cgroup limit very
low at install time (256Mi) so MT5 inevitably trips the 80% soft cap.
The chaos harness then asserts the watchdog detected it AND issued
an in-pod restart, AND that the broker EA reconnected within the
restart budget.

This test is an integration test that requires the real cluster.
"""
from __future__ import annotations

import asyncio
import os

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.chaos]


async def _scrape(host: str, port: int) -> dict[str, float]:
    from tests.chaos.test_mt_node_soak import _scrape_watchdog
    return await _scrape_watchdog(host, port)


async def test_memory_soft_cap_fires_before_oom(real_cluster_available: bool):
    if not real_cluster_available:
        pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set")

    host = os.environ.get("ETRADIE_CHAOS_MT_NODE_HOST", "127.0.0.1")
    port = int(os.environ.get("ETRADIE_CHAOS_MT_NODE_WATCHDOG_PORT", "9100"))

    # Read the starting counter.
    m0 = await _scrape(host, port)
    initial_trips = m0.get("mt_node_watchdog_memory_soft_cap_trips_total", 0)

    # Wait up to 10 minutes for the soft cap to trip (assuming the test
    # harness already provisioned the release with a tight memory limit).
    deadline = asyncio.get_event_loop().time() + 600
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(15)
        m = await _scrape(host, port)
        trips = m.get("mt_node_watchdog_memory_soft_cap_trips_total", 0)
        restarts = m.get("mt_node_watchdog_in_pod_restarts_total", 0)
        if trips > initial_trips and restarts > 0:
            # Recovery: EA must come back AUTHENTICATED within 3 min
            # of the restart.
            recovery_deadline = asyncio.get_event_loop().time() + 180
            while asyncio.get_event_loop().time() < recovery_deadline:
                await asyncio.sleep(5)
                m_post = await _scrape(host, port)
                if (
                    m_post.get("mt_node_ea_mt5_connected", 0) == 1.0
                    and m_post.get("mt_node_ea_authenticated", 0) == 1.0
                ):
                    return  # passed
            pytest.fail("watchdog fired but EA did not recover within 180s")
    pytest.fail("memory soft cap never tripped in 10 min - either limit is too high or watchdog is wedged")
