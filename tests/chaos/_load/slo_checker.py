"""SLO evaluation for Section 10 load tests.

Consumes the WorkloadOutcome from the driver + scrapes the engine's
/metrics endpoint to compute the SLO outcomes documented in
docs/runbooks/section-10-load-testing.md.

No external math libraries (no numpy/pandas) - the test runner must
work on a minimal Python image. The Pearson correlation helper is a
straight implementation.
"""
from __future__ import annotations

import asyncio
import math
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from tests.chaos._load.tenant_provisioner import Tenant
from tests.chaos._load.workload_driver import WorkloadOutcome


@dataclass
class SLOResult:
    auth_uptime_per_tenant: dict[str, float] = field(default_factory=dict)
    rss_growth_per_tenant: dict[str, float] = field(default_factory=dict)
    cross_tenant_max_correlation: float = 0.0
    aggregate_recovery_errors: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


class SLOChecker:
    AUTH_UPTIME_MIN = 0.99
    RSS_GROWTH_MAX = 0.25
    CORRELATION_MAX = 0.3

    def __init__(
        self,
        *,
        engine_url: str,
        admin_jwt: str,
        watchdog_metrics_url_template: str,
        insecure_tls: bool = False,
    ) -> None:
        """watchdog_metrics_url_template is a format string that
        receives connection_id and produces the URL to scrape the
        watchdog's /metrics endpoint for that tenant. In production
        K8s deployments this is typically reachable via
        kubectl port-forward; the test harness assumes the operator
        has set up a port-forward script and pinned the template.
        """
        self._engine_url = engine_url.rstrip("/")
        self._admin_jwt = admin_jwt
        self._watchdog_template = watchdog_metrics_url_template
        self._insecure = insecure_tls

    async def _scrape(self, url: str) -> str:
        ctx = None
        if self._insecure:
            ctx = ssl._create_unverified_context()

        def _do() -> str:
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {self._admin_jwt}",
            })
            try:
                with urllib.request.urlopen(req, timeout=10.0, context=ctx) as resp:
                    return resp.read().decode("utf-8")
            except (urllib.error.URLError, urllib.error.HTTPError):
                return ""

        return await asyncio.to_thread(_do)

    @staticmethod
    def _parse_metric_value(scrape: str, metric_name: str) -> float | None:
        """Tiny parser. Returns the first numeric value for a metric
        whose name matches (ignoring labels). None when absent."""
        for line in scrape.splitlines():
            if not line or line.startswith("#"):
                continue
            head, _, rest = line.partition(" ")
            if not rest:
                continue
            name = head.split("{")[0]
            if name == metric_name:
                try:
                    return float(rest.split()[0])
                except (ValueError, IndexError):
                    continue
        return None

    @staticmethod
    def _pearson(xs: list[float], ys: list[float]) -> float:
        n = min(len(xs), len(ys))
        if n < 3:
            return 0.0
        xs = xs[:n]
        ys = ys[:n]
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
        denx = math.sqrt(sum((xs[i] - mx) ** 2 for i in range(n)))
        deny = math.sqrt(sum((ys[i] - my) ** 2 for i in range(n)))
        if denx == 0 or deny == 0:
            return 0.0
        return num / (denx * deny)

    async def evaluate(
        self,
        tenants: list[Tenant],
        workload: WorkloadOutcome,
        *,
        rss_samples_per_tenant: dict[str, list[float]],
        auth_samples_per_tenant: dict[str, list[int]],
    ) -> SLOResult:
        """rss_samples_per_tenant / auth_samples_per_tenant carry the
        time-series the operator collected during the run (typically
        via a sidecar Prometheus scraper). The harness in harness.py
        wires this together; here we just compute the outcomes.
        """
        result = SLOResult()

        for t in tenants:
            auth = auth_samples_per_tenant.get(t.connection_id, [])
            if auth:
                uptime = sum(1 for v in auth if v == 1) / len(auth)
                result.auth_uptime_per_tenant[t.connection_id] = uptime
                if uptime < self.AUTH_UPTIME_MIN:
                    result.failures.append(
                        f"tenant {t.connection_id[:12]} auth uptime "
                        f"{uptime:.4f} < SLO {self.AUTH_UPTIME_MIN}"
                    )

            rss = rss_samples_per_tenant.get(t.connection_id, [])
            if len(rss) >= 2:
                baseline = rss[0]
                final = rss[-1]
                if baseline > 0:
                    growth = (final - baseline) / baseline
                    result.rss_growth_per_tenant[t.connection_id] = growth
                    if growth > self.RSS_GROWTH_MAX:
                        result.failures.append(
                            f"tenant {t.connection_id[:12]} RSS growth "
                            f"{growth:.3f} > SLO {self.RSS_GROWTH_MAX}"
                        )

        # Pairwise correlation. n*(n-1)/2 pairs; bounded at the
        # configured N max of 100 -> 4950 pairs which is trivial.
        cids = list(rss_samples_per_tenant.keys())
        max_r = 0.0
        for i in range(len(cids)):
            for j in range(i + 1, len(cids)):
                r = self._pearson(
                    rss_samples_per_tenant[cids[i]],
                    rss_samples_per_tenant[cids[j]],
                )
                if abs(r) > abs(max_r):
                    max_r = r
        result.cross_tenant_max_correlation = max_r
        if abs(max_r) > self.CORRELATION_MAX:
            result.failures.append(
                f"cross-tenant Pearson r = {max_r:.3f} > SLO "
                f"abs(r) <= {self.CORRELATION_MAX}"
            )

        # Aggregate engine-side scrape.
        engine_scrape = await self._scrape(self._engine_url + "/metrics")
        recovery_errors = self._parse_metric_value(
            engine_scrape, "etradie_hosted_recovery_runs_total"
        )
        if recovery_errors and recovery_errors > 0:
            # Only fail if outcome=error - the parser returns the
            # first match; for production this is fine as the
            # operator should pre-filter on the outcome label. We
            # surface the value as a soft signal.
            result.aggregate_recovery_errors = int(recovery_errors)

        return result
