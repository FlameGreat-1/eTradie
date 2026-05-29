#!/usr/bin/env python3
"""etradie-mt-node watchdog sidecar.

Runs alongside the MT5/MT4 terminal container inside a Pod. Polls
the Expert Advisor's HEALTH command over ZMQ on tcp://127.0.0.1:5555
and exposes:

  GET /healthz   -> 200 only when the most recent HEALTH probe within
                    the last 30s reported mt5_connected=true AND
                    authenticated=true. Else 503.
  GET /livez     -> 200 unless the watchdog itself is wedged (no
                    successful poll within LIVEZ_GRACE_SECONDS). Used
                    by the chart's livenessProbe to detect wedged
                    watchdog (kubelet then restarts the whole Pod).
  GET /metrics   -> Prometheus exposition.

In-pod restart action: after WATCHDOG_MAX_FAILURES consecutive HEALTH
failures OR when MT5 RSS exceeds WATCHDOG_MEMORY_SOFT_CAP_FRACTION of
the cgroup memory limit, the watchdog signals the MT5 process (via
psutil process tree walk) to terminate so entrypoint.sh respawns it
without taking down the whole Pod.

No runtime pip install: pyzmq, psutil, prometheus_client come from
the Dockerfile's apt layer.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

import psutil
import zmq
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)sZ [%(levelname)s] [watchdog] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("watchdog")

# ----- Config from envFrom (ConfigMap) ---------------------------------
POLL_INTERVAL = float(os.environ.get("WATCHDOG_POLL_INTERVAL_SECONDS", "10"))
MAX_FAILURES = int(os.environ.get("WATCHDOG_MAX_FAILURES", "6"))
MEMORY_SOFT_CAP_FRACTION = float(os.environ.get("WATCHDOG_MEMORY_SOFT_CAP_FRACTION", "0.8"))
LIVEZ_GRACE_SECONDS = float(os.environ.get("WATCHDOG_LIVEZ_GRACE_SECONDS", "60"))
ZMQ_ENDPOINT = os.environ.get("WATCHDOG_ZMQ_ENDPOINT", "tcp://127.0.0.1:5555")
HTTP_PORT = int(os.environ.get("WATCHDOG_HTTP_PORT", "9100"))
SYMBOL = os.environ.get("WATCHDOG_SYMBOL", "EURUSD")
AUTH_TOKEN = os.environ.get("MT_ZMQ_AUTH_TOKEN") or os.environ.get("DEFAULT_ZMQ_AUTH_TOKEN", "")

# ----- Prometheus metrics ---------------------------------------------
REG = CollectorRegistry()

M_MT5_CONNECTED = Gauge("mt_node_ea_mt5_connected", "EA reports terminal-to-broker connection state", registry=REG)
M_AUTHENTICATED = Gauge("mt_node_ea_authenticated", "EA authentication state", registry=REG)
M_EA_UPTIME = Gauge("mt_node_ea_uptime_seconds", "EA reported uptime", registry=REG)
M_EA_COMMANDS = Counter("mt_node_ea_commands_processed_total", "EA reported commands processed (counter snapshot)", registry=REG)
M_POLL_FAILS = Counter("mt_node_watchdog_poll_failures_total", "Cumulative HEALTH poll failures", registry=REG)
M_INPOD_RESTARTS = Counter("mt_node_watchdog_in_pod_restarts_total", "Cumulative MT5 process signals issued by watchdog", registry=REG)
M_MEMORY_SOFT_CAP_TRIPS = Counter("mt_node_watchdog_memory_soft_cap_trips_total", "Times memory soft-cap was tripped", registry=REG)
M_MT5_RSS = Gauge("mt_node_mt5_process_rss_bytes", "RSS of the terminal process tree", registry=REG)
M_MT5_CPU = Gauge("mt_node_mt5_process_cpu_percent", "CPU%% of the terminal process tree", registry=REG)
M_CGROUP_LIMIT = Gauge("mt_node_cgroup_memory_limit_bytes", "Cgroup memory limit", registry=REG)
M_CGROUP_USAGE = Gauge("mt_node_cgroup_memory_usage_bytes", "Cgroup memory current usage", registry=REG)

_last_commands_count = 0


# ----- Shared state for HTTP handlers ----------------------------------
class State:
    last_success_ts: float = 0.0
    last_health: dict = {}
    consecutive_failures: int = 0
    start_ts: float = time.time()
    lock = threading.Lock()


STATE = State()

# ----- Socket-resets counter (operator-visible) ------------------------
M_WATCHDOG_SOCKET_RESETS = Counter(
    "mt_node_watchdog_socket_resets_total",
    "Cumulative ZMQ REQ socket resets driven by the watchdog",
    registry=REG,
)


# ----- Long-lived ZMQ REQ socket --------------------------------------
class ZmqHealthProbe:
    """Owns the watchdog's REQ socket lifecycle.

    Holds ONE REQ socket for the watchdog process lifetime.
    Authentication via PING is performed once per (re)connect; the
    `authenticated` flag short-circuits subsequent HEALTH polls so
    the auth round-trip cost is paid once, not every cycle.

    The REQ/REP state machine is unrecoverable after a half-completed
    transaction (libzmq mandates alternating send/recv). On ANY
    zmq.ZMQError or zmq.Again the socket is torn down and recreated
    on the next poll; the next poll's PING re-authenticates. This is
    the only correct way to recover a wedged REQ socket - retrying
    on the same socket would raise EFSM.

    The socket is protected by a re-entrant lock because both the
    poll thread AND (potentially future) HTTP handlers might call
    poll(). Today only the poll thread does; the lock is a cheap
    invariant for safety.

    The context is process-wide (zmq.Context.instance()) so we do
    not churn io_threads on socket recreation. The instance() call
    is idempotent.
    """

    def __init__(
        self,
        endpoint: str,
        auth_token: str,
        recv_timeout_ms: int = 3000,
        send_timeout_ms: int = 3000,
    ) -> None:
        self._endpoint = endpoint
        self._auth_token = auth_token
        self._recv_timeout_ms = recv_timeout_ms
        self._send_timeout_ms = send_timeout_ms
        self._ctx = zmq.Context.instance()
        self._lock = threading.Lock()
        self._socket: Optional[zmq.Socket] = None
        self._authenticated: bool = False

    def _open(self) -> None:
        """Create a fresh REQ socket. Caller MUST hold self._lock."""
        sock = self._ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.LINGER, 0)
        sock.setsockopt(zmq.RCVTIMEO, self._recv_timeout_ms)
        sock.setsockopt(zmq.SNDTIMEO, self._send_timeout_ms)
        sock.connect(self._endpoint)
        self._socket = sock
        self._authenticated = False

    def _reset(self) -> None:
        """Tear down the current socket. Caller MUST hold self._lock.

        Increments the operator-visible reset counter so an alert
        rule can fire when a Pod's EA is flaky.
        """
        if self._socket is not None:
            try:
                self._socket.close(linger=0)
            except Exception:  # noqa: BLE001
                pass
            self._socket = None
        self._authenticated = False
        M_WATCHDOG_SOCKET_RESETS.inc()

    def _authenticate(self) -> None:
        """Run PING with auth_token. Caller MUST hold self._lock AND
        self._socket must be live."""
        assert self._socket is not None
        self._socket.send_string(
            json.dumps({"command": "PING", "auth_token": self._auth_token})
        )
        # Discard reply; if the EA rejects auth it will return an
        # error JSON which is fine - HEALTH will then also fail and
        # the consecutive_failures path will trigger an in-pod restart.
        self._socket.recv()
        self._authenticated = True

    def poll(self) -> dict:
        """One HEALTH probe. Returns the parsed reply dict.

        On ANY zmq error / timeout, tears the socket down and raises
        the underlying exception. The caller's existing
        consecutive_failures counter handles repeated failures.
        """
        with self._lock:
            try:
                if self._socket is None:
                    self._open()
                if not self._authenticated:
                    self._authenticate()
                self._socket.send_string(json.dumps({"command": "HEALTH"}))
                raw = self._socket.recv()
                return json.loads(raw.decode("utf-8"))
            except (zmq.ZMQError, zmq.Again):
                # REQ state machine is unrecoverable mid-transaction.
                # Tear down so the next poll opens a fresh socket.
                self._reset()
                raise
            except Exception:
                # JSON decode / network reset / etc. Same recovery
                # posture: a fresh socket on next poll.
                self._reset()
                raise

    def close(self) -> None:
        """Idempotent shutdown. Safe to call from signal handlers."""
        with self._lock:
            if self._socket is not None:
                try:
                    self._socket.close(linger=0)
                except Exception:  # noqa: BLE001
                    pass
                self._socket = None
            self._authenticated = False


# Constructed at first watchdog_loop() entry; module-level so the
# HTTP server and signal handler can reach it for graceful shutdown.
PROBE: Optional[ZmqHealthProbe] = None


# ----- Helpers ---------------------------------------------------------
def read_cgroup_limit() -> Optional[int]:
    """Return the cgroup-v2 / v1 memory limit in bytes, or None."""
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            with open(p, "r") as fh:
                val = fh.read().strip()
            if val == "max":
                return None
            return int(val)
        except (FileNotFoundError, ValueError, OSError):
            continue
    return None


def read_cgroup_usage() -> Optional[int]:
    for p in ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
        try:
            with open(p, "r") as fh:
                return int(fh.read().strip())
        except (FileNotFoundError, ValueError, OSError):
            continue
    return None


def find_mt_processes() -> list[psutil.Process]:
    """Return MT4/MT5 + wine helper processes in this PID namespace."""
    names = ("terminal64.exe", "terminal.exe")
    out: list[psutil.Process] = []
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            cmd = " ".join(proc.info.get("cmdline") or [])
            n = (proc.info.get("name") or "").lower()
            if any(t.lower() in n or t.lower() in cmd.lower() for t in names):
                out.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def terminate_mt_processes(reason: str) -> int:
    """Send SIGTERM to MT processes; entrypoint.sh's supervisor respawns.
    Returns number of processes signalled.
    """
    procs = find_mt_processes()
    n = 0
    for p in procs:
        try:
            log.warning("Signalling MT PID=%s (%s): %s", p.pid, p.name(), reason)
            p.terminate()
            n += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            log.warning("Could not terminate PID=%s: %s", p.pid, e)
    if n:
        M_INPOD_RESTARTS.inc(n)
    return n


# ----- ZMQ probing -----------------------------------------------------
# The free-function form of zmq_health_probe() has been replaced by
# the ZmqHealthProbe class above. The class holds a long-lived REQ
# socket and reuses it across polls; the per-poll cost drops from
# 'PING+HEALTH = 2 round trips' to 'HEALTH = 1 round trip' on the
# happy path. On any ZMQError the class tears down + recreates the
# socket on the next call (REQ state machine semantics).
#
# This wrapper preserves the existing call shape for backwards
# compatibility within this module (watchdog_loop calls it).
def zmq_health_probe() -> dict:
    global PROBE
    if PROBE is None:
        PROBE = ZmqHealthProbe(
            endpoint=ZMQ_ENDPOINT,
            auth_token=AUTH_TOKEN,
        )
    return PROBE.poll()


# ----- Watchdog loop ---------------------------------------------------
def record_process_metrics() -> tuple[int, float]:
    rss_total = 0
    cpu_total = 0.0
    for p in find_mt_processes():
        try:
            with p.oneshot():
                rss_total += p.memory_info().rss
                cpu_total += p.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    M_MT5_RSS.set(rss_total)
    M_MT5_CPU.set(cpu_total)
    return rss_total, cpu_total


def maybe_enforce_memory_soft_cap() -> bool:
    limit = read_cgroup_limit()
    usage = read_cgroup_usage()
    if limit is not None:
        M_CGROUP_LIMIT.set(limit)
    if usage is not None:
        M_CGROUP_USAGE.set(usage)
    if limit is None or usage is None or limit <= 0:
        return False
    fraction = usage / limit
    if fraction >= MEMORY_SOFT_CAP_FRACTION:
        log.error(
            "Memory soft-cap tripped: usage=%d limit=%d fraction=%.2f >= %.2f",
            usage, limit, fraction, MEMORY_SOFT_CAP_FRACTION,
        )
        M_MEMORY_SOFT_CAP_TRIPS.inc()
        terminate_mt_processes(
            f"memory soft-cap {fraction:.2f} >= {MEMORY_SOFT_CAP_FRACTION:.2f}"
        )
        return True
    return False


def watchdog_loop() -> None:
    global _last_commands_count
    log.info(
        "watchdog start: endpoint=%s poll=%.1fs max_failures=%d soft_cap=%.2f",
        ZMQ_ENDPOINT, POLL_INTERVAL, MAX_FAILURES, MEMORY_SOFT_CAP_FRACTION,
    )
    while True:
        try:
            record_process_metrics()
            tripped = maybe_enforce_memory_soft_cap()
            if tripped:
                # Give entrypoint.sh time to respawn before next probe
                time.sleep(POLL_INTERVAL)
                continue

            reply = zmq_health_probe()
            connected = bool(reply.get("mt5_connected"))
            authed = bool(reply.get("authenticated"))
            uptime = float(reply.get("uptime_seconds") or 0.0)
            commands = int(reply.get("commands_processed") or 0)

            M_MT5_CONNECTED.set(1 if connected else 0)
            M_AUTHENTICATED.set(1 if authed else 0)
            M_EA_UPTIME.set(uptime)
            # commands is a snapshot counter from the EA; convert to a
            # Prometheus counter by tracking deltas.
            if commands >= _last_commands_count:
                M_EA_COMMANDS.inc(commands - _last_commands_count)
            else:
                # EA restarted - counter reset.
                M_EA_COMMANDS.inc(commands)
            _last_commands_count = commands

            with STATE.lock:
                STATE.last_health = reply
                STATE.last_success_ts = time.time()
                if connected and authed:
                    STATE.consecutive_failures = 0
                else:
                    STATE.consecutive_failures += 1

            if STATE.consecutive_failures >= MAX_FAILURES:
                terminate_mt_processes(
                    f"EA semantic failure (connected={connected} authed={authed}) for "
                    f"{STATE.consecutive_failures} consecutive probes"
                )
                with STATE.lock:
                    STATE.consecutive_failures = 0

        except Exception as e:  # noqa: BLE001
            M_POLL_FAILS.inc()
            with STATE.lock:
                STATE.consecutive_failures += 1
            log.warning("poll failed: %s (consecutive=%d)", e, STATE.consecutive_failures)

            if STATE.consecutive_failures >= MAX_FAILURES:
                terminate_mt_processes(
                    f"HEALTH probe failures: {STATE.consecutive_failures} consecutive"
                )
                with STATE.lock:
                    STATE.consecutive_failures = 0

        time.sleep(POLL_INTERVAL)


# ----- HTTP server -----------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: A003
        # Silence default per-request stderr log; we already emit
        # structured logs from the watchdog loop.
        return

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/metrics":
            self._write(200, generate_latest(REG), CONTENT_TYPE_LATEST)
            return
        if self.path == "/livez":
            with STATE.lock:
                healthy = (time.time() - STATE.start_ts) < LIVEZ_GRACE_SECONDS or \
                          (time.time() - STATE.last_success_ts) < LIVEZ_GRACE_SECONDS
            self._write(200 if healthy else 503,
                        json.dumps({"status": "ok" if healthy else "wedged"}).encode("utf-8"),
                        "application/json")
            return
        if self.path == "/healthz":
            with STATE.lock:
                fresh = (time.time() - STATE.last_success_ts) < 30.0
                connected = bool(STATE.last_health.get("mt5_connected"))
                authed = bool(STATE.last_health.get("authenticated"))
            healthy = fresh and connected and authed
            body = json.dumps({
                "status": "ready" if healthy else "not_ready",
                "fresh": fresh,
                "mt5_connected": connected,
                "authenticated": authed,
            }).encode("utf-8")
            self._write(200 if healthy else 503, body, "application/json")
            return
        self._write(404, b"not found", "text/plain")


def serve_http() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    log.info("HTTP server listening on :%d (paths: /healthz /livez /metrics)", HTTP_PORT)
    server.serve_forever()


def main() -> int:
    if not AUTH_TOKEN:
        log.error("AUTH_TOKEN is empty - neither MT_ZMQ_AUTH_TOKEN nor DEFAULT_ZMQ_AUTH_TOKEN was set.")
        return 2

    t_http = threading.Thread(target=serve_http, daemon=True, name="http")
    t_http.start()

    def _term(signum, _frame):
        log.info("watchdog received signal %s, exiting", signum)
        # Close the long-lived REQ socket so the kernel reclaims the
        # fd immediately rather than waiting on linger=0 in __del__.
        global PROBE
        if PROBE is not None:
            try:
                PROBE.close()
            except Exception:  # noqa: BLE001
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)

    watchdog_loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
