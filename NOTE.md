
Both let you `kubectl` from your workstation against the K3s cluster on the VPS.

**`ssh-add ~/.ssh/id_ed25519`** — unlocks your SSH key once per WSL boot, so commands like `ssh` and `scp` don't prompt for the passphrase every time.

**`ssh -N -L 6443:127.0.0.1:6443 etradie@...`** — opens the encrypted tunnel that lets `kubectl get pods`, `kubectl apply`, `helm install`, `argocd app sync` (every Phase 3+ command on the workstation) reach the K3s API. Without this tunnel, kubectl hangs because the VPS firewall blocks the API publicly.

**Daily use pattern after a WSL reboot:**

```bash
ssh-add ~/.ssh/id_ed25519                                  # passphrase once
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173       # in a dedicated terminal, leave open
# then in other terminals, kubectl/helm/argocd just work
kubectl get nodes
```

That's it. Phase 3 onward needs both running.

WE ARE WORKING ON THE DEPLOYMENT FOR THE STAGING OF THE EXOPER. THE /docs/runbooks/README.md CONTAINS THE FULL DEPLOYMENT PHASES STEP BY STEP.

AND WE HAVE DONE PHASE 0, 1, 2, 3, 4, 5, 6, 7, 8 AND 9 AS YOU CAN SEE IN THE /docs/runbooks/README.md AND THE /docs/runbooks/PROGRESS.md

SO YOU EXAMINE BOTH FILES THOROUGHLY FROM THE BEGINNING TO THE END.

 EXAMINE IT  THOROUGHLY FROM  THE BEGINNING TO THE END BECAUSE YOU NEED TO UNDERSTAND AND KNOW HOW TO PICK UP FROM WHERE WE STOPPED

 SO WE ARE GOING TO CONTINUE WITH PHASE 10 THIS IS WHAT YOU SAID LAST IN THE PREVIOUS SESSION.


 THESE ARE THE LAST THINGS YOU ASKED ME TO DO IN THE PREVIOUS SESSION:




Committed. The fix:

- Migration 0028 now uses `sqlalchemy.inspect()` to check whether `auth_users` exists before attempting the FK creation.
- If it exists (re-run, upgrade, prior gateway start): FK created exactly as before. Zero behaviour change for existing clusters.
- If it doesn't exist (fresh deploy = current cluster state): FK skipped with a structured log. The `updated_by` column stays a plain VARCHAR(32) with no referential constraint. Same posture as migration 0011's `user_id` columns.
- Downgrade is also conditional so it doesn't error on a cluster where the FK was never created.

This unblocks the engine startup. Once gateway pod is up and `auth_users` table exists, an operator can add the FK in a future migration if strict referential integrity matters. For staging, it's not needed.

On the workstation:

```bash
cd ~/eTradie
git status                          # PROBLEM.md unstaged
git stash push -u -m "PROBLEM.md before alembic-0028 fix pull"

git pull --rebase gitlab main
git log --oneline -3                # latest: "phase10.6 fix: alembic 0028 conditional FK on auth_users..."

git push origin main                # CI rebuilds the engine image

git stash pop
```

Wait for CI to go green. Should be ~15 min — same as before. Then:

```bash
# Watch CI
gh run list --workflow=ci.yml --limit 3 --repo FlameGreat-1/eTradie
# Wait for all jobs ✓

# Force the cluster to re-pull the engine image with the new digest.
# (Same mutable-tag containerd cache invalidation as before.)
ssh etradie@13.140.164.173 \
  sudo k3s crictl rmi ghcr.io/flamegreat-1/etradie/engine:0.1.0

# Verify GHCR has a NEWER digest than 06ec7804 from this morning
GHCR_PAT=$(cat ~/.ghcr_pull_pat)
TOKEN=$(curl -sS -u "flamegreat-1:$GHCR_PAT" \
  "https://ghcr.io/token?service=ghcr.io&scope=repository:flamegreat-1/etradie/engine:pull" \
  | jq -r .token)
curl -sS -I -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.oci.image.manifest.v1+json,application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
  "https://ghcr.io/v2/flamegreat-1/etradie/engine/manifests/0.1.0" \
  | grep -i 'docker-content-digest'
unset GHCR_PAT TOKEN

# Force engine pod recreation
kubectl -n etradie-system delete pod -l app.kubernetes.io/name=etradie-engine
sleep 5

# Watch the new pod
kubectl -n etradie-system get pods -l app.kubernetes.io/name=etradie-engine -w
```

This time, the expected sequence:
1. `Init:0/3` → `Init:1/3` (wait-for-deps done — postgres/redis/chromadb reachable)
2. `Init:1/3` for ~15-30s (migrate runs alembic upgrade head: 33 migrations, 0028 logs the FK skip)
3. `Init:2/3` (migrate complete, linkerd-init starts)
4. `Init:3/3` (linkerd-init done)
5. `Running 1/2` (engine main starting, linkerd-proxy up)
6. `Running 2/2` (engine main bound to :8000, ready)

Once you see `2/2 Running` stable for 30+ seconds Ctrl-C the watch. Then paste:

```bash
# Verify alembic completed cleanly
kubectl -n etradie-system logs deploy/etradie-engine -c migrate --tail=30

# Engine HTTP health
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- \
  curl -sf http://localhost:8000/health 2>&1 | head -5

# Full namespace cascade state
kubectl -n etradie-system get pods

# Application state
argocd app list --grpc-web | grep staging
```

If the cascade unblocks, gateway/execution/management/billing will be progressing through their own init containers in the next 2-3 minutes. That gets us to Phase 10.6 fully closed.


Back on the workstation (close this VPS SSH, return to your WSL terminal):

```bash
exit                # close VPS SSH back to workstation

# 1. Wait for CI to finish on the de7a4c84 commit
gh run list --workflow=ci.yml --limit 2 --repo FlameGreat-1/eTradie
# Wait until the engine-ExternalSecret commit row shows ✓ Status

# 2. Sanity: tunnel + KUBECONFIG + argocd login
kubectl get nodes
argocd account list 2>&1 | head -3

# 3. Force ESO to re-resolve the engine secret with the new key mapping
kubectl -n etradie-system delete externalsecret etradie-engine

# 4. ArgoCD recreates the ExternalSecret (it owns the manifest) on next sync
argocd app get engine-staging --refresh >/dev/null
argocd app sync engine-staging --timeout 600

# 5. Verify the new key now appears in the materialized Secret
kubectl -n etradie-system get secret etradie-engine -o jsonpath='{.data}' \
  | jq 'keys[]' | grep -i internal_shared
# Expect: "ENGINE_INTERNAL_SHARED_SECRET"

# 6. Sanity-verify the value matches what gateway and execution hold
#    (sha256 to keep it out of scrollback)
for SVC in gateway engine execution management; do
  case "$SVC" in
    gateway)
      KEY=GATEWAY_ENGINE_INTERNAL_SHARED_SECRET
      SECRET=etradie-gateway
      ;;
    *)
      KEY=ENGINE_INTERNAL_SHARED_SECRET
      SECRET=etradie-$SVC
      ;;
  esac
  H=$(kubectl -n etradie-system get secret "$SECRET" -o jsonpath="{.data.$KEY}" 2>/dev/null \
        | base64 -d 2>/dev/null | sha256sum | head -c 16)
  echo "$SVC: $H"
done
# All four lines should print the SAME 16 hex chars. Per PROGRESS.md end-of-Phase-8 the
# canonical sha256 (full) starts with 6037ddef7ab86629..., so all four should be 6037ddef7ab86629.

# 7. Force the engine pod to re-create so it picks up the new env var.
#    (Reloader will also detect the Secret data delta; deleting the pod is faster.)
kubectl -n etradie-system delete pod -l app.kubernetes.io/name=etradie-engine

# 8. Watch
kubectl -n etradie-system get pods -l app.kubernetes.io/name=etradie-engine -w
```

Watch for `2/2 Running` stable for 30+s. Then:

```bash
NEWPOD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o jsonpath='{.items[0].metadata.name}')

echo "=== engine main stderr ==="
kubectl -n etradie-system logs "$NEWPOD" -c engine --tail=50

echo "=== engine /health ==="
kubectl -n etradie-system exec "$NEWPOD" -c engine -- curl -sf http://localhost:8000/health 2>&1 | head -5

echo "=== full cascade ==="
kubectl -n etradie-system get pods

echo "=== argocd staging apps ==="
argocd app list --grpc-web | grep staging
```

Paste the four blocks. If the sha256 in step 6 shows all four matching `6037ddef7ab86629`, no Vault work is needed at all and the engine will boot. If step 6 shows engine's hash mismatching the other three, only THEN do we go into Vault to fix it — and even then it's because something drifted post-Phase-8, not because the property is missing.



Two important findings from this output:

1. **The secret name is `etradie-engine-secrets`, not `etradie-engine`.** That's why steps 5 and 6 returned empty — I had the wrong name. The chart's `engine.secretName` helper produces `etradie-engine-secrets` (you can see it in the argocd app output: `etradie-engine-secrets   OutOfSync   Healthy`).

2. **All four sha256 came out as `e3b0c44298fc1c14`** — that's the sha256 of an EMPTY string. So my lookup found no data because the Secret name was wrong, not because the values are missing. We need to redo the verification with the correct name.

The pods are still crashing because step 7 deleted them but the underlying Secret was never re-verified. Let me find the correct names quickly, then re-run.

```bash
# Find the correct Secret names for all 4 services
for SVC in gateway engine execution management; do
  echo "=== $SVC ==="
  kubectl -n etradie-system get secrets -o name | grep -E "etradie-$SVC"
done
```

Paste that output. While you do that, also grab the engine pod stderr — since the crash is happening AGAIN, either the new env var still isn't there or there's a different new error. Run in parallel:

```bash
# Pick whichever pod is currently in CrashLoop
NEWPOD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | head -1)
echo "Pod: $NEWPOD"

echo "=== engine env: does ENGINE_INTERNAL_SHARED_SECRET exist? ==="
kubectl -n etradie-system get pod "$NEWPOD" -o jsonpath='{.spec.containers[?(@.name=="engine")].envFrom}' | jq

echo "=== current engine stderr ==="
kubectl -n etradie-system logs "$NEWPOD" -c engine --tail=30 2>&1

echo "=== previous engine stderr ==="
kubectl -n etradie-system logs "$NEWPOD" -c engine --previous --tail=30 2>&1
```

Paste both blocks. The engine stderr will tell us exactly which env var (if any) is still failing the startup guard. The Secret list will tell us the right name so we can verify the value is byte-identical across all four services. Once we have those two facts the next step is decided.


softverse@Softverse:/eTradie$
softverse@Softverse:/eTradie$ # Find the correct Secret names for all 4 services
for SVC in gateway engine execution management; do
  echo "=== $SVC ==="
  kubectl -n etradie-system get secrets -o name | grep -E "etradie-$SVC"
done
=== gateway ===
secret/etradie-gateway-secrets
=== engine ===
secret/etradie-engine-secrets
=== execution ===
secret/etradie-execution-secrets
=== management ===
secret/etradie-management-secrets
softverse@Softverse:~/eTradie$ # Pick whichever pod is currently in CrashLoop
NEWPOD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine   -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | head -1)
echo "Pod: $NEWPOD"
echo "=== engine env: does ENGINE_INTERNAL_SHARED_SECRET exist? ==="
kubectl -n etradie-system get pod "$NEWPOD" -o jsonpath='{.spec.containers[?(@.name=="engine")].envFrom}' | jq
echo "=== current engine stderr ==="
kubectl -n etradie-system logs "$NEWPOD" -c engine --tail=30 2>&1
echo "=== previous engine stderr ==="
kubectl -n etradie-system logs "$NEWPOD" -c engine --previous --tail=30 2>&1
Pod: etradie-engine-598658f7cd-xk5vb
=== engine env: does ENGINE_INTERNAL_SHARED_SECRET exist? ===
[
  {
    "configMapRef": {
      "name": "etradie-engine-config",
      "optional": false
    }
  },
  {
    "secretRef": {
      "name": "etradie-engine-secrets",
      "optional": false
    }
  }
]
=== current engine stderr ===
=== previous engine stderr ===
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/contextlib.py", line 210, in aenter
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/fastapi/routing.py", line 225, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/contextlib.py", line 210, in aenter
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/fastapi/routing.py", line 225, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/contextlib.py", line 210, in aenter
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/fastapi/routing.py", line 225, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/contextlib.py", line 210, in aenter
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/engine/main.py", line 107, in lifespan
    await container.rag_bootstrap_service.bootstrap()
  File "/usr/local/lib/python3.12/site-packages/engine/rag/services/bootstrap.py", line 93, in bootstrap
    raise RAGBootstrapError(
engine.shared.exceptions.RAGBootstrapError: Failed to bootstrap knowledge assets: connection was closed in the middle of operation
ERROR:    Application startup failed. Exiting.
softverse@Softverse:~/eTradie$


**Massive progress.** Three layers cleared in one shot:

1. **`ENGINE_INTERNAL_SHARED_SECRET` is now present** — the engine got past the module-import fail-fast guard (no more `RuntimeError: ENGINE_INTERNAL_SHARED_SECRET is required in staging`).
2. **Settings construction succeeded** — Settings, Container, dependency injection all built cleanly.
3. **Lifespan startup is running** — we're inside FastAPI's `lifespan` context manager. The engine is now executing application bootstrap logic.

The NEW error is in **RAG bootstrap**, specifically in `engine/rag/services/bootstrap.py::bootstrap()` line 93:

```
RAGBootstrapError: Failed to bootstrap knowledge assets: connection was closed in the middle of operation
```

This is a network-level error talking to **ChromaDB** (the RAG vector store). The engine connects to chromadb at `chromadb.etradie-system.svc.cluster.local:8000`, runs ingest on startup (`ingestOnStartup: "true"` in values-staging.yaml), and the TCP connection got cut mid-operation. Two prime suspects:

1. **ChromaDB itself is unstable.** Worth checking — the chromadb pod has been heavily restarted today (subpath / log_config saga).
2. **Linkerd proxy timing.** Engine's RAG ingest is one of the heaviest startup operations (sentence-transformer model load + embedding generation + chroma writes). If chromadb's linkerd-proxy or its server-side connection drops during a long upsert, the client sees "connection was closed in the middle of operation".

Let me gather facts before proposing anything. First confirm the new pod env actually has the secret, then check chromadb state, then read the bootstrap source.

```bash
# 1. Confirm the new Secret has ENGINE_INTERNAL_SHARED_SECRET, and value matches the cohort
for SVC in gateway engine execution management; do
  case "$SVC" in
    gateway) KEY=GATEWAY_ENGINE_INTERNAL_SHARED_SECRET ;;
    *)       KEY=ENGINE_INTERNAL_SHARED_SECRET ;;
  esac
  SECRET=etradie-$SVC-secrets
  H=$(kubectl -n etradie-system get secret "$SECRET" -o jsonpath="{.data.$KEY}" 2>/dev/null \
        | base64 -d 2>/dev/null | sha256sum | head -c 16)
  echo "$SVC: $H"
done
# All four should be 6037ddef7ab86629 per PROGRESS.md Phase 8 matrix

# 2. ChromaDB state
echo ""
echo "=== chromadb pod state ==="
kubectl -n etradie-system get pod chromadb-0 -o wide
echo ""
echo "=== chromadb recent restarts ==="
kubectl -n etradie-system describe pod chromadb-0 | grep -E "Restart Count|Last State|Reason" | head -20
echo ""
echo "=== chromadb container stderr (last 50) ==="
kubectl -n etradie-system logs chromadb-0 -c chromadb --tail=50
echo ""
echo "=== chromadb linkerd-proxy stderr (last 20) ==="
kubectl -n etradie-system logs chromadb-0 -c linkerd-proxy --tail=20 2>&1 | tail -20
echo ""
echo "=== chromadb heartbeat from inside engine pod ==="
NEWPOD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  -o jsonpath='{.items[0].metadata.name}')
kubectl -n etradie-system exec "$NEWPOD" -c engine -- \
  curl -sf -m 5 -w "\nHTTP: %{http_code}  TIME: %{time_total}s\n" \
  http://chromadb.etradie-system.svc.cluster.local:8000/api/v2/heartbeat 2>&1 | head -10
```

Paste all five blocks. With those facts in hand I'll know if this is:

- A chromadb instability (fix chromadb itself), or
- A linkerd-proxy timeout on a long-running connection (add `config.linkerd.io/opaque-ports: "8000"` to chromadb to bypass HTTP proxying for the ingest path), or
- A RAG bootstrap retry/timeout configuration that needs to be more resilient (read the bootstrap.py source).

One thing I noticed: there are TWO engine pods running (598658f7cd-xk5vb and d7bd6444d-j6m55). The second one is from the OLD ReplicaSet (the previous deployment). It'll get reaped automatically once the new one is Ready. Don't act on that — it's normal rollout behavior.