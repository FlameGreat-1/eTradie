# Phase 10.6 — Linkerd opaque-ports + appProtocol RCA and Revert Guide

**Date:** 2026-06-17
**Status:** APPLIED on `main` (GitHub source-of-truth + GitLab mirror)
**Scope:** staging mesh data path (engine is separately un-meshed in staging; see note at the end)
**Author context:** Phase 10.6 staging deployment, single-node Contabo K3s, ArgoCD GitOps, Linkerd `stable-2.14.10`.

---

## 1. TL;DR (what changed)

Two coordinated changes were made so the meshed Go services
(`gateway`, `execution`, `management`, `billing`) can connect to
TLS-serving postgres and redis through the Linkerd mesh:

1. **Removed `appProtocol`** from the postgres and redis Services
   (the raw data ports only).
2. **Added `config.linkerd.io/opaque-ports: "5432,6379"`** to the pod
   annotations of all four Go services (the CALLER side).

Both are needed together. Change #2 is the one that actually fixed the
crash; change #1 removes a contradicting hint and makes all three data
Services (postgres, redis, chromadb) consistent.

---

## 2. The symptom we were fixing

Every meshed Go service crash-looped on startup with, e.g.:

```
fatal: failed to connect to `user=etradie database=etradie`:
  10.43.151.84:5432 (postgres.etradie-system.svc.cluster.local):
  tls error: read tcp 10.42.0.166:56304->10.43.151.84:5432:
  read: connection reset by peer
```

The connection to postgres was **reset mid-TLS-handshake**. The Python
engine connected to the SAME postgres fine — because the engine is
currently **un-meshed** in staging, so nothing intercepted its outbound
connection.

---

## 3. Plain-English explanation (the "why")

Think of the Linkerd service mesh as putting a smart **proxy** next to
every pod. All traffic in and out of a pod goes through its proxy, and
the proxy normally tries to *understand* the traffic (is this HTTP? gRPC?)
so it can give you metrics, retries, etc. That "understanding" step is
called **protocol detection**.

Postgres and Redis do NOT speak HTTP. They speak their own binary,
"server-talks-first" protocols, and postgres also does its own TLS
negotiation (it sends a tiny "can we use SSL?" request, waits for a
one-byte reply, then upgrades to TLS). If a proxy tries to "understand"
that traffic as if it were HTTP, it mangles the handshake and the
connection dies.

The fix for that is to mark those ports **opaque**, which tells the
proxy: *"don't try to understand this traffic — just encrypt it with
mTLS and pass the raw bytes straight through."*

**The key insight that took us two days:** marking a port opaque is a
**two-sided contract**. BOTH proxies on the connection must agree:

- The **destination** pod (postgres/redis) must say "my port is opaque"
  → its INBOUND proxy tunnels raw TCP. *(This was already set.)*
- The **caller** pod (the Go service) must ALSO say "I treat that port
  as opaque" → its OUTBOUND proxy skips protocol detection. *(This was
  MISSING — that was the bug.)*

Linkerd 2.14 does **not** automatically figure out the caller side from
the destination's setting. So the Go pods' outbound proxies kept doing
protocol detection on the postgres handshake and resetting it.

**Why removing `appProtocol` mattered too:** the postgres/redis
Services had `appProtocol: postgresql` / `appProtocol: redis`. That is a
hint telling proxies "manage this as a known L7 protocol" — the exact
opposite of "opaque". It directly contradicted the pods' opaque-ports
setting. Removing it leaves opaque-ports as the single, consistent
instruction governing the hop.

**Security is unchanged.** "Opaque" still means fully **mTLS-encrypted**
between the two proxies — it only means "encrypt but don't inspect".
We did NOT turn off the mesh or encryption for these hops. The only
thing lost is L7 (per-query) mesh metrics on the data hops, which
Linkerd can't produce for binary protocols anyway. The dedicated
postgres/redis Prometheus exporters on their `:9187` / `:9121` HTTP
ports are untouched and still scraped.

---

## 4. Exact files and places changed

### 4a. `appProtocol` removed (destination Services)

| File | What was removed | Kept |
|---|---|---|
| `helm/data-layer/templates/postgres-service.yaml` | `appProtocol: postgresql` from the `postgres` ClusterIP Service (port 5432) **and** the `postgres-headless` Service (port 5432) | `appProtocol: http` on the `metrics` port `:9187` (genuinely HTTP) |
| `helm/data-layer/templates/redis-service.yaml` | `appProtocol: redis` from the `redis` ClusterIP Service (port 6379) **and** the `redis-headless` Service (port 6379) | `appProtocol: http` on the `metrics` port `:9121` (genuinely HTTP) |

`helm/data-layer/templates/chromadb-service.yaml` was already correct
(no `appProtocol`) and was NOT changed.

### 4b. Caller-side opaque-ports added (the actual fix)

Added `config.linkerd.io/opaque-ports: "5432,6379"` to `podAnnotations`:

| File | Service |
|---|---|
| `helm/gateway/values.yaml` | gateway |
| `helm/execution/values.yaml` | execution |
| `helm/management/values.yaml` | management |
| `helm/billing/values.yaml` | billing (the stale comment claiming the proxy "auto-marks" datastore ports was also corrected) |

These pods already had `linkerd.io/inject: enabled`,
`config.linkerd.io/proxy-enable-native-sidecar: "true"`, and
`config.linkerd.io/skip-outbound-ports: "4317"` (OTLP); only
`opaque-ports` was missing.

### 4c. Commits (on `main`)

- `phase10.6 fix(data-layer): remove appProtocol:postgresql from postgres Service`
- `phase10.6 fix(data-layer): remove appProtocol:redis from redis Service`
- `phase10.6 fix(go-services): add caller-side opaque-ports 5432,6379` (gateway/execution/billing)
- `phase10.6 fix(management): add caller-side opaque-ports 5432,6379`

---

## 5. The matching state on the destination side (for reference)

These were ALREADY present and were NOT changed — they are the
"other half" of the two-sided contract:

- `helm/data-layer/values.yaml` → `postgres.podAnnotations` →
  `config.linkerd.io/opaque-ports: "5432"`
- `helm/data-layer/values.yaml` → `redis.podAnnotations` →
  `config.linkerd.io/opaque-ports: "6379"`
- `helm/data-layer/values.yaml` → `chromadb.podAnnotations` →
  `config.linkerd.io/opaque-ports: "8000"`

---

## 6. How to REVERT

Reverting puts the contradiction back and WILL re-break the meshed
Go-service → postgres/redis hops. Only revert if you are also doing
one of: (a) moving postgres/redis off-cluster (managed), (b) upgrading
Linkerd to a version with different opaque-handling and re-testing, or
(c) deliberately un-meshing the Go services.

### Option A — full revert (undo both changes)

1. **Re-add `appProtocol`** to the data Services:
   - `helm/data-layer/templates/postgres-service.yaml`: add back
     `appProtocol: postgresql` to BOTH the `postgres` and
     `postgres-headless` Services on port 5432.
   - `helm/data-layer/templates/redis-service.yaml`: add back
     `appProtocol: redis` to BOTH the `redis` and `redis-headless`
     Services on port 6379.
2. **Remove the caller-side opaque-ports** line
   `config.linkerd.io/opaque-ports: "5432,6379"` from the
   `podAnnotations` of:
   `helm/gateway/values.yaml`, `helm/execution/values.yaml`,
   `helm/management/values.yaml`, `helm/billing/values.yaml`.
3. Commit on `main`, push to GitHub (ArgoCD source) and GitLab mirror.
4. `argocd app sync data-layer-staging gateway-staging execution-staging management-staging billing-staging --grpc-web`
5. `kubectl -n etradie-system rollout restart deployment etradie-gateway etradie-execution etradie-management etradie-billing`

### Option B — keep appProtocol removed, only drop opaque-ports

If you only want to undo the caller-side opaque-ports (e.g. testing a
Linkerd upgrade that auto-handles it), do only step 2 + 3 + sync +
rollout from Option A. Leave the Services without `appProtocol`.

### Recommended safest revert path (if un-meshing is acceptable)

If the goal is simply to stop fighting the mesh on the data hops, the
lower-risk move is NOT to re-add appProtocol, but to set
`linkerd.io/inject: "disabled"` on the Go-service pods (same escape
hatch used for the engine). That keeps every other hop meshed and
avoids the contradiction entirely. Document it if you do.

---

## 7. How to VERIFY (after apply OR after revert)

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml

# 1. Services: data ports should have EMPTY appProtocol (current state),
#    or `postgresql`/`redis` if you reverted.
kubectl -n etradie-system get svc postgres redis \
  -o jsonpath='{range .items[*]}{.metadata.name}{": "}{range .spec.ports[*]}{.name}{"="}{.appProtocol}{" "}{end}{"\n"}{end}'
# applied  -> postgres: postgres= metrics=http   redis: redis= metrics=http
# reverted -> postgres: postgres=postgresql metrics=http   redis: redis=redis metrics=http

# 2. A fresh Go pod should carry opaque-ports (current state) or not (reverted).
GW=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-gateway \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl -n etradie-system get pod "$GW" \
  -o jsonpath='{.metadata.annotations.config\.linkerd\.io/opaque-ports}'; echo
# applied -> 5432,6379   reverted -> (empty)

# 3. The four Go services should be 2/2 Ready when APPLIED.
kubectl -n etradie-system get pods -l 'app.kubernetes.io/part-of=etradie' --no-headers \
  | grep -vE 'mt-node|postgres|redis|chromadb'

# 4. No reset in the logs when APPLIED.
kubectl -n etradie-system logs "$GW" -c gateway --tail=10 | grep -i 'connection reset' \
  && echo 'STILL BROKEN' || echo 'OK: no reset'
```

A correctly-applied state shows: empty appProtocol on data ports,
`5432,6379` opaque-ports on the Go pods, all four Go services `2/2`
Ready, and no `connection reset by peer` in their logs.

---

## 8. Related note — the engine is separate

The engine's staging mesh was DISABLED for a different reason (an
engine → chromadb outbound opaque-discovery issue), tracked separately.
The engine is un-meshed in staging and `1/1` Ready; it connects to
TLS postgres via native asyncpg (`ENGINE_DB_NATIVE_TLS=true`). The
opaque-ports change in this document is for the four meshed Go services
and does NOT affect the engine. Production engine mesh is untouched.
