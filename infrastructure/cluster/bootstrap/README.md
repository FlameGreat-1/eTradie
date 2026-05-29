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

- A Kubernetes cluster (>= v1.27) reachable via kubectl from the
  operator's machine. K3s, kubeadm, kind, k3d, or any conformant
  distribution is fine.
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

## 3. Install Vault (skip if using HCP / external Vault)

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --namespace vault --create-namespace \
  --set 'server.ha.enabled=true' \
  --set 'server.ha.replicas=3'
```

After install, initialise + unseal Vault and capture the root
token (production: enable auto-unseal via the cluster's KMS).

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

ArgoCD then reconciles the 14 child Applications. With
`syncPolicy.automated` disabled on production children, the
first rollout requires an explicit operator click in the ArgoCD
UI — deliberate.

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
  mt_node_credential_encryption_key="$(openssl rand -hex 32)" \
  default_zmq_auth_token="$(openssl rand -hex 32)"
```

The engine reads `MT_NODE_CREDENTIAL_ENCRYPTION_KEY` from this path
to AES-GCM seal per-user MT broker credentials before writing them
to a per-tenant Kubernetes Secret. Without it, the dashboard's
'Hosted' connection option fails with a clear ConfigurationError.

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
