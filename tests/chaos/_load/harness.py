"""Top-level orchestrator for Section 10 load tests.

Public API: LoadHarness.run(n_tenants, duration_secs). Used by every
test in tests/chaos/test_mt_node_*.py.

The harness wires the four components in tests/chaos/_load/:
  - TenantProvisioner: provisions N tenants (lease() context manager).
  - WorkloadDriver: drives the production-shaped command mix.
  - MetricsCollector (inline below): scrapes watchdog /metrics every
    10s during the workload and records the RSS + auth time-series.
  - SLOChecker: evaluates the time-series against the runbook SLOs.
"""

from __future__ import annotations

import asyncio
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from tests.chaos._load.slo_checker import SLOChecker, SLOResult
from tests.chaos._load.tenant_provisioner import (
    ProvisioningOutcome,
    Tenant,
    TenantProvisioner,
)
from tests.chaos._load.workload_driver import (
    WorkloadDriver,
    WorkloadOutcome,
)

_METRICS_SCRAPE_INTERVAL_SECS = 10.0


@dataclass
class HarnessResult:
    provisioning: ProvisioningOutcome
    workload: WorkloadOutcome
    slo: SLOResult


async def _scrape_watchdog(url: str, jwt: str, insecure: bool) -> dict[str, float]:
    ctx = None
    if insecure:
        ctx = ssl._create_unverified_context()

    def _do() -> str:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {jwt}"})
        try:
            with urllib.request.urlopen(req, timeout=5.0, context=ctx) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError):
            return ""

    raw = await asyncio.to_thread(_do)
    out: dict[str, float] = {}
    for line in raw.splitlines():
        if not line or line.startswith("#"):
            continue
        head, _, rest = line.partition(" ")
        if not rest:
            continue
        name = head.split("{")[0]
        try:
            out[name] = float(rest.split()[0])
        except (ValueError, IndexError):
            continue
    return out


class LoadHarness:
    def __init__(
        self,
        *,
        engine_url: str,
        admin_jwt: str,
        watchdog_metrics_url_template: str,
        insecure_tls: bool = False,
    ) -> None:
        self._engine_url = engine_url
        self._admin_jwt = admin_jwt
        self._watchdog_template = watchdog_metrics_url_template
        self._insecure = insecure_tls

    async def _collect_metrics(
        self,
        tenants: list[Tenant],
        stop_event: asyncio.Event,
    ) -> tuple[dict[str, list[float]], dict[str, list[int]]]:
        rss: dict[str, list[float]] = {t.connection_id: [] for t in tenants}
        auth: dict[str, list[int]] = {t.connection_id: [] for t in tenants}
        while not stop_event.is_set():
            tick_start = time.monotonic()
            scrape_coros = [
                _scrape_watchdog(
                    self._watchdog_template.format(connection_id=t.connection_id),
                    self._admin_jwt,
                    self._insecure,
                )
                for t in tenants
            ]
            scrapes = await asyncio.gather(*scrape_coros, return_exceptions=False)
            for t, scrape in zip(tenants, scrapes):
                rss[t.connection_id].append(scrape.get("mt_node_mt5_process_rss_bytes", 0.0))
                auth[t.connection_id].append(int(scrape.get("mt_node_ea_authenticated", 0.0)))
            elapsed = time.monotonic() - tick_start
            sleep_for = max(0.0, _METRICS_SCRAPE_INTERVAL_SECS - elapsed)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
                return rss, auth
            except TimeoutError:
                continue
        return rss, auth

    async def run(
        self,
        n_tenants: int,
        duration_secs: float,
    ) -> HarnessResult:
        provisioner = TenantProvisioner(
            engine_url=self._engine_url,
            admin_jwt=self._admin_jwt,
            insecure_tls=self._insecure,
        )
        driver = WorkloadDriver(
            engine_url=self._engine_url,
            admin_jwt=self._admin_jwt,
            insecure_tls=self._insecure,
        )
        checker = SLOChecker(
            engine_url=self._engine_url,
            admin_jwt=self._admin_jwt,
            watchdog_metrics_url_template=self._watchdog_template,
            insecure_tls=self._insecure,
        )
        async with provisioner.lease(n_tenants) as provisioning:
            if provisioning.failed:
                # Provisioning errors short-circuit the test; the SLO
                # evaluation is not meaningful with a partial fleet.
                return HarnessResult(
                    provisioning=provisioning,
                    workload=WorkloadOutcome(duration_secs=0.0, per_tenant={}),
                    slo=SLOResult(
                        failures=[
                            f"provisioning failed for {len(provisioning.failed)} tenants: "
                            + "; ".join(f"{login}: {err[:80]}" for login, err in provisioning.failed[:5])
                        ]
                    ),
                )
            tenants = provisioning.successful
            stop_event = asyncio.Event()
            collector_task = asyncio.create_task(self._collect_metrics(tenants, stop_event))
            workload = await driver.run(tenants, duration_secs=duration_secs)
            stop_event.set()
            rss_samples, auth_samples = await collector_task
            slo = await checker.evaluate(
                tenants,
                workload,
                rss_samples_per_tenant=rss_samples,
                auth_samples_per_tenant=auth_samples,
            )
            return HarnessResult(
                provisioning=provisioning,
                workload=workload,
                slo=slo,
            )


def build_harness_from_env() -> LoadHarness | None:
    """Returns None when the required env vars are not all set so
    tests can pytest.skip cleanly."""
    engine_url = os.environ.get("ETRADIE_CHAOS_ENGINE_URL", "").strip()
    admin_jwt = os.environ.get("ETRADIE_CHAOS_ADMIN_JWT", "").strip()
    watchdog_template = os.environ.get("ETRADIE_CHAOS_WATCHDOG_URL_TEMPLATE", "").strip()
    creds_file = os.environ.get("ETRADIE_CHAOS_TEST_CREDS_FILE", "").strip()
    if not (engine_url and admin_jwt and watchdog_template and creds_file):
        return None
    insecure = os.environ.get("ETRADIE_CHAOS_INSECURE_TLS", "false").strip().lower() in ("1", "true", "yes")
    return LoadHarness(
        engine_url=engine_url,
        admin_jwt=admin_jwt,
        watchdog_metrics_url_template=watchdog_template,
        insecure_tls=insecure,
    )
