# infrastructure/gateway

Terraform module that deploys the eTradie gateway service into a Kubernetes
cluster by applying the kustomize tree at
`deployments/gateway/kubernetes/overlays/<environment>` with the appropriate
per-environment image tag, replica count, and trust-chain settings.

This module is **thin on purpose**. The Kubernetes resources themselves are
defined in `deployments/gateway/kubernetes/` (kustomize) and
`helm/gateway/` (Helm). Terraform's role is orchestration and
environment-specific value injection, not resource definition. Owning the
resource bodies in two places would create drift the moment a kustomize
patch lands without a parallel Terraform change.

## Module dependencies (must be applied in this order)

```text
cluster-bootstrap                 (creates namespaces, PSS, OPA)
        ↓
cluster-platform                  (Vault, ESO, prometheus-operator)
        ↓
infrastructure/cloudflare         (zone setup, AOP CA in Vault)
        ↓
infrastructure/gateway   (THIS MODULE)
        ↓
infrastructure/envoy
        ↓
infrastructure/edge-ingress
```

Applying the chain out of order leaves pods in `ContainerCreating` waiting
for Secrets that have not been synthesised yet.

## Inputs

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `namespace` | `string` | `etradie-system` | Must already exist. |
| `environment` | `string` | `production` | One of `local`, `staging`, `production`. Picks the kustomize overlay. |
| `image_repository` | `string` | `registry.gitlab.com/cotradee3/cotradeecode/gateway` | |
| `image_tag` | `string` | `0.1.0` | CI overrides this with the SHA-tagged build. |
| `replicas_min` | `number` | `2` | Lower bound on the HPA. |
| `replicas_max` | `number` | `6` | Upper bound on the HPA. |
| `vault_path` | `string` | `etradie/services/gateway` | ExternalSecret remote-ref path. |
| `log_level` | `string` | `INFO` | One of `DEBUG`, `INFO`, `WARN`, `ERROR`. |
| `trusted_proxy_cidrs` | `string` | `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16` | Comma-separated CIDR list passed to AUTH_TRUSTED_PROXY_CIDRS. |
| `trust_cloudflare` | `bool` | `false` | Maps to AUTH_TRUST_CLOUDFLARE. |

## Outputs

| Output | Description |
|--------|-------------|
| `namespace` | The namespace gateway runs in. Consumed by sibling envoy module. |
| `service_name` | The ClusterIP Service name (`gateway-service`). |
| `headless_service_name` | The headless Service name (`gateway-headless`). |
| `deployment_name` | The Deployment name (`etradie-gateway`). |
| `image_ref` | Fully-qualified image reference applied by this module. |

## Usage

```hcl
module "gateway" {
  source = "../../infrastructure/gateway"

  environment = "production"
  image_tag   = var.gateway_image_tag

  replicas_min       = 5
  replicas_max       = 10
  trusted_proxy_cidrs = "10.100.0.0/16"
  trust_cloudflare   = true
  vault_path         = "etradie/services/gateway/production"

  depends_on = [
    module.cluster_bootstrap,
    module.cluster_platform,
    module.cloudflare,
  ]
}
```

## Validating an apply

After `terraform apply`:

```bash
kubectl -n etradie-system rollout status deploy/etradie-gateway --timeout=5m
kubectl -n etradie-system get hpa etradie-gateway
kubectl -n etradie-system get pdb etradie-gateway
kubectl -n etradie-system get servicemonitor etradie-gateway

# Trust-chain sanity check (must echo the configured CIDRs):
kubectl -n etradie-system exec deploy/etradie-gateway -- \
  printenv AUTH_TRUSTED_PROXY_CIDRS AUTH_TRUST_CLOUDFLARE
```

## Why no helm_release here

We do not use the `helm_release` Terraform resource for this module because:

1. The helm chart at `helm/gateway/` is values-only (no `templates/`); it is
   designed to feed kustomize, not to be installed directly.
2. Mixing Terraform-applied kustomize with helm-managed releases creates a
   resource-ownership conflict: helm thinks it owns the Deployment, kustomize
   thinks it owns the Deployment, and a `helm uninstall` would silently delete
   resources Terraform expects to manage.
3. GitOps tooling (ArgoCD, Flux) consumes the kustomize tree directly. Keeping
   Terraform in the same lane means a single tool owns each resource.
