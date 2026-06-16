# Phase 10.6 Checkpoint — Engine RAG bootstrap blocker (chromadb mesh path)

> **Status: 🟡 IN PROGRESS — engine still CrashLoopBackOff.** 3 of 4 root
> causes FIXED; 1 open (linkerd-policy Service endpoint staleness causing
> chromadb L7 fail-fast). Read this top-to-bottom before touching anything.
> This supersedes the provisional "operator gotcha #36" in PROGRESS.md
> (that hypothesis — "Linkerd 2.14.10 opaque-port outbound silently fails"
> — was WRONG; the real causes are documented below).

**Last updated:** 2026-06-16, mid-session.
**Cluster:** staging, single-node Contabo K3s, mesh ON.
**Symptom:** `etradie-engine` CrashLoopBackOff. FastAPI lifespan dies at
`engine/main.py:107 -> rag_bootstrap_service.bootstrap()`.

---

## TL;DR for the next operator

The engine's RAG bootstrap fails at its FIRST step,
`bootstrap_collections()` (chromadb), with:

```
RAGVectorStoreConnectionError: Failed to connect to ChromaDB at
  chromadb.etradie-system.svc.cluster.local:8000
  (bootstrap.py:49)
```

The chromadb HTTP call (`GET /api/v2/auth/identity`, made by
`chromadb.HttpClient()` on construction) returns **504 Gateway Timeout
then 503 fail-fast** through the Linkerd mesh, while chromadb itself is
healthy (200/0.01s on loopback inside its own pod).

Root cause of the 504/503: the Linkerd **policy controller**
(`linkerd-policy.linkerd.svc:8090`, hosted in the `linkerd-destination`
pod) was being dialed by chromadb's inbound proxy at a **dead/stale pod
IP**, because `linkerd-destination` rolled multiple times during this
session (mostly during an earlier mistaken Linkerd version-bump arc) and
the `linkerd-policy` Service Endpoints lagged behind the live pod IP.
chromadb is the ONLY data-layer service that does L7/HTTP through the
proxy (it has `appProtocol: http`), so it is the only one that depends on
the policy controller on its data path. postgres/redis are opaque-ports
(raw-TCP mTLS), bypass the policy controller, and have worked throughout.

**The endpoint was reconciled** (rollout-restart of linkerd-destination;
`linkerd-policy` endpoint now == live destination pod IP 10.42.0.24), BUT
the engine + chromadb proxies that were already running raced/ did not
pick up the corrected endpoint, so the engine still fails. The next
session must restart chromadb + engine in a clean window AFTER confirming
the policy endpoint is live, and verify a fresh meshed probe reaches
chromadb BEFORE relying on the engine.

---

## The 4 root causes (this whole session was one bug with four layers)

The engine RAG bootstrap touches, in order: chromadb (collections) ->
postgres (seed + draft query) -> read knowledge files (ingest) ->
chromadb (embed/upsert). Each layer had its own defect; they were
discovered and fixed one at a time as each unblocked the next.

| # | Layer | Root cause | Status | Fix commit / action |
|---|---|---|---|---|
| 1 | postgres/redis mesh inbound | Every meshed service NetworkPolicy admitted only the app port (5432/6379/8000/...) + 4191, never the Linkerd proxy inbound port **4143**. Meshed proxy-to-proxy connections arrive on :4143 and the CNI dropped them. | ✅ FIXED + LIVE-VERIFIED | commits `57e73bf6`, `4ec17f6e`, `0d3e9a51`, `3f23c7d8`, `74574c4c` (4143 ingress on all 8 meshed services). Proven: meshed probe -> postgres `SELECT 1 = 1` with NetworkPolicy in place. |
| 2 | chromadb mesh treatment | chromadb is `appProtocol: http` (L7), so its proxy depends on the linkerd-policy controller. When that's unreachable, the engine's outbound proxy enters fail-fast -> 504/503. postgres/redis (opaque) are immune. | ✅ FIXED (chart) | commit `c52ea2fc` — added `config.linkerd.io/opaque-ports: "8000"` to chromadb podAnnotations (matches postgres/redis; raw-TCP mTLS, no L7 policy dependency). Live-proven once (bootstrap got PAST chromadb when both proxies were fresh). |
| 3 | knowledge files missing from image | The engine RAG bootstrap reads 9 knowledge docs from `/app/knowledge`, but the Dockerfile never copied `knowledge/`, AND `.dockerignore` excluded `*.md` + `knowledge/scenarios/`. RAGLoaderError on `master_rulebook.md`. | ✅ FIXED + VERIFIED IN IMAGE | commit `c52ea2fc` (`COPY knowledge/`) + commit (`.dockerignore` re-include `!knowledge` / `!knowledge/**`, drop `knowledge/scenarios/`). CI engine build = success. Verified: `find /app/knowledge -name '*.md'` lists all 9 docs in the new image (digest sha256:8c93d709...). |
| 4 | linkerd-policy endpoint staleness | `linkerd-destination` rolled repeatedly this session; the `linkerd-policy` Service Endpoints pointed at dead pod IPs (10.42.0.209 / 10.42.0.249 / 10.42.0.154 at various points). chromadb's proxy got `Connection refused` on :8090 -> no inbound policy -> refuses :8000 -> engine 504/fail-fast. | 🟡 PARTIALLY FIXED — endpoint reconciled, proxies not yet confirmed to pick it up | `kubectl -n linkerd rollout restart deployment linkerd-destination` made `linkerd-policy` endpoint == live pod IP 10.42.0.24. BUT engine still crashes — chromadb/engine proxies need a clean restart AFTER the endpoint settled. THIS IS THE OPEN BLOCKER. |

---

## What is PROVEN (do not re-test these)

- postgres + redis reachable through the mesh from the engine identity
  (`db.health_check()` returns True; meshed probe `SELECT 1` works). The
  4143 NetworkPolicy fix is correct and necessary.
- asyncpg with `ssl=False` + `server_settings` (the engine's exact DB
  connect args) works through the mesh — the DB connection code is fine;
  the engine's crashes were NEVER a postgres problem (the wrapped
  "connection was closed in the middle of operation" was misleading;
  the real first failure is always chromadb at bootstrap.py:49).
- All 9 knowledge docs ARE in the new engine image
  (digest sha256:8c93d709da3cfbd220d3957afc65a152a3f759e8b94fd03e956d33959ac4c591).
- chromadb itself is healthy: `GET /api/v2/auth/identity` over loopback
  inside chromadb-0 returns HTTP 200 in 0.01s. The token matches
  (engine RAG_CHROMA_AUTH_TOKEN sha == chromadb CHROMA_SERVER_AUTHN_CREDENTIALS
  sha == e0675e34e492...).
- The linkerd policy controller process is healthy and listening
  (`policy gRPC server listening addr=0.0.0.0:8090`); the problem was the
  Service Endpoints pointing at a dead pod IP, NOT the controller itself.

## What was RULED OUT (dead ends — do NOT retry)

- NOT a Linkerd version bug. The 2.14.10 -> 2.14.12 / 2.16 upgrade idea
  was abandoned: `helm.linkerd.io/stable` only ships up to
  control-plane 1.16.11 / crds 1.8.0 (2.14.10); there is no newer stable.
  The bad version-bump commit was reverted.
- NOT the asyncpg ssl=False translation (engine connection.py) — proven
  to work via direct probe.
- NOT the engine ServiceAccount identity or pod annotations — a probe
  with engine SA + engine annotations connected fine.
- NOT a token mismatch — sha256 of both chromadb tokens are identical.
- NOT chromadb server-side telemetry/posthog backoff — chromadb auth
  handler responds in 0.01s on loopback regardless of telemetry noise.
- NOT the engine NetworkPolicy egress — engine failed identically with
  its NetworkPolicy deleted entirely.
- NOT "opaque-ports silently fails on 2.14.10" (the old PROGRESS gotcha
  #36 hypothesis) — that was wrong; the real cause is the policy-endpoint
  staleness above.

---

## Fix commits landed this session (GitLab + GitHub `main`)

| Commit | What |
|---|---|
| `57e73bf6` | NetworkPolicy 4143 — RCA + revert dead Linkerd bump |
| `4ec17f6e` | 4143 ingress: postgres/redis/chromadb |
| `0d3e9a51` | 4143 ingress: engine/gateway/execution/management/billing |
| `3f23c7d8` | 4143 ingress: envoy + edge-ingress + gateway(envoy-system) |
| `74574c4c` | 4143 ingress: mt-node (audit completion, 8/8 meshed services) |
| `c52ea2fc` | `COPY knowledge/` in engine Dockerfile + chromadb opaque-ports 8000 |
| (`.dockerignore` fix) | re-include `!knowledge` / `!knowledge/**`, drop `knowledge/scenarios/` (engine build was failing) |

PLUS one commit prepared but **NOT yet pushed to GitHub** (held on
GitLab only, intentionally): `security(deps): bump aiohttp 3.14.0->3.14.1
and cryptography 46.0.7->48.0.1`. These clear the pip-audit CI failures
(newly-published CVEs from a CVE-DB refresh, NOT introduced by us). The
trivy `form-data` HIGH in `cotradee/package-lock.json` is the frontend
(out of scope) and was deliberately NOT touched. Neither pip-audit nor
trivy gates the CI `build` job (build needs only [test, test-go, helm]),
so the engine image still builds + pushes despite them being red.

---

## EXACT RESUME STEPS (next session — do these in order)

```bash
# 0. Reopen the SSH tunnel (it dropped at end of last session) + KUBECONFIG
ssh-add ~/.ssh/id_ed25519
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173   # dedicated terminal
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes   # confirm reachable

# 1. Confirm linkerd-policy endpoint == live destination pod IP (the open fix).
kubectl -n linkerd get pod -l linkerd.io/control-plane-component=destination \
  -o jsonpath='dest_ip={.items[0].status.podIP}{"\n"}'
kubectl -n linkerd get endpoints linkerd-policy \
  -o jsonpath='policy_ep={.subsets[*].addresses[*].ip}{"\n"}'
# They MUST match. If not, rollout-restart linkerd-destination and wait.

# 2. Restart chromadb so its proxy resolves the CURRENT policy endpoint,
#    and CONFIRM its proxy is clean (no 'Connection refused' to :8090).
kubectl -n etradie-system delete pod chromadb-0
kubectl -n etradie-system wait --for=condition=Ready pod/chromadb-0 --timeout=180s
sleep 10
kubectl -n etradie-system logs chromadb-0 -c linkerd-proxy --tail=20 \
  | grep -iE 'refused|fail-fast|8090|Certified'
# WANT: 'Certified identity', NO recent 'Connection refused' to :8090.

# 3. PROVE the path with a FRESH meshed probe BEFORE touching the engine.
#    (engine image has the venv; engine SA + mesh annotations.)
ENGINE_IMG=$(kubectl -n etradie-system get deploy etradie-engine \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="engine")].image}')
kubectl -n etradie-system delete pod cprobe --ignore-not-found --force --grace-period=0 2>/dev/null
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: cprobe
  namespace: etradie-system
  labels: {app: cprobe, app.kubernetes.io/name: cprobe}
  annotations:
    linkerd.io/inject: enabled
    config.linkerd.io/proxy-enable-native-sidecar: "true"
spec:
  serviceAccountName: etradie-engine
  imagePullSecrets: [{name: ghcr-pull}]
  securityContext: {runAsNonRoot: true, runAsUser: 1000, runAsGroup: 1000, fsGroup: 1000, seccompProfile: {type: RuntimeDefault}}
  containers:
    - name: c
      image: ${ENGINE_IMG}
      command: ["sleep","300"]
      resources: {requests: {cpu: 50m, memory: 64Mi}, limits: {cpu: 200m, memory: 256Mi}}
      securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, runAsNonRoot: true, runAsUser: 1000, capabilities: {drop: [ALL]}}
      volumeMounts: [{name: t, mountPath: /tmp}, {name: h, mountPath: /home/etradie/.cache}]
  volumes: [{name: t, emptyDir: {}}, {name: h, emptyDir: {}}]
EOF
kubectl -n etradie-system wait --for=condition=Ready pod/cprobe --timeout=120s
TOK=$(kubectl -n etradie-system get secret etradie-engine-secrets -o jsonpath='{.data.RAG_CHROMA_AUTH_TOKEN}' | base64 -d)
kubectl -n etradie-system exec cprobe -c c -- python3 -c "
import urllib.request,time
for i in range(4):
  t=time.monotonic()
  try:
    r=urllib.request.urlopen(urllib.request.Request('http://chromadb.etradie-system.svc.cluster.local:8000/api/v2/auth/identity',headers={'Authorization':'Bearer $TOK'}),timeout=15)
    print(f'  try {i+1}: HTTP {r.status} in {time.monotonic()-t:.2f}s')
  except Exception as e:
    print(f'  try {i+1}: {type(e).__name__}: {str(e)[:55]} after {time.monotonic()-t:.2f}s')
  time.sleep(2)
"
unset TOK

# 4a. IF cprobe gets HTTP 200 -> path is clean. Restart the engine; it will
#     boot through bootstrap_collections -> seed -> ingest 9 docs ->
#     rag_bootstrap_completed -> 2/2 Running.
kubectl -n etradie-system delete pod -l app.kubernetes.io/name=etradie-engine
sleep 90
NEWPOD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o jsonpath='{.items[0].metadata.name}')
kubectl -n etradie-system get pod "$NEWPOD" -o custom-columns=READY:.status.containerStatuses[*].ready,PHASE:.status.phase,RESTARTS:.status.containerStatuses[*].restartCount
kubectl -n etradie-system logs "$NEWPOD" -c engine --tail=60 2>&1 | grep -iE 'rag_bootstrap|loaded_markdown|ingesting|rag_startup|application_started|error'

# 4b. IF cprobe STILL 504/fail-fast -> chromadb's inbound proxy still cannot
#     reach the policy controller. Escalation options, in order:
#     (i)   restart linkerd-destination AGAIN, wait for endpoint to settle,
#           THEN restart chromadb (ordering matters — destination first).
#     (ii)  restart linkerd-proxy-injector too (clears injected-config cache),
#           then chromadb.
#     (iii) last resort to unblock staging: the engine reaching chromadb does
#           NOT strictly require chromadb's L7 policy if BOTH sides are
#           opaque on :8000 — verify chromadb opaque-ports=8000 is on the
#           live pod (it is, per c52ea2fc) AND that the engine's OUTBOUND
#           to chromadb is treated opaque. If the engine still does L7 to
#           chromadb, that's the engine pod's skip/opaque config, not
#           chromadb's. Re-check engine podAnnotations.
```

## Phase 10.6 closeout TODOs (after engine reaches 2/2 Running)

1. Confirm cascade: gateway/execution/management/billing init containers
   clear and pods reach Running (they wait on engine).
2. Push the held `security(deps)` commit (aiohttp/cryptography) from
   GitLab to GitHub so CI pip-audit goes green.
3. (Optional) bump `form-data` -> 4.0.6 in `cotradee/package-lock.json`
   for a fully-green trivy (frontend, out of scope but trivial).
4. Delete the debug probe pods: `kubectl -n etradie-system delete pod
   cprobe asyncpg-probe mesh-probe pg-probe-bare --ignore-not-found`.
5. Clean up the doubled-prefix Vault entries (14) + vault-auth
   non-expiring token + disable /tmp/vault-audit.log (carried over from
   the earlier Phase 10 continuation TODOs).
6. Update PROGRESS.md status board: Phase 10 -> ✅, move to Phase 11.
7. Remove the stale provisional "operator gotcha #36" from PROGRESS.md
   (the opaque-ports-silently-fails hypothesis was WRONG; the real
   causes are documented in this checkpoint).

## Operator gotchas confirmed this session

- The wrapped `RAGBootstrapError: ... connection was closed in the middle
  of operation` is MISLEADING — it's asyncpg phrasing but the FIRST real
  failure is `bootstrap_collections` (chromadb) at bootstrap.py:49, which
  runs BEFORE any postgres call. Always get the UNWRAPPED traceback (run
  the bootstrap directly in a probe with the engine image + full env).
- chromadb is the ONLY data service that is L7/HTTP through the proxy
  (`appProtocol: http`); it alone depends on the linkerd-policy
  controller on its data path. opaque-ports (postgres/redis/now-chromadb)
  bypass that dependency.
- Repeated `linkerd-destination` rollouts leave the `linkerd-policy`
  Service Endpoints stale, breaking every L7 meshed hop until the
  endpoint reconciles AND the dependent proxies restart. Avoid
  gratuitous control-plane restarts.
- CI `build` job does NOT depend on pip-audit/trivy (needs only
  [test, test-go, helm]); the engine image builds + pushes even when
  those security jobs are red. ArgoCD pulls from GHCR regardless of CI
  gate color.
- `.dockerignore` `*.md` exclusion silently strips the knowledge base
  from the engine build context; `COPY knowledge/` needs the
  `!knowledge` / `!knowledge/**` re-include.
