"""24-hour mt-node soak test (CI: 30 min; nightly: 24h; weekly: 72h).

Duration is controlled by SOAK_DURATION_SECONDS (default 1800).

The test runs against the watchdog sidecar's /metrics endpoint to
assert:
  - mt_node_ea_mt5_connected stays at 1.
  - mt_node_ea_authenticated stays at 1.
  - mt_node_mt5_process_rss_bytes does not grow more than 25% above
    the steady-state baseline (proxy for 'no memory leak').
  - mt_node_watchdog_in_pod_restarts_total stays at 0 (no semantic
    failure caused a restart).

Skips when ETRADIE_CHAOS_KUBECONFIG is not set so CI can run it
selectively. Provisions a real mt-node release via the chart's helm
template + kubectl apply on the supplied kubeconfig.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.chaos, pytest.mark.slow]


async def _scrape_watchdog(host: str, port: int) -> dict[str, float]:
    """Tiny parser that pulls Prometheus exposition into a flat dict."""
    import urllib.request

    raw = await asyncio.to_thread(
        lambda: urllib.request.urlopen(f"http://{host}:{port}/metrics", timeout=5).read().decode("utf-8"),
    )
    out: dict[str, float] = {}
    for line in raw.splitlines():
        if not line or line.startswith("#"):
            continue
        name, _, rest = line.partition(" ")
        if not rest:
            continue
        try:
            out[name.split("{")[0]] = float(rest.split()[0])
        except (ValueError, IndexError):
            continue
    return out


async def test_mt_node_24h_soak(real_cluster_available: bool, soak_duration: int):
    if not real_cluster_available:
        pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set")

    host = os.environ.get("ETRADIE_CHAOS_MT_NODE_HOST", "127.0.0.1")
    port = int(os.environ.get("ETRADIE_CHAOS_MT_NODE_WATCHDOG_PORT", "9100"))
    leak_ceiling = float(os.environ.get("ETRADIE_CHAOS_LEAK_CEILING_FRACTION", "0.25"))

    # Warm-up window before establishing the baseline.
    await asyncio.sleep(60)
    metrics = await _scrape_watchdog(host, port)
    baseline_rss = metrics.get("mt_node_mt5_process_rss_bytes", 0.0)
    assert baseline_rss > 0, "baseline RSS must be > 0 - is the EA up?"

    deadline = time.monotonic() + soak_duration
    last_check = time.monotonic()
    while time.monotonic() < deadline:
        await asyncio.sleep(min(60.0, deadline - time.monotonic()))
        m = await _scrape_watchdog(host, port)

        assert m.get("mt_node_ea_mt5_connected", 0) == 1.0, \
            f"EA disconnected at t={int(time.monotonic() - last_check)}s"
        assert m.get("mt_node_ea_authenticated", 0) == 1.0, \
            "EA unauthenticated mid-soak"
        assert m.get("mt_node_watchdog_in_pod_restarts_total", 0) == 0, \
            "watchdog had to in-pod restart MT5"

        rss = m.get("mt_node_mt5_process_rss_bytes", 0)
        growth = (rss - baseline_rss) / max(baseline_rss, 1)
        assert growth < leak_ceiling, \
            f"RSS grew {growth:.2%} from baseline ({baseline_rss:.0f}->{rss:.0f}); leak suspected"
