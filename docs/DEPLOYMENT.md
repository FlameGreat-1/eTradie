# eTradie deployment

> **Superseded.** This file's previous contents (AWS EKS / ACM / NLB
> / kustomize references) no longer reflect the platform. The
> current authoritative deployment runbooks live under
> [`./deployment/`](./deployment/).
>
> Use:
>
> * [`./deployment/README.md`](./deployment/README.md) — entry-point
>   and target selection.
> * [`./deployment/contabo-k3s.md`](./deployment/contabo-k3s.md) —
>   full Contabo VPS K3s runbook.
> * [`./deployment/oci-oke.md`](./deployment/oci-oke.md) — full OCI
>   OKE runbook.
>
> The platform is no longer deployed on AWS. Cloudflare Tunnel is
> the public-edge strategy on every supported target.

## Quick start (any target)

1. Provision a Kubernetes cluster on your chosen target.
2. Install Vault, External Secrets Operator (ESO), ArgoCD.
3. Create a Cloudflare Zero Trust Tunnel; copy the token.
4. Apply `infrastructure/cluster/vault-paths/` (Terraform) to bootstrap
   the Vault KV path schema.
5. Populate Vault with the real secret bytes.
6. Apply `deployments/argocd/appproject.yaml` and
   `deployments/argocd/root-app.yaml`.
7. Sync each `*-production` ArgoCD Application in sync-wave order.

Detailed step-by-step procedures (with verifications, troubleshooting,
and DR) are in the runbooks linked above.
