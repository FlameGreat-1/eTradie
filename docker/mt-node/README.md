# etradie-mt-node

Production-grade headless MetaTrader 4 / 5 terminal container. Runs
MT under Wine + Xvfb, exposes the EA over ZeroMQ on `:5555`, and
runs a sidecar watchdog on `:9100` that enforces memory + CPU
soft-caps and reports the EA's connection state to Prometheus.

## Deployment model

The etradie platform deploys **one mt-node Pod per user broker
connection**. There are two equivalent production paths and one
legacy fallback:

### 1. Engine-driven (runtime; dashboard flow)

When a user picks `connection_type=hosted` in the dashboard, the
engine's `HostedProvisioner` (`src/engine/ta/broker/mt5/hosted/
provisioner.py`) calls the Kubernetes API to render a per-tenant
`StatefulSet` + `ClusterIP Service` + `headless Service` + `Secret`
in the `etradie-system` namespace. The objects' labels, selectors,
PVC naming, and security context all match the chart's shape
(`helm/mt-node/templates/statefulset.yaml`) so an operator can
`kubectl describe sts <release>` and find an identical resource
regardless of which path created it.

### 2. GitOps-driven (helm/mt-node chart via ArgoCD)

For platform-level resources (`PriorityClass`, the platform
`ExternalSecret` for `DEFAULT_ZMQ_AUTH_TOKEN`, the watchdog
`ConfigMap`) the helm/mt-node chart is registered as an ArgoCD
Application with `mtConnection.enabled=false`. This renders ONLY
the shared cluster resources — not a per-tenant StatefulSet. Both
staging and production overlays exist.

The chart can ALSO render per-tenant StatefulSets when
`mtConnection.enabled=true` and the operator passes the
per-tenant `--set` values. This path is reserved for emergency
operator action (e.g. the engine is down and an operator must
bring a specific user's MT terminal back up via GitOps). The
resulting K8s objects are wire-compatible with what the engine
provisions.

### 3. EA-on-VPS (local development only — NOT a production path)

`connection_type='ea'` reads single-tenant `MT5_ZMQ_HOST` / `MT5_ZMQ_PORT` /
`MT5_ZMQ_AUTH_TOKEN` env vars from the engine's own environment. It is a
local-development escape hatch so engineers can run MT5 on their own machine
and point the engine at it during development. The router **rejects this
connection type in production and staging** (hardcoded `APP_ENV` check in
`src/engine/routers/broker_connections.py`). The mt-node container is NOT
involved in this path.

### 4. MetaAPI cloud (no container)

`connection_type=metaapi` uses MetaQuotes' cloud-hosted terminals.
The engine talks REST to MetaAPI, no per-tenant container exists.
Useful for users who do not want to self-host.

## Per-tenant credential flow

```
   user dashboard "add broker"
     │
     ▼
   engine: broker_connections row (column-encrypted at rest)
     │   ├─ mt5_login
     │   ├─ mt5_password
     │   └─ ea_auth_token (engine generates per-tenant)
     │
     ▼
   HostedProvisioner.provision_account()
     │   │ (1) Write to Vault KV-v2 at
     │   │     etradie/data/tenants/mt-node/<connection_id>
     │   │       mt5_login, mt5_password, mt5_zmq_auth_token
     │   │ (2) Create per-tenant ServiceAccount etradie-mt-<id12>
     │   │     (matches the Vault role's bound-SA glob)
     │   └─ (3) Create StatefulSet + Services with Vault Agent
     │         Injector annotations on the pod template
     │
     ▼
   Pod scheduling: kube-apiserver mutating webhook injects two
     containers ahead of mt-node:
     │   ├─ vault-agent-init  (authenticates with the projected SA
     │   │                       token via the kubernetes auth backend
     │   │                       role mt-node-tenant, renders the
     │   │                       credentials template to
     │   │                       /vault/secrets/mt-credentials.env on
     │   │                       a tmpfs emptyDir, exits 0)
     │   └─ vault-agent       (long-running sidecar; re-renders on
     │                         lease renewal so credential rotations
     │                         are picked up on the next file source)
     │
     ▼
   mt-node Pod boots
     │   │ (1) entrypoint.sh sources /vault/secrets/mt-credentials.env
     │   │ (2) MT_LOGIN / MT_PASSWORD / MT_ZMQ_AUTH_TOKEN are now in env
     │   │ (3) Wine + MT5 terminal launched (auto-login from startup.ini)
     │   │ (4) ZeroMQ EA loaded with AUTH_TOKEN=<MT_ZMQ_AUTH_TOKEN>
     │   └─ (5) Watchdog parses the same file at startup; PINGs MT5
     │
     ▼
   engine.ZmqClient dials <release>.etradie-system.svc:5555
         with auth_token = ea_auth_token (decrypted from broker_connections)
```

Key security properties:

  - Credentials never traverse a Kubernetes Secret. Vault KV-v2 is
    sealed at rest by Vault itself (AES-256-GCM with a key sealed
    by the cluster's auto-unseal KMS); `kubectl get secret` cannot
    leak broker credentials because no such Secret exists.
  - The projected SA token mounted into the pod can only exchange
    for a Vault token bound to one role (`mt-node-tenant`) which
    has READ on a single KV path templated by the SA name. A
    compromised pod cannot read another tenant's credentials.
  - The Vault-rendered file lives on an in-memory tmpfs emptyDir,
    not on the underlying node disk.
  - Drop-ALL capabilities, non-root user, and read-only rootfs
    keep the in-pod blast radius narrow if MT5 itself is
    compromised.
  - NetworkPolicy egress restricted to public IP space only (no
    in-cluster pivot; no cloud metadata IMDS access).

## Wine prefix PVC lifecycle

The StatefulSet's `volumeClaimTemplates` produces a per-replica
PVC named **`wine-prefix-<release>-0`**. K8s creates the PVC on
first pod scheduling and re-attaches it on every Pod restart.
The Wine prefix carries:

  - MT5/MT4 terminal profile (the broker's "trusted device"
    registration; without this every restart triggers the
    broker's 2FA / new-device flow).
  - Chart templates + indicator caches.
  - EA `.set` file with the per-tenant `AUTH_TOKEN`.

Lifecycle:

  - **Pod restart**: PVC re-attached; MT5 re-launches against the
    existing profile in ~30s.
  - **StatefulSet recreate** (e.g. `helm upgrade` with image bump):
    pod terminates, PVC stays bound, new pod attaches.
  - **Connection delete**: engine's `HostedProvisioner.delete_account()`
    explicitly deletes the PVC because StatefulSet GC does NOT
    cascade to volumeClaimTemplate PVCs.
  - **Reclaim policy**: set at the StorageClass level. The
    convention is `Retain` so a `helm uninstall` does NOT lose
    the Wine prefix; the operator must explicitly delete the PV.

## Watchdog contract

The watchdog sidecar (`/opt/watchdog/watchdog.py`) runs alongside
the MT5/MT4 container. It exposes three HTTP endpoints on `:9100`:

  - `GET /healthz` → 200 only when the EA reported
    `mt5_connected=true` AND `authenticated=true` in the last 30s.
    Bound to the chart's `readinessProbe`.
  - `GET /livez` → 200 unless the watchdog itself is wedged for
    `WATCHDOG_LIVEZ_GRACE_SECONDS` (default 60s). Bound to the
    chart's `livenessProbe`; kubelet kills the Pod when this 503s.
  - `GET /metrics` → Prometheus exposition.

In-pod enforcement (forces a clean MT restart through the
`entrypoint.sh` supervisor loop; the whole Pod does NOT restart):

  - **Memory soft-cap**: when MT5 RSS exceeds
    `WATCHDOG_MEMORY_SOFT_CAP_FRACTION` (default 0.8) of the
    cgroup memory limit, SIGTERM the MT tree BEFORE the kernel
    OOM-killer runs. Catches the slow-leak case before journal
    writes are interrupted mid-trade.
  - **CPU soft-cap**: when more than
    `WATCHDOG_CPU_THROTTLE_SOFT_CAP_FRACTION` (default 0.5) of
    CFS periods are throttled, sustained for
    `WATCHDOG_CPU_THROTTLE_CONSECUTIVE_POLLS` (default 6 ≈ 60s),
    SIGTERM the MT tree. Section 1 CHECKLIST item 'Indicator
    recalculation spikes do not freeze system'.
  - **EA health failures**: after
    `WATCHDOG_MAX_FAILURES` (default 6) consecutive HEALTH probe
    failures, SIGTERM the MT tree. The supervisor loop respawns
    MT5 within the in-pod restart budget.

Prometheus alarms (`helm/mt-node/templates/prometheusrule.yaml`):

  - `MTNodePodPending` — cluster capacity warning.
  - `MTNodeWatchdogDown` — 5min watchdog unreachable; operator
    intervention required.
  - `MTNodeBrokerDisconnected` — EA reports `mt5_connected=false`
    for 3min.
  - `MTNodeMemoryLeak` — RSS deriv > 50MB/h over 4h. Fires hours
    before the memory soft-cap would.
  - `MTNodeMemorySoftCapTripFrequent` — memory cap trips > 1/h
    for 2h. The leak is severe.
  - `MTNodeCPUThrottledSustained` — cgroup CFS-throttled for 10min.
  - `MTNodeCPUSoftCapTripFrequent` — CPU cap trips > 1/h for 2h.

Every alarm carries `severity`, `component`, `team`,
`connection_id`, `user_id`, and `runbook_url` labels for
PagerDuty routing.

## Build

### Local dev (SHA checks bypassed)

```bash
make build-mt-node
```

### Production CI (full supply-chain pinning)

```bash
# 1. Compute the EA .ex5 SHA so CI can pin it:
make mt-node-ea-sha

# 2. Build with all four SHAs pinned + image tag:
MT5_INSTALLER_SHA256=<from-mql5> \
MT4_INSTALLER_SHA256=<from-mql5> \
EA_EX5_SHA256=$(sha256sum docker/mt-node/ea/ZeroMQ_EA.ex5 | awk '{print $1}') \
EA_EX4_SHA256=$(sha256sum docker/mt-node/ea/ZeroMQ_EA.ex4 2>/dev/null | awk '{print $1}' || echo skip) \
MT_NODE_TAG=0.1.0 \
  make build-mt-node
```

### Air-gapped CI (offline MT installer mirror)

For regulated environments where the build host cannot reach
`download.mql5.com`:

```bash
docker build \
  --build-arg MT5_INSTALLER_URL=https://artifactory.example.com/mql5/mt5setup-v5.0.123.exe \
  --build-arg MT5_INSTALLER_SHA256=<sha-of-that-blob> \
  --build-arg MT4_INSTALLER_URL=https://artifactory.example.com/mql5/mt4setup-v4.0.123.exe \
  --build-arg MT4_INSTALLER_SHA256=<sha-of-that-blob> \
  --build-arg EA_EX5_SHA256=$(sha256sum docker/mt-node/ea/ZeroMQ_EA.ex5 | awk '{print $1}') \
  --build-arg EA_EX4_SHA256=$(sha256sum docker/mt-node/ea/ZeroMQ_EA.ex4 | awk '{print $1}') \
  -t ghcr.io/flamegreat-1/etradie-mt-node:0.1.0 \
  docker/mt-node/
```

## Operator runbook

### Logs

```bash
# Per-pod tail:
kubectl -n etradie-system logs etradie-mt-<conn-id-prefix>-0 -c mt-node -f

# Per-tenant LogQL (Loki via Grafana):
{app="etradie-mt-node", user_id="u-abc123"}
```

### Force a restart

```bash
# Soft (drains gracefully):
kubectl -n etradie-system delete pod etradie-mt-<conn-id-prefix>-0

# Hard (forces wineserver kill):
kubectl -n etradie-system exec etradie-mt-<conn-id-prefix>-0 -c mt-node \
  -- pkill -9 -f terminal64.exe
```

### Inspect EA state

```bash
kubectl -n etradie-system port-forward etradie-mt-<conn-id-prefix>-0 9100:9100
curl -s http://localhost:9100/metrics | grep mt_node_ea
```

## Required env vars (from envFrom Secret)

| Var                      | Source                                     | Notes                                          |
|--------------------------|--------------------------------------------|------------------------------------------------|
| `MT_LOGIN`               | broker_connections.mt5_login (decrypted)   | Trading account number.                        |
| `MT_PASSWORD`            | broker_connections.mt5_password (decrypted)| Broker trading password.                       |
| `MT_ZMQ_AUTH_TOKEN`      | broker_connections.ea_auth_token (decrypted)| Per-tenant. Engine generates one per provision.|
| `DEFAULT_ZMQ_AUTH_TOKEN` | platform ExternalSecret                    | Fallback when MT_ZMQ_AUTH_TOKEN is empty.      |

Required env vars (from chart env block):

| Var                | Source                              | Notes                       |
|--------------------|-------------------------------------|-----------------------------|
| `MT_PLATFORM`      | broker_connections (mt4 \| mt5)     | Selects terminal binary.    |
| `MT_SERVER`        | broker_connections.mt5_server       | e.g. `Exness-MT5Trial9`.    |
| `MT_SYMBOL`        | broker_connections.symbol           | Default chart symbol.       |
| `ZMQ_PORT`         | service.zmqPort (default 5555)      | EA REQ/REP port.            |

## Architecture notes (advanced)

- **PID 1**: `tini` reaps zombie wine processes that survive
  `wineserver -k`. Without this, MT5 helpers leak into the next
  restart cycle.
- **Wine prefix corruption**: `entrypoint.sh` auto-detects a
  missing `drive_c/windows/system32` or stale `.update-timestamp.lock`
  and resets the prefix. Recovery path for unclean pod kills.
- **Supervised restart loop**: `MAX_INPOD_RESTARTS` (default 5) in
  a 5-minute window. On exhaustion, exit non-zero so kubelet
  recreates the Pod — the kernel does a full clean restart.
- **Zombie wine drain**: every loop iteration `pkill -9 -f` the
  terminal/wineserver/wineboot patterns so a stuck helper from
  the previous iteration cannot collide with the next launch on
  the `.X99-lock` or wineserver socket.

## Security posture (CIS Kubernetes Benchmark v1.8)

  - 5.1.5  ServiceAccount: `automountServiceAccountToken: false`.
  - 5.2.1  Privileged: `false`.
  - 5.2.4  HostNetwork: `false`.
  - 5.2.5  HostPID:     `false`.
  - 5.2.6  HostIPC:     `false`.
  - 5.2.7  HostPath:    `false` (PVC only).
  - 5.2.8  Capabilities: drop ALL.
  - 5.3.2  NetworkPolicy: egress restricted to public IP space via
           ipBlock + RFC1918 + IMDS exclusions.
  - 5.7.3  Seccomp: `RuntimeDefault`.
  - 5.7.4  PodSecurityContext: `runAsNonRoot=true`, `runAsUser=1000`.
  - 5.7.5  readOnlyRootFilesystem: `true` (Wine prefix is the sole
           writable mount via PVC).
