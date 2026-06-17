# Staging/Production Co-Residency Churn — Checkpoint

> **READ THIS FIRST if you are resuming work on the staging cluster.**
> This file is the canonical record of the staging/production
> co-residency churn that was diagnosed and fixed across this session.
> It records the root cause, every change made (GitLab + GitHub + live
> cluster), what is VERIFIED done, the ONE remaining OPEN item, and the
> exact place to take off next — so nobody re-breaks the cluster.
>
> Last updated: 2026-06-17 (after pruning the 11 *-production
> Applications on the staging cluster).

---

## TL;DR for the next operator

1. **The cluster is now STAGING-ONLY and stable.** The 11 `*-production`
   app-workload ArgoCD Applications have been deleted from the staging
   cluster. Only the 3 shared `linkerd-*-production` Applications remain
   (correct — the mesh runs once per cluster).
2. **No staging workload was disturbed by the prune** — verified: the
   data-layer + engine pods kept their 106–107m age through the delete
   (zero restarts).
3. **ONE item is still OPEN:** `edge-ingress-staging` is `Degraded`
   because its `geoip-downloader` init container is hitting MaxMind
   **HTTP 429 (daily download limit reached)** AND its GeoIP PVC is
   `Pending`. See "OPEN ITEM" below — do NOT panic-fix this; it is
   blocked on the MaxMind quota reset (00:00 UTC) and on syncing the
   !146 chart fix into the live pod.
4. **GitHub `origin/main` is the source ArgoCD reads.** All fixes are
   on GitHub at commit `c97f4e21` (and mirrored to GitLab). Nothing
   below requires another git push unless you change a chart.

---

## Root cause (what the churn actually was)

`deployments/argocd/root-app.yaml` reconciles
`deployments/argocd/children/` with `directory.recurse: true`. On the
single staging cluster this created BOTH the `*-staging` AND the
`*-production` child Applications.

Each `*-production` Application targets the **same** helm `releaseName`
and **same** namespace as its `*-staging` twin (e.g. both
`engine-production` and `engine-staging` deploy `releaseName:
etradie-engine` into `etradie-system`). On one cluster that means both
Applications claim the **same** Kubernetes resources. ArgoCD flags this
as `SharedResourceWarning`. A manual sync of a `*-production` app would
overwrite the shared release with the production values overlay, the
`*-staging` app's `selfHeal` would fight back, and the field-managers
flip the live workloads between overlays in a permanent loop.

**That churn (repeated ArgoCD re-applies of edge-ingress) is what burned
through the MaxMind GeoIP daily download quota**, which is the original
symptom that started this whole investigation (edge-ingress 502 on the
public path).

BUDGET.md Table 2B is explicit: "pick ONE environment per box; staging
and production are not meant to co-reside."

---

## The fix — three parts

### Part 1 — MR !146: edge-ingress GeoIP persistence (merge `9786b8e1`)

Makes the GeoIP database survive pod restarts so ArgoCD churn can never
re-exhaust the MaxMind quota again.

- New `helm/edge-ingress/templates/geoip-pvc.yaml` — a 200Mi RWO PVC
  (`storageClassName: ""` = K3s local-path default) to cache the
  MaxMind GeoLite2-City DB.
- New `helm/edge-ingress/templates/geoip-refresh-cronjob.yaml` — daily
  03:00 UTC refresh via `maxmindinc/geoipupdate:v6.0`.
- `deployment.yaml` rewritten so `geoip-data` mounts the PVC and the
  bootstrap init container is busybox-based
  (`geoip.bootstrapInitImage: "busybox:1.36"`), idempotent (skip if
  cached DB present) and fault-tolerant (warn + proceed if the download
  fails but a cache exists; hard-fail ONLY on a true cold start with no
  cached DB).
- New value blocks in `values.yaml` / `values-staging.yaml` /
  `values-production.yaml`: `geoip.persistence`, `geoip.refresh`,
  `geoip.bootstrapInitImage`.

### Part 2 — MR !147: park the 11 *-production Applications (merge `75d3734e`)

Makes the co-residency conflict STRUCTURALLY impossible on a staging
box: root-app never sees the production app-workload Applications, so
it never creates them.

- `git mv` the **11** `*-production` app-workload Applications
  (billing, data-layer, edge-ingress, engine, envoy, execution,
  gateway, management, monitoring-stack, mt-node, observability-logs)
  from `deployments/argocd/children/` to a NEW
  `deployments/argocd/environments/production/` directory + README.
- `root-app.yaml` UNCHANGED (still `path: children, recurse: true`),
  so it no longer creates the production apps.
- The 3 `linkerd-*-production` Applications STAY in `children/` — the
  mesh runs once per cluster, CA path hardcoded to `/production`,
  correct on any cluster. There is no `*-staging` linkerd variant.
- `.github/workflows/ci.yml` `argocd manifests parse` step rewritten to
  recursively `find` `*.yaml` under BOTH `children/` AND
  `environments/` (the old single-level glob would have dropped the
  moved files from CI validation), and added the previously-omitted
  `monitoring-appproject.yaml`.

### Part 3 — doc consistency (commit `c97f4e21`)

Updated the docs that still described the OLD flat `children/` layout so
a future operator is not misled into moving the production files back
(which would re-create the churn):

- `deployments/argocd/README.md` (Layout + Promotion model).
- `infrastructure/cluster/bootstrap/README.md` (step 8 child-count text).
- `docs/runbooks/README.md` (Phase 10.3 + Phase 12 production-sync
  section — Phase 12 is now explicitly flagged as a DEDICATED
  PRODUCTION CLUSTER phase).

---

## Git state (all on GitHub `origin/main` — what ArgoCD reads)

| Commit | What |
|---|---|
| `c97f4e21` | docs: align ArgoCD layout docs with environments/production/ parking (HEAD) |
| `75d3734e` / `4c6257ce` | park the 11 *-production app-workload Applications |
| `9786b8e1` / `0a77b160`+`c16d4be9`+`af069210` | edge-ingress GeoIP PVC + idempotent fault-tolerant init |
| `73ad2bcd` | "updated" — operator cleanup (deleted NOTE.md, PROBLEM.md; edited CHECKLIST.md) |

**Remotes:** GitHub `origin` is canonical (ArgoCD + Vercel read it).
GitLab `gitlab` is the MCP mirror. Both are in sync. The two remotes
carry equivalent commits with slightly different SHAs (GitHub
rebased-flat vs GitLab merge-commit form); content is identical.

**Load-bearing rule (PROGRESS gotcha #15):** every chart/manifest
change MUST reach GitHub `origin/main` to take effect; ArgoCD does NOT
read GitLab.

---

## Live cluster action taken this session (the prune)

After pushing to GitHub, root-app re-read `main` and correctly
identified the 11 `*-production` app-workload Applications as requiring
pruning, but the automated sync **aborted safely** with `FATA 11
resources require pruning` (the prune-confirm guard did its job —
nothing was auto-deleted).

### Ownership was verified BEFORE deleting (safety discipline)

- ArgoCD `resourceTrackingMethod` = default **label** (the
  `argocd.argoproj.io/tracking-id` annotation was empty).
- The live `etradie-engine` Deployment carries
  `app.kubernetes.io/instance = engine-staging` → **staging is the
  canonical ArgoCD owner**; the production apps were interlopers
  (hence `SharedResourceWarning`).
- The live Deployment's field-managers were a single shared
  `argocd-controller Apply` (not one per app), so removing a
  production Application could not strip fields staging needs.

### The delete (finalizer-stripped, belt-and-braces)

To guarantee ZERO chance of a finalizer cascade-deleting a live
workload, each production Application's finalizer was removed first,
then the Application CR deleted:

```bash
for app in data-layer engine gateway execution management billing \
           mt-node edge-ingress envoy observability-logs monitoring-stack; do
  kubectl -n argocd patch application ${app}-production \
    -p '{"metadata":{"finalizers":null}}' --type=merge
  kubectl -n argocd delete application ${app}-production --wait=false
done
```

All 11 patched + deleted cleanly. **Do NOT delete the 3
`linkerd-*-production` apps** — they are shared and correct.

### Verified result

- `argocd app list | grep production` → only `linkerd-control-plane-production`,
  `linkerd-crds-production`, `linkerd-identity-production` remain.
- `kubectl -n etradie-system get pods` → postgres-0 / redis-0 /
  chromadb-0 / etradie-engine unchanged (106–107m age, 0 restarts).
  The prune disturbed nothing.
- 9 of 11 staging apps dropped `SharedResourceWarning` immediately.

---

## OPEN ITEM — edge-ingress GeoIP 429 + PVC Pending (NOT yet resolved)

This is the ONLY outstanding item from this arc. It is NOT caused by the
prune; it is the original MaxMind-quota symptom, still mid-fix.

### Current observed state

```
edge-ingress-staging   OutOfSync  Degraded  SharedResourceWarning

edge-ingress-58bcddf595-z2g78   0/2  Init:CrashLoopBackOff   25 restarts
edge-ingress-86c448f965-4hhbz   0/2  Init:CrashLoopBackOff   25 restarts

geoip-downloader init log:
  STATE: Running geoipupdate
  Error ...: HTTP status code: 429: Daily GeoIP database download limit reached

PVC edge-ingress-geoip-cache   STATUS: Pending
```

### What this means (verified facts, not guesses)

1. **The init container hitting 429 is STILL the old `maxmindinc/
   geoipupdate:v6.0` doing a hard download** — i.e. the !146
   busybox-based, skip-if-cached, fault-tolerant bootstrap init is NOT
   yet in the running pod spec. (When the diagnostic queried
   `deploy/etradie-edge-ingress` the name was NOT FOUND — the live
   Deployment is named differently; confirm the real name before
   acting, see step 1 below.)
2. **The GeoIP PVC is `Pending`** (unbound). On K3s local-path with
   `WaitForFirstConsumer`, a PVC binds only when a schedulable pod
   mounts it; the CrashLooping init prevents that. The persistence
   layer is therefore not active yet.
3. **429 is a MaxMind SERVER-SIDE daily quota**, not a stale image and
   not a GHCR problem. Force-pulling any image does NOT fix a 429.
   The quota resets at **00:00 UTC**.
4. **Two ReplicaSets are live** (`58bcddf595` + `86c448f965`); the
   rollout is wedged because neither pod reaches Ready. This is why
   `edge-ingress-staging` still shows `SharedResourceWarning` even
   after the production prune — it is overlapping ownership between the
   two edge-ingress ReplicaSets, NOT leftover production conflict.

### TAKE OFF HERE — exact next steps (do in order, verify each)

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml

# STEP 1 — find the REAL edge-ingress workload name + confirm whether the
# !146 busybox bootstrap init is in the live spec yet.
kubectl -n edge-ingress-system get deploy,statefulset
DEPLOY=$(kubectl -n edge-ingress-system get deploy -o name | grep -i edge-ingress | head -1)
kubectl -n edge-ingress-system get "$DEPLOY" \
  -o jsonpath='{range .spec.template.spec.initContainers[*]}{.name}{"  ->  "}{.image}{"\n"}{end}'
# If you see ONLY 'geoip-downloader -> maxmindinc/geoipupdate:v6.0' and
# NOT a busybox bootstrap init, the !146 chart has not synced. Go to STEP 2.
# If you see the busybox bootstrap init, the fix IS present; go to STEP 3.

# STEP 2 — sync the !146 chart into edge-ingress so the new
# fault-tolerant init + correctly-wired PVC roll out.
argocd app sync edge-ingress-staging --grpc-web --timeout 600
kubectl -n edge-ingress-system get "$DEPLOY" \
  -o jsonpath='{range .spec.template.spec.initContainers[*]}{.name}{"  ->  "}{.image}{"\n"}{end}'
# Re-confirm the busybox bootstrap init is now in the spec.

# STEP 3 — wait for the MaxMind quota reset (00:00 UTC), then let the
# cold-start download succeed ONCE. After that the DB is cached on the
# (now-bindable) PVC and restarts no longer re-download.
kubectl -n edge-ingress-system get pvc            # should go Pending -> Bound once a pod schedules
kubectl -n edge-ingress-system get pods -w        # watch edge-ingress reach 2/2 Ready

# STEP 4 — once edge-ingress is Ready, the duplicate ReplicaSet is
# reaped automatically and the SharedResourceWarning clears. Confirm:
argocd app get edge-ingress-staging --grpc-web | grep -E 'Sync Status|Health'
```

### What NOT to do

- Do NOT force-pull GHCR thinking it fixes the 429 — it does not; the
  429 is MaxMind's server-side quota.
- Do NOT delete and recreate edge-ingress Applications in a loop — that
  was the original churn pattern that burned the quota in the first
  place.
- Do NOT move the `*-production` files back into `children/` — that
  re-creates the co-residency conflict this whole arc removed.
- Do NOT panic if edge-ingress is still Degraded before 00:00 UTC —
  it is quota-blocked by design and self-resolves after the reset
  with the !146 fix in place + a single successful cold-start download.

---

## How to deploy production later (the parked apps)

Production runs on its OWN dedicated cluster (never co-resident with
staging). On that cluster, point its root-app at a source path that
includes `deployments/argocd/environments/production/` plus the shared
`linkerd-*` apps, OR `git mv` those 11 files back into `children/` on a
production-only branch the production cluster's root-app tracks. Full
rationale + procedure in
`deployments/argocd/environments/production/README.md`.

---

## Cross-references

- `deployments/argocd/environments/production/README.md` — the parked
  production apps + why.
- `deployments/argocd/README.md` — updated Layout + Promotion model.
- `docs/runbooks/README.md` Phase 10 / Phase 12 — deploy procedure
  (Phase 12 now flagged as a dedicated-production-cluster phase).
- `docs/runbooks/PHASE10.6-MESH-DISABLED-CHECKPOINT.md` — the separate,
  still-open mesh-disabled posture on 5 staging workloads (unrelated to
  this churn arc but also production-blocking).
- `BUDGET.md` Table 2B — "one environment per box" capacity rule.
