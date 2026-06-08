# Observability & Monitoring — Operator Runbook

> Companion to the per-service Helm charts (`helm/*/templates/servicemonitor.yaml`,
> `prometheusrule.yaml`) and the logging chart (`helm/observability-logs`).
> This runbook is the single authoritative operator reference for the
> three observability pillars — **metrics, logs, traces** — across every
> service. It documents how each is wired, how you access it, every
> per-service toggle, the full alert catalogue, and the procedures to
> enable, verify, and troubleshoot each pillar.
>
> Scope: `src/*` instrumentation, `docker/prometheus`, `docker/grafana`,
> `helm/*` ServiceMonitors/PrometheusRules, `helm/observability-logs`
> (Loki + Promtail), and the OpenTelemetry/Jaeger tracing path.

---

## 0. At a glance — current posture

| Pillar  | Local dev (docker-compose)            | Cluster (staging/production)                          | State |
| ------- | ------------------------------------- | ----------------------------------------------------- | ----- |
| Metrics | Prometheus `:9090` + Grafana `:3000`  | Prometheus Operator (`ServiceMonitor` + `PrometheusRule`) | LIVE |
| Logs    | container stdout (JSON)               | Loki + Promtail in `etradie-observability`            | LIVE |
| Traces  | Jaeger `:16686` (OTLP `:4317`)        | OTel Collector + Jaeger in `etradie-observability`; all services export OTLP | LIVE |

**Read this first:** all three pillars are live in cluster. Distributed
tracing is instrumented in code (engine
`src/engine/shared/tracing/otel.py`, gateway
`src/gateway/internal/observability/tracing.go`), and the
`helm/observability-logs` chart now deploys an **OpenTelemetry
Collector + Jaeger** (enabled in the prod + staging overlays via
`tracing.enabled=true`). Every service's prod + staging overlay sets
its OTEL endpoint to
`otel-collector.etradie-observability.svc.cluster.local:4317`, so spans
flow Browser → gateway → (engine | execution | management) → Collector
→ Jaeger. Section 4 covers how the stack is wired and how to verify,
tune, and roll it back. Tracing stays a clean no-op only where the
endpoint is left empty (a bare `helm template` / dev render with
`tracing.enabled=false`).

---

## 1. Metrics (Prometheus)

### 1.1 How it is wired

* Every service exposes Prometheus metrics on its HTTP port at
  `/metrics`:
  * engine `:8000`, gateway `:8080`, execution `:8080`,
    management `:8083`, edge-ingress `:9902`, billing (ops port),
    mt-node node-exporter-style `:9100`.
* Engine metric definitions live in
  `src/engine/shared/metrics/prometheus.py` (RED/USE methodology,
  every series namespaced `etradie_`). Go services expose `promhttp`
  and their own `observability/metrics.go`.
* **Cardinality discipline (do not regress this):** metric labels are
  bounded enumerations (status, operation, error_type, provider,
  account_id). User IDs, UUIDs, and timestamps are NEVER labels;
  per-connection / per-user detail goes to structured logs instead.
  A PR that adds a high-cardinality label is a Prometheus OOM risk.

### 1.2 Scrape configuration

* **Local (docker-compose):** `docker/prometheus/prometheus.yml`
  static-scrapes engine/gateway/execution/management every 15s.
* **Cluster:** each service chart renders a Prometheus-Operator
  `ServiceMonitor` (`helm/<svc>/templates/servicemonitor.yaml`),
  selected by the operator's `ruleSelector`/`serviceMonitorSelector`
  via the label `prometheus: kube-prometheus`. Default interval
  15–30s, scrapeTimeout 10s. `metricRelabelDropPrefixes`
  (`go_`, `process_`, `promhttp_`) trims runtime noise.
* **Toggle per service:** `serviceMonitor.enabled` in the service's
  values file. Set `false` on a cluster with no Prometheus Operator.

### 1.3 Alerting (PrometheusRule)

* Each chart ships a `PrometheusRule` (`prometheusrule.yaml`), enabled
  via `prometheusRule.enabled` and selected by
  `prometheusRule.labels.prometheus: kube-prometheus`.
* Every alert carries `severity`, `component`, `team`, and a
  `runbook_url`. See the catalogue in Section 5.
* **Toggle per service:** `prometheusRule.enabled`.

### 1.4 Operator access

* **Cluster:** Grafana lives in the `monitoring` namespace (alongside
  the Prometheus Operator — it is NOT deployed by these charts). Add
  the in-cluster Prometheus as a datasource. Query the
  `etradie_*` series; dashboards key off the
  `service`/`component`/`namespace` labels.
* **Local:** Grafana `http://localhost:3000`
  (`GF_ADMIN_USER`/`GF_ADMIN_PASSWORD` from `.env`), Prometheus
  `http://localhost:9090`. Datasources are provisioned read-only by
  `docker/grafana/datasources.yml`.

---

## 2. Logs (Loki + Promtail)

### 2.1 How it is wired

* **Structured logging in code:** Go services use zerolog JSON
  (`src/gateway/internal/observability/logger.go` and the per-service
  equivalents) with `trace_id` / `cycle_id` binding and a
  **sensitive-field redaction allowlist** (password, secret, token,
  api_key, cookie, access_token, refresh_token, card_number, cvv, …
  → `***REDACTED***`). The engine mirrors this; its global exception
  handler emits a sanitized generic 500 and logs the real cause via
  secret-sanitized `log_panic_recovery`.
* **Cluster aggregation:** `helm/observability-logs` deploys, in the
  `etradie-observability` namespace:
  * **Loki** (StatefulSet) — 14d retention (`retentionPeriod: 336h`),
    50Gi (base) / 100Gi (prod) PVC, hardened (non-root, RO-rootfs,
    drop-ALL caps), per-stream ingestion + line-size limits.
  * **Promtail** (DaemonSet) — tails `/var/log/pods`, parses CRI +
    JSON, extracts `level`/`logger`/`user_id`/`connection_id`/
    `request_id`, relabels with namespace/pod/container/node and the
    eTradie tenant labels (`etradie_user_id`, `etradie_platform`),
    drops `kube-proxy`/`calico-node`/`csi-node-driver-registrar` noise,
    pushes to Loki with backoff.
* **Local:** logs go to container stdout as JSON; no Loki in
  docker-compose. Use `docker compose logs -f <service>`.

### 2.2 NetworkPolicy topology

* Loki accepts ingress only from Promtail and from Grafana
  (`networkPolicy.grafanaNamespace: monitoring`).
* Promtail egresses only to Loki and the K8s API (service discovery).
* `networkPolicy.enabled` controls both.

### 2.3 Operator access

* Grafana (monitoring ns) → add Loki as a datasource at
  `http://loki.etradie-observability.svc.cluster.local:3100`.
* Common queries (LogQL):
  * All errors for one service:
    `{app="etradie-engine"} | json | level="ERROR"`
  * One user's hosted-node trail:
    `{namespace="etradie-system"} | json | user_id="<uuid>"`
  * Correlate with a trace/cycle:
    `{app="etradie-gateway"} | json | cycle_id="<id>"`

---

## 3. Tracing (OpenTelemetry → Jaeger)

### 3.1 How it is wired (code)

* **Engine:** `src/engine/shared/tracing/otel.py` — OTLP/gRPC exporter,
  `BatchSpanProcessor`, validates the endpoint, emits span
  metrics (`etradie_tracing_spans_created_total`,
  `..._errors_total`). `init_tracing` is called from `main.py`'s
  lifespan UNLESS `settings.is_testing`.
* **Gateway:** `src/gateway/internal/observability/tracing.go` —
  OTLP/gRPC, `WithBatcher`, `initOnce`, graceful `Shutdown` flush.
* **Opt-in semantics (critical):** an EMPTY OTLP endpoint is treated
  as "tracing explicitly disabled" — no dial, no exporter, no retry
  noise, a no-op tracer. This is by design: absent configuration
  means absent telemetry, not best-effort retries.

### 3.2 Configuration keys

| Service | Env var                        | Helm values key                        |
| ------- | ------------------------------ | -------------------------------------- |
| Engine  | `OTEL_EXPORTER_OTLP_ENDPOINT`  | `config.observability.otelEndpoint`    |
| Gateway | `GATEWAY_OTEL_ENDPOINT`        | `config.gateway.otelEndpoint`          |
| Execution | `EXECUTION_OTEL_ENDPOINT`    | `config.execution.otelEndpoint`        |
| Management | `MANAGEMENT_OTEL_ENDPOINT`  | `config.management.otelEndpoint`       |

Service-name keys (`*.otelServiceName`) are already set
(`etradie-engine` / `-gateway` / `-execution` / `-management`).

### 3.3 Current state

* **Local docker-compose:** Jaeger runs (`jaegertracing/all-in-one`,
  `COLLECTOR_OTLP_ENABLED=true`, OTLP ingest `:4317`, UI `:16686`).
  Grafana has a Jaeger datasource (`docker/grafana/datasources.yml`).
* **Cluster (staging/production): LIVE.** `helm/observability-logs`
  deploys, in the `etradie-observability` namespace:
  * an **OpenTelemetry Collector** (Deployment + Service `otel-collector`,
    OTLP/gRPC `:4317` + OTLP/HTTP `:4318`, memory-limiter + batch
    processors, self-metrics `:8888`), and
  * **Jaeger all-in-one** (Deployment + Service, OTLP ingest `:4317`,
    query UI `:16686`, admin/metrics `:14269`, in-memory store).
  Both are gated by `tracing.enabled` (false in base, true in the prod
  + staging overlays). Every service's prod + staging overlay sets its
  OTEL endpoint to `otel-collector.etradie-observability.svc.cluster.local:4317`.
  The NetworkPolicies lock the collector's ingress to the
  `etradie-system` namespace (OTLP) + Prometheus (self-metrics), and
  its egress to Jaeger + DNS; Jaeger ingress is collector + Grafana
  (UI) + Prometheus only.

---

## 4. Tracing stack — wiring, verify, tune, roll back

The collector + Jaeger are deployed and tracing is ON in prod + staging.
This section is the operator reference for that stack.

### 4.1 What is deployed (and the contract)

* Templates: `helm/observability-logs/templates/otel-collector-*.yaml`,
  `jaeger-*.yaml`, `networkpolicy-tracing.yaml`. Values: the
  `tracing.*` block in `values.yaml` (+ prod/staging overlays).
* **Fixed contract:** the collector Service is named exactly
  `otel-collector` on `:4317`, so
  `otel-collector.etradie-observability.svc.cluster.local:4317`
  resolves and matches the per-service egress
  (`app.kubernetes.io/name: otel-collector`, port 4317) already present
  in every service's NetworkPolicy. Do NOT rename the Service or move
  its namespace without updating those egress rules + the overlays.
* Pipeline: service SDK → Collector (OTLP, batched, memory-bounded) →
  Jaeger (OTLP) → Jaeger in-memory store → query UI.

### 4.2 Per-service OTEL endpoint (where it is set)

| Service | Overlay key (prod + staging)        |
| ------- | ----------------------------------- |
| Engine  | `config.observability.otelEndpoint` |
| Gateway | `config.gateway.otelEndpoint`       |
| Execution | `config.execution.otelEndpoint`   |
| Management | `config.management.otelEndpoint` |

All set to `otel-collector.etradie-observability.svc.cluster.local:4317`.
After changing any of these, rollout-restart (the value is read at
boot):

```bash
kubectl -n etradie-system rollout restart deploy/engine deploy/gateway \
  deploy/execution
kubectl -n etradie-system rollout restart deploy/management   # singleton; Recreate strategy
```

### 4.3 Alternative backend (SaaS OTLP)

To export to a vendor (Grafana Cloud Tempo, Honeycomb, …) instead of
in-cluster Jaeger: set `tracing.jaeger.enabled=false`, point the
collector's `otlp/jaeger` exporter at the vendor (edit
`otel-collector-config.yaml` / parameterise it), and widen the
collector's egress NetworkPolicy to the vendor endpoint. The services
still export to the in-cluster collector, so their overlays are
unchanged.

### 4.4 Verify

```bash
# 1. The service logged tracing as initialised (not disabled):
kubectl -n etradie-system logs deploy/gateway | grep tracing_initialized
kubectl -n etradie-system logs deploy/engine  | grep tracing_initialized
# A line 'tracing_disabled_no_otlp_endpoint_configured' means the
# endpoint did not reach the pod — re-check the overlay + restart.

# 2. Span-creation metric is climbing:
#    etradie_tracing_spans_created_total  (engine)
# 3. A cross-service trace (Browser -> gateway -> engine/execution)
#    appears in the Jaeger UI for service 'etradie-gateway'.
```

### 4.5 Roll back

Two levers, smallest blast radius first:

* **Disable one service's export:** set its `otelEndpoint` back to `""`
  in the overlay and rollout-restart that deployment. Its exporter
  reverts to a no-op immediately; the rest keep tracing.
* **Tear down the backend:** set `tracing.enabled=false` in the
  `observability-logs` overlay and sync. The Collector + Jaeger +
  their NetworkPolicies are removed. Leave the service `otelEndpoint`s
  set or clear them too — with the collector gone the SDK simply fails
  the dial and drops spans (BatchSpanProcessor swallows export errors;
  it does NOT block request handling), but clearing the endpoints is
  tidier and silences the export-retry logs.

### 4.6 Tuning

* **Span loss under load:** raise `tracing.jaeger.memoryMaxTraces` and
  the collector's `batch` size, or move Jaeger to a durable store.
* **Durable / HA traces:** the all-in-one in-memory store is ephemeral
  (lost on restart). For production-grade retention, point
  `tracing.jaeger.image` at a badger/Elasticsearch-backed Jaeger (or
  split collector/query) and add persistence — deliberately out of
  scope for this chart's minimal footprint.
* **Collector pipeline metrics:** scraped on `:8888` via the
  collector's ServiceMonitor (`prometheus: kube-prometheus`); watch
  `otelcol_processor_dropped_spans` / `otelcol_exporter_send_failed_spans`.

---

## 5. Alert catalogue (PrometheusRule)

All alerts carry `severity` / `component` / `team` / `runbook_url`.
This is the authoritative list of what pages and why.

### 5.1 Engine — `engine.broker`

| Alert | Expr (summary) | Severity |
| ----- | -------------- | -------- |
| `EngineBrokerInflightGateP95High` | in-flight gate wait p95 > 2s for 5m | warning |
| `EngineBrokerInflightGateExhausted` | gate rejections > 1/min for 5m | critical |
| `EngineBrokerRequestDeadlineSpike` | deadline-exceeded > 1/min for 5m | warning |
| `EngineOutboundRateExhausted` | outbound limiter `exhausted` > 0.1/s for 5m | warning |
| `EngineEAIdentityMismatch` | any EA identity mismatch (Section-4 kill-switch fired) | critical |
| `EngineEAClockSkewHigh` | abs(EA clock skew) > 5s for 5m | warning |

### 5.2 Engine — `engine.process`

| Alert | Expr (summary) | Severity |
| ----- | -------------- | -------- |
| `EnginePodMemoryGrowth` | working-set slope > 50 MB/h over 6h | warning |
| `EnginePodHighRestarts` | > 3 restarts in 15m | critical |

### 5.3 Engine — `engine.hosted_recovery`

| Alert | Expr (summary) | Severity |
| ----- | -------------- | -------- |
| `HostedRecoveryReprovisionsHigh` | reprovisions > 1/h sustained 2h | critical |
| `HostedRecoveryServiceStuck` | no sweep completed in > 5m | warning |
| `HostedRecoveryPodsUnhealthyPersistent` | unhealthy pods > 0 for 30m | warning |

### 5.4 Execution / Management / Gateway

* **Execution** (`helm/execution/templates/prometheusrule.yaml`):
  order failure rate, placement latency, queue drops, latency
  kill-switch firings, audit-write failures.
* **Gateway** (`prometheusRule` in `helm/gateway`): abuse-monitoring
  rules — gateway per-user limiter, execution per-user limiter, Envoy
  L7 backstop, edge-ingress connection caps.
* **Management**: per-service rule set (PnL/EOD job health).

> When you add a new alert, ALWAYS include a `runbook_url`. The
> existing alerts point at `https://docs.etradie.com/runbooks/...`;
> keep the convention so a paged on-call has a landing page.

---

## 6. Namespace & access topology (reference)

```text
monitoring            Prometheus Operator + Prometheus + Grafana
                      (NOT deployed by these charts; cluster add-on)
etradie-observability Loki + Promtail   (helm/observability-logs)
                      [+ OTel Collector + Jaeger once Section 4 is done]
etradie-system        all app services expose /metrics + JSON logs
edge-ingress-system   edge-ingress /metrics :9902
```

Access control:

* Prometheus scrapes are authorised by NetworkPolicy (monitoring ns
  Prometheus pod → service `:metrics` + Linkerd proxy `:4191`) and,
  where `linkerdPolicy.enabled=true`, by Linkerd
  `NetworkAuthentication` for the un-meshed Prometheus source.
* Grafana, Prometheus, and the Jaeger UI must sit behind the cluster's
  operator-access control (SSO / VPN / bastion). None are part of the
  public `api.exoper.com` surface and MUST NOT be exposed through the
  Cloudflare → edge-ingress → Envoy → gateway chain.

---

## 7. Troubleshooting

| Symptom | Likely cause | Action |
| ------- | ------------ | ------ |
| Service missing from Prometheus targets | `serviceMonitor.enabled=false`, or operator's `serviceMonitorSelector` does not match `prometheus: kube-prometheus` | enable it / align the selector label |
| Alerts never fire | `prometheusRule.enabled=false` or `prometheusRule.labels` not matched by the operator `ruleSelector` | enable + fix the label |
| No logs in Loki for a pod | container in Promtail `dropContainers`, or pod not on a node Promtail tolerates | check `promtail.pipeline.dropContainers` + tolerations |
| Logs present but no `level`/`user_id` labels | log line is not JSON (Promtail only json-parses lines starting `{`) | ensure `logJson: "true"` for the service |
| `tracing_disabled_no_otlp_endpoint_configured` in logs | OTEL endpoint empty (expected in prod until Section 4) | follow Section 4 to enable |
| Traces missing after enabling | endpoint set but no collector, or NetworkPolicy egress blocks `:4317` | verify collector is up + egress allows the target |
| Prometheus OOM / cardinality blow-up | a new high-cardinality metric label (user_id/UUID/timestamp) | revert the label; move detail to logs |

---

## 8. Invariants (do not regress)

1. Metric labels stay bounded — no user_id/UUID/timestamp labels.
2. Secrets never reach logs — the zerolog redaction allowlist is the
   backstop; never log a raw credential field.
3. Tracing stays opt-in — empty endpoint must remain a clean no-op,
   not a retrying dial.
4. Observability UIs (Grafana/Prometheus/Jaeger/Loki) are
   operator-only and never routed through the public edge chain.
5. Every new PrometheusRule alert carries `severity` + `runbook_url`.
