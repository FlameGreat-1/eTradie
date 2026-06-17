# infrastructure/cluster/bootstrap/

Bootstrap path for clusters NOT provisioned by the `cluster/oci/`
Terraform module: Contabo K3s, kubeadm, hand-rolled bare-metal,
kind / k3d for local. Lists the exact steps to bring the cluster
from 'empty' to 'ArgoCD can reconcile the platform'.

If you are on OCI use `../oci/` instead (run `terraform apply`,
then jump to step 1 of this guide for ESO + Vault setup; the OCI
module already created the cluster + node pool + taint).

The platform does NOT deploy on AWS (see infrastructure/README.md).
Audit ref: IB-C1.

## 0. Prerequisites

- Host hardening (self-managed hosts only). BEFORE installing K3s /
  kubeadm on a VPS or bare-metal host, harden the host per
  `docs/runbooks/tier11-vps-host-hardening.md`: SSH key-only auth,
  password login disabled, fail2ban, a default-deny host firewall, and
  a private (non-public) K8s API reached over SSH tunnel / VPN. The OCI
  OKE path delegates this to the managed node image and can skip it.
- A Kubernetes cluster (>= v1.29) reachable via kubectl from the
  operator's machine. K3s, kubeadm, kind, k3d, or any conformant
  distribution is fine.
  NOTE: >= 1.29 is REQUIRED (not just recommended) because the Linkerd
  mesh (Tier 9) enables native sidecar injection
  (config.linkerd.io/proxy-enable-native-sidecar), which depends on the
  K8s SidecarContainers feature that is GA/stable only from 1.29. On an
  older cluster the annotation is ignored, the linkerd proxy starts
  AFTER init containers, and meshed init hops (engine alembic migrate,
  the wait-for-deps probes, the mt-node Vault Agent init) are refused
  by the meshed datastores -> pods never become Ready. The provisioned
  OKE cluster (infrastructure/cluster/oci) defaults to v1.32.
- A Vault instance reachable from the cluster (HCP, Vault chart,
  or external VM). The platform charts read every secret through
  the External Secrets Operator + a Vault ClusterSecretStore.
- A Cloudflare account with a Zero Trust Tunnel pre-created (if
  using `service.cloudProvider=cloudflare-tunnel`, the default).

## 1. Install cert-manager (only if NOT using Cloudflare Tunnel)

Cloudflare Tunnel mode terminates TLS at Cloudflare's edge, so
cert-manager is not required. If you opted into
`service.cloudProvider=generic`, install cert-manager so
edge-ingress can mint its own TLS certs (Let's Encrypt or
internal CA):

```bash
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --version v1.15.3 \
  --set installCRDs=true
```

## 2. Install External Secrets Operator (always)

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace \
  --version 0.10.4
```

## 3. Install Vault + Vault Agent Injector (skip Vault server step if using HCP / external Vault)

The mt-node hosting path's H1 fix REQUIRES the Vault Agent Injector to be
installed in-cluster. The injector mutates per-tenant mt-node Pods so
Vault renders broker credentials into a tmpfs file at startup; the
plaintext credentials never appear in a K8s Secret.

### 3a. Self-hosted Vault (server + injector together)

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --namespace vault --create-namespace \
  --set 'server.ha.enabled=true' \
  --set 'server.ha.replicas=3' \
  --set 'injector.enabled=true' \
  --set 'injector.replicas=2' \
  --set 'injector.metrics.enabled=true'
```

After install, initialise + unseal Vault and capture the root
token (production: enable auto-unseal via the cluster's KMS).

### 3b. HCP Vault / external Vault (injector only)

When Vault itself runs outside the cluster, install ONLY the Vault Agent
Injector with the chart's server.enabled=false flag. The injector
authenticates against the external Vault using its own SA via the
Kubernetes auth backend configured in step 4.

```bash
helm install vault hashicorp/vault \
  --namespace vault --create-namespace \
  --set 'server.enabled=false' \
  --set 'injector.enabled=true' \
  --set 'injector.externalVaultAddr=https://vault.example.com' \
  --set 'injector.replicas=2' \
  --set 'injector.metrics.enabled=true'
```

### 3c. Verify the injector is healthy before continuing

```bash
kubectl -n vault get pods -l app.kubernetes.io/name=vault-agent-injector
# Expected: NAME ... STATUS=Running   READY=1/1
```

## 4. Apply Vault path schema

```bash
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=...

cd ../vault-paths
terraform init
terraform apply -var environment=production -var vault_address=$VAULT_ADDR
```

## 5. Populate the Vault paths with real secrets

For each path printed by the previous step's `vault_paths` output,
write the real bytes:

```bash
vault kv put secret/etradie/services/edge-ingress/production/cloudflare/tunnel \
  tunnel_token=eyJhIjoi...   # from Cloudflare Zero Trust UI

# Authenticated Origin Pulls CA bundle. The KEY name MUST be 'aop_ca'
# (matches helm/edge-ingress/templates/externalsecret-aop-ca.yaml which
# reads property: aop_ca). The CA bytes come from the AOP endpoint, NOT
# the Origin CA endpoint - they are different CAs. Audit ref: IV-H5, IB-H1, IB-H2.
vault kv put secret/etradie/services/edge-ingress/production/cloudflare/aop_ca \
  aop_ca="$(curl -fsS https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem)"

# ChromaDB auth token. THIS PATH IS THE SINGLE SOURCE OF TRUTH for the
# token - both the ChromaDB server pod and the engine pod read it from
# here. Audit ref: IV-C2.
vault kv put secret/etradie/data-layer/chromadb/production \
  auth_token="$(openssl rand -hex 32)"

# ... and so on for every path in the vault_paths output.
```

## 6. Create the Vault ClusterSecretStore

Apply a ClusterSecretStore named `vault-backend` (the chart default):
see the External Secrets docs for the `kind: ClusterSecretStore` +
`provider.vault` block. The ClusterSecretStore must authenticate
the ESO pod to Vault — typically via Kubernetes ServiceAccount
auth method on Vault.

## 7. Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml
```

## 8. Apply the platform AppProject + root Application

```bash
kubectl apply -f ../../../deployments/argocd/appproject.yaml
kubectl apply -f ../../../deployments/argocd/root-app.yaml
```

ArgoCD then reconciles every Application under
`deployments/argocd/children/` (`directory.recurse: true`). On a
staging cluster that is the 11 `*-staging` app-workload
Applications (auto-sync: `automated.{prune:true, selfHeal:true}`)
plus the 3 shared `linkerd-*-production` Applications (manual
sync). The `*-production` app-workload Applications are parked
under `deployments/argocd/environments/production/` (outside
`children/`), so root-app does NOT create them here — see
`deployments/argocd/environments/production/README.md`. On a
dedicated production cluster, point root-app at a source path that
includes `environments/production/` + the `linkerd-*` apps; those
production Applications have `syncPolicy.automated` disabled, so
their first rollout requires an explicit operator click in the
ArgoCD UI — deliberate.

## 9. Install the Cluster Autoscaler (OKE / cloud-managed pools only)

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set cloudProvider=oci-oke \
  --set extraArgs.balance-similar-node-groups=true \
  --set extraArgs.skip-nodes-with-local-storage=false \
  --set extraArgs.skip-nodes-with-system-pods=false
```

The OCI Terraform module already tagged the node pool with the
autoscaler-required tags (`k8s.io_cluster-autoscaler_*`). For K3s /
kubeadm clusters running on fixed-size pools (Contabo VPS), skip this
step entirely - the chart's HPAs will autoscale the workloads, but
the NODE pool stays fixed.

## 10. Populate the mt-node platform Vault path

```bash
vault kv put secret/etradie/services/mt-node/production \
  default_zmq_auth_token="$(openssl rand -hex 32)"
```

This Vault path holds the platform-level fallback ZMQ auth token (used
by the mt-node container's EA AUTH_TOKEN input when no per-tenant
override is set). Per-tenant MT broker credentials (login, password,
per-tenant ZMQ token) are no longer stored as a K8s Secret with
plaintext values - the H1 fix uses the Vault Agent Injector to render
them directly into the per-tenant Pod at startup. See step 12 for the
per-tenant infrastructure.

The legacy mt_node_credential_encryption_key key is no longer required
for new deployments. Existing deployments may retain it for backwards
compatibility during the cutover window; the engine logs an
informational message when it is unset.

## 12. Provision the mt-node tenant Vault infrastructure (Vault Agent Injector)

The terraform/cluster/vault-paths module bootstraps the per-tenant
Vault path prefix, the Kubernetes auth roles, and the policies that
lock each Pod to its own connection_id. Apply it AFTER step 11.

```bash
cd ../vault-paths
terraform apply \
  -var environment=production \
  -var vault_address=$VAULT_ADDR \
  -var k8s_host=https://kubernetes.default.svc \
  -var k8s_ca_cert="$(kubectl get cm -n kube-system kube-root-ca.crt -o jsonpath='{.data.ca\.crt}')" \
  -var k8s_reviewer_jwt="$(kubectl create token -n vault vault-auth)"
```

What this provisions (see vault-paths/mt_node_tenant_secrets.tf for the
full contract):

  - `vault_auth_backend.kubernetes` - declared as managed; idempotent on
    a cluster where ESO already enabled it.
  - `vault_kubernetes_auth_backend_config.kubernetes` - configures the
    cluster API server + reviewer JWT.
  - `vault_policy.mt_node_provisioner` - WRITE on every tenant path
    under `etradie/data/tenants/mt-node/*`. Granted to the engine SA.
  - `vault_policy.mt_node_tenant` - READ on EXACTLY the requesting
    Pod's own tenant path (templated by the auth role's connection_id
    metadata).
  - `vault_kubernetes_auth_backend_role.mt_node_provisioner` - binds
    the engine SA in etradie-system namespace.
  - `vault_kubernetes_auth_backend_role.mt_node_tenant` - binds every
    per-tenant SA the engine provisions (name pattern etradie-mt-*).

Prerequisite: a vault-auth ServiceAccount with the
`system:auth-delegator` ClusterRole must exist in the vault namespace.
The Vault helm chart creates this automatically when injector.enabled=true.
For external Vault, create it manually:

```bash
kubectl create serviceaccount -n vault vault-auth
kubectl create clusterrolebinding vault-auth-delegator \
  --clusterrole=system:auth-delegator \
  --serviceaccount=vault:vault-auth
```

## 11. Verify

```bash
kubectl -n etradie-system get pods
kubectl -n edge-ingress-system get pods       # cloudflared + edge-ingress
kubectl -n envoy-system get pods
```

All pods should be Ready. If `cloudflared` is in CrashLoop, check
step 5 (the tunnel token must be the literal token string, not
base64-encoded, not JSON-quoted).

If a user picks 'Hosted MT' in the dashboard and the engine fails
with a 5xx, check:
  - `kubectl auth can-i create deployments --as system:serviceaccount:etradie-system:etradie-engine -n etradie-system` (should return yes)
  - `kubectl -n etradie-system get externalsecret etradie-mt-node-platform-platform` (should be Ready)
  - `kubectl -n etradie-system logs deployment/etradie-engine | grep hosted_`
