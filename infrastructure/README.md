# infrastructure/

Terraform modules that own **cloud** resources only. Kubernetes
manifests live in `helm/<svc>/`; ArgoCD applications under
`deployments/argocd/` reconcile them onto the cluster these modules
provision.

## Module layout

| Module | Owns | Does NOT own |
|--------|------|--------------|
| `cluster/` | EKS cluster, node groups, IAM roles for ESO / cluster-autoscaler / AWS Load Balancer Controller, Vault path schema bootstrap. | Any Kubernetes manifest, any helm release. |
| `cloudflare/` | Cloudflare zone, AOP enablement, R53 records, origin-firewall security groups. | Any Kubernetes manifest, the AOP CA bytes themselves (those live in Vault). |

## Apply order

```text
cluster/         (creates EKS, OIDC provider, IAM roles, Vault paths)
        ↓
cloudflare/      (creates DNS records that point at the EKS NLB)
        ↓
ArgoCD bootstrap (apply the root Application from deployments/argocd/)
        ↓
ArgoCD reconciles helm/edge-ingress + helm/envoy + helm/gateway
```

Applying out of order leaves Cloudflare records pointing at NLBs that
do not exist yet, or ArgoCD trying to mount Secrets that ESO has not
yet had IAM permissions to synthesise.

## Why no infrastructure/<svc>/ modules

The deleted `infrastructure/gateway/` module shelled out to
`kustomize build` and applied the rendered manifests via the
`gavinbunney/kubectl` provider. This made Terraform an unwitting
competitor with ArgoCD for ownership of Deployments, NetworkPolicies,
and HPAs. Removing it and giving ArgoCD exclusive ownership of every
Kubernetes resource eliminates the reconciliation conflict by
construction.

If a future service needs cloud-side primitives (an SQS queue, an S3
bucket, an additional IAM role), those go in a new module under
`infrastructure/<svc>-cloud/` - never `infrastructure/<svc>/` (which
implies the module owns the running service).
