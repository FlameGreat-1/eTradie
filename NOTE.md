
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

 SO WE ARE GOING TO CONTINUE WITH PHASE 10 THIS IS WHAT YOU SAID LAST IN THE PREVIOUS SESSION:





THIS IS THE COMMIT YOU WANTED TO MAKE BUT IT FAILED BECAUSE THE SESSION ENDED:


docs(runbooks): PROGRESS.md — Phase 10 continuation 2026-06-15 — Vault path defect + migration + Linkerd mesh up + staging children Missing

Records the full Phase 10 debug arc since the previous PROGRESS
checkpoint:

  1. ESO Vault path resolution defect proven from external-secrets
     v0.10.4 source. Terraform wrote at the doubled-prefix path;
     ESO resolves chart keys to single-prefix. Mismatch.

  2. Three pre-flight commits 40676e7c, c0fb63d8, 42cb67e9.

  3. Terraform fix 3410f13e — drop redundant etradie/ prefix from
     vault_kv_secret_v2 names.

  4. Live Vault HTTP-API migration of all 14 paths. Byte-verified.

  5. AppProject whitelist commit af9a1536 — add batch/CronJob.

  6. Direct kubectl apply of linkerd-appproject.yaml because root-app
     does NOT include AppProject files in its source path.

  7. ESO + token_reviewer_jwt + ClusterSecretStore repairs (mid-debug).

  8. Linkerd control plane Running with sidecars.

  9. STAGING CHILDREN STILL Missing — next session's first task.

PHASE 10 STATUS: mesh HEALTHY + 14 secret paths ALIGNED. Phase 10
NOT YET COMPLETE — 10 staging Apps OutOfSync/Missing pending root
cause investigation.

Captures three follow-ups: vault-auth token_reviewer_jwt 24h TTL
re-token; disable Vault audit log; PROGRESS gotcha #9 correction.





--- docs/runbooks/PROGRESS.md
+++ docs/runbooks/PROGRESS.md
@@ -1,1 +1,1 @@
-| 10 | ArgoCD + AppProjects + root app | 🟡 in progress (pre-flight + §10.0 + §10.1 done; §10.2–10.5 pending) |
+| 10 | ArgoCD + AppProjects + root app | 🟡 in progress (control plane HEALTHY; staging children OutOfSync/Missing — diagnosis TBC) |



--- docs/runbooks/PROGRESS.md
+++ docs/runbooks/PROGRESS.md
@@ -1,9 +1,258 @@
 **8. ClusterSecretStore mount mismatch (pre-this-revision).** The
 ReadME §4.2 (pre-this-revision) created the ClusterSecretStore
 with `path: "secret"`. Combined with gotcha #6, that meant chart
 ExternalSecrets would have looked at the WRONG mount. Fixed in
 §4.2 (sibling commit) by changing the default to `path: "etradie"`
 and adding an inline `kubectl patch` recipe for in-place fixup on
 an already-deployed cluster (the staging deploy needs that
 patch executed before §8.4 onwards). Audit trail: the deploy
-that surfaced this is logged in this checkpoint.
+that surfaced this is logged in this checkpoint.
+
+---
+
+## Phase 10 — continuation 2026-06-15 (Vault path defect + Linkerd mesh up + staging children pending)
+
+This section continues the Phase 10 timeline AFTER the prior
+checkpoint that closed §10.0 + §10.1. The next session resumes
+at the bottom of this section.
+
+### Headline state at end of this session
+
+- **ArgoCD healthy.** 7 pods Running. CLI logged in via `127.0.0.1:8080` port-forward.
+- **All 3 AppProjects + root-app applied.** 22 child Applications discovered.
+- **3 linkerd-* Applications synced; Linkerd control plane Running.** Identity, destination, and proxy-injector pods all up with sidecars (2/2 or 4/4 Ready).
+- **14 Vault KV paths aligned with chart ExternalSecret keys.** ESO resolves every chart key to a real Vault secret; verified on `linkerd-identity-issuer` (SecretSynced/True, fresh lastTransitionTime, K8s Secret of type `kubernetes.io/tls` with `tls.crt` + `tls.key`).
+- **STAGING CHILDREN STILL Missing.** 10 staging Applications (`data-layer-staging`, `engine-staging`, `gateway-staging`, `execution-staging`, `management-staging`, `billing-staging`, `mt-node-staging`, `edge-ingress-staging`, `envoy-staging`, `observability-logs-staging`) all show `OutOfSync / Missing` with empty `etradie-system` / `edge-ingress-system` / `envoy-system` namespaces. Not yet diagnosed — the next session starts here.
+
+### What broke in this session
+
+#### Defect: ESO Vault path resolution silently strips the leading mount-name segment
+
+**Root cause traced to external-secrets v0.10.4 source at `pkg/provider/vault/client_get.go::buildPath()`:**
+
+When the ClusterSecretStore has `spec.provider.vault.path: etradie` (the KV-v2 mount name) AND the ExternalSecret's `remoteRef.key` starts with `etradie/`, ESO strips the leading `etradie/` segment, then prepends `etradie/data/`. The effective API path for a chart key `etradie/services/engine/staging` is `etradie/data/services/engine/staging` — NOT `etradie/data/etradie/services/engine/staging`.
+
+But `infrastructure/cluster/vault-paths/main.tf` (pre-this-revision) created every `vault_kv_secret_v2` resource with both `mount = "etradie"` AND `name = "etradie/services/..."`. KV-v2 writes that to API path `etradie/data/etradie/services/...` — doubled-prefix.
+
+**Net effect:** every chart ExternalSecret resolved to the single-prefix path; Phase 8 wrote data ONLY at the doubled-prefix path. Every read returned `Secret does not exist`. Undetected through Phase 8 because Phase 8 only WROTE; Phase 10 is the first phase that READS via ESO.
+
+**Empirically verified** with two test ExternalSecrets on the live cluster:
+- Key `platform/linkerd/test1` + data at `etradie/data/platform/linkerd/test1` → SecretSynced/True ✓
+- Key `etradie/platform/linkerd/test2` + data at `etradie/data/etradie/platform/linkerd/test2` → SecretSyncedError / Secret does not exist ✗
+
+The second case is exactly what every chart was experiencing. The first case is what we need.
+
+PROGRESS.md gotcha #9 from the previous Phase 8 entry — which documented the doubled-prefix as intentional — was **incorrect**. A separate correction commit is TODO.
+
+### What was fixed in this session
+
+#### 1. ArgoCD pre-flight commits (in order)
+
+| Commit | Subject | What it fixes |
+|---|---|---|
+| `40676e7c` | remove stale identityTrustAnchorsPEM parameter sentinel | Helm `--set` override would have clobbered the values-file PEM at sync time; identity controller would fail with invalid issuer cert chain |
+| `c0fb63d8` | add argocd namespace to etradie AppProject destinations | root-app places Application children into `argocd` ns; project must whitelist that destination |
+| `42cb67e9` | fix Linkerd Helm repoURL to `/stable` | Upstream restructured the chart index; bare `https://helm.linkerd.io/index.yaml` returns 404 |
+
+#### 2. Terraform fix — commit `3410f13e`
+
+Dropped the redundant `etradie/` prefix from the `name` attribute of every `vault_kv_secret_v2` resource in `infrastructure/cluster/vault-paths/main.tf`. `mount` stays `etradie`. After this commit a fresh terraform apply will write secrets at the correct (single-prefix) location:
+
+```
+services/edge-ingress/${env}/tls
+services/edge-ingress/${env}/cloudflare/aop_ca
+services/edge-ingress/${env}/cloudflare/tunnel
+services/edge-ingress/${env}/maxmind
+services/gateway/${env}
+services/engine/${env}
+services/execution/${env}
+services/management/${env}
+services/billing/${env}
+data-layer/postgres/${env}
+data-layer/redis/${env}
+data-layer/chromadb/${env}
+platform/linkerd/${env}    # always /production even on staging
+services/mt-node/${env}
+```
+
+**Chart `vaultPath` values keep their `etradie/services/...` form — intentional.** ESO's `buildPath` silently strips the leading `etradie/` segment when it matches the CSS path; chart keys `etradie/services/engine/staging` and `services/engine/staging` are functionally identical at resolution time. A separate cosmetic cleanup PR may drop the redundant prefix from chart values later; not a blocker.
+
+**mt-node-tenant subsystem — NO CHANGE NEEDED.** Single-prefix paths throughout (`tenants/mt-node/<sa>`) on the same mount; not affected by the terraform fix.
+
+#### 3. Live Vault data migration (executed via Vault HTTP API)
+
+For each of the 14 Phase-8 secrets at the doubled-prefix path, read the JSON payload, write it to the corrected single-prefix path via Vault's `POST /v1/etradie/data/<dst>` endpoint, then byte-verify by sha256 comparison of jq-sorted `.data.data`.
+
+Why HTTP API instead of `vault kv put`: the CLI's flag parser rejects `-` as a value sentinel + the placeholder string contained leading hyphens, and the doubled-jq-escape needed to feed `key=value` pairs hit a brick wall in nested kubectl exec. The HTTP API takes a single JSON body — no quoting issues.
+
+**14/14 paths migrated. Phase B verification: 14/14 byte-perfect.** Doubled-prefix originals NOT deleted (safety net until §10.5 succeeded; can be cleaned in a later commit).
+
+#### 4. ESO + ClusterSecretStore + token_reviewer_jwt repairs
+
+Mid-debug, three Vault-auth issues surfaced and were repaired in place:
+
+- **`etradie-eso` policy:** updated to grant `read,list` on `etradie/data/*` + `etradie/metadata/*` paths.
+- **`vault-auth` SA `token_reviewer_jwt`:** the original JWT bound to Vault's `kubernetes/config` had expired. Minted a new 24h TTL token. **TODO before Phase 10 closeout:** mint a non-expiring legacy Secret-bound token (the enterprise pattern). Otherwise ESO will start 403'ing again at the 24h mark.
+- **ClusterSecretStore `vault-backend`:** deleted and recreated mid-session. Current spec: `path: etradie`, `version: v2`, k8s auth role `etradie-eso`. Status: `Valid`.
+- **ESO controller restarted** to clear cached path-resolution state.
+
+#### 5. AppProject whitelist commit `af9a1536`
+
+Added `batch/CronJob` to the `linkerd` AppProject's `namespaceResourceWhitelist`. The Linkerd control-plane chart renders a `CronJob linkerd-heartbeat` by default. Without this entry, ArgoCD refused to create the CronJob and aborted the entire wave; every other resource was left OutOfSync/Missing as a downstream effect.
+
+With the whitelist updated, the chart renders unchanged from upstream defaults.
+
+#### 6. Direct kubectl apply of `deployments/argocd/linkerd-appproject.yaml`
+
+After the `af9a1536` commit landed on GitHub, a root-app sync reported `Synced` but the `linkerd` AppProject on the live cluster STILL did not contain `batch/CronJob`. Diagnosis: root-app's source path is `deployments/argocd/children`, but the AppProject files live at `deployments/argocd/` (one directory up). Root-app's `directory.recurse: true` only reconciles files UNDER `children/`; the AppProjects are out of scope.
+
+The fix was a direct `kubectl apply -f deployments/argocd/linkerd-appproject.yaml`. The AppProject is Git-canonical but **not GitOps-managed** in the current repo layout. New PROGRESS gotcha.
+
+#### 7. §10.5 manual sync — waves -6, -5, -4 in order
+
+After all the above fixes:
+
+```
+§10.5.1 argocd app sync linkerd-identity-production       → OutOfSync/Healthy
+§10.5.2 argocd app sync linkerd-crds-production           → Synced/Healthy (7 CRDs)
+§10.5.3 argocd app sync linkerd-control-plane-production  → OutOfSync/Healthy
+```
+
+Final pod state in `linkerd` namespace:
+
+```
+linkerd-destination-79865f5b4-qd7b9       4/4 Running
+linkerd-identity-759f6d955-jssdj          2/2 Running
+linkerd-proxy-injector-7c87f4fc86-5lzzl   2/2 Running
+```
+
+### About the `OutOfSync / Healthy` lines on the linkerd-* Apps
+
+Two of the three Linkerd Applications show `OutOfSync` even though they are Healthy. These are **expected, by-design** behaviors and NOT blockers:
+
+1. **`linkerd-identity-production: OutOfSync / Healthy`.** The `ExternalSecret linkerd-identity-issuer` is server-side-applied by ESO using its own field-manager. ArgoCD sees the field-manager delta vs the chart-rendered spec and reports OutOfSync. The K8s Secret the ExternalSecret manages is correctly populated. No action needed.
+2. **`linkerd-control-plane-production: OutOfSync / Healthy`.** The 3 webhook TLS Secrets (`linkerd-policy-validator-k8s-tls`, `linkerd-proxy-injector-k8s-tls`, `linkerd-sp-validator-k8s-tls`) and the 2 Deployments that consume them are **mutated at runtime** by Linkerd's identity controller (rotates the webhook certs on a schedule). ArgoCD sees the runtime drift vs the chart template and reports OutOfSync. Leave as-is.
+
+### What is NOT yet diagnosed (the next session's first task)
+
+10 staging Applications show `OutOfSync / Missing`:
+
+```
+data-layer-staging         OutOfSync  Missing  Auto-Prune  etradie-system
+engine-staging             OutOfSync  Missing  Auto-Prune  etradie-system
+gateway-staging            OutOfSync  Missing  Auto-Prune  etradie-system
+execution-staging          OutOfSync  Missing  Auto-Prune  etradie-system
+management-staging         OutOfSync  Missing  Auto-Prune  etradie-system
+billing-staging            OutOfSync  Missing  Auto-Prune  etradie-system
+mt-node-staging            OutOfSync  Healthy  Auto-Prune  etradie-system
+edge-ingress-staging       OutOfSync  Missing  Auto-Prune  edge-ingress-system
+envoy-staging              OutOfSync  Missing  Auto-Prune  envoy-system
+observability-logs-staging OutOfSync  Missing  Auto-Prune  etradie-observability
+```
+
+All namespaces empty (`No resources found`). Auto-sync has not fired.
+
+**`mt-node-staging` shows `Healthy`** because `mtConnection.enabled=false` in staging means the chart renders no resources — confirms this is an auto-sync trigger issue, not a chart-render issue.
+
+Most likely causes (in priority order):
+
+1. **Backoff state from earlier failed reconciles**. The staging Applications were created by root-app during §10.3 BEFORE the mesh was up. Their first reconcile attempts likely failed (pods would have been Pending waiting for proxy injector that didn't exist). ArgoCD entered backoff and has not retried in the 4 minutes since the mesh came up.
+2. **Another AppProject whitelist gap** — this time in the `etradie` AppProject (staging apps belong to `etradie`, not `linkerd`). Possible missing kinds: `NetworkPolicy`, `PodDisruptionBudget`, `Job`, `CronJob`, `HorizontalPodAutoscaler`, etc.
+3. **Helm template render error** on one of the values overlays.
+
+**Diagnostic plan for next session:**
+
+```bash
+# 1. Get the actual reason from data-layer-staging (wave -1, others depend on it)
+argocd app get data-layer-staging --grpc-web
+kubectl -n argocd get application data-layer-staging \
+  -o jsonpath='{.status.operationState}' | jq .
+
+# 2. Check controller logs for staging-related sync errors
+kubectl -n argocd logs statefulset/argocd-application-controller \
+  --tail=500 | grep -iE 'staging|data-layer|error|fail'
+
+# 3. Confirm etradie AppProject syncWindows don't block staging
+kubectl -n argocd get appproject etradie \
+  -o jsonpath='{.spec.syncWindows}' | jq .
+
+# 4. After fixing, refresh all 10 staging apps:
+for app in data-layer engine gateway execution management billing \
+           mt-node edge-ingress envoy observability-logs; do
+  kubectl -n argocd annotate application ${app}-staging \
+    argocd.argoproj.io/refresh=hard --overwrite
+done
+sleep 30
+argocd app list --grpc-web | grep staging
+```
+
+Do NOT issue a blind hard-refresh-everything before knowing the root cause; a true permission failure stays a failure after refresh, and we lose signal on what was wrong.
+
+### Phase 10 (continuation) operator gotchas
+
+**23. ESO `buildPath` silently strips the leading mount-name segment.** This is the load-bearing fact behind the whole Phase 10 debug arc. If the ClusterSecretStore has `path: <X>` AND the ExternalSecret key starts with `<X>/`, ESO strips the `<X>/` prefix and prepends `<X>/data/`. Verified in external-secrets v0.10.4 source at `pkg/provider/vault/client_get.go::buildPath()`. PROGRESS gotcha #9 (Phase 8 entry) is incorrect and needs an in-place correction in a follow-up commit.
+
+**24. Root-app source path is `deployments/argocd/children`, NOT `deployments/argocd`.** AppProject files (`appproject.yaml`, `linkerd-appproject.yaml`) live one directory up, OUTSIDE root-app's scope. AppProject changes require direct `kubectl apply -f`. Long-term TODO; for this deploy use the direct apply.
+
+**25. ArgoCD port-forward dies silently across WSL sleep / focus changes.** Symptoms: `argocd <any-command>` returns `connection reset by peer` or `connection refused`. Fix: reopen the `kubectl -n argocd port-forward svc/argocd-server 8080:443` command in a dedicated, never-closed terminal. Each reopen also invalidates the argocd CLI's auth token; re-login with `argocd login 127.0.0.1:8080 ...` after each reopen.
+
+**26. ArgoCD `app sync` operations stay `Phase: Running` even after the CLI disconnects.** A killed port-forward mid-sync leaves the server-side operation in flight; subsequent sync commands fail with `another operation is already in progress`. Fix: `argocd app terminate-op <app-name>` before retrying.
+
+**27. Linkerd-heartbeat CronJob.** The Linkerd control-plane Helm chart renders a `batch/CronJob linkerd-heartbeat` by default. Daily anonymous telemetry to api.linkerd.io. NOT load-bearing; cannot reach the upstream from inside ufw egress posture. Kept as upstream-default for shape-parity. AppProject must whitelist `batch/CronJob` for the chart to render (commit `af9a1536`).
+
+**28. ESO `token_reviewer_jwt` lifetime trap.** ESO authenticates to Vault as the `vault-auth` ServiceAccount using a JWT issued from that SA's token. Modern Kubernetes (>=1.24) issues ServiceAccount tokens with bounded TTLs by default; long-running ESO controllers will start 403'ing once the JWT expires. The staging deploy hit this mid-session and minted a 24h TTL token as a stopgap. **Enterprise-grade fix:** mint a non-expiring legacy Secret-bound token for the `vault-auth` SA. TODO before Phase 10 declared closed.
+
+**29. Vault audit log left enabled at `/tmp/vault-audit.log`.** Enabled mid-debug to trace ESO's API calls; accumulates fast. Disable at start of next session:
+```bash
+kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
+  vault audit disable file
+```
+
+**30. Watch Health column, not just Sync column.** The `OutOfSync / Healthy` rows on `linkerd-*` Applications are by-design; the `OutOfSync / Missing` rows on staging children are NOT. Auto-sync is aggressive enough to fix a transient backoff; a true defect stays as `Missing` after a `--refresh hard` annotation.
+
+### Vault state at end of this session
+
+All 14 KV paths exist at TWO locations: doubled (legacy, kept for safety) and single-prefix (canonical, what ESO + every chart reads). A future cleanup commit removes the doubled-prefix entries via `vault kv metadata delete -mount=etradie etradie/<rest>` once all charts have rolled out without incident.
+
+### Session-resume recovery — read this if the session ended
+
+1. **Tunnel** (dedicated terminal, leave open):
+   ```bash
+   ssh-add ~/.ssh/id_ed25519  # once per WSL boot
+   ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173
+   ```
+2. **ArgoCD port-forward** (separate dedicated terminal, leave open):
+   ```bash
+   export KUBECONFIG=~/.kube/etradie-contabo.yaml
+   kubectl -n argocd port-forward svc/argocd-server 8080:443
+   ```
+3. **Working terminal env**:
+   ```bash
+   export KUBECONFIG=~/.kube/etradie-contabo.yaml
+   ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
+   ```
+4. **Argocd CLI login**:
+   ```bash
+   ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
+     -o jsonpath='{.data.password}' | base64 -d)
+   argocd login 127.0.0.1:8080 --username admin \
+     --password "$ADMIN_ARGO_PWD" --insecure
+   unset ADMIN_ARGO_PWD
+   ```
+5. **Sanity** — all of these should be true:
+   - `kubectl -n linkerd get pods` → 3 control-plane pods all Running (2/2 or 4/4)
+   - `kubectl -n linkerd get secret linkerd-identity-issuer` → exists, type `kubernetes.io/tls`, DATA 2
+   - `kubectl -n argocd get appproject linkerd -o jsonpath='{.spec.namespaceResourceWhitelist}' | jq` → contains `{ group: batch, kind: CronJob }`
+   - `kubectl exec -n vault vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault kv get -mount=etradie services/engine/staging` → returns secret data (single-prefix path)
+   - `argocd app list --grpc-web | grep linkerd` → 3 apps, all `Healthy` (mix of Synced and OutOfSync, both expected)
+   - `argocd app list --grpc-web | grep staging` → 10 apps, all `OutOfSync/Missing` (except `mt-node-staging` → `OutOfSync/Healthy`)
+6. **First action**: run the diagnostic block from "What is NOT yet diagnosed" above — `argocd app get data-layer-staging` to surface the real reason staging children are not rendering. Then apply the right fix once for all 10.
+
+### Phase 10 closeout TODOs (do these BEFORE flipping the status board to ✅)
+
+1. Diagnose + fix the 10 staging children `OutOfSync/Missing` state.
+2. Mint a non-expiring legacy Secret-bound token for `vault-auth` SA and replace the 24h TTL `token_reviewer_jwt` on Vault's `kubernetes/config`.
+3. Disable the Vault audit log at `/tmp/vault-audit.log`.
+4. PROGRESS.md gotcha #9 (Phase 8 entry) correction commit ("the doubled-prefix was NOT intentional; here is the actual ESO `buildPath` behavior").
+5. Once all staging Applications report `Synced/Healthy`, delete the 14 doubled-prefix Vault entries (`vault kv metadata delete -mount=etradie etradie/<rest>` × 14).
+6. Optional cosmetic: drop the leading `etradie/` prefix from chart `vaultPath` values across the helm/ tree. No functional effect; pure clarity.






Linkerd mesh is **rock solid**: 3 pods, ages 4 min, all `Running` with sidecars. ✓

**Observation:** All staging Applications show `OutOfSync / Missing` — meaning ArgoCD knows about them but has not yet rendered/applied their resources. Zero pods in any namespace. The auto-sync hasn't fired for them.

This is most likely because:
1. The staging Applications were created by root-app during §10.3, **before** Linkerd was up.
2. Their first reconcile attempts failed (likely because pods would have queued waiting for the proxy injector which didn't exist).
3. ArgoCD then went into a backoff state on them and hasn't retried since Linkerd came up 4 minutes ago.

A **hard refresh** on the staging apps will trigger fresh reconcile attempts now that the mesh is up. But first, let's check one app's actual sync state for the real reason it's `Missing`, in case there's a deeper issue:

```bash
# 1. Inspect why data-layer-staging is OutOfSync/Missing (it's wave -1, the first staging app)
echo "=== Why is data-layer-staging Missing? ==="
argocd app get data-layer-staging --grpc-web 2>&1 | head -40
echo ""

# 2. Inspect any sync attempt history / last operation
echo "=== data-layer-staging last operation ==="
kubectl -n argocd get application data-layer-staging \
  -o jsonpath='{.status.operationState}' 2>/dev/null | jq '.' 2>/dev/null | head -30
echo ""

# 3. Check ArgoCD application-controller logs for staging-related errors (last 100 lines)
echo "=== application-controller recent log lines mentioning staging ==="
kubectl -n argocd logs statefulset/argocd-application-controller --tail=200 2>&1 | grep -iE 'staging|error|fail' | tail -20
echo ""

# 4. Check the etradie AppProject sync windows — they were noted as
#    targeting *-production only, but let's verify staging has no window block
echo "=== etradie AppProject sync windows ==="
kubectl -n argocd get appproject etradie \
  -o jsonpath='{.spec.syncWindows}' | jq '.'
```

#### What I'm looking for

- **Step 1**: error message in `data-layer-staging`'s status. Likely candidates:
  - "rendered manifests contain a resource that already exists" (race with namespace creation)
  - A specific resource kind not whitelisted in the `etradie` AppProject (e.g. `CronJob`, `NetworkPolicy`, `Job`)
  - A Helm template render error
  - A missing values file
- **Step 2**: the actual phase/message from the last sync attempt
- **Step 3**: any pattern across all staging apps (vs single-app problems)
- **Step 4**: confirm staging is not blocked by a sync window

I don't want to issue a blind hard-refresh on all 10 apps until I see why this one is failing. If it's a single rookie issue (like another missing AppProject kind), we fix once and refresh everything in one go. If it's per-app, we tackle them one at a time.

Run the block and paste the output. Then we proceed with the right fix.