# eTradie deployment

Single authoritative reference for how the platform is built, packaged,
and reconciled onto a cluster.

## The chain

```text
Client
   ↓ (TLS, Cloudflare-anycast)
Cloudflare edge
   ↓ (mTLS, AOP CA-signed client cert)
edge-ingress  (Rust)        - TLS termination + geo routing
   ↓ (HTTP/1.1)
etradie-envoy (C++/WASM)    - rate limiting + request validation
   ↓ (HTTP/1.1)
etradie-gateway (Go)        - auth, sessions, business orchestration
   ↓ (gRPC, HTTP)
engine / execution / management (Python + Go)
```

Each hop runs in its own Kubernetes namespace with PodSecurityStandard
=restricted, NetworkPolicy that only opens the previous + next hop, and
a ServiceMonitor + ResourceQuota.

## Tooling

| Tool | Role |
|------|------|
| **Helm** | Source of truth for every Kubernetes manifest. Three charts: `helm/edge-ingress/`, `helm/envoy/`, `helm/gateway/`. |
| **ArgoCD** | The only thing that applies manifests to clusters. Six Applications under `deployments/argocd/children/` (one per service × environment). |
| **Terraform** | Cloud only. `infrastructure/cluster/` (EKS + IAM + Vault paths) and `infrastructure/cloudflare/` (zone, AOP, DNS, origin firewall). Never touches a Kubernetes manifest. |
| **External Secrets Operator** | Resolves Vault secrets into Kubernetes Secrets. The helm charts ship the ExternalSecret CRDs; ESO synthesises the actual Secret bytes. |
| **MaxMind geoipupdate** | Populates the GeoLite2-City database used by edge-ingress's geo-router. Init container in production; sidecar in local docker-compose. |

What is **not** used:

* Kustomize. The previous `deployments/<svc>/kubernetes/` tree was
  deleted in this consolidation. Helm covers every overlay need via
  `values-<env>.yaml`.
* `helm install` from CI. The pipeline never calls helm directly. CI
  rewrites the ArgoCD `Application.spec.source.targetRevision` to the
  new git SHA and lets ArgoCD reconcile.

## Bootstrap order

First-time setup of an environment:

1. **`infrastructure/cluster/`** - EKS, OIDC, IAM roles, Vault paths.
2. **Operator populates Vault** at the four paths bootstrapped by
   step 1. ArgoCD will not be able to start any pod until this is
   done; that is the intent.
3. **Helm install ArgoCD itself** (one-time):
   ```bash
   helm repo add argo https://argoproj.github.io/argo-helm
   helm install argocd argo/argo-cd -n argocd --create-namespace
   ```
4. **Apply the AppProject + root Application:**
   ```bash
   kubectl apply -n argocd -f deployments/argocd/appproject.yaml
   kubectl apply -n argocd -f deployments/argocd/root-app.yaml
   ```
5. **`infrastructure/cloudflare/`** - DNS records pointing at the
   NLB. Apply this AFTER the edge-ingress NLB is provisioned by
   ArgoCD reconciling the helm chart, because the AWS Load Balancer
   Controller needs the Service object to exist before it issues an
   NLB and exposes its hostname.
6. **Validate end-to-end** using `make edge-test` patterns adapted
   to the cluster's external endpoint.

## ArgoCD sync waves

Waves enforce a clean cold-start order. The annotations live on each
resource template inside the helm charts:

| Wave | Resources |
|------|-----------|
| 0    | Namespace, ServiceAccount, RBAC, PriorityClass |
| 1    | ExternalSecret (must precede anything that references the synthesised Secret) |
| 2    | ConfigMap, Service |
| 3    | Deployment, HPA, PodDisruptionBudget |
| 4    | NetworkPolicy (last - placing it earlier blocks ESO from reaching Vault during bootstrap) |

Application-level waves (so envoy comes up after gateway is reachable,
and edge-ingress comes up after envoy is reachable):

| Application | Application sync-wave |
|-------------|------------------------|
| `gateway-*` | 0 |
| `envoy-*`   | 5 |
| `edge-ingress-*` | 10 |

## Promotion model

* **Staging** (`*-staging` Applications): `targetRevision: HEAD`, full
  auto-sync. Every commit on `main` deploys.
* **Production** (`*-production` Applications): `targetRevision: vX.Y.Z`,
  manual sync only, gated by the `etradie` AppProject's sync window
  (business hours UTC, Mon-Fri).

A production deploy is therefore three steps:

1. Cut a git tag `vX.Y.Z` on `main`.
2. CI rewrites `targetRevision: vX.Y.Z` in the production Applications
   (one PR auto-merged by the release workflow).
3. Maintainer clicks Sync in ArgoCD inside the sync window.

## Image and WASM injection at install

The helm charts deliberately do NOT bake image tags or WASM bytes into
`values.yaml`. CI provides them at promotion time via
`argocd app set <app> --helm-set-file ...`. This keeps the chart in
git pure (auditable, byte-stable across reviews) while letting the
build artefacts live with the image registry.

Required CI injections per Application:

| Application | Required `--helm-set` |
|-------------|-----------------------|
| `edge-ingress-*` | `image.tag`, `service.tlsCertificateArn` |
| `envoy-*` | `image.tag`, `wasm.base64` (file), `wasm.sha256`, `wasm.builtAt` |
| `gateway-*` | `image.tag` |

The charts fail-fast on missing required values - see the
`{{- fail ... }}` guards in:

- `helm/edge-ingress/templates/configmap.yaml`
- `helm/edge-ingress/templates/service.yaml`
- `helm/envoy/templates/configmap-wasm.yaml`

## Local development

```bash
make edge-up    # full Cloudflare-emulating chain with mTLS
make edge-test  # validate the chain end-to-end
make edge-down  # tear down
```

The `edge` profile in the top-level `docker-compose.yml` mirrors the
production chain: an `edge-geoip-init` service populates the
`geoip-data` named volume, which `edge-ingress` mounts read-only at
`/data/geoip` (matching the in-pod path used by the helm chart).

Local mTLS uses a self-signed CA generated by `make dev-certs`. The
bytes of the dev CA are gitignored; the generator script is
committed.

## Validating the chain

```bash
# 1) Pods Ready (each environment + each service)
kubectl -n etradie-system rollout status deploy/etradie-gateway --timeout=10m
kubectl -n envoy-system  rollout status deploy/etradie-envoy --timeout=10m
kubectl -n edge-ingress-system rollout status deploy/edge-ingress --timeout=10m

# 2) ExternalSecrets resolved (no "SecretSyncedError" condition)
kubectl -n edge-ingress-system get externalsecret
kubectl -n etradie-system get externalsecret

# 3) AOP CA mounted and non-empty
kubectl -n edge-ingress-system exec deploy/edge-ingress -- \
  wc -c /etc/edge-ingress/cloudflare/origin-pull-ca.pem

# 4) NLB has external hostname
kubectl -n edge-ingress-system get svc edge-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# 5) End-to-end
curl -v https://api.etradie.com/auth/healthz   # via Cloudflare, must 200
curl -v --resolve api.etradie.com:443:<NLB-IP> \
  https://api.etradie.com/auth/healthz          # direct origin: must FAIL TLS
```

## Trust chain (auth client-IP resolution)

`src/auth/clientip.go` consumes:

* `AUTH_TRUSTED_PROXY_CIDRS` - operator CIDRs (helm `trustChain.trustedProxyCidrs`).
* `AUTH_TRUST_CLOUDFLARE` - boolean (helm `trustChain.trustCloudflare`).
* `/etc/etradie/cloudflare/{ipv4,ipv6}.txt` - Cloudflare published
  ranges, mounted by the helm gateway chart only when
  `trustChain.trustCloudflare="true"`. Source of truth:
  `deployments/cloudflare/ip-ranges/`. Chart-local copy:
  `helm/gateway/files/cloudflare/`. CI gates drift.

## Where each NOTE.md / FIX.md / AUDIT.md issue ended up resolved

| Original issue | Resolution |
|---|---|
| Edge-ingress namespace mismatch | Helm chart owns the namespace; kustomize deleted. |
| NetworkPolicy label / namespace mismatch | Helm chart uses correct selectors against `etradie-envoy` in `envoy-system`. |
| Two manifests own `etradie-system` | Only the gateway helm chart creates it. |
| WASM placeholder text | Chart fails fast unless `wasm.base64` is injected. |
| Hardcoded ACM ARN | Removed; chart fails fast unless `service.tlsCertificateArn` is injected. |
| `helm/` orphan files at root | Deleted. |
| EXOPER rebrand orphans under `deployments/docker/` | Deleted. |
| `infrastructure/gateway/` applies k8s | Replaced with `infrastructure/cluster/` + `infrastructure/cloudflare/`. |
| ServiceMonitor selector conflicts | One source of truth (helm); no conflict possible. |
| `make edge-test` false-greens | Replaced with five-step validation that detects crashed daemons. |
| Local docker-compose geoip path broken | Added `edge-geoip-init` service + named volume. |
| Cloudflare AOP CA in wrong namespace | Helm edge-ingress chart owns the ExternalSecret in the same namespace as the consuming pod. |