# Deploying eTradie on Contabo VPS (K3s)

End-to-end production deployment of the full eTradie platform onto a
Contabo VPS using K3s as the Kubernetes distribution. Every step is
explicit; nothing is skipped or hand-waved. After completing this
runbook you will have a publicly reachable, Cloudflare-Tunnel-fronted
eTradie deployment with no AWS, OCI, or GCP dependency anywhere.

The same chart code deploys identically on OCI OKE (see
`oci-oke.md`), kubeadm bare-metal, or any conformant Kubernetes
cluster. The differences live exclusively in this runbook (which
provisions the cluster) and the Vault values the operator writes.

---

## Architecture recap

```text
Internet
   |
   v
Cloudflare edge        (TLS termination, DDoS, WAF, anycast)
   |
   v  outbound tunnel (initiated by cloudflared from inside cluster)
+--------------------------------------------------------------+
| Contabo VPS  (Ubuntu 22.04, K3s)                              |
|                                                               |
|  edge-ingress-system ns:                                      |
|    cloudflared  (Deployment, 2 replicas)                      |
|    edge-ingress (Rust, Deployment + HPA)                      |
|                                                               |
|  envoy-system ns:                                             |
|    etradie-envoy (Deployment + HPA, WASM filter)              |
|                                                               |
|  etradie-system ns:                                           |
|    gateway     (Go,     Deployment + HPA, headless Service)   |
|    engine      (Python, Deployment + HPA)                     |
|    execution   (Go,     Deployment + HPA)                     |
|    management  (Go,     Deployment + HPA)                     |
|    postgres    (StatefulSet)                                  |
|    redis       (StatefulSet)                                  |
|    chromadb    (StatefulSet)                                  |
|    postgres-backup (CronJob)                                  |
|                                                               |
|  vault, external-secrets, argocd ns:                          |
|    Platform infra (operator-installed Helm charts)            |
+--------------------------------------------------------------+
```

There is **no public LoadBalancer Service** and **no port exposed**
from the VPS to the internet. Cloudflare Tunnel handles all inbound
traffic via an outbound persistent connection.

---

## 0. Prerequisites

* A Contabo VPS with **at least** the following spec for production:

  | Resource | Minimum | Recommended |
  |---|---|---|
  | vCPU | 6 | 8 |
  | RAM | 16 GB | 32 GB |
  | Storage | 200 GB NVMe | 400 GB NVMe |
  | OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
  | Network | 1 Gbit/s | 1 Gbit/s |

  Smaller specs work for staging but production HPA + ChromaDB
  embedding model + Postgres + Redis + four Go services will exhaust
  4 vCPU / 8 GB.

* A registered domain on Cloudflare with the zone in **Active**
  state (Free plan is sufficient).

* The following local tools on your workstation:
  * `ssh`, `kubectl` (>= 1.28), `helm` (>= 3.14), `terraform` (>= 1.6),
    `vault` CLI (>= 1.15), `cloudflared` (latest).

* GitHub access to clone the repo (the platform charts live there;
  ArgoCD reads from it).

---

## 1. Initial VPS hardening

SSH in as `root` (Contabo's default).

### 1.1 Create a non-root sudo user

```bash
adduser etradie
usermod -aG sudo etradie
mkdir -p /home/etradie/.ssh
cp ~/.ssh/authorized_keys /home/etradie/.ssh/authorized_keys
chown -R etradie:etradie /home/etradie/.ssh
chmod 700 /home/etradie/.ssh
chmod 600 /home/etradie/.ssh/authorized_keys
```

Log out and reconnect as `etradie` for the rest of this runbook.

### 1.2 Disable root SSH + password auth

```bash
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl reload sshd
```

### 1.3 Install baseline packages

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install ca-certificates curl gnupg lsb-release \
    apt-transport-https git make jq unzip ufw chrony
```

### 1.4 Time sync (Postgres + Redis correctness depend on this)

```bash
sudo systemctl enable --now chrony
chronyc tracking   # confirm Stratum is <= 3
```

### 1.5 Kernel + ulimit tuning

K3s + Postgres + Redis under load will breach the default limits.

```bash
sudo tee /etc/sysctl.d/99-etradie.conf >/dev/null <<'EOF'
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65000
net.ipv4.tcp_tw_reuse = 1
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 1024
vm.max_map_count = 262144
vm.swappiness = 10
EOF
sudo sysctl --system

sudo tee /etc/security/limits.d/99-etradie.conf >/dev/null <<'EOF'
*  soft  nofile  65535
*  hard  nofile  65535
*  soft  nproc   65535
*  hard  nproc   65535
EOF
```

### 1.6 Firewall

Cloudflare Tunnel is outbound-only, so we close everything except SSH:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw --force enable
sudo ufw status verbose
```

---

## 2. Install K3s

K3s is the simplest production-grade Kubernetes for a single-node or
small multi-node cluster. Use the official installer pinned to a
specific minor version.

### 2.1 Install (single-node)

```bash
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="v1.30.4+k3s1" \
  K3S_KUBECONFIG_MODE="644" \
  INSTALL_K3S_EXEC="server \
    --disable=traefik \
    --disable=servicelb \
    --write-kubeconfig-mode=644 \
    --kube-apiserver-arg=enable-admission-plugins=NodeRestriction,PodSecurity \
    --kubelet-arg=eviction-hard=memory.available<200Mi \
    --kubelet-arg=eviction-soft=memory.available<400Mi \
    --kubelet-arg=eviction-soft-grace-period=memory.available=2m" \
  sh -
```

Why these flags:

| Flag | Reason |
|---|---|
| `--disable=traefik` | We run our own ingress (cloudflared + edge-ingress). Traefik would compete on ports. |
| `--disable=servicelb` | We do not use LoadBalancer Services. Tunnel mode uses ClusterIP only. |
| `--write-kubeconfig-mode=644` | Lets the `etradie` user read kubeconfig without sudo. |
| `enable-admission-plugins=NodeRestriction,PodSecurity` | PSS `restricted` enforcement that the charts rely on. |
| `eviction-*` | Prevent OOM cascade by evicting pods cleanly under memory pressure. |

### 2.2 Verify K3s is up

```bash
sudo systemctl status k3s
sudo k3s kubectl get nodes
sudo k3s kubectl get pods -A
```

Expected: node `Ready`; pods in `kube-system` (`coredns`, `metrics-server`,
`local-path-provisioner`) all `Running`.

### 2.3 Export kubeconfig for your workstation

On the VPS:

```bash
sudo cat /etc/rancher/k3s/k3s.yaml
```

On your **workstation**, save it as `~/.kube/etradie-contabo.yaml`,
replacing the `127.0.0.1` line with `<vps-public-ip>`:

```bash
sed -i.bak "s/127.0.0.1/<vps-public-ip>/" ~/.kube/etradie-contabo.yaml
chmod 600 ~/.kube/etradie-contabo.yaml
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes
```

From this point everything in this guide runs from your workstation
against the VPS via the K3s API on `:6443` (which is open by
default inside Contabo's network; tighten with `ufw allow from
<your-ip> to any port 6443` if you want stricter ACLs).

### 2.4 (HA only) Add additional nodes

For a 3-node HA control plane on three separate Contabo VPS:

On the **first** node only, capture the cluster join token:

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```

On each **additional** server-mode node:

```bash
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="v1.30.4+k3s1" \
  K3S_TOKEN="<token-from-above>" \
  K3S_URL="https://<first-node-ip>:6443" \
  INSTALL_K3S_EXEC="server --disable=traefik --disable=servicelb" \
  sh -
```

Verify:

```bash
kubectl get nodes -o wide
```

All nodes should be `Ready` with role `control-plane,master`.

---

## 3. Install Vault

Vault is the source of truth for every platform secret (DB passwords,
JWT signing key, encryption keys, broker creds, LLM API keys,
Cloudflare Tunnel token, AOP CA bytes).

### 3.1 Install

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

kubectl create namespace vault

helm install vault hashicorp/vault \
  --namespace vault \
  --version 0.28.1 \
  --set 'server.standalone.enabled=true' \
  --set 'server.dataStorage.enabled=true' \
  --set 'server.dataStorage.size=10Gi' \
  --set 'server.dataStorage.storageClass=local-path' \
  --set 'ui.enabled=true'
```

> For multi-node K3s: switch `server.standalone.enabled=true` to
> `server.ha.enabled=true` + `server.ha.raft.enabled=true` and bump
> `server.ha.replicas=3`. The rest of this guide is identical.

### 3.2 Initialise + unseal

```bash
kubectl -n vault wait --for=condition=Ready pod/vault-0 --timeout=120s
kubectl -n vault exec -ti vault-0 -- vault operator init \
  -key-shares=5 -key-threshold=3 > vault-init.txt
```

**CRITICAL:** `vault-init.txt` contains 5 unseal keys + the root
token. Store offline (password manager, hardware token, encrypted
file on a separate machine). Losing it = total data loss.

Unseal:

```bash
for i in 1 2 3; do
  KEY=$(grep "Unseal Key $i:" vault-init.txt | awk '{print $4}')
  kubectl -n vault exec -ti vault-0 -- vault operator unseal "$KEY"
done
```

Verify:

```bash
kubectl -n vault exec -ti vault-0 -- vault status
# Sealed: false
```

### 3.3 Configure auth + KV mount + ESO policy

From your workstation:

```bash
ROOT_TOKEN=$(grep 'Initial Root Token:' vault-init.txt | awk '{print $4}')
kubectl -n vault port-forward svc/vault 8200:8200 &
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=$ROOT_TOKEN

vault status
vault secrets enable -version=2 -path=secret kv
vault auth enable kubernetes

vault write auth/kubernetes/config \
  kubernetes_host=https://kubernetes.default.svc.cluster.local

vault policy write etradie-eso - <<'EOF'
path "secret/data/etradie/*" {
  capabilities = ["read", "list"]
}
path "secret/metadata/etradie/*" {
  capabilities = ["read", "list"]
}
EOF

vault write auth/kubernetes/role/etradie-eso \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=etradie-eso \
  ttl=1h
```

---

## 4. Install External Secrets Operator (ESO)

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

kubectl create namespace external-secrets

helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --version 0.10.4 \
  --set installCRDs=true \
  --set webhook.port=9443

kubectl -n external-secrets wait --for=condition=Available \
  deployment/external-secrets --timeout=120s
```

Create the `vault-backend` ClusterSecretStore that every ExternalSecret
in every chart references:

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

---

## 5. Cloudflare Tunnel setup

### 5.1 Create the Tunnel (Cloudflare Zero Trust UI)

1. Log into https://one.dash.cloudflare.com/ (Zero Trust)
2. **Networks -> Tunnels -> Create a tunnel** -> Cloudflared
3. Name: `etradie-production` (or `etradie-staging`)
4. **Save tunnel** -> copy the **token** displayed under "Install
   and run a connector". This is the literal token string starting
   with `eyJ...`. Save it; you cannot recover it later (you can
   only rotate to a new one).
5. **Public Hostnames** tab: add one entry per public DNS name:
   * Subdomain: `api`, Domain: `etradie.com`
   * Type: **HTTPS**
   * URL: `edge-ingress.edge-ingress-system.svc.cluster.local:443`
   * Additional application settings -> TLS: leave **No TLS Verify**
     UNCHECKED (the AOP CA establishes trust correctly).
6. Repeat for any other public hostname (e.g. `app.etradie.com`).

Cloudflare auto-creates the CNAME records for you when you add Public
Hostnames in the Tunnel UI; you do not need
`infrastructure/cloudflare/` for this. (The Terraform module is
optional for declarative DNS management.)

### 5.2 Note the tunnel UUID + token

From the Tunnel detail page:

* Tunnel UUID: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
* Tunnel token: `eyJhIjoi...`  (long base64-looking string)

---

## 6. Bootstrap Vault paths + populate secrets

### 6.1 Apply the cloud-agnostic Vault path module

```bash
git clone https://github.com/FlameGreat-1/eTradie.git
cd eTradie/infrastructure/cluster/vault-paths

terraform init
terraform apply \
  -var environment=production \
  -var vault_address=http://127.0.0.1:8200
```

Expected output: 8 `vault_kv_secret_v2` paths created. Each path is
seeded with `bootstrap=placeholder`; you overwrite them next.

### 6.2 Populate the secrets

```bash
# Cloudflare Tunnel token from step 5.2
vault kv put secret/etradie/services/edge-ingress/production/cloudflare/tunnel \
  tunnel_token='eyJhIjoi...your-token...'

# Cloudflare Authenticated Origin Pulls CA. Public, fixed bytes.
vault kv put secret/etradie/services/edge-ingress/production/cloudflare/aop_ca \
  origin-pull-ca.pem="$(curl -fsS https://developers.cloudflare.com/ssl/static/origin_ca_rsa_root.pem)"

# MaxMind GeoLite2 (free signup at maxmind.com -> generate a license key)
vault kv put secret/etradie/services/edge-ingress/production/maxmind \
  account-id='1234567' \
  license-key='your-maxmind-license-key'

# Per-host TLS certs are NOT NEEDED in Cloudflare Tunnel mode
# (Cloudflare terminates public TLS; edge-ingress only needs the AOP CA).
# Seed the path with empty values so ESO does not error:
vault kv put secret/etradie/services/edge-ingress/production/tls \
  api_cert='' api_key='' \
  wildcard_cert='' wildcard_key=''

# Gateway: DB, JWT, encryption keys.
# Generate strong random values; do NOT reuse from anywhere else.
GATEWAY_DB_PASS=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
JWT_SECRET=$(openssl rand -base64 64 | tr -d '/+=' | head -c 64)
BROKER_KEY=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
LLM_KEY=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
ADMIN_PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)

vault kv put secret/etradie/services/gateway/production \
  postgres_user='etradie' \
  postgres_password="$GATEWAY_DB_PASS" \
  postgres_host='postgres.etradie-system.svc.cluster.local' \
  postgres_port='5432' \
  postgres_db='etradie' \
  auth_database_url="postgres://etradie:${GATEWAY_DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=disable" \
  gateway_redis_url='redis://redis.etradie-system.svc.cluster.local:6379/0' \
  auth_jwt_secret="$JWT_SECRET" \
  auth_admin_password="$ADMIN_PASS" \
  broker_encryption_key="$BROKER_KEY" \
  llm_encryption_key="$LLM_KEY"

# Engine: LLM + data-provider keys (replace with real values)
vault kv put secret/etradie/services/engine/production \
  anthropic_api_key='sk-ant-...' \
  openai_api_key='sk-...' \
  twelvedata_api_key='...' \
  fred_api_key='...' \
  database_url="postgres://etradie:${GATEWAY_DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=disable" \
  redis_url='redis://redis.etradie-system.svc.cluster.local:6379/0'

# Execution + Management: same DB + Redis
vault kv put secret/etradie/services/execution/production \
  execution_database_url="postgres://etradie:${GATEWAY_DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=disable" \
  execution_redis_url='redis://redis.etradie-system.svc.cluster.local:6379/1'

vault kv put secret/etradie/services/management/production \
  management_database_url="postgres://etradie:${GATEWAY_DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=disable" \
  management_redis_url='redis://redis.etradie-system.svc.cluster.local:6379/1'

# Save GATEWAY_DB_PASS / JWT_SECRET / ADMIN_PASS securely — you may need
# them for direct DB access or first admin login.
echo "Gateway DB password: $GATEWAY_DB_PASS" >> ~/etradie-prod-creds.txt
echo "JWT secret:          $JWT_SECRET"      >> ~/etradie-prod-creds.txt
echo "Admin password:      $ADMIN_PASS"      >> ~/etradie-prod-creds.txt
chmod 600 ~/etradie-prod-creds.txt
```

---

## 7. Install ArgoCD and bootstrap the platform

### 7.1 Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.12.4/manifests/install.yaml

kubectl -n argocd wait --for=condition=Available \
  deployment/argocd-server --timeout=180s
```

Fetch the auto-generated initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d ; echo
```

Access the UI by port-forwarding (NOT exposing publicly):

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443
# open https://localhost:8080  (login: admin / <password-above>)
```

### 7.2 Apply the AppProject and root Application

```bash
cd ~/eTradie
kubectl apply -f deployments/argocd/appproject.yaml
kubectl apply -f deployments/argocd/root-app.yaml
```

In the ArgoCD UI you will see:

* `etradie-root` Application (the App-of-Apps)
* 14 child Applications (`*-staging` + `*-production` for each
  service)

Production children have **manual sync** disabled by policy
(`automated.{prune:false,selfHeal:false}`). Click each
`*-production` Application -> **Sync** -> **Synchronise**.

Recommended sync order (matches `argocd.argoproj.io/sync-wave`
annotations on the children):

1. `data-layer-production` (wave -2; postgres, redis, chromadb)
2. `engine-production`     (wave -1)
3. `gateway-production`,
   `execution-production`,
   `management-production`  (wave 0, in any order)
4. `envoy-production`       (wave 5)
5. `edge-ingress-production` (wave 10; cloudflared + edge-ingress)

Watch each application reach `Synced + Healthy` before moving on.

---

## 8. End-to-end verification

### 8.1 Pod readiness

```bash
kubectl get pods -A | grep -vE '(Completed|Running)'
# Expected: empty output (all pods Running or Completed).
```

If any pod is in `Init:` for more than 5 minutes, see
*Troubleshooting* below.

### 8.2 Cloudflare Tunnel health

In the Cloudflare Zero Trust UI -> Networks -> Tunnels, the tunnel
status should be **HEALTHY** with 2 connectors (matching
`cloudflared` replicaCount=2).

From the cluster:

```bash
kubectl -n edge-ingress-system logs -l app.kubernetes.io/name=cloudflared --tail=50
# Look for: "Registered tunnel connection" × 2 (one per replica)
```

### 8.3 Public hostname reachability

```bash
curl -fsS -o /dev/null -w "HTTP %{http_code}\n" https://api.etradie.com/healthz
# Expected: HTTP 200
```

If you get a Cloudflare 502 / 522, the tunnel is up but the upstream
(edge-ingress) is not Ready. Check `kubectl -n edge-ingress-system
get pods` and the cloudflared logs.

### 8.4 OAuth + login round-trip

```bash
curl -fsS https://api.etradie.com/api/v1/auth/health
# Expected: {"status":"ok",...}

curl -fsS -X POST https://api.etradie.com/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<ADMIN_PASS-from-step-6.2>"}'
# Expected: 200 with access_token + refresh_token JSON
```

### 8.5 Internal call chain

```bash
TOKEN=$(curl -fsS -X POST https://api.etradie.com/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<ADMIN_PASS>"}' | jq -r .access_token)

curl -fsS https://api.etradie.com/api/v1/state/account \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 with {"balance": 10000.0, ...}
```

This exercises gateway -> execution gRPC -> mock broker round-trip.

---

## 9. Day-2 operations

### 9.1 Postgres backup verification

The data-layer chart deploys a CronJob that runs `pg_dump` nightly:

```bash
kubectl -n etradie-system get cronjob postgres-backup
kubectl -n etradie-system get jobs --sort-by=.metadata.creationTimestamp | tail -5
kubectl -n etradie-system exec -ti $(kubectl -n etradie-system get po -l app.kubernetes.io/name=postgres -o name | head -1) \
  -- ls -lh /backups
```

Quarterly: restore the most recent dump into a scratch namespace and
run a smoke query.

### 9.2 Secret rotation

* **JWT secret:** `vault kv patch secret/etradie/services/gateway/production
  auth_jwt_secret="$(openssl rand -base64 64 | tr -d '/+=' | head -c 64)"`
  then `kubectl -n etradie-system rollout restart deployment etradie-gateway`.
  All existing access tokens become invalid; clients must re-login.
* **Postgres password:** rotate inside Postgres first (`ALTER USER
  etradie WITH PASSWORD '...'`), then update Vault, then restart
  every consumer (gateway, engine, execution, management).
* **Cloudflare Tunnel token:** rotate via Cloudflare Zero Trust UI ->
  Tunnel -> ... -> Refresh Token. Update Vault. Restart cloudflared.

### 9.3 K3s upgrade

K3s minor upgrades are in-place:

```bash
sudo curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="v1.31.x+k3s1" sh -
```

Drain Postgres / Redis pods first if you cannot tolerate the
~30s connection-loss window during kubelet restart.

### 9.4 Optional: monitoring stack

The AppProject already allowlists the `monitoring` namespace. To
add Prometheus + Grafana:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.enabled=true
```

The charts' ServiceMonitors are auto-discovered by the kube-prometheus
Prometheus instance via the `prometheus: kube-prometheus` label
selector.

To enable distributed tracing, install an OTel collector in the
`etradie-observability` namespace (also allowlisted) and override
`config.observability.otelEndpoint` in each service's
`values-production.yaml`.

---

## 10. Disaster recovery

### Total VPS loss

RTO ~ 60 minutes. RPO ~ 24 hours (last nightly Postgres backup).

1. Provision a new Contabo VPS, repeat sections 1–2.
2. Restore Vault from backup (Vault stores its data in
   `vault.vault.svc.cluster.local`'s PVC; the operator's Vault
   backup procedure is documented in HashiCorp's docs and is
   beyond this runbook's scope).
3. Repeat sections 4 (ESO), 7 (ArgoCD).
4. Restore the most recent `pg_dump` from the off-VPS backup
   location into the freshly initialised Postgres pod.
5. Trigger a sync of every `*-production` Application.
6. Update Cloudflare Tunnel's connector token if you re-created
   the Tunnel; the public hostnames stay intact.

What survives without backup: every Kubernetes manifest (in git);
every chart values file (in git); every ArgoCD Application (in git).

What **must** be backed up out-of-band: Vault data (Raft snapshot),
the latest Postgres `pg_dump` (CronJob produces it nightly to
`/backups` PVC — sync to off-VPS storage manually or via cron).

---

## Troubleshooting

### Pod stuck in `Init:0/N`

* `kubectl describe pod <name>` -> read events.
* If the init-container is `wait-for-deps`, the dep service is not
  Ready. Sync the dep's Application first (data-layer before
  engine; engine before gateway).
* If the init-container is `aop-ca-preflight`, the AOP CA bytes in
  Vault are missing or malformed. Re-run section 6.2 for that path.

### `cloudflared` `CrashLoopBackOff`

* `kubectl -n edge-ingress-system logs deploy/cloudflared`.
* Most common cause: tunnel token mismatched. Re-copy from Cloudflare
  UI, re-write to Vault, restart.

### `helm/edge-ingress: ...vaultPath is required`

A chart render-time guard tripped because a Vault path is empty.
Re-run section 6.2 for the named path.

### `external-secrets` reports `permission denied` reading Vault

The Kubernetes auth role binding is wrong. Re-run section 3.3
`vault write auth/kubernetes/role/etradie-eso ...`.

### Cloudflare returns `HTTP 1033`

The Tunnel is not connected. Either the tunnel token is wrong or
cloudflared cannot reach Cloudflare from inside the cluster
(corporate firewall / Contabo egress rules). Verify outbound :443
works: `kubectl -n edge-ingress-system run debug --rm -ti
--image=alpine --restart=Never -- sh -c 'apk add curl && curl
-vk https://api.cloudflare.com'`.

---

## Reference

* Bootstrap-only README: `infrastructure/cluster/bootstrap/README.md`
* Cloud-agnostic Vault path Terraform: `infrastructure/cluster/vault-paths/`
* Cloudflare zone Terraform (optional): `infrastructure/cloudflare/`
* Edge defence chain reference: `docs/architecture/edge-cloudflare-envoy.md`
