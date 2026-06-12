"""Simulate broker disconnect and assert watchdog-driven recovery.

The scenario:
  1. The test calls into the EA via its ZMQ socket and sends a
     synthetic LOGOUT (handled by the EA: clears authenticated=false).
  2. The watchdog detects mt5_connected=false / authenticated=false
     for WATCHDOG_MAX_FAILURES consecutive probes.
  3. The watchdog signals MT5 to terminate. entrypoint.sh respawns.
  4. The new MT5 process auto-logins via startup.ini.
  5. The test asserts mt_node_ea_authenticated=1 again within the
     restart budget.

This test depends on a synthetic LOGOUT command. If your EA does not
implement one (the default eTradie EA does not - check
src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq5), the test substitutes
in a direct ZMQ-level disconnect via socket close.
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.chaos]


async def _scrape(host: str, port: int) -> dict[str, float]:
    from tests.chaos.test_mt_node_soak import _scrape_watchdog

    return await _scrape_watchdog(host, port)


async def test_broker_disconnect_recovery(real_cluster_available: bool):
    if not real_cluster_available:
        pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set")

    host = os.environ.get("ETRADIE_CHAOS_MT_NODE_HOST", "127.0.0.1")
    port = int(os.environ.get("ETRADIE_CHAOS_MT_NODE_WATCHDOG_PORT", "9100"))
    zmq_port = int(os.environ.get("ETRADIE_CHAOS_MT_NODE_ZMQ_PORT", "5555"))
    token = os.environ.get("ETRADIE_CHAOS_MT_NODE_TOKEN", "")
    if not token:
        pytest.skip("ETRADIE_CHAOS_MT_NODE_TOKEN not set")

    import zmq
    import zmq.asyncio as zmq_async

    ctx = zmq_async.Context.instance()
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.RCVTIMEO, 5000)
    sock.setsockopt(zmq.SNDTIMEO, 5000)
    sock.setsockopt(zmq.LINGER, 0)
    sock.connect(f"tcp://{host}:{zmq_port}")

    try:
        await sock.send_string(json.dumps({"command": "PING", "auth_token": token}))
        await sock.recv()  # authenticated

        # Force a session reset by abruptly closing the socket. The EA
        # will set authenticated=false on the next request. From the
        # watchdog's perspective: HEALTH starts returning authenticated=false.
        sock.close(linger=0)
    finally:
        try:
            sock.close(linger=0)
        except Exception:  # noqa: BLE001
            pass

    # Watchdog should issue an in-pod restart within MAX_FAILURES * POLL.
    # Defaults: 6 * 10 = 60s + 5s grace.
    deadline = asyncio.get_event_loop().time() + 120
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(5)
        m = await _scrape(host, port)
        if m.get("mt_node_watchdog_in_pod_restarts_total", 0) >= 1:
            break
    else:
        pytest.fail("watchdog did not in-pod restart after broker disconnect within 120s")

    # Now verify recovery: EA reauthenticates within the supervised restart budget.
    recovery_deadline = asyncio.get_event_loop().time() + 240
    while asyncio.get_event_loop().time() < recovery_deadline:
        await asyncio.sleep(5)
        m = await _scrape(host, port)
        if m.get("mt_node_ea_mt5_connected", 0) == 1.0 and m.get("mt_node_ea_authenticated", 0) == 1.0:
            return
    pytest.fail("EA did not recover authenticated state within 240s")
