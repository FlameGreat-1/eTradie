# Hosted-MT (Wine) Provisioning — In-Flight Session Runbook

**Status:** IN PROGRESS. Read this top-to-bottom before running anything.
This is the authoritative "pick up exactly here" record for the hosted-MT
provisioning effort on the **staging** Contabo box (`vmi3362776`,
`13.140.164.173`). Any operator can resume from this file alone.

**Last updated:** 2026-06-22, session through **defect #17** (multi-broker
bundle layering) and into the **readiness-timeout** wall described below.

> Companion docs:
> - `MT5_Multi_Broker_Provisioning_Architecture.md` — the authoritative
>   multi-broker design (broker registry, R2 bundles, bake procedure).
>   §14 of that doc is the Phase resume state for the bake/catalog.
> - `docs/runbooks/README.md` — the full platform deploy runbook (Vault,
>   ArgoCD, R2 image-bake Phase 2.5, GitHub-is-load-bearing rule).

---

## 0. TL;DR — where we are RIGHT NOW (read first)

The whole multi-broker bundle pipeline now WORKS up to MT5 launch:

- The engine stamps a `broker-bundle` initContainer on every tenant pod.
- That init `wget`s the broker's portable zip from Cloudflare R2,
  `sha256sum -c` verifies it, and `unzip`s it into `/broker-bundle`.
- `entrypoint.sh` FINDs the broker's `servers.dat` under `/broker-bundle`
  and installs it into the terminal's `config/` before launch.
- On the latest provision the bundle init logged
  `/broker-bundle/bundle.zip: OK` + `Bundle extracted successfully.` and
  the pod reached `2/3 Running`.

**THE CURRENT OPEN WALL:** the tenant never reaches `3/3 Ready` within the
provisioner's **300s readiness gate** (`_wait_ready` phase 1: StatefulSet
Ready replica). When the gate expires the provisioner raises
`ProviderTimeoutError` and `_best_effort_cleanup` DELETES the whole tenant
(StatefulSet, Services, SA, watchdog CM, PVC, Vault path) and the
`broker_connections` row is marked:

```
status = failed
status_message = Provisioning failed: mt-node StatefulSet did not become Ready within timeout
```

The pod becomes Ready only when the watchdog `/healthz` reports
`mt5_connected=1 AND authenticated=1` — i.e. MT5 has LOGGED IN to the
broker and the EA has bound `:5555`. So the wall is now at
**MT5 login -> EA :5555 bind -> pod 3/3 Ready**, NOT at the bundle/servers.dat
layer (that is fixed).

**THE OPEN QUESTION (decide this next):** is the failure
(a) SLOW FIRST BOOT exceeding 300s (264MB bundle download + 166MB Wine
    prefix seed + MT5 453-file recompile + login all in one cold boot), or
(b) a REAL LOGIN FAILURE (MT5 cannot authenticate / connect to Deriv)?

We have NOT yet captured a live MT5 journal showing a login attempt,
because the pod is torn down at the 300s mark before we read it. The
immediate next step (§5) raises the timeout and tails the journal live to
tell (a) from (b).

---

## 1. Environment / identity

| Item | Value |
|---|---|
| Environment | `staging` |
| VPS / node | Contabo VPS 30 NVMe, node `vmi3362776`, public IP `13.140.164.173` |
| Namespace | `etradie-system` |
| Engine deploy | `deploy/etradie-engine` |
| Vault | `vault-0` in `vault` ns; KV-v2 mount `etradie`; `http://vault.vault.svc.cluster.local:8200` |
| Current image SHA (engine + mt-node) | `1735eeea08ab69c397441065b02cfcca6b0c6dbc` |
| Git remotes | `origin` = GitHub `FlameGreat-1/eTradie` (CI + ArgoCD source, LOAD-BEARING), `gitlab` = `intelli1344225/exoper` (mirror / MCP) |
| Broker under test | Deriv, entity `deriv_com_limited`, server `Deriv-Demo` |
| Dashboard user_id under test | `83d7fb874e2f9e8c091e07cf76ebaad8` |

**R2 broker bundles (Cloudflare, bucket `etradie-installers`, public r2.dev):**

| Object | Size | SHA256 (== catalog `bundle_sha256`) |
|---|---|---|
| `broker-bundles/deriv-portable.zip` | 264 MB | `b0c68f1b3316b7d2aaf8495519642af8dc5947bc4dcf4a1703c520e48d81b5b3` |
| `broker-bundles/exness-portable.zip` | 156 MB | `eadee9c7a152514f9c904b381a9416cf3d88dc5e480a12a62544079743c5e11c` |
| `broker-bundles/exness-mt4-portable.zip` | 43 MB | (MT4; not yet wired in catalog) |

> The Deriv zip is a re-zip of the bake (`compression method=store`, 264MB,
> carries full `Bases/Deriv-Demo` history + MetaEditor cruft). Only its
> `MetaTrader 5/config/servers.dat` is used at runtime. The catalog SHA was
> re-pinned from the stale `ec1be686…` to the actual object SHA `b0c68f1b…`
> (defect #17d). Exness already matched; no re-pin needed.

---

## 2. Defect #17 — multi-broker bundle layering (ALL FIXED, live on 1735eeea)

Four sub-defects, found+fixed in this session by tracing the full path
(provisioner.py, entrypoint.sh, registry.py, deriv.json, Dockerfile,
helm/mt-node/templates/statefulset.yaml):

- **#17a — broker-bundle initContainer never attached.** The provisioner
  BUILT `bundle_init_container` but the `V1PodSpec` had
  `containers=[…]` and NO `init_containers=`, so the init was a dead local
  and `/broker-bundle` stayed empty. Fix: add
  `init_containers=[bundle_init_container]` to the PodSpec
  (`src/engine/ta/broker/mt5/hosted/provisioner.py`). Engine image.

- **#17b — entrypoint looked for servers.dat at the wrong path.** The zip
  unzips to `/broker-bundle/MetaTrader 5/config/servers.dat` (top-level
  `MetaTrader 5/` dir, proven by the Dockerfile's own MT install), but
  `entrypoint.sh` only checked `/broker-bundle/config/`. Fix: FIND
  `servers.dat` (+ any `*.srv`) anywhere under `/broker-bundle` and install
  into `$MT_DIR/config/` (`docker/mt-node/entrypoint.sh`). mt-node image.

- **#17c — broker-bundle init hit a read-only filesystem.** The init runs
  `readOnlyRootFilesystem=true` with only the `broker-bundle` emptyDir
  mounted; `wget -qO /tmp/bundle.zip` failed `Read-only file system` ->
  `Init:CrashLoopBackOff`. Fix: stage/verify/unzip the zip INSIDE the
  writable `/broker-bundle` emptyDir (`/broker-bundle/bundle.zip`), then
  `rm` it. Applied to BOTH the provisioner AND
  `helm/mt-node/templates/statefulset.yaml` (parity). Engine + chart.

- **#17d — deriv bundle_sha256 stale.** The R2 object hashes to
  `b0c68f1b…`, not the recorded `ec1be686…`; `sha256sum -c` failed every
  provision. Verified the object IS the correct Deriv bundle (top-level
  `MetaTrader 5/`, `config/servers.dat`, `Bases/Deriv-Demo` for account
  201415706) — just a re-zip. Fix: re-pin `bundle_sha256` to `b0c68f1b…`
  in `infrastructure/broker-catalog/deriv.json`. Engine image (catalog is
  baked into the engine image at `/app/infrastructure/broker-catalog`).

**All four are merged to `main` and live in image `1735eeea`.** Confirmed
on the cluster: bundle init logs `OK` + `Bundle extracted successfully.`;
running engine has `b0c68f1b…` in its catalog (`NEW SHA LOADED`).

---

## 3. The full provisioning chain (where each step lives)

1. Dashboard submit (`connection_type=hosted`, broker_id+entity_id+server) ->
   `broker_connections` row created.
2. Engine `HostedProvisioner.provision_account` resolves the broker via
   the registry -> `bundle_r2_path` + `bundle_sha256`.
3. Upserts: Vault creds, ServiceAccount, watchdog ConfigMap, StatefulSet
   (with `broker-bundle` initContainer + `MT_SYMBOL=__pending__` sentinel),
   ClusterIP + headless Services.
4. Pod init: `vault-agent-init` (renders creds) -> `broker-bundle`
   (wget+sha+unzip to `/broker-bundle`).
5. mt-node entrypoint: seed Wine prefix from baked template -> Xvfb ->
   INSTALL `/broker-bundle/.../servers.dat` into `$MT_DIR/config/` ->
   write `startup.ini` (Login/Password/Server) -> pin LiveUpdate ->
   `wine terminal64.exe /config:startup.ini`.
6. MT5: resolve `Server=Deriv-Demo` (now in servers.dat) -> LOGIN ->
   symbols -> chart -> EA attaches -> `libzmq.dll` -> bind `:5555`.
7. watchdog `/healthz` -> `mt5_connected=1 + authenticated=1` -> pod 3/3.
8. Engine `_wait_ready` (300s): StatefulSet Ready replica AND ZMQ PING ok.
9. Engine resolves first symbol via `GET_ALL_SYMBOLS`, patches `MT_SYMBOL`,
   K8s rolls the pod ONCE (the documented symbol "two-boot").

**CURRENT WALL: step 6/7 not completing within the step-8 300s gate.**

---

## 4. Operator routine (every command below needs this)

Two terminals.

```bash
# Terminal 1 (leave open) — SSH tunnel to the K3s API:
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173

# Terminal 2 — every command runs here:
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes        # vmi3362776 Ready  => tunnel live
```

The tunnel drops often; if `kubectl` hangs ~30s then fails, re-open
Terminal 1. `gh` + `git` + GHCR `curl` run from `~/eTradie` on the
workstation (no tunnel needed for those).

---

## 5. >>> RESUME HERE — immediate next step (decide slow-boot vs login-fail) <<<

The last provision (`f5807ee7-e8c`) FAILED the 300s gate. The fixes are
live; the open question is WHY login/Ready did not complete in time. Do
this, in order:

### 5.1 — Raise the readiness timeout so a slow-but-correct boot can finish

The provisioner reads `MT_NODE_READINESS_TIMEOUT_SECS` (default 300). A
cold first boot does: 264MB bundle download + unzip, 166MB Wine-prefix
seed (`cp -a` + `wineboot -u`), MT5 453-file recompile (~100s), THEN
login. That can exceed 300s. Bump it to 900s (runtime env override; NO
image rebuild):

```bash
kubectl -n etradie-system set env deploy/etradie-engine MT_NODE_READINESS_TIMEOUT_SECS=900
kubectl -n etradie-system rollout status deploy/etradie-engine
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_READINESS_TIMEOUT_SECS  # 900
```

### 5.2 — Clean the failed tenant + row

```bash
kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
kubectl -n etradie-system exec -i postgres-0 -c postgres -- \
  psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE status IN ('failed','provisioning','active') RETURNING id;"
kubectl -n etradie-system get statefulset,svc,sa,pvc | grep -i 'mt-' || echo "clean"
```

### 5.3 — Re-submit Deriv from the dashboard, then TAIL THE JOURNAL LIVE

Submit `connection_type=hosted`, broker Deriv, entity `deriv_com_limited`,
Server `Deriv-Demo`, with valid MT5 login + password. Then immediately:

```bash
# Resolve the pod (re-run until it appears; it survives longer now that
# the gate is 900s):
POD=$(kubectl -n etradie-system get pods -o name | grep 'etradie-mt-' | head -1 | cut -d/ -f2); echo "$POD"

# Watch it climb: Init:1/2 -> Init:2/2 -> 2/3 Running -> 3/3 Running
kubectl -n etradie-system get pod "$POD" -o wide -w
```

In a 3rd terminal (tunnel shared), once the pod is past Init and `mt-node`
is Running, watch the DECISIVE MT5 journal — this tells slow-boot from
login-failure:

```bash
P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

# entrypoint confirms servers.dat install (should be immediate):
kubectl -n etradie-system logs "$POD" -c mt-node | grep -iE 'Installed broker servers.dat|Launching terminal'

# servers.dat carries Deriv (defect #16/#17 proof):
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "grep -aiE 'deriv' \"$P/config/servers.dat\" | head"

# THE JOURNAL — re-run every ~20s. Look for a 'login'/'authorized'/'network'
# line vs only '0 file(s) compiled' then silence:
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log 2>/dev/null|head -1); echo \"=== \$f ===\"; tail -50 \"\$f\""

# lowercase bases/ appears ONLY after a successful broker connect:
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c "ls \"$P/bases\" 2>&1"

# :5555 bound? (EA up)
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'cat /proc/net/tcp | grep -i 15B3 && echo ":5555 LISTEN" || echo ":5555 not bound"'
```

### 5.4 — Interpret

- **Pod reaches 3/3 within the 900s window** -> the cause was SLOW FIRST
  BOOT, not login. Action: keep a higher `MT_NODE_READINESS_TIMEOUT_SECS`
  (and consider trimming the 264MB Deriv bundle to a thin servers.dat-only
  bundle — see §7 follow-ups — so future boots are fast). Then let the
  symbol two-boot complete and mark active.
- **Journal shows a broker LOGIN/authorized line, lowercase `bases/`
  appears, `:5555 LISTEN`** -> login works; if it still timed out it was
  purely speed -> raise timeout / speed up bundle.
- **Journal ends at `0 file(s) compiled` with NO network/login line, no
  lowercase `bases/`, `:5555 not bound` even after several minutes** ->
  REAL LOGIN FAILURE. Next: verify `startup.ini` has the right
  Login/Password/Server, that the creds are valid for `Deriv-Demo`, and
  that the pod has egress to Deriv's trade servers. Capture the full
  journal + `startup.ini` + `ps -ef | grep terminal64` before the next
  teardown.

---

## 6. Reference — the full CI -> roll -> verify cycle (when you change code)

Both the provisioner (engine image) and entrypoint (mt-node image) are
IMAGE-BAKED, and the broker catalog is baked into the ENGINE image. Any
change to provisioner.py, entrypoint.sh, or infrastructure/broker-catalog/
requires a CI rebuild + roll. Runtime-only knobs (e.g.
`MT_NODE_READINESS_TIMEOUT_SECS` via `kubectl set env`) do NOT.

### 6.1 — Push to GitHub (LOAD-BEARING; CI + ArgoCD read GitHub only)

```bash
cd ~/eTradie
git fetch gitlab main && git reset --hard gitlab/main   # MCP commits land on gitlab
git push --force-with-lease origin main
# If the tip is a '[skip ci] pin' commit, CI will NOT trigger; nudge it:
git commit --allow-empty -m "ci: rebuild for <reason>"
git push origin main
```

### 6.2 — Wait for the CI run (NOT Security Scan) to go fully green

```bash
gh run list --repo FlameGreat-1/eTradie --branch main --limit 5
gh run watch --repo FlameGreat-1/eTradie    # select the CI run
```
- The image-building job is `Build (and push on main) all four service
  images` (a matrix: engine, gateway, execution, management, billing,
  edge-ingress, mt-node).
- `fail-fast: false`, so one leg can fail independently. If a leg fails on
  the Docker Hub buildx blip
  (`Head "https://registry-1.docker.io/.../moby/buildkit…": unknown`),
  it is FLAKY — re-run the failed jobs:
  `gh run rerun --repo FlameGreat-1/eTradie <RUN_ID> --failed`.
- `deploy-bump` (`Pin staging overlays to the built image SHA`) only runs
  if the WHOLE build job is green. It commits
  `ci: pin staging image tags to <SHA> [skip ci]` and pins every
  `helm/<svc>/values-staging.yaml` + `helm/engine/values-staging.yaml`
  `config.mtNode.image` to the source SHA.

### 6.3 — Confirm images exist in GHCR for the pinned SHA

```bash
git fetch origin main && git pull --rebase origin main   # pick up the deploy-bump pin
PIN=$(git show origin/main:helm/engine/values-staging.yaml | grep -E '^[[:space:]]*tag:' | head -1 | tr -d ' "' | cut -d: -f2)
echo "staging pin = $PIN"
GH_OWNER=FlameGreat-1; GH_PAT=$(cat ~/.ghcr_pat)
for repo in flamegreat-1/etradie/engine flamegreat-1/etradie/mt-node; do
  token=$(curl -sS -u "$GH_OWNER:$GH_PAT" "https://ghcr.io/token?service=ghcr.io&scope=repository:${repo}:pull" | jq -r .token)
  printf '%-40s ' "$repo:$PIN"
  curl -sS -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $token" \
    -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json,application/vnd.oci.image.manifest.v1+json" \
    "https://ghcr.io/v2/${repo}/manifests/$PIN"
done
```

> GOTCHA: GHCR tags are the FULL 40-char git SHA. A short SHA 404s. And
> NEVER query `git rev-parse origin/main` blindly — if the tip is the
> `[skip ci]` deploy-bump commit it has NO image; read `$PIN` from the
> values file (as above), which is always the real source SHA.

Both must be `200`.

### 6.4 — Sync ArgoCD + roll, then verify the engine actually loaded it

```bash
kubectl -n argocd patch application engine-staging  --type merge -p '{"operation":{"sync":{"revision":"HEAD"}}}'
kubectl -n argocd patch application mt-node-staging --type merge -p '{"operation":{"sync":{"revision":"HEAD"}}}' 2>/dev/null || true
kubectl -n etradie-system rollout status deploy/etradie-engine

# engine image == PIN
kubectl -n etradie-system get deploy etradie-engine \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="engine")].image}{"\n"}'
# MT_NODE_IMAGE == PIN (the tenant pod image the provisioner stamps)
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_IMAGE
# catalog change actually loaded (example: a deriv sha):
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- \
  grep -o '<expected-sha-or-string>' /app/infrastructure/broker-catalog/deriv.json && echo LOADED || echo STALE
kubectl -n etradie-system logs deploy/etradie-engine -c engine | grep -i broker_registry_loaded | tail -1
```

> NOTE: ArgoCD auto-sync is OFF on these apps by design (operator syncs
> manually via the patch above). `OutOfSync` is normal until you patch.
> Mirror back to GitLab after: `git push gitlab main`.

---

## 7. Outstanding follow-ups (not blocking the current wall)

- **Thin the Deriv bundle.** The 264MB `deriv-portable.zip` carries full
  `Bases/Deriv-Demo` history + `MetaEditor64.exe` + examples the tenant
  never uses (the entrypoint installs ONLY `servers.dat`). Re-bake a
  servers.dat-only (or config-only) bundle to cut init download time +
  ephemeral-storage pressure, then re-pin `bundle_sha256`. This is likely
  contributing to the slow-first-boot timeout.
- **`MT_NODE_READINESS_TIMEOUT_SECS`.** If slow-boot is confirmed, decide a
  permanent value (set it in `helm/engine/values-staging.yaml` ->
  ConfigMap, not just `kubectl set env`, so it survives rolls).
- **Doc drift.** `MT5_Multi_Broker_Provisioning_Architecture.md` §14.3
  still records the Deriv zip SHA as `ec1be686…`; update it to the actual
  `b0c68f1b…` so the doc stays authoritative.
- **Exness end-to-end.** Exness bundle SHA already matches; once Deriv is
  green, provision Exness (`exness_technologies_ltd`) and verify.
- **CI Docker Hub flakiness.** The buildx `moby/buildkit` pull from Docker
  Hub fails intermittently; consider a GHCR-hosted/digest-pinned buildkit
  image so a leg does not flake and block `deploy-bump`.
- **MT4 path.** `exness-mt4-portable.zip` exists in R2 but MT4 is not yet
  wired in the catalog; unproven end-to-end.

---

## 8. Quick fault map (symptom -> meaning)

| Symptom | Meaning |
|---|---|
| `broker-bundle` init only initContainer; no `vault-agent-init` issue but no bundle init | (pre-#17a) provisioner not attaching init — FIXED in 1735eeea |
| `/broker-bundle/bundle.zip: Read-only file system` | (pre-#17c) init wrote to read-only `/tmp` — FIXED |
| `/broker-bundle/bundle.zip: FAILED` + `sha256sum: … did NOT match` | bundle SHA in catalog != R2 object (defect #17d class). Verify R2 object SHA, re-pin catalog (never weaken the gate). |
| `/broker-bundle/bundle.zip: OK` + `Bundle extracted successfully.` | bundle layer healthy (current good state) |
| `Init:CrashLoopBackOff` | an initContainer is failing — check `kubectl logs <pod> -c broker-bundle` |
| Pod `2/3 Running` then row `status=failed: … did not become Ready within timeout` | CURRENT WALL — MT5 login/EA-bind not done within `MT_NODE_READINESS_TIMEOUT_SECS` (300s). Raise timeout + tail journal (§5). |
| Journal ends at `0 file(s) compiled`, no network/login line, no lowercase `bases/`, `:5555 not bound` | MT5 not logging in — investigate startup.ini creds / Deriv egress |
| Pod re-enters `Init` shortly after `2/3` with a new resourceVersion | either the symbol two-boot (engine patched `MT_SYMBOL`) OR teardown by `_best_effort_cleanup`. Check engine log for `hosted_statefulset_symbol_patched` vs `ProviderTimeoutError`/cleanup, and the row status. |

---

## 9. Git remotes dance (MCP writes to GitLab; CI is on GitHub)

```bash
# MCP/agent commits land on gitlab. To deploy, get them onto GitHub:
git fetch gitlab main && git reset --hard gitlab/main
git push --force-with-lease origin main      # LOAD-BEARING (CI + ArgoCD)
# nudge if tip is [skip ci]:
git commit --allow-empty -m "ci: rebuild for <reason>" && git push origin main
# after CI + deploy-bump:
git fetch origin main && git pull --rebase origin main
git push gitlab main                          # keep mirror aligned
```

Never cross-rebase the two remotes repeatedly — GitHub carries the
`[skip ci]` deploy-bump bot commits GitLab lacks, so SHAs diverge and you
get non-fast-forward rejections. Treat GitLab as source, force GitHub to
match, let deploy-bump add its commit, then mirror GitHub back to GitLab.
