"""Workload driver for Section 10 load tests.

Given a list of provisioned tenants, drives the production-shaped
command mix for a configurable duration. Records per-tenant outcomes
for SLO evaluation.

The command mix matches the production tick rate documented in
docs/architecture/broker-connectivity.md:
  - TICK_PRICE   every 250ms  (240 cmds/min per tenant)
  - ACCOUNT_INFO every  5s    ( 12 cmds/min per tenant)
  - CANDLES H1   every 60s    (  1 cmd/min per tenant)

Each command is driven via the engine's /internal/broker/* path, NOT
the ZMQ socket directly, because the load test must exercise the
FULL engine -> ZmqClient -> EA round-trip plus every middleware
(in-flight gate, outbound rate limiter, request-deadline propagation).
"""

from __future__ import annotations

import asyncio
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from tests.chaos._load.tenant_provisioner import Tenant

_TICK_INTERVAL_SECS = 0.25
_ACCOUNT_INTERVAL_SECS = 5.0
_CANDLES_INTERVAL_SECS = 60.0
_REQUEST_TIMEOUT_SECS = 10.0


@dataclass
class TenantOutcome:
    user_id: str
    connection_id: str
    total_commands: int = 0
    successes: int = 0
    timeouts: int = 0
    throttled: int = 0
    other_errors: int = 0
    latency_samples_ms: list[float] = field(default_factory=list)


@dataclass
class WorkloadOutcome:
    duration_secs: float
    per_tenant: dict[str, TenantOutcome]  # keyed by connection_id


class WorkloadDriver:
    def __init__(
        self,
        *,
        engine_url: str,
        admin_jwt: str,
        insecure_tls: bool = False,
    ) -> None:
        self._engine_url = engine_url.rstrip("/")
        self._admin_jwt = admin_jwt
        self._insecure = insecure_tls

    async def _call(
        self,
        tenant: Tenant,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> tuple[int, float]:
        """Return (http_status, latency_ms). Never raises.

        The engine's /internal/broker/* endpoints take an X-User-Id
        header to resolve the per-user broker client. We use Bearer
        admin auth + the tenant's user_id.
        """
        url = self._engine_url + path
        if params:
            from urllib.parse import urlencode

            url = url + "?" + urlencode(params)
        headers = {
            "Authorization": f"Bearer {self._admin_jwt}",
            "X-User-Id": tenant.user_id,
        }
        req = urllib.request.Request(url, method="GET", headers=headers)
        ctx = None
        if self._insecure:
            ctx = ssl._create_unverified_context()

        def _do() -> tuple[int, float]:
            start = time.monotonic()
            try:
                with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECS, context=ctx) as resp:
                    resp.read()
                    return (resp.status, (time.monotonic() - start) * 1000.0)
            except urllib.error.HTTPError as exc:
                return (exc.code, (time.monotonic() - start) * 1000.0)
            except (urllib.error.URLError, TimeoutError):
                return (0, _REQUEST_TIMEOUT_SECS * 1000.0)

        return await asyncio.to_thread(_do)

    @staticmethod
    def _classify(status: int, outcome: TenantOutcome) -> None:
        outcome.total_commands += 1
        if status == 200:
            outcome.successes += 1
        elif status == 0:
            outcome.timeouts += 1
        elif status in (429, 503):
            outcome.throttled += 1
        else:
            outcome.other_errors += 1

    async def _drive_tenant(
        self,
        tenant: Tenant,
        outcome: TenantOutcome,
        stop_event: asyncio.Event,
    ) -> None:
        next_tick = time.monotonic()
        next_account = next_tick
        next_candles = next_tick
        while not stop_event.is_set():
            now = time.monotonic()
            tasks: list[asyncio.Task] = []
            if now >= next_tick:
                tasks.append(
                    asyncio.create_task(self._call(tenant, "/internal/broker/tick_price", params={"symbol": "EURUSD"}))
                )
                next_tick = now + _TICK_INTERVAL_SECS
            if now >= next_account:
                tasks.append(asyncio.create_task(self._call(tenant, "/internal/broker/account_info")))
                next_account = now + _ACCOUNT_INTERVAL_SECS
            if now >= next_candles:
                tasks.append(
                    asyncio.create_task(
                        self._call(
                            tenant,
                            "/internal/broker/candles",
                            params={"symbol": "EURUSD", "timeframe": "H1", "count": "100"},
                        )
                    )
                )
                next_candles = now + _CANDLES_INTERVAL_SECS
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=False)
                for status, latency_ms in results:
                    self._classify(status, outcome)
                    outcome.latency_samples_ms.append(latency_ms)
            # Sleep until the next due tick or the stop_event fires.
            wait_until = min(next_tick, next_account, next_candles)
            sleep_for = max(0.0, wait_until - time.monotonic())
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
                return  # stop_event was set
            except TimeoutError:
                pass  # next tick due

    async def run(
        self,
        tenants: list[Tenant],
        *,
        duration_secs: float,
    ) -> WorkloadOutcome:
        outcomes = {t.connection_id: TenantOutcome(t.user_id, t.connection_id) for t in tenants}
        stop_event = asyncio.Event()
        coros = [self._drive_tenant(t, outcomes[t.connection_id], stop_event) for t in tenants]
        start = time.monotonic()
        try:
            await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=False),
                timeout=duration_secs,
            )
        except TimeoutError:
            stop_event.set()
            # Give the per-tenant coroutines a moment to exit cleanly.
            await asyncio.gather(*coros, return_exceptions=True)
        return WorkloadOutcome(
            duration_secs=time.monotonic() - start,
            per_tenant=outcomes,
        )
