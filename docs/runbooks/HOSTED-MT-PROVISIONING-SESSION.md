# Hosted-MT (Wine) Provisioning — In-Flight Session Runbook

**Status:** IN PROGRESS. Read this top-to-bottom before running anything.
This is the authoritative resume point for the hosted-MT provisioning
effort on the **staging** Contabo box (`vmi3362776`).

**Last updated:** 2026-06-19, late-session (through defect #8).

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
