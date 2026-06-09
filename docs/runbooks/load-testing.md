# Section 10 load-testing runbook

Operator procedure for the multi-tenant load tests that satisfy
CHECKLIST Section 10. The test files live under `tests/chaos/`:

  - `test_mt_node_load_n_tenants.py` (N=10 / 50 / 100)
  - `test_mt_node_market_open_spike.py`
  - `test_mt_node_random_kill.py`

**Status as of this commit**: the test files exist as skeletons.
The assertion bodies are deferred to the load-test follow-up MR.
This runbook documents the contract the assertions will check, so
an operator running the suite manually can already verify the
system's behaviour against the documented SLOs.

## Cluster prerequisites

Do NOT run this suite against production. A dedicated staging
cluster with the same chart values as production is required.

  - Node pool with at least N=100 * 1.5Gi memory + 1500m CPU
    headroom for the worst-case load. With the production
    overlay's mt-node resource limits, that is ~150Gi memory +
    150 CPU cores of free capacity beyond the steady-state
    workload.
  - StorageClass with VolumeSnapshot support (the Wine prefix
    snapshotter CronJob lands during the test window; the suite
    asserts snapshots actually get created).
  - Prometheus Operator installed; the suite reads metrics via
    `kubectl exec ... curl /metrics` rather than the operator's
    API.
  - Loki + Promtail (helm/observability-logs); the suite spot-
    checks LogQL queries to verify per-tenant log isolation.

## SLOs the suite enforces

| Scenario | SLO | Source of truth |
|---|---|---|
| N=10 provisioning | < 60s end-to-end | Wall-clock from first POST to last Ready |
| N=50 provisioning | < 180s | Same |
| N=100 provisioning | < 300s | Same |
| Per-tenant uptime during soak | >= 99% authenticated | mt_node_ea_authenticated samples |
| Per-tenant RSS growth | < 25% over soak window | mt_node_mt5_process_rss_bytes |
| Cross-tenant correlation | abs(Pearson r) < 0.3 for any tenant pair | RSS time-series |
| Market-open burst throttling | 100% of excess commands rejected with 429 / OutboundRateLimitExceededError | Engine HTTP responses |
| Post-burst recovery | < 1s to resume normal cadence | TICK_PRICE round-trip |
| Random-kill recovery (per release) | < 1200s worst-case | mt_node_ea_authenticated returns to 1 |
| Random-kill bystander impact | zero bystander tenants lose authenticated state | mt_node_ea_authenticated samples |

## Execution

```bash
# 1. Acquire staging admin JWT.
export ETRADIE_CHAOS_ENGINE_URL=https://engine.staging.etradie.com:8000
export ETRADIE_CHAOS_ADMIN_JWT="$(...)"
export ETRADIE_CHAOS_KUBECONFIG=/path/to/staging-kubeconfig
export SOAK_DURATION_SECONDS=1800   # 30 min default; bump for nightly

# 2. Run the full Section-10 suite.
make mt-node-load-test
```

The Makefile target chains the three suites and exits non-zero if
any SLO is breached.

## Pass / fail decision tree

  - Any SLO breach -> FAIL. The follow-up MR's implementation
    surfaces the breached metric in the pytest failure message.
    Do NOT promote the staging image to production until the
    breach is diagnosed and the fix is verified via a green
    re-run.
  - Reprovisioning > unhealthy_threshold + cooldown + readiness
    -> FAIL. Likely cluster autoscaler saturation; bump the
    node-pool max size and re-run.
  - Cross-tenant correlation breach -> CRITICAL FAIL. Indicates
    a shared-state bug that violates Section 5 isolation. Page
    the on-call engineer; do NOT promote.

## Rollback

The suite cleans up via the engine's DELETE
/api/broker/connections/<id> endpoint at the end of each test
(success OR failure path). If the cleanup itself fails, the
follow-up MR's implementation calls
`HostedProvisioner.gc_orphans(known_connection_ids=[])` to delete
every StatefulSet labeled `app.kubernetes.io/name=etradie-mt-node`.
This is destructive; only safe on the dedicated staging cluster.
