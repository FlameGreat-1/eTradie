# Hosted-MT (Wine) Provisioning — In-Flight Session Runbook

**Status:** IN PROGRESS. Read this top-to-bottom before running anything.
This is the authoritative resume point for the hosted-MT provisioning
effort on the **staging** Contabo box (`vmi3362776`).

**Last updated:** 2026-06-21, session through defect #13 (MT terminal binary
missing from the image -> portable MT5/MT4 artifact build).

> SESSION UPDATE 2026-06-21 (defect #13 - MT terminal binary missing
> from the mt-node image). READ THIS BLOCK FIRST; it supersedes every
> older resume pointer below.
>
> WHAT WAS WRONG:
> - After defects #10/#11/#12 cleared (no more 'Read-only file system'
>   and no more 'is not owned by you'), the tenant pod's mt-node
>   container Wine-launched and immediately looped on
>   `ShellExecuteEx failed: File not found` / `Application could not be
>   started`, exhausted its 6x in-pod restart budget, and CrashLooped.
> - Filesystem-confirmed on the running pod: NO `terminal64.exe`
>   anywhere in `/opt/wine-template` or `/home/mt/.wine/prefix`, and NO
>   `MetaTrader 5` dir at all in the baked template (only Wine's
>   built-in stubs: iexplore/wmplayer/wordpad). The MT5/MT4 install
>   simply never happened during the image build.
> - ROOT CAUSE: `docker/mt-node/Dockerfile` ran
>   `wine /tmp/mtXsetup.exe /auto 2>/dev/null || true` at build time
>   with NO X display and ALL errors swallowed. MetaQuotes' mtXsetup.exe
>   is an interactive GUI web-installer; even with /auto it needs a
>   display and does not reliably complete unattended. With no display
>   and `|| true` it silently no-op'd, the build 'succeeded', and the
>   image shipped with no terminal. (The prior 'working' builds were an
>   illusion: the install was ALWAYS a no-op, hidden by `|| true`.)
>
> FIRST FIX ATTEMPT (insufficient, do NOT rely on it):
> - Ran the installer under `xvfb-run`, dropped `|| true`, added a hard
>   `terminal64.exe`/`terminal.exe` assertion. Result: the build no
>   longer silently ships broken, but the GUI web-installer HANGS
>   indefinitely under xvfb (waits on a prompt nobody clicks). CI stuck
>   30min+ on the MT5 install step. Confirms: running the installer in
>   `docker build` is the wrong design, period.
>
> PERMANENT FIX (in progress): do NOT run the installer in the build.
> Bake PRE-INSTALLED PORTABLE MT5 + MT4 directories into the image.
> - Generated once on a workstation with Wine 9.0 + Xvfb:
>     export WINEPREFIX=~/mt-portable/wine
>     wine wineboot --init; wineserver --wait
>     xvfb-run -a -s "-screen 0 1024x768x24" wine mt5setup.exe /auto; wineserver --wait
>     xvfb-run -a -s "-screen 0 1024x768x24" wine mt4setup.exe /auto; wineserver --wait
>   (the installer's post-install UI page-faults / 'X connection broken'
>   are COSMETIC; the files land before that.) Both binaries verified:
>     .../drive_c/Program Files/MetaTrader 5/terminal64.exe
>     .../drive_c/Program Files (x86)/MetaTrader 4/terminal.exe
> - Zipped from inside the respective Program Files dir so each zip has
>   a top-level `MetaTrader 5` / `MetaTrader 4` folder:
>     cd "$WINEPREFIX/drive_c/Program Files"       && zip -rq mt5-portable.zip "MetaTrader 5"
>     cd "$WINEPREFIX/drive_c/Program Files (x86)" && zip -rq mt4-portable.zip "MetaTrader 4"
> - Artifact sha256 (these are the NEW values for the *_INSTALLER_SHA256
>   secrets - the pins now fingerprint the PORTABLE ZIPS, not the .exe):
>     mt5-portable.zip  166M  32675431e68ab8715ee6e0b45d77d58b206fbbc8f610ad54d71b32c7f821ece3
>     mt4-portable.zip   41M  b2dcd86fcc658a41d677f0fee5d3b725ab8e6aa539929d5199a7d854210b7ff9
>
> HOSTING: both zips uploaded to a Cloudflare R2 public bucket
> (`etradie-installers`, r2.dev public subdomain). Any anonymous HTTPS
> host works; the URL just must NOT contain `download.mql5.com` (the CI
> production-build guard blocks that substring).
>
> GITHUB ACTIONS SECRETS after this change (repo FlameGreat-1/eTradie,
> Settings -> Secrets and variables -> Actions). Already present from
> deploy time: WINEHQ_VERSION, EA_EX5_SHA256, EA_EX4_SHA256,
> ETRADIE_ALLOW_PUBLIC_INSTALLER_CDN. REWIRED for defect #13:
>   MT5_INSTALLER_URL    = https://pub-<hash>.r2.dev/mt5-portable.zip
>   MT4_INSTALLER_URL    = https://pub-<hash>.r2.dev/mt4-portable.zip
>   MT5_INSTALLER_SHA256 = 32675431e68ab8715ee6e0b45d77d58b206fbbc8f610ad54d71b32c7f821ece3
>   MT4_INSTALLER_SHA256 = b2dcd86fcc658a41d677f0fee5d3b725ab8e6aa539929d5199a7d854210b7ff9
>
> DOCKERFILE CHANGE (docker/mt-node/Dockerfile): both MT install steps
> are being rewritten to: add `unzip` to apt; download the portable zip
> from MTx_INSTALLER_URL; verify sha256 against MTx_INSTALLER_SHA256;
> `unzip` into `$WINE_TEMPLATE/drive_c/Program Files/` (MT5) and
> `$WINE_TEMPLATE/drive_c/Program Files (x86)/` (MT4); keep the hard
> terminal64.exe / terminal.exe assertions; NO `wine ... /auto` run.
> Deterministic, reproducible, no hang.
>
> >>> RESUME HERE (2026-06-21) <<<
> 1. Confirm the two zips are live + byte-correct:
>      curl -fsI "$MT5_INSTALLER_URL" | head -1   # HTTP/2 200
>      curl -fsSL "$MT5_INSTALLER_URL" | sha256sum # == 32675431...ece3
>      curl -fsI "$MT4_INSTALLER_URL" | head -1   # HTTP/2 200
>      curl -fsSL "$MT4_INSTALLER_URL" | sha256sum # == b2dcd86f...7ff9
> 2. Confirm the four GitHub secrets above are set, then push the
>    Dockerfile rewrite to the GitLab mirror (propagates GitLab -> GitHub
>    -> CI). Watch the GitHub Actions `build (mt-node)` job: it must now
>    download+unzip (seconds), print `INFO: MT5 terminal64.exe verified`
>    and `INFO: MT4 terminal.exe verified`, and go GREEN with NO hang.
> 3. After CI green + deploy-bump, the new mt-node image SHA is pinned
>    into helm/mt-node/values-staging.yaml + helm/engine/values-staging
>    .yaml::config.mtNode.image. Confirm the engine picked it up:
>      export KUBECONFIG=~/.kube/etradie-contabo.yaml
>      kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_IMAGE
>    (must be the new git SHA, NOT 34a2dabd / 8deaafc2). NOTE: a stale
>    inline `MT_NODE_IMAGE` env on the Deployment can override envFrom -
>    if so, `kubectl -n etradie-system set env deploy/etradie-engine
>    MT_NODE_IMAGE-` to drop it and let the ConfigMap value win.
> 4. Clean the prior failed tenant + rows, re-provision FROM THE
>    DASHBOARD (connection_type=hosted), gate on the pod image, then
>    watch the decisive log:
>      kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
>      kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c "DELETE FROM broker_connections WHERE status IN ('failed','provisioning') RETURNING id;"
>      # submit in dashboard, then:
>      CONN=$(kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -t -A -c "SELECT left(id::text,12) FROM broker_connections ORDER BY created_at DESC LIMIT 1;")
>      kubectl -n etradie-system get pod etradie-mt-${CONN}-0 -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'
>      kubectl -n etradie-system logs etradie-mt-${CONN}-0 -c mt-node --tail=40 -f
>    SUCCESS = `Launching terminal64.exe` is NOT followed by
>    `ShellExecuteEx failed: File not found`; MT5 actually starts.
> 5. Anticipated NEXT walls after Wine launches (not hit yet): MT5
>    broker login on Deriv-Demo, EA ZMQ bind on :5555, then the symbol
>    two-boot (one expected roll). Watchdog /healthz needs
>    mt5_connected=true AND authenticated=true to go Ready.
>
> CAUTION ON THE PORTABLE ARTIFACT: the zips carry a full MT5/MT4
> install (166M/41M). They are broker-agnostic (Deriv-Demo login is
> supplied at runtime via startup.ini). If a broker requires its own
> custom MT build, the portable terminal still connects to standard
> MT5/MT4 servers; only re-generate the zip if you intentionally change
> the MT base version (then recompute + update the *_INSTALLER_SHA256
> secrets).


> SESSION UPDATE 2026-06-20 (defects #10/#11/#12 + mt-node image
> delivery GitOps). Read this block FIRST; it supersedes older resume
> pointers below. Current GitHub `main` image SHA tag after this work:
> `8deaafc2d54e13ce614498573cd668dc13cd257d` (the mt-node image that
> carries ALL fixes below). The engine ConfigMap
> `etradie-engine-config::MT_NODE_IMAGE` already renders this SHA and
> the engine has rolled to it.
>
> WHAT WAS WRONG (cascade continued from #9):
> - Defect #10 - mt-node never re-pulled (GitOps gap). mt-node was the
>   ONLY CI-built/staging service NOT wired into the `deploy-bump`
>   immutable-SHA GitOps. Its image stayed pinned to mutable `0.1.0`
>   (helm/mt-node/values-image.yaml + engine config.mtNode.image). With
>   pullPolicy IfNotPresent and 0.1.0 already cached on the node, a
>   rebuilt image republished as 0.1.0 was NEVER re-pulled; ArgoCD saw
>   no diff. CI green did NOT mean fix-on-cluster.
> - Defect #11 - Wine prefix reset hit read-only FS. entrypoint.sh ran
>   `rm -rf "$WINE_PREFIX"` (the PVC mount point) on the fresh-PVC
>   "appears corrupted" path; under readOnlyRootFilesystem=true that
>   failed 'Read-only file system', exit 1, CrashLoopBackOff.
> - Defect #12 - Wine prefix ownership. After #11, Wine aborted:
>   `wine: '/home/mt/.wine' is not owned by you`. The PVC mount root is
>   owned by uid 0 (fsGroup sets group only); Wine requires WINEPREFIX
>   owned by the running euid (1000). Container is non-root under the
>   etradie-system RESTRICTED PodSecurity Standard, so NO root chown /
>   root init-container is possible.
>
> FIXES (all merged to `main`; flow GitLab mirror -> GitHub -> CI/ArgoCD):
> - #10 -> MR !2: wired mt-node into `deploy-bump` (staging-only,
>   lockstep). Added helm/mt-node/values-staging.yaml::image.tag and
>   helm/engine/values-staging.yaml::config.mtNode.image; CI rewrites
>   BOTH to the immutable git SHA each push. Production untouched (still
>   rolls on values-image.yaml RELEASE_TAG - the intended human-gated
>   invariant; this is the flagged prod cutover follow-up).
> - #11 -> MR !1 (commit 2601dbb2): reset the prefix CONTENTS, not the
>   mount point.
> - #12 -> MR !3 (commit 2225afbf): point WINEPREFIX at an OWNED
>   subdirectory /home/mt/.wine/prefix (created by uid 1000) instead of
>   the root-owned PVC mount root. Pure entrypoint.sh change; both MT4
>   and MT5 branches derive MT_DIR from $WINE_PREFIX so both are fixed;
>   no securityContext/PSS change. Permanent + environment-agnostic
>   (applies to staging AND production, chart + engine-runtime paths).
> - GitOps follow-ups MR !4 + MR !5: !4 consolidated a duplicate
>   config.mtNode block in helm/engine/values-staging.yaml (MR !2 had
>   created a second mtNode mapping). !5 made the CI `deploy-bump`
>   engine write idempotent/race-proof via `del(.config.mtNode.image)`
>   then set, so a checkout-timing race can never re-create a duplicate
>   and any existing GitHub duplicate self-heals on the next bump.
>
> >>> RESUME HERE (2026-06-20) <<<
> 1. ArgoCD is OutOfSync on engine-staging and mt-node-staging
>    (Healthy). selfHeal is on; confirm both flip to Synced. If they
>    stick OutOfSync, the engine-values duplicate-key (pre-!5 bump) can
>    keep ArgoCD detecting drift - the next deploy-bump run (post-!5)
>    collapses it; or force `argocd app sync engine-staging
>    mt-node-staging`. Verify after: both Synced + MT_NODE_IMAGE =
>    8deaafc2... (or a newer SHA if more pushes landed).
> 2. Confirm the GitOps lockstep is clean (after the next bump):
>      git show origin/main:helm/engine/values-staging.yaml | grep -c 'mt-node:'   # expect 1
>      git show origin/main:helm/mt-node/values-staging.yaml | grep -A1 '^image:'  # tag == engine SHA
> 3. Re-provision the tenant FROM THE DASHBOARD (connection_type=hosted;
>    NOT via kubectl). Before submitting, clean the prior failed tenant
>    (last under test: etradie-mt-f7cafe99-07c):
>      kubectl -n etradie-system delete statefulset etradie-mt-f7cafe99-07c --ignore-not-found
>      kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c "DELETE FROM broker_connections WHERE status IN ('failed','provisioning') RETURNING id;"
> 4. Watch the decisive log (expect NO 'Read-only file system' and NO
>    'is not owned by you'; then Xvfb ready -> Launching terminal64.exe
>    -> pod climbs to 3/3 Ready, one roll for the symbol two-boot):
>      CONN=$(kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -t -A -c "SELECT left(id::text,12) FROM broker_connections ORDER BY created_at DESC LIMIT 1;")
>      kubectl -n etradie-system get pod etradie-mt-${CONN}-0 -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'   # must be 8deaafc2 (or newer) SHA
>      kubectl -n etradie-system logs etradie-mt-${CONN}-0 -c mt-node --tail=40 -f
> 5. Anticipated NEXT walls after Wine launches (not hit this session):
>    MT5 broker login on Deriv-Demo, EA ZMQ bind on :5555, then the
>    symbol two-boot (one expected roll). Watchdog /healthz needs
>    mt5_connected=true AND authenticated=true to go Ready.
>
> GIT REMOTES DANCE: merges land on the GitLab mirror;
> `git pull --rebase gitlab main` then `git pull --rebase origin main`
> then `git push origin main` propagates to GitHub (which carries the
> etradie-ci[bot] [skip ci] deploy-bump commit your local lacks). CI
> runs on GitHub Actions; the GitLab MR page shows no real pipeline.

> SESSION UPDATE (defect #9 + msgpack CVE): the engine image carrying
> the defect 7+8 fixes rolled (`0b5f2b5e…`) but the new engine pod
> crash-looped. Root cause was NOT a 7+8 regression (the rendered
> tenant StatefulSet spec is correct). It is a **new defect #9**: the
> eager hosted-recovery startup sweep was awaited synchronously BEFORE
> the lifespan `yield`. `run_once_at_startup() -> _sweep -> _reprovision
> -> HostedProvisioner.provision_account() -> _wait_ready` blocks up to
> `_READINESS_TIMEOUT_SECS` (300s) PER tenant on StatefulSet-Ready + ZMQ
> PING. During that window uvicorn never binds `:8000`, the engine
> `/health` startup probe gets connection-refused, the kubelet kills the
> pod, and the engine crash-loops -- which never gives the tenant Wine
> pod a stable parent to finish booting.
>
> FIX (on `main` via MR !157): in `src/engine/main.py` keep
> `start_background_loop()` + the construction/ConfigurationError guard
> on the boot path (both instant), but run the eager bypass-threshold
> sweep as a fire-and-forget background task via
> `container.background_tasks.schedule_once("lifespan:hosted_recovery_startup_sweep", ..., cooldown_s=3600, timeout_s=1800)`,
> mirroring the macro-cache warmup and the provisioner's own
> `_catalog_sync_runner` wave. `timeout_s=1800` comfortably exceeds the
> 300s per-tenant gate under the default `max_concurrent_reprovisions=4`.
> The engine now reaches `yield` and serves `/health` immediately, then
> converges hosted tenants in the background. The "full system restart
> recovery" guarantee is preserved (the eager sweep still runs, just not
> on the blocking boot path).
>
> ALSO: `requirements/base.txt` bumped `msgpack 1.1.0 -> 1.2.1`
> (GHSA-6v7p-g79w-8964) to clear the `pip-audit --strict` job
> (committed directly to `main`).

---

## TL;DR — where we are right now

We are provisioning the **first hosted-MT (Wine) tenant** via the dashboard
(`connection_type=hosted`). The engine's `HostedProvisioner` runs the
provisioning at runtime (not ArgoCD). Each dashboard submit creates a
`broker_connections` row; the engine then writes per-tenant creds to Vault
and creates a per-tenant StatefulSet + ServiceAccount + Services + watchdog
ConfigMap + PVC. The platform is healthy throughout — only hosted-MT
provisioning is affected. No outage.

Provisioning failed in a **cascade of 8 distinct defects**, each revealed
after the previous was fixed. **All 8 are now fixed in code on `main`.**
The infra fixes (egress, RBAC) are live and verified. The 4 most recent
fixes are **engine-image (Python) changes** that need CI to build + roll a
new engine image before the runtime `HostedProvisioner` produces correct
tenant pods.

### RESUME POINTER (read this first)

- **Last barrier:** tenant pod's Vault Agent login was failing
  `403 invalid audience` (defect #8). Fix: project an `aud=vault` SA
  token onto the tenant pod and have the agent read it. Two follow-on
  errors were fixed in turn:
  (a) agent pointed at token-path but volume not mounted on the agent
  container -> `no such file or directory`; fixed with
  `agent-copy-volume-mounts: "mt-node"`.
- **What we are waiting on RIGHT NOW:** CI to build a new engine image
  past `ghcr.io/flamegreat-1/etradie/engine:2e4aba9f...` and bump
  `helm/engine/values-staging.yaml::image.tag`, then ArgoCD rolls it.
  The provisioner fix only takes effect once that new engine pod runs.
- **Then:** delete the stuck connection from the dashboard, re-create,
  and verify the tenant pod's `vault-agent-init` logs
  `authentication successful` and the pod reaches `3/3 Ready`.
  See "RESUME HERE" below for exact commands.

### Fixes committed to `main` (GitLab mirror -> GitHub `origin` -> ArgoCD/CI)

| # | Defect | Layer | Needs engine image rebuild? | Status |
|---|---|---|---|---|
| 1 | engine egress to Vault `:8200` + `http` scheme | Helm values | No | DONE, live, verified |
| 2+3 | idempotent alembic migrate + read-path token decrypt for `hosted` (`_load_active_broker_connection` + `test` endpoint) | Engine image | **Yes** | DONE, rolled |
| 4 | engine projects `aud=vault` SA token (engine->Vault) | Helm pod-spec | No | DONE, live, verified |
| 5 | engine egress to K8s API (post-DNAT apiserver `:6443`, `0.0.0.0/0:6443`) | Helm values | No | DONE, live, verified (`6443 OPEN`) |
| 6 | RBAC: engine Role needs `configmaps` `create/update/patch/delete` for the per-tenant watchdog ConfigMap | Helm role | No | DONE, live, verified (`Forbidden` cleared) |
| 7 | tenant pod Vault Agent `aud=vault`: project token + mount + `auth-config-token-path` + `auth-config-audience` | Engine image (provisioner.py) + chart | **Yes** | DONE on main; **awaiting image roll** |
| 8 | tenant pod Vault Agent could not read token: `agent-copy-volume-mounts: "mt-node"` so the injector mounts the projected token onto the agent containers | Engine image (provisioner.py) + chart | **Yes** | DONE on main; **awaiting image roll (current step)** |

> NOTE: items 7+8 are the SAME wall (tenant Vault login) fixed in three
> increments: project aud=vault token -> point agent at it -> copy the
> mount onto the agent. All committed; they ride the next engine image.

### The failure cascade (each was a real, separate root cause)

1. **Empty `BROKER_ENCRYPTION_KEY`** — stale ESO render. Fixed live
   (force-sync ESO + engine restart); KEK 64 hex at
   `etradie/services/engine/staging:broker_encryption_key`.
2. **Alembic crash-loop** — empty `alembic_version` but tables existed.
   Fixed live (`stamp 0033`) + permanently in code (idempotent migrate).
3. **Vault unreachable** — engine egress had no rule to Vault `:8200`.
4. **`https` vs `http`** — in-cluster Vault is plain HTTP.
5. **Engine Vault 403** — default SA token aud was the API server, role
   needs `audience="vault"`. Fixed by projecting an `aud=vault` token.
6. **K8s API unreachable** — `10.43.0.1:443` DNATs to the node's
   apiserver `:6443` BEFORE kube-router egress eval; allowing the VIP
   never matched. Fixed by egress to `0.0.0.0/0:6443`. (kube-router
   REJECTs on policy deny, so it presented as `Connection refused`, not
   a timeout — that misled diagnosis early.)
7. **K8s API 403 Forbidden on create** — apiserver reachable but the
   engine Role lacked `create` on `configmaps` (the per-tenant watchdog
   ConfigMap). Fixed by granting configmaps create/update/patch/delete.
8. **Tenant pod Vault Agent 403 `invalid audience`** — the injected
   Vault Agent read the pod's DEFAULT SA token (aud=API server) but the
   `mt-node-tenant` role requires `audience="vault"`. Fixed (mirroring
   the engine) by projecting an `aud=vault` token + pointing the agent
   at it + copying the mount onto the agent containers. **<-- current.**

### Read-path note (separate from provisioning)

Even after a tenant pod is Ready, the dashboard's `GET /api/broker/symbols`
and positions endpoints raised `Hosted connection has no ea_auth_token`
because `_load_active_broker_connection` (and the `test` endpoint) only
decrypted `ea_auth_token_encrypted` for `connection_type=="ea"`. Fixed to
decrypt for `"hosted"` too (commits 2+3 group). Rides the engine image.

---

## Environment / identity (this session)

| Item | Value |
|---|---|
| Environment | `staging` |
| VPS / node | Contabo VPS 30 NVMe, node `vmi3362776`, public IP `13.140.164.173` |
| Namespace | `etradie-system` |
| Engine deploy | `deploy/etradie-engine` (mesh-OFF on staging per PHASE10.6 checkpoint) |
| Vault | `vault-0` in `vault` ns; KV-v2 mount `etradie`; `http://vault.vault.svc.cluster.local:8200` |
| Vault role (engine) | `mt-node-provisioner` (audience `vault`), policy `mt-node-provisioner-staging`, write on `etradie/data/tenants/mt-node/*` |
| Vault role (tenant pod) | `mt-node-tenant` (SA glob `etradie-mt-*`, read own path) |
| mt-node image | `ghcr.io/flamegreat-1/etradie-mt-node:0.1.0` (present in GHCR) |
| Dashboard user_id under test | `83d7fb874e2f9e8c091e07cf76ebaad8` |
| Git remotes | `origin` = GitHub (ArgoCD/CI source), `gitlab` = this MCP mirror (auto-pushes to origin) |

---

## Operator routine (every command below needs this)

Two terminals. Terminal 1 holds the SSH tunnel; Terminal 2 runs commands.

```bash
# Terminal 1 (leave open):
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173

# Terminal 2:
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes   # vmi3362776 Ready -> tunnel is live
```

Vault root token (read-only use here):
```bash
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
# ... use ...
unset ROOT_TOKEN
```

---

## RESUME HERE — current step: roll engine image with defect 7+8 fix, then re-provision

**Why we wait:** defects 7+8 (tenant pod Vault `aud=vault`) live in
`src/engine/ta/broker/mt5/hosted/provisioner.py` (the runtime that stamps
the tenant pod spec). They only take effect once CI builds a NEW engine
image carrying those commits and ArgoCD rolls it. The Helm/infra fixes
(1,4,5,6) are already live. The chart copies of 7+8 are in
`helm/mt-node/templates/statefulset.yaml` for the by-hand/platform path.

### Step A — confirm the new engine image has rolled

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
# GitHub main must include the latest provisioner commits (defect 7+8):
git ls-remote https://github.com/FlameGreat-1/eTradie.git main
# The engine deployment image SHA must be NEWER than
# ghcr.io/flamegreat-1/etradie/engine:2e4aba9f... (the last pre-fix image)
kubectl -n etradie-system get deploy etradie-engine \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="engine")].image}{"\n"}'
kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o wide  # AGE fresh after roll
```
If the image SHA has NOT changed, CI has not built/bumped it yet. Wait
(or check the GitHub Actions pipeline). Do NOT re-provision until the
engine pod runs the new image, or the tenant pod will lack the projected
aud=vault token and loop on Vault 403 again.

### Step B — (one-time, already done this session) verify infra fixes live

```bash
# K8s API egress (defect 6): both should print OPEN.
GW=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  --field-selector=status.phase=Running -o jsonpath='{.items[-1].metadata.name}')
kubectl -n etradie-system exec "$GW" -c engine -- python3 -c "
import socket
for h,p in [('10.43.0.1',443),('13.140.164.173',6443)]:
    s=socket.socket(); s.settimeout(5)
    try: s.connect((h,p)); print(h,p,'OPEN')
    except Exception as e: print(h,p,type(e).__name__,e)
    finally: s.close()"
# RBAC (defect 7-infra): configmaps must include create.
kubectl -n etradie-system get role etradie-engine \
  -o jsonpath='{range .rules[?(@.resources[0]=="configmaps")]}{.resources}{" -> "}{.verbs}{"\n"}{end}'
```
Expect: `10.43.0.1 443 OPEN`, `13.140.164.173 6443 OPEN`, and configmaps
verbs include `create,update,patch,delete`.

### Step B2 — DECISIVE: verify the tenant pod's Vault Agent authenticates

After the new engine image is live, delete the stuck connection from the
dashboard, re-create, then:

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
CONN=$(kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -t -A -c \
  "SELECT left(id::text,12) FROM broker_connections ORDER BY created_at DESC LIMIT 1;")
echo "CONN=$CONN"
# The agent's auto_auth config must show token_path=/var/run/secrets/vault/token:
kubectl -n etradie-system get pod etradie-mt-${CONN}-0 \
  -o jsonpath='{.spec.initContainers[?(@.name=="vault-agent-init")].env[?(@.name=="VAULT_CONFIG")].value}' \
  | base64 -d | python3 -m json.tool | grep -A5 auto_auth
# And the init log must show authentication SUCCESS (not 403 / no-such-file):
kubectl -n etradie-system logs etradie-mt-${CONN}-0 -c vault-agent-init --tail=15
```
Expect: `token_path` = `/var/run/secrets/vault/token`, and
`agent.auth.handler: authentication successful` (NOT
`invalid audience (aud) claim` and NOT `no such file or directory`).
Once that passes, the pod leaves `Init` -> `ContainerCreating` (Wine
pull) -> `3/3 Ready`. Proceed to Step C/D/E.

### Step C — confirm the prior fixes are STILL live (regression guard)

```bash
GW=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o jsonpath='{.items[0].metadata.name}')
# Vault scheme + reachability
kubectl -n etradie-system exec "$GW" -c engine -- sh -c 'echo "VAULT_ADDR=$VAULT_ADDR"'   # http://...:8200
kubectl -n etradie-system exec "$GW" -c engine -- python3 -c "
import urllib.request
try:
    r=urllib.request.urlopen('http://vault.vault.svc.cluster.local:8200/v1/sys/health',timeout=5); print('VAULT HTTP',r.status)
except urllib.error.HTTPError as e: print('VAULT HTTP',e.code,'(reachable)')
except Exception as e: print('VAULT UNREACHABLE:',e)
"
# SA token audience
kubectl -n etradie-system exec "$GW" -c engine -- python3 -c "
import base64,json
t=open('/var/run/secrets/vault/token').read().split('.')[1]; t+='='*(-len(t)%4)
print('aud=', json.loads(base64.urlsafe_b64decode(t)).get('aud'))
"   # aud= ['vault']
```

### Step D — clean any failed row, then re-provision from the dashboard

```bash
# Delete the most recent failed row (id changes each attempt — list first):
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message FROM broker_connections ORDER BY created_at DESC LIMIT 3;"
# Then delete the failed one(s):
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE status='failed' RETURNING id, status;"
```

Now **submit the broker connection in the dashboard** (`connection_type=hosted`,
MT5 login/password/server). Then watch:

```bash
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message FROM broker_connections ORDER BY created_at DESC LIMIT 1;"
kubectl -n etradie-system get pod,statefulset,sa | grep -i 'mt-' || echo "none yet"
kubectl -n etradie-system logs deploy/etradie-engine -c engine --since=3m \
  | grep -iE 'hosted|provision|vault|statefulset' | grep -iv positions | tail -25
```

**Success signals:**
- Row `status` = `provisioning` then `active` (NOT `failed`).
- StatefulSet `etradie-mt-<id12>`, SA `etradie-mt-<id12>`, pod `etradie-mt-<id12>-0` appear.
- Engine log shows `hosted_*` progress, no `vault`/`403`/`Cannot connect` errors.
- First pod is slow (large Wine image pull) and rolls ONCE for the
  symbol-resolution two-boot dance (Phase 14.5.2 — expected, not a fault).

---

## Step E — tenant verification (run once the pod is up)

Set `CONN` to the first 12 chars of the connection_id (release =
`etradie-mt-<CONN>`):

```bash
CONN=<first-12-chars-of-connection-id>

# 1. Pod Ready + injected containers (mt-node, watchdog, vault-agent)
kubectl -n etradie-system get pod etradie-mt-${CONN}-0 -o wide
kubectl -n etradie-system get pod etradie-mt-${CONN}-0 \
  -o jsonpath='{range .spec.containers[*]}{.name}{"\n"}{end}'

# 2. Vault rendered per-tenant creds to tmpfs (no plaintext K8s Secret)
kubectl -n etradie-system exec etradie-mt-${CONN}-0 -c mt-node -- \
  sh -c 'test -s /vault/secrets/mt-credentials.env && echo creds-present'

# 3. EA health via the watchdog (both gauges should read 1)
kubectl -n etradie-system port-forward etradie-mt-${CONN}-0 9100:9100 &
curl -fsS http://localhost:9100/healthz && echo OK
curl -s http://localhost:9100/metrics | grep -E 'mt_node_ea_(mt5_connected|authenticated) '

# 4. Wine prefix PVC bound
kubectl -n etradie-system get pvc wine-prefix-etradie-mt-${CONN}-0

# 5. ZMQ bridge reachable from the engine
kubectl -n etradie-system logs deploy/etradie-engine -c engine | grep -i 'hosted_' | tail -20
```

---

## Known-good facts (verified live this session — don't re-debug)

- KEK present: `etradie/services/engine/staging:broker_encryption_key` = 64 hex; engine runtime `BROKER_ENCRYPTION_KEY` len 64.
- DB schema at Alembic `0033` (stamped); tables for 0001..0033 all present.
- Vault role `mt-node-provisioner` exists, bound to SA `etradie-engine` in `etradie-system`, policy `mt-node-provisioner-staging` grants write on `etradie/data/tenants/mt-node/*`. A manual `kubectl create token etradie-engine --audience=vault` -> login -> `vault kv put -mount=etradie tenants/mt-node/etradie-mt-probe` SUCCEEDS.
- Engine RBAC Role grants create/delete on statefulsets, serviceaccounts, services, and delete on pvc/secrets in `etradie-system`. `kubectl auth can-i create statefulsets/services --as=system:serviceaccount:etradie-system:etradie-engine` = yes.
- mt-node image `ghcr.io/flamegreat-1/etradie-mt-node:0.1.0` present in GHCR.
- Pre-flight ExternalSecret `etradie-mt-node-platform-platform` = SecretSynced/True.
- Vault reachable from engine: TCP 8200 OPEN, HTTP 200. Projected token `aud=['vault']`.

---

## Possible NEXT walls (anticipated, not yet hit)

1. **Per-tenant pod -> Vault**: the tenant pod uses the Vault Agent Injector
   (role `mt-node-tenant`, audience `vault`, injector handles token). It is a
   different pod/NetworkPolicy scope than the engine; watch its
   `vault-agent-init` if the pod sticks in `Init`.
2. **Wine image pull time**: first pull is large/slow; `ContainerCreating`
   for a couple minutes is normal, not a fault.
3. **Symbol two-boot**: one rolling restart shortly after Ready is expected
   (entrypoint resolves the broker's real symbol, patches `MT_SYMBOL`, K8s
   rolls once). Repeated rolling = fault (check entrypoint log).
4. **Capacity**: each tenant pod ~0.70 CPU; this box is sized ~1 prod MT user.

---

## Outstanding code follow-ups (proper fixes, not yet done)

- **Empty-KEK fail-closed**: engine should refuse to boot if
  `BROKER_ENCRYPTION_KEY` is empty/short (lives in `engine.shared.crypto` /
  the vault settings, NOT `config.py`). Prevents the silent-empty-KEK class.
- **Misleading provisioner error**: `dependencies.py:559` raises
  "broker connection vanished between metadata fetch and construction" for
  what is really "no ea_auth_token / KEK unreadable". Make it specific.
- **Migration image rollout**: commits 2+3 are on main but need the CI
  engine image to actually run in-cluster; until then the idempotent-migrate
  guard is not active (DB is already stamped, so not currently blocking).

---

## Rollback / safety notes

- All fixes 1,4,5 are Helm values/pod-spec only -> revert = `git revert` the
  commit + `argocd app sync engine-staging`. No data touched.
- The Alembic `stamp 0033` and the ESO KEK force-sync were one-time live
  rescues; they are also fixed in code so they won't recur.
- Failed `broker_connections` rows are safe to delete (no SA/STS/Vault path
  is created on a failed provision; verified `kubectl get sa | grep mt-` = none).
