# Phase 10.6 Checkpoint — Linkerd mesh DISABLED on 5 staging workloads

> **Active checkpoint. Read in full before re-enabling mesh on any of
> the affected services or before promoting any of these chart changes
> to production.** The rest of `PROGRESS.md` only cross-references this
> file; the canonical record of WHAT is disabled, WHY, HOW to verify,
> and HOW to re-enable lives here.

## TL;DR for the next operator

Five staging workloads currently run with `linkerd.io/inject: "disabled"`:

| Namespace | Workload | Disabled how |
|---|---|---|
| `etradie-system` | `etradie-engine` (Deployment) | committed in `helm/engine/values-staging.yaml::podAnnotations` |
| `etradie-system` | `etradie-gateway` (Deployment) | live-only on the cluster (annotation applied via `kubectl patch`; NOT yet committed to `helm/gateway/values-staging.yaml`) |
| `etradie-system` | `etradie-execution` (Deployment) | live-only on the cluster (NOT yet committed to `helm/execution/values-staging.yaml`) |
| `etradie-system` | `etradie-management` (Deployment) | live-only on the cluster (NOT yet committed to `helm/management/values-staging.yaml`) |
| `etradie-system` | `etradie-billing` (Deployment) | live-only on the cluster (NOT yet committed to `helm/billing/values-staging.yaml`) |

**Drift risk:** the 4 Go services' mesh-disable is on the live
Deployment specs only. ArgoCD with `selfHeal: true` may reconcile the
pod template back to the chart-rendered spec (which lacks the
annotation) on the next sync; the staging children's `automated.
{prune:true, selfHeal:true}` makes this likely. Before the next
ArgoCD reconcile of any of these 4 Applications, either commit the
annotation to each chart's `values-staging.yaml` OR re-apply the
live patch immediately after sync. Engine is safe (committed).

Everything else stays meshed:

| Namespace | Workload | Mesh state |
|---|---|---|
| `etradie-system` | `postgres-0` (StatefulSet) | meshed (`linkerd-proxy` + `postgres` + `postgres-exporter`) |
| `etradie-system` | `redis-0` (StatefulSet) | meshed (`linkerd-proxy` + `redis` + `redis-exporter`) |
| `etradie-system` | `chromadb-0` (StatefulSet) | meshed (`linkerd-proxy` + `chromadb`) |
| `edge-ingress-system` | `edge-ingress` (Deployment) | meshed (`linkerd-proxy` + `edge-ingress`) |
| `envoy-system` | `etradie-envoy` (Deployment) | meshed (`linkerd-proxy` + `envoy`) |
| `edge-ingress-system` | `cloudflared` (Deployment) | NOT meshed (no annotation; intentional — cloudflared dials Cloudflare edge over outbound :443/QUIC and the tunnel JWT is the trust boundary) |
| `linkerd`, `monitoring`, `argocd`, `vault`, `external-secrets`, `reloader` | platform infrastructure | meshed or N/A per chart base values |

## Verification on a live cluster

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml

echo "=== Pods + containers (look for linkerd-proxy presence) ==="
for ns in etradie-system edge-ingress-system envoy-system; do
  echo "--- $ns ---"
  kubectl -n "$ns" get pods -o custom-columns='NAME:.metadata.name,CONTAINERS:.spec.containers[*].name,INJECT:.metadata.annotations.linkerd\.io/inject'
done

echo
echo "=== Deployment / StatefulSet pod-template annotations ==="
for ns in etradie-system edge-ingress-system envoy-system; do
  echo "--- $ns ---"
  kubectl -n "$ns" get deploy,statefulset \
    -o custom-columns='KIND:.kind,NAME:.metadata.name,INJECT:.spec.template.metadata.annotations.linkerd\.io/inject'
done
```

Expected steady-state output (the 5 disabled rows are the working
posture; data-layer + envoy + edge-ingress meshed):

```
etradie-billing       INJECT=disabled    containers: billing
etradie-engine        INJECT=disabled    containers: engine
etradie-execution     INJECT=disabled    containers: execution
etradie-gateway       INJECT=disabled    containers: gateway
etradie-management    INJECT=disabled    containers: management
chromadb-0            INJECT=enabled     containers: linkerd-proxy, chromadb
postgres-0            INJECT=enabled     containers: linkerd-proxy, postgres, postgres-exporter
redis-0               INJECT=enabled     containers: linkerd-proxy, redis, redis-exporter
edge-ingress-*        INJECT=enabled     containers: linkerd-proxy, edge-ingress
etradie-envoy-*       INJECT=enabled     containers: linkerd-proxy, envoy
cloudflared-*         INJECT=<none>      containers: cloudflared
```

If any of the 5 disabled services flips to `enabled` after an ArgoCD
reconcile and starts CrashLooping, that is the drift documented above:
the live patch was reverted and the chart's `values-staging.yaml`
still doesn't carry the disable. Either re-apply the live patch or
commit the chart change (see "Re-enable / re-pin" section below).

## Why mesh is disabled on each service

All 5 share the same class of failure observed across the Phase 10.6
staging bring-up: at FastAPI / Go HTTP-server startup, the pod's
first outbound call (DB / Redis / cache / chromadb / another service)
fires within tens of milliseconds of the linkerd2 proxy becoming
`Certified`. In that window, the proxy's outbound discovery / route
layer is not yet warm, and Linkerd 2.14's behaviour on a single-node
K3s with native sidecar is to reset the connection ("Connection
reset by peer" / `502` / `503 fail-fast`). The app crashes on its
first dependency check, K8s restarts the pod, the race repeats.

The engine case is the most documented because its FastAPI lifespan
failures produced the loudest stack traces (`RAGBootstrapError ...
failed to connect to ChromaDB`, `connection was closed in the middle
of operation` from asyncpg, etc.). The 4 Go services hit the same
class of race on their first `pgxpool` / `redis.Client` /
`http.Client` call during `main()` initialisation, surfacing as
plain `dial tcp ...: connection reset by peer` from inside the
pod logs.

What we tried, in roughly chronological order, before settling on
the broader mesh-disable as the staging unblock:

1. NetworkPolicy 4143 fix on every meshed service (the 5 service
   NetworkPolicies were admitting only the app port + 4191, dropping
   the meshed proxy-to-proxy hop on :4143). Necessary, not
   sufficient. Commits `57e73bf6`, `4ec17f6e`, `0d3e9a51`,
   `3f23c7d8`, `74574c4c`.
2. `config.linkerd.io/opaque-ports: "8000"` on chromadb so the engine
   would tunnel raw TCP to it instead of doing L7/HTTP through the
   proxy. Necessary for chromadb specifically; commit `c52ea2fc`.
3. `config.linkerd.io/proxy-await: "enabled"` on engine to make
   linkerd-init gate the app container on proxy readiness. Helped
   but did not eliminate the race.
4. Engine lifespan re-order + retry-with-backoff prototypes + OTel
   instrumentation version bump + pre-baking HF model + base-image
   digest pin. Resolved engine-internal startup issues unrelated to
   mesh but did not fix the mesh-side race.
5. postgres TLS server-side (`tls-cert-init` initContainer + `-c
   ssl=on`) so the engine asyncpg / Go pgx clients negotiate TLS
   against a TLS-serving postgres (matches the apps'
   `sslmode=require` config validators). Necessary and committed;
   resolved one class of "Connection reset by peer" but not the
   class that surfaces against redis and chromadb hops.

After (1)–(5) the engine's failure mode shifted from
"can't reach postgres" to "502 / Connection refused at chromadb".
The 4 Go services then surfaced their own analogous resets at
run-time. At that point we disabled mesh on the 5 affected
workloads to unblock the public-path verification.

## What stays ON / works correctly in staging without mesh on these 5

- **Cloudflare DDoS / WAF / origin-IP secrecy / tunnel JWT auth**:
  unaffected.
- **ufw inbound deny**: unaffected.
- **cloudflared → edge-ingress TLS** with the internal CA bundle
  (mTLS server-auth one direction; AOP client-cert OPTIONAL after the
  `client_auth.required` rust change landed): working.
- **edge-ingress → envoy → gateway / billing**: working via envoy's
  upstream clusters. The envoy ↔ edge-ingress hop is meshed.
- **Gateway's trust-aware `CF-Connecting-IP` resolution**: working
  via `trustChain.trustedProxyCidrs: ["10.42.0.0/16"]` in
  `helm/gateway/values-staging.yaml` (any pod-network peer is
  treated as a trusted proxy that may set `CF-Connecting-IP`).
- **Linkerd mesh mTLS on the data-layer hops**: postgres / redis /
  chromadb continue to mTLS each other and the meshed edge
  (edge-ingress + envoy). The 5 disabled services dial them in
  plaintext (their outbound is no longer wrapped by a proxy).

## What is LOST while these 5 are mesh-disabled

- **Service-identity mTLS on east-west calls leaving the 5 services**.
  Their outbound to postgres / redis / chromadb / each other is
  plaintext on the pod network. Inside the K3s cluster network
  namespace this is still gated by ufw + NetworkPolicies, but the
  cryptographic identity binding the mesh provides is absent for
  these hops.
- **Linkerd-viz observability** for these 5 services (`linkerd viz
  stat`, `linkerd viz edges`, `linkerd viz routes`) — they don't show
  up in the mesh telemetry because there's no proxy to scrape.
- **Per-route authorisation policy** via Linkerd `Server` /
  `AuthorizationPolicy` resources: cannot apply to these 5 until
  the proxy is back.

This is acceptable for staging because the trust boundary remains
at Cloudflare's edge + ufw + the tunnel JWT, and inside the cluster
the pod network is private. It is NOT acceptable for production —
see the re-enable plan below.

## Re-enable / re-pin plan (must run BEFORE production cutover)

The order matters because the 4 Go services have a downstream
dependency on the engine being Ready (their wait-for-deps init
container probes engine's `/readiness`).

### Step 1 — fix the underlying race in each service's startup path

The right long-term fix is application-side retry-with-backoff on
the first dependency call:

- **engine (`src/engine/main.py::lifespan`)**: wrap the first
  `database.health_check()`, `cache.ping()`, and
  `rag_bootstrap_service.bootstrap()` in a retry loop that tolerates
  `Connection reset by peer` / `Connection refused` / `502` for ~5
  seconds before giving up. The lifespan already has exponential
  backoff on DB + cache; extend to the chromadb hop too.
- **gateway / execution / management / billing**: each Go service's
  `main.go` opens `pgxpool.New(...)`. Wrap that in `backoff.Retry`
  (already imported in `internal/util/retry`) with a 5–10s budget
  tolerant of the same error class. Same pattern for the
  `redis.NewClient(...).Ping(ctx)` call.

### Step 2 — validate against a freshly-rolled Linkerd control plane

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl -n linkerd rollout restart deployment linkerd-destination
kubectl -n linkerd rollout status deployment linkerd-destination --timeout=180s
```

This forces a fresh control-plane state so the data-layer pods'
proxies re-resolve the `linkerd-policy` Service Endpoints to the
live destination pod (Phase 10.6 operator gotcha — stale endpoints
are what made the engine ↔ chromadb mesh hop fail in the first
place).

### Step 3 — re-enable mesh, one service at a time, engine first

For each service, the chart change is to remove the
`linkerd.io/inject: "disabled"` annotation from the staging overlay
(the engine is the only one currently committed; the 4 Go services
are live-only and will need their staging overlays updated AT THE
SAME TIME the live patch is removed):

```yaml
# helm/engine/values-staging.yaml — delete this whole block from
# `podAnnotations:` (the TEMPORARY ... REVERT PATH ... comment block
# and the `linkerd.io/inject: "disabled"` line beneath it).

# helm/gateway/values-staging.yaml — ADD a podAnnotations stanza if
# it doesn't already exist, with the inject annotation set to enabled.
# Same for execution / management / billing. The base values.yaml in
# each chart already enables mesh; the overlay just needs to NOT
# override that.
```

Then for each service in order (engine, then any one of the 4 Go
services, watching it for ~5 minutes before moving on):

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
argocd app sync engine-staging --grpc-web --timeout 600
argocd app wait engine-staging --health --timeout 600
kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o wide
# expect: 2/2 Running, containers linkerd-proxy + engine.
kubectl -n etradie-system logs -l app.kubernetes.io/name=etradie-engine -c engine \
  --tail=50 | grep -iE 'rag_bootstrap|application_started|error'
# expect: rag_bootstrap_completed and application_started, no errors.
```

If the engine flips back to CrashLoopBackOff after re-enabling, the
startup-race fix in Step 1 is not yet sufficient. Re-add the
`linkerd.io/inject: "disabled"` and revisit Step 1 — do NOT brute-
force by restarting things repeatedly.

### Step 4 — verify mesh telemetry sees all 5 services

After all 5 are back on mesh:

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl -n linkerd get pods   # control plane Healthy
# Optional: install linkerd-viz on demand and:
# linkerd viz stat deploy -n etradie-system
# linkerd viz edges -n etradie-system
# Every meshed deployment should appear in the output.
```

### Step 5 — production overlay sanity

Confirm `helm/{engine,gateway,execution,management,billing}/values-production.yaml`
does NOT carry `linkerd.io/inject: "disabled"`. Production must be
mesh-on end-to-end. If any production overlay accidentally inherited
the staging disable (it shouldn't have — staging overlays are
separate files), remove it BEFORE the production cutover.

## How this checkpoint was reached (audit trail summary)

The Phase 10.6 bring-up arc spanned multiple debug sessions and
produced multiple intermediate fixes that ARE committed and ARE
correct (NetworkPolicy 4143, chromadb opaque-ports, postgres TLS,
edge-ingress mTLS optional, envoy `/healthz` direct response). The
mesh-disable on these 5 services is the LAST remaining temporary
posture from that arc; everything else is permanent.

The PROGRESS.md sections that documented the day-by-day debugging
(NetworkPolicy 4143 audit, chromadb appProtocol arc, OpenTelemetry
version bumps, postgres TLS bring-up, engine RAG bootstrap, etc.)
have been collapsed into a brief cross-reference pointing at this
file. The full debug detail is preserved in the git history of
PROGRESS.md if a future operator needs it.

## Operator gotchas confirmed during this checkpoint

1. **`kubectl patch` on a Deployment's pod template does not
   trigger an Argo `OutOfSync` immediately.** The 4 Go services
   were patched live and ArgoCD showed `Synced` for several
   minutes before the controller noticed the drift. Do NOT trust
   `argocd app list` as proof that the chart matches reality
   when a live patch is involved. Always cross-check with
   `kubectl get deploy -o jsonpath='{.spec.template.metadata.annotations}'`.
2. **`linkerd.io/inject: "disabled"` on the Deployment is enough
   to keep new pods unmeshed; you do NOT need to also strip the
   annotation from existing pods.** Pod recreation (rollout
   restart or natural pod replacement) is enough — but a stuck
   old pod still has the linkerd-proxy container until it is
   replaced.
3. **cloudflared is intentionally never meshed.** It dials
   Cloudflare's edge over outbound :443/QUIC and the tunnel JWT
   is the trust boundary; injecting a Linkerd proxy in front of
   that would break the QUIC handshake. The `helm/edge-ingress/
   templates/cloudflared-deployment.yaml` pod template carries no
   `linkerd.io/inject` annotation — leave it that way.

## Cross-references

- `PROGRESS.md` Phase 10 entry (status board + completion notes).
- `docs/runbooks/README.md` Phase 10 + Phase 14 (verification).
- `helm/engine/values-staging.yaml` (the one committed disable).
- `BUDGET.md` Table 2B (Linkerd `highAvailability` and `viz` are
  already OFF in staging per the budget profile; this checkpoint
  documents an additional temporary disable on top of that).
