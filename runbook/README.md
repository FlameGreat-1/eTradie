# eTradie — End-to-End Deployment Runbook (Contabo VPS 30, single-node)

**Scope:** the full backend platform (data layer + 4 services + billing + edge + envoy + observability + Linkerd mesh) onto ONE Contabo VPS 30 NVMe (8 vCPU / 24 GB / 200 GB), profile **BUDGET.md TABLE 2B** (everything ON, single-node lean). **The frontend `cotradee/` is OUT OF SCOPE** (already deployed on Vercel).

**Follow every section in order. Do not skip. Do not reorder.** Each step states what it does and how to verify it before you move on. Values here are verified against the repository (chart values, `ci.yml`, `infrastructure/cluster/vault-paths/main.tf`, ArgoCD manifests). Where the older `docs/deployment/contabo-k3s.md` disagrees, THIS runbook is correct (notably image tags and the Linkerd mesh, which that doc omits).

> Capacity (BUDGET.md Table 2B): this box hosts the full stack + **~1 production MT user**, or **~4–5 staging test users**. CPU requests are the limiter. Pick ONE environment per box; staging and production are not meant to co-reside.

---

## Verified version + image facts

| Item | Value | Source |
|---|---|---|
| App service image tag (engine, gateway, execution, management, billing) | `0.1.0` | each chart `values.yaml` + `ci.yml` `RELEASE_TAG` |
| edge-ingress image tag | `0.2.0` | `helm/edge-ingress/values.yaml` |
| mt-node image tag | `0.1.0` | `helm/mt-node/values-image.yaml` |
| Image registry base | `ghcr.io/flamegreat-1/etradie` | `ci.yml` `IMAGE_BASE` |
| K3s | `v1.30.4+k3s1` (MUST be >= 1.29 for native sidecars) | bootstrap README |
| Environment in this runbook | `production` | replace with `staging` everywhere for a staging box |

---

## Phase 0 — Prerequisites

0.1 Workstation tools: `ssh`, `kubectl` (>=1.29), `helm` (>=3.14), `terraform` (>=1.7), `vault` CLI (>=1.15), `git`, `jq`, `openssl`, `base64`, `curl`, `rustup` (for the envoy WASM build), `step` (smallstep, for the mesh CA), `argocd` CLI.

0.2 Accounts/assets ready first: Cloudflare zone `exoper.com` Active; MaxMind GeoLite2 account (`account_id` + `license_key`); engine LLM/data keys (Anthropic + as used OpenAI/Gemini/TwelveData/FRED/CFTC); billing keys (Paddle + Lemon Squeezy) or billing CrashLoops.

0.3 Clone:
```bash
git clone https://github.com/FlameGreat-1/eTradie.git
cd eTradie
```

0.4 Confirm images exist in GHCR (else `ImagePullBackOff`):
```bash
for svc in engine gateway execution management billing mt-node; do
  echo -n "$svc:0.1.0 -> "
  curl -fsS -o /dev/null -w "%{http_code}\n" \
    "https://ghcr.io/v2/flamegreat-1/etradie/$svc/manifests/0.1.0" \
    -H "Authorization: Bearer $(echo -n null | base64)" || echo "check GH Packages UI"
done
echo -n "edge-ingress:0.2.0 -> "
curl -fsS -o /dev/null -w "%{http_code}\n" \
  "https://ghcr.io/v2/flamegreat-1/etradie/edge-ingress/manifests/0.2.0" \
  -H "Authorization: Bearer $(echo -n null | base64)" || true
```
If missing, push to `main` to trigger CI, or build+push manually (see `docs/deployment/contabo-k3s.md` section 6.5).

---

## Phase 1 — VPS host hardening

SSH in as `root`. Run the full procedure in `docs/runbooks/vps-host-hardening.md`. Minimum:

1.1 Create non-root sudo user `etradie`, copy your SSH key, reconnect as it.
1.2 Disable root SSH + password auth in `/etc/ssh/sshd_config` (`PermitRootLogin no`, `PasswordAuthentication no`), then `sudo systemctl reload sshd`.
1.3 `sudo apt update && sudo apt -y upgrade`; install `ca-certificates curl gnupg git make jq unzip ufw chrony`.
1.4 Time sync: `sudo systemctl enable --now chrony && chronyc tracking` (stratum <= 3).
1.5 Kernel/ulimit tuning in `/etc/sysctl.d/99-etradie.conf` (`vm.max_map_count=262144`, `fs.inotify.max_user_watches=524288`, `net.core.somaxconn=65535`, `vm.swappiness=10`) and `/etc/security/limits.d/99-etradie.conf` (`nofile`/`nproc` 65535); `sudo sysctl --system`.
1.6 Firewall (Cloudflare Tunnel is outbound-only — close all inbound except SSH):
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw --force enable
```
**Verify:** `sudo ufw status verbose` shows only 22/tcp inbound.

---

## Phase 2 — Install K3s (>= 1.29 REQUIRED for Linkerd native sidecars)

2.1 On the VPS:
```bash
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="v1.30.4+k3s1" \
  K3S_KUBECONFIG_MODE="644" \
  INSTALL_K3S_EXEC="server --disable=traefik --disable=servicelb --write-kubeconfig-mode=644 --kube-apiserver-arg=enable-admission-plugins=NodeRestriction,PodSecurity --kubelet-arg=eviction-hard=memory.available<200Mi" \
  sh -
```
Why: own ingress (no traefik), no LoadBalancer (no servicelb), PSS `restricted` the charts rely on.

2.2 Verify: `sudo k3s kubectl get nodes` Ready; `kube-system` pods Running.

2.3 Export kubeconfig to workstation as `~/.kube/etradie-contabo.yaml`, replace `127.0.0.1` with the VPS public IP:
```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes   # Ready
```
Everything below runs from your workstation.

---

## Phase 3 — Vault + Vault Agent Injector

Injector is MANDATORY (per-tenant mt-node credentials are rendered to tmpfs, never a plaintext Secret).

3.1 Install:
```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
kubectl create namespace vault
helm install vault hashicorp/vault \
  --namespace vault --version 0.28.1 \
  --set 'server.standalone.enabled=true' \
  --set 'server.dataStorage.enabled=true' \
  --set 'server.dataStorage.size=10Gi' \
  --set 'server.dataStorage.storageClass=local-path' \
  --set 'injector.enabled=true' \
  --set 'ui.enabled=true'
```

3.2 Init + unseal (STORE `vault-init.txt` OFFLINE — losing it = total data loss):
```bash
kubectl -n vault wait --for=condition=Ready pod/vault-0 --timeout=120s
kubectl -n vault exec -ti vault-0 -- vault operator init -key-shares=5 -key-threshold=3 > vault-init.txt
for i in 1 2 3; do
  KEY=$(grep "Unseal Key $i:" vault-init.txt | awk '{print $4}')
  kubectl -n vault exec -ti vault-0 -- vault operator unseal "$KEY"
done
kubectl -n vault exec -ti vault-0 -- vault status   # Sealed: false
```

3.3 Verify injector:
```bash
kubectl -n vault get pods -l app.kubernetes.io/name=vault-agent-injector   # Running 1/1
```

3.4 Auth + KV mount + ESO policy:
```bash
ROOT_TOKEN=$(grep 'Initial Root Token:' vault-init.txt | awk '{print $4}')
kubectl -n vault port-forward svc/vault 8200:8200 &
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=$ROOT_TOKEN
vault status
vault secrets enable -version=2 -path=secret kv
vault auth enable kubernetes
vault write auth/kubernetes/config kubernetes_host=https://kubernetes.default.svc.cluster.local
vault policy write etradie-eso - <<'EOF'
path "secret/data/etradie/*"     { capabilities = ["read","list"] }
path "secret/metadata/etradie/*" { capabilities = ["read","list"] }
EOF
vault write auth/kubernetes/role/etradie-eso \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=etradie-eso ttl=1h
```

3.5 Token-review SA for the mt-node tenant infra (Phase 11):
```bash
kubectl create serviceaccount -n vault vault-auth 2>/dev/null || true
kubectl create clusterrolebinding vault-auth-delegator \
  --clusterrole=system:auth-delegator --serviceaccount=vault:vault-auth 2>/dev/null || true
```

---

## Phase 4 — External Secrets Operator + ClusterSecretStore

4.1 Install:
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
kubectl create namespace external-secrets
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --version 0.10.4 --set installCRDs=true
kubectl -n external-secrets wait --for=condition=Available deployment/external-secrets --timeout=120s
```

4.2 ClusterSecretStore `vault-backend` (referenced by every chart):
```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "http://vault.vault.svc.cluster.local:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "etradie-eso"
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
EOF
```
**Verify:** `kubectl get clustersecretstore vault-backend -o jsonpath='{.status.conditions[0].reason}'` -> `Valid`.

---

## Phase 5 — Stakater Reloader (REQUIRED)

The mt-node StatefulSet carries `secret.reloader.stakater.com/reload`; without Reloader, ZMQ-token rotation will not roll the pods.
```bash
helm repo add stakater https://stakater.github.io/stakater-charts
helm repo update
helm install reloader stakater/reloader -n reloader --create-namespace
kubectl -n reloader rollout status deployment/reloader-reloader --timeout=120s
```

---

## Phase 6 — Cloudflare Tunnel

6.1 Zero Trust UI -> Networks -> Tunnels -> Create a tunnel -> Cloudflared -> name `etradie-production`. Copy the token (`eyJ...`) — unrecoverable later.
6.2 Public Hostnames tab -> add `api.exoper.com`, Type HTTPS, URL `edge-ingress.edge-ingress-system.svc.cluster.local:443`, leave No TLS Verify UNCHECKED. Repeat for other hosts (e.g. `app`). Cloudflare auto-creates the CNAMEs.
6.3 Note the Tunnel UUID + token.

---

## Phase 7 — Generate the Linkerd mesh CA (mesh is ON)

No cert-manager; CA lives in Vault.
```bash
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca --no-password --insecure
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca --not-after 8760h --no-password --insecure \
  --ca ca.crt --ca-key ca.key
```
Keep `ca.crt` (also passed at control-plane sync, Phase 10.4).

---

## Phase 8 — Bootstrap Vault paths + populate every secret

8.1 Create empty KV paths:
```bash
cd infrastructure/cluster/vault-paths
terraform init
terraform apply -var environment=production -var vault_address=http://127.0.0.1:8200
cd ../../..
```

8.2 Generate shared secrets ONCE (consumers must share identical values):
```bash
DB_PASS=$(openssl rand -hex 32)
REDIS_PASS=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 64)
BROKER_KEY=$(openssl rand -hex 32)
CHROMA_TOKEN=$(openssl rand -hex 32)
ADMIN_PASS=$(openssl rand -hex 24)
ENGINE_SHARED=$(openssl rand -hex 32)
BILLING_SHARED=$(openssl rand -hex 32)
MT_DEFAULT_ZMQ=$(openssl rand -hex 32)
DB_URL_GO="postgres://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=disable"
DB_URL_PY="postgresql+asyncpg://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie"
REDIS0="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/0"
REDIS1="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/1"
```

8.3 Data layer (write FIRST — StatefulSets block without these). Key names EXACT per `vault-paths/main.tf`:
```bash
vault kv put secret/etradie/data-layer/postgres/production \
  postgres_user=etradie postgres_db=etradie postgres_password="${DB_PASS}"
vault kv put secret/etradie/data-layer/redis/production redis_password="${REDIS_PASS}"
# chromadb: SINGLE key 'auth_token' (server + engine both read it)
vault kv put secret/etradie/data-layer/chromadb/production auth_token="${CHROMA_TOKEN}"
```

8.4 Linkerd identity (before control-plane sync):
```bash
vault kv put secret/etradie/platform/linkerd/production \
  trust_anchor_pem=@ca.crt issuer_tls_crt=@issuer.crt issuer_tls_key=@issuer.key
```

8.5 Edge-ingress (AOP CA key MUST be `aop_ca`; MaxMind keys `license_key`+`account_id`):
```bash
vault kv put secret/etradie/services/edge-ingress/production/cloudflare/tunnel \
  tunnel_token='eyJhIjoi...PASTE_FROM_PHASE_6...'
vault kv put secret/etradie/services/edge-ingress/production/cloudflare/aop_ca \
  aop_ca="$(curl -fsS https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem)"
vault kv put secret/etradie/services/edge-ingress/production/maxmind \
  license_key='YOUR_MAXMIND_LICENSE_KEY' account_id='YOUR_MAXMIND_ACCOUNT_ID'
# TLS path empty (Cloudflare terminates public TLS; only needed for cloudProvider=generic)
vault kv put secret/etradie/services/edge-ingress/production/tls \
  api_cert='' api_key='' wildcard_cert='' wildcard_key=''
```

8.6 Gateway (owns JWT + admin password; holds BOTH shared secrets):
```bash
vault kv put secret/etradie/services/gateway/production \
  auth_database_url="${DB_URL_GO}" \
  postgres_user=etradie postgres_password="${DB_PASS}" \
  postgres_host=postgres.etradie-system.svc.cluster.local \
  postgres_port=5432 postgres_db=etradie postgres_sslmode=disable \
  gateway_redis_url="${REDIS0}" \
  auth_jwt_secret="${JWT_SECRET}" auth_admin_password="${ADMIN_PASS}" \
  engine_internal_shared_secret="${ENGINE_SHARED}" \
  billing_internal_shared_secret="${BILLING_SHARED}"
```

8.7 Engine (sole holder of `broker_encryption_key`; chroma token NOT here). Replace provider keys:
```bash
vault kv put secret/etradie/services/engine/production \
  database_url="${DB_URL_PY}" \
  postgres_user=etradie postgres_password="${DB_PASS}" \
  redis_url="${REDIS0}" redis_password="${REDIS_PASS}" \
  broker_encryption_key="${BROKER_KEY}" \
  auth_jwt_secret="${JWT_SECRET}" engine_internal_shared_secret="${ENGINE_SHARED}" \
  cftc_app_token='REPLACE' fred_api_key='REPLACE' twelvedata_api_key='REPLACE' \
  processor_anthropic_api_key='REPLACE' processor_openai_api_key='REPLACE' \
  processor_gemini_api_key='REPLACE' mt5_metaapi_token='REPLACE_OR_OMIT'
```

8.8 Execution + Management (`auth_jwt_secret` AND `engine_internal_shared_secret` MUST equal gateway/engine, else fail-fast when BROKER_MODE=mt5):
```bash
vault kv put secret/etradie/services/execution/production \
  execution_database_url="${DB_URL_GO}" execution_redis_url="${REDIS1}" \
  auth_jwt_secret="${JWT_SECRET}" engine_internal_shared_secret="${ENGINE_SHARED}"
vault kv put secret/etradie/services/management/production \
  management_database_url="${DB_URL_GO}" management_redis_url="${REDIS1}" \
  auth_jwt_secret="${JWT_SECRET}" engine_internal_shared_secret="${ENGINE_SHARED}"
```

8.9 Billing (`internal_shared_secret` MUST equal gateway's `billing_internal_shared_secret`; `billing_redis_url` same Redis the gateway subscribes to). Replace provider values:
```bash
vault kv put secret/etradie/services/billing/production \
  billing_database_url="${DB_URL_GO}" internal_shared_secret="${BILLING_SHARED}" \
  billing_redis_url="${REDIS0}" \
  paddle_webhook_secret='REPLACE' paddle_api_key='REPLACE' \
  paddle_price_pro_byok='REPLACE' paddle_price_pro_managed='REPLACE' \
  lemonsqueezy_webhook_secret='REPLACE' lemonsqueezy_api_key='REPLACE' \
  lemonsqueezy_store_id='REPLACE' \
  lemonsqueezy_variant_pro_byok='REPLACE' lemonsqueezy_variant_pro_managed='REPLACE'
```

8.10 mt-node platform fallback ZMQ token:
```bash
vault kv put secret/etradie/services/mt-node/production default_zmq_auth_token="${MT_DEFAULT_ZMQ}"
```

8.11 Save generated values out-of-band (mode 0600, never commit):
```bash
umask 077
cat > ~/etradie-prod-creds.txt <<EOF
DB_PASS=${DB_PASS}
REDIS_PASS=${REDIS_PASS}
JWT_SECRET=${JWT_SECRET}
ADMIN_PASS=${ADMIN_PASS}
BROKER_KEY=${BROKER_KEY}
CHROMA_TOKEN=${CHROMA_TOKEN}
ENGINE_SHARED=${ENGINE_SHARED}
BILLING_SHARED=${BILLING_SHARED}
EOF
```

---

## Phase 9 — Build + inject the envoy WASM filter

`helm/envoy/values.yaml` ships `wasm.base64: ""`; the chart fails to render until real bytes are supplied, and ArgoCD cannot `--set-file` at sync time, so the bytes must live in a values file the app reads.
```bash
cd src/envoy
rustup target add wasm32-wasi
cargo build --release --target wasm32-wasi
WASM=target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm
cat > ../../helm/envoy/values-production-wasm.yaml <<EOF
wasm:
  base64: "$(base64 -w0 "$WASM")"
  sha256: "$(sha256sum "$WASM" | awk '{print $1}')"
  builtAt: "$(date -u +%FT%TZ)"
EOF
cd ../..
```
Reference the overlay from the envoy production app and push to `main`:
```bash
# Edit deployments/argocd/children/envoy-production.yaml -> source.helm.valueFiles:
#   - values.yaml
#   - values-production.yaml
#   - values-production-wasm.yaml
git add helm/envoy/values-production-wasm.yaml deployments/argocd/children/envoy-production.yaml
git commit -m "deploy: inject production envoy WASM bytes"
git push origin main
```
> The WASM overlay holds compiled filter bytes, no secrets. Prefer a private release branch + `targetRevision` if you do not want it on `main`.

---

## Phase 10 — ArgoCD + both AppProjects + root app

10.1 Install:
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml
kubectl -n argocd wait --for=condition=Available deployment/argocd-server --timeout=180s
```
10.2 Admin password + UI (port-forward only):
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
kubectl -n argocd port-forward svc/argocd-server 8080:443 &   # https://localhost:8080
```
10.3 Apply BOTH AppProjects + root app-of-apps:
```bash
kubectl apply -f deployments/argocd/appproject.yaml
kubectl apply -f deployments/argocd/linkerd-appproject.yaml
kubectl apply -f deployments/argocd/root-app.yaml
```
10.4 Pass the Linkerd trust anchor to the control-plane app (values file leaves it empty by design):
```bash
argocd app set linkerd-control-plane-production --helm-set-file identityTrustAnchorsPEM=ca.crt
```

---

## Phase 11 — Provision mt-node tenant Vault infrastructure

Run AFTER ArgoCD exists. Creates per-tenant Vault auth roles/policies:
```bash
cd infrastructure/cluster/vault-paths
terraform apply \
  -var environment=production -var vault_address=http://127.0.0.1:8200 \
  -var k8s_host=https://kubernetes.default.svc \
  -var k8s_ca_cert="$(kubectl get cm -n kube-system kube-root-ca.crt -o jsonpath='{.data.ca\.crt}')" \
  -var k8s_reviewer_jwt="$(kubectl create token -n vault vault-auth)"
cd ../../..
```

---

## Phase 12 — Sync the platform in dependency order

Production children are manual-sync (`automated.{prune:false,selfHeal:false}`). Sync in EXACT order; wait for Synced+Healthy before the next.

| Order | Application | Wave |
|---|---|---|
| 1 | `linkerd-identity-production` | -6 |
| 2 | `linkerd-crds-production` | -5 |
| 3 | `linkerd-control-plane-production` | -4 |
| 4 | `observability-logs-production` | -2 |
| 5 | `data-layer-production` | -2 |
| 6 | `engine-production` + `mt-node-production` | -1 |
| 7 | `billing-production` | 1 |
| 8 | `gateway-production`, `execution-production`, `management-production` | 0 |
| 9 | `envoy-production` | 5 |
| 10 | `edge-ingress-production` | 10 |

```bash
for app in linkerd-identity-production linkerd-crds-production \
           linkerd-control-plane-production observability-logs-production \
           data-layer-production engine-production mt-node-production \
           billing-production gateway-production execution-production \
           management-production envoy-production edge-ingress-production; do
  echo "=== syncing $app ==="
  argocd app sync "$app" --timeout 600
  argocd app wait "$app" --health --timeout 600
done
```
> The `*-staging` children also exist in `children/`. On a production box, sync ONLY the `*-production` + three `linkerd-*` apps. Do NOT sync `*-staging` on the same cluster (identical namespace/release names).

---

## Phase 13 — Database migrations

The engine deployment's `migrate` init container runs Alembic on every rollout, so a healthy `engine-production` already migrated. Verify:
```bash
kubectl -n etradie-system exec -ti postgres-0 -- psql -U etradie -d etradie -c '\dt'
# Expected: many tables (auth_users, sessions, trades, signals, broker_connections, billing_*, ...)
```
If empty, inspect the init log and fix the cause (usually a wrong `database_url`):
```bash
kubectl -n etradie-system logs deploy/etradie-engine -c migrate
```

---

## Phase 14 — End-to-end verification

14.1 All pods Ready:
```bash
kubectl get pods -A | grep -vE '(Running|Completed)'   # expect empty
```
14.2 Mesh healthy + proxies injected:
```bash
kubectl -n linkerd get pods
kubectl -n etradie-system get pods -o json | jq -r '.items[].spec.containers[].name' | grep -c linkerd-proxy
```
14.3 ESO synced every Secret:
```bash
kubectl get externalsecret -A
```
14.4 Cloudflare Tunnel HEALTHY (Zero Trust UI) and:
```bash
kubectl -n edge-ingress-system logs -l app.kubernetes.io/name=cloudflared --tail=50 | grep -i 'Registered tunnel connection'
```
14.5 Public reachability + auth round-trip:
```bash
ADMIN_PASS=$(vault kv get -field=auth_admin_password secret/etradie/services/gateway/production)
curl -fsS -o /dev/null -w 'edge HTTP %{http_code}\n' https://api.exoper.com/healthz
curl -fsS https://api.exoper.com/api/v1/auth/health
TOKEN=$(curl -fsS -X POST https://api.exoper.com/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"admin\",\"password\":\"${ADMIN_PASS}\"}" | jq -r .access_token)
curl -fsS https://api.exoper.com/api/v1/state/account -H "Authorization: Bearer $TOKEN"
# Expect 200 account JSON (gateway -> execution -> mock broker chain)
```
14.6 Frontend (`cotradee/` on Vercel) reaches `https://api.exoper.com`. The gateway CORS origin is `https://app.exoper.com` (`helm/gateway/values-production.yaml`). If your SPA host differs, update `config.gateway.allowedOrigins` and re-sync gateway.

---

## Phase 15 — Post-deploy operational notes

- **Disabled toggles (BUDGET.md Table 2B re-enable index):** HPAs, PDBs, Linkerd `highAvailability`, Linkerd viz, per-service `linkerdPolicy`, snapshotter are intentionally OFF. Each has its re-enable pointer in BUDGET.md. Do not re-enable ad hoc on this box.
- **Mesh verification before per-service authz:** install viz on demand (`git mv deployments/argocd/optional/linkerd-viz-production.yaml deployments/argocd/children/` then sync), run `linkerd viz edges` until every internal edge is SECURED, then set `linkerdPolicy.enabled: true` per service and re-sync. See `docs/runbooks/linkerd-mesh-rollout.md`.
- **Backups:** production postgres backup CronJob + weekly restore drill are ON. Populate the offsite B2 path `etradie/data-layer/postgres-backup/production` (rclone_remote_name, rclone_config, remote_bucket, remote_path_prefix) BEFORE the first 02:00 UTC run. See `docs/runbooks/database-backup-restore.md`.
- **Vault Raft snapshots:** back up Vault out-of-band — it is the source of truth for every secret and the mesh CA.
- **Monitoring (optional):** install kube-prometheus-stack into `monitoring` (AppProject-allowlisted); ServiceMonitors auto-discover via the `prometheus: kube-prometheus` label.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Pod `Pending` forever | ResourceQuota / node ledger full | `kubectl describe pod`; at capacity (Table 2B ~1 prod user) |
| `Init:` > 5 min, init=`wait-for-deps` | dependency not Ready | sync the dependency app first (data-layer -> engine -> gateway) |
| edge-ingress `Init:`, init=`aop-ca-preflight` | AOP CA bytes missing/malformed | re-run Phase 8.5 `aop_ca` |
| `vaultPath is required` render error | a Vault path empty | re-run the matching Phase 8 put |
| ESO `permission denied` | wrong auth role | re-run Phase 3.4 `etradie-eso` role |
| `cloudflared` CrashLoop | wrong tunnel token | re-copy from CF UI, re-write Vault, restart |
| Cloudflare `HTTP 1033` | tunnel not connected | verify outbound :443 from cluster; check token |
| meshed pods never Ready | K3s < 1.29 (no native sidecar) | reinstall K3s >= 1.29 |
| envoy app won't render | WASM bytes missing | complete Phase 9 |

---

## Reference

- Resource profile + capacity: `BUDGET.md` (Table 2B)
- Bootstrap-only steps: `infrastructure/cluster/bootstrap/README.md`
- Vault path schema: `infrastructure/cluster/vault-paths/main.tf`
- Mesh rollout: `docs/runbooks/linkerd-mesh-rollout.md`
- Host hardening: `docs/runbooks/vps-host-hardening.md`
- Backup/restore: `docs/runbooks/database-backup-restore.md`
- Older single-doc guide (image tags there are stale; THIS runbook is authoritative): `docs/deployment/contabo-k3s.md`
