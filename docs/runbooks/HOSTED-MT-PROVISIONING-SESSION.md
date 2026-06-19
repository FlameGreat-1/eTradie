# Hosted-MT (Wine) Provisioning — In-Flight Session Runbook

**Status:** IN PROGRESS. Read this top-to-bottom before running anything.
This is the authoritative resume point for the hosted-MT provisioning
effort on the **staging** Contabo box (`vmi3362776`).

**Last updated:** 2026-06-19, mid-session.

---

## TL;DR — where we are right now

We are provisioning the **first hosted-MT (Wine) tenant** via the dashboard
(`connection_type=hosted`). The engine's `HostedProvisioner` runs the
provisioning at runtime (not ArgoCD). Each dashboard submit creates a
`broker_connections` row; the engine then writes per-tenant creds to Vault
and creates a per-tenant StatefulSet + ServiceAccount + Services.

Provisioning was failing in a **cascade of distinct defects**, each one
revealed after fixing the previous. We have fixed four and are verifying
the fifth. **The platform itself is healthy throughout — only hosted-MT
provisioning is affected.** No outage.

### Fixes committed to `main` (GitLab mirror -> GitHub `origin` -> ArgoCD/CI)

| # | Commit subject | Layer | Needs image rebuild? | Status |
|---|---|---|---|---|
| 1 | `fix(engine): allow HostedProvisioner egress to Vault + use http scheme` | Helm values | No | DONE, synced, verified (TCP 8200 OPEN, HTTP 200) |
| 2+3 | `fix(engine/migrations): make migrate idempotent ...` | Engine image | **Yes** | DONE on main; image build via CI; DB already stamped 0033 manually so not blocking |
| 4 | `fix(engine): project Vault-audience SA token ...` | Helm pod-spec | No | DONE, synced, verified (`aud=['vault']`) |
| 5 | `fix(engine): allow egress to the Kubernetes API server ...` | Helm values | No | DONE on main; **needs sync + verify (current step)** |

### The failure cascade (each was a real, separate root cause)

1. **Empty `BROKER_ENCRYPTION_KEY`** — engine Secret rendered the KEK empty
   (stale ESO render). Fixed live by `force-sync` of the ExternalSecret +
   engine restart. KEK is `f7f59b...` (64 hex) in Vault at
   `etradie/services/engine/staging:broker_encryption_key`.
2. **Alembic crash-loop** — `alembic_version` was empty but tables existed,
   so `alembic upgrade head` hit `DuplicateTableError` on
   `central_bank_events`. Fixed live by `alembic stamp head` (DB now at
   `0033`); fixed permanently in code (commits 2+3, idempotent migrate).
3. **Vault unreachable** — engine NetworkPolicy egress had no rule to Vault
   `:8200`. Fixed (commit 1).
4. **`https://` vs `http://`** — in-cluster Vault serves plain HTTP; engine
   used `https`. Fixed (commit 1).
5. **Vault 403** — engine's default SA token has audience
   `https://kubernetes.default.svc`, but the `mt-node-provisioner` Vault
   role requires `audience="vault"`. Fixed by projecting an `aud=vault`
   token (commit 4).
6. **K8s API unreachable (`10.43.0.1:443`)** — after the Vault write
   succeeds, the provisioner creates the StatefulSet/SA/Services via the
   K8s API, which the engine egress blocked (service-CIDR excluded). Fixed
   (commit 5). **<-- verifying this now.**

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

## RESUME HERE — current step: verify commit 5 (K8s API egress) and re-provision

### Step A — pull mirror + sync engine

```bash
cd ~/eTradie
git stash push -u -m wip 2>/dev/null || true
git pull --rebase gitlab main
git stash pop 2>/dev/null || true
git log --oneline -6   # confirm the 5 fix commits are present

export KUBECONFIG=~/.kube/etradie-contabo.yaml
argocd app sync engine-staging --grpc-web
argocd app wait engine-staging --health --timeout 300
```

> NOTE: there are leftover git stashes (`git stash list`) from earlier in
> the session. Review/clean them when convenient; they are not needed for
> provisioning.

### Step B — verify the API-server egress fix is live

```bash
kubectl -n etradie-system get networkpolicy etradie-engine-network-policy -o yaml | grep -B2 -A4 '10.43.0.1'
GW=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o jsonpath='{.items[0].metadata.name}')
kubectl -n etradie-system exec "$GW" -c engine -- python3 -c "
import socket
s=socket.socket(); s.settimeout(5)
try: s.connect(('10.43.0.1',443)); print('API 443 OPEN')
except Exception as e: print('BLOCKED:', e)
finally: s.close()
"
```
Expect: rule present + `API 443 OPEN`.

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
