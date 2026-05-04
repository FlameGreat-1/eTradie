# infrastructure/cluster

Provisions the EKS cluster, IAM roles for cluster add-ons, and the
empty Vault path schema that the helm charts' ExternalSecrets
reference.

## What it owns

* EKS cluster (private endpoint), KMS-encrypted secrets at rest.
* Default managed node group (c6i.2xlarge by default).
* `coredns`, `kube-proxy`, `vpc-cni`, `aws-ebs-csi-driver` add-ons.
* OIDC provider (required for IRSA).
* IAM roles for IRSA bindings to External Secrets Operator,
  cluster-autoscaler, and the AWS Load Balancer Controller.
* Vault KV-v2 paths (empty, with `ignore_changes = [data_json]` so
  operator writes are not overwritten on subsequent applies):
  - `secret/etradie/services/edge-ingress/<env>/tls`
  - `secret/etradie/services/edge-ingress/<env>/cloudflare/aop_ca`
  - `secret/etradie/services/edge-ingress/<env>/maxmind`
  - `secret/etradie/services/gateway/<env>`

## What it does NOT own

* Any Kubernetes manifest, helm release, or ArgoCD Application.
  Those are reconciled onto the cluster by ArgoCD after the cluster
  is reachable.
* The bytes of any Vault secret. Operators populate them post-apply
  using whatever credential management workflow is in place
  (`vault kv put`, AWS Secrets Manager sync, etc.).

## Apply

```bash
cd infrastructure/cluster
terraform init
terraform apply -var environment=production -var vpc_id=<...> ...
```

Once `terraform apply` completes:

1. Annotate the ESO ServiceAccount with
   `eks.amazonaws.com/role-arn=<irsa_eso_role_arn>` (already done by
   the helm install of external-secrets if you pass
   `--set serviceAccount.annotations.eks\.amazonaws\.com/role-arn=...`).
2. Populate the four Vault paths above.
3. Apply the ArgoCD root Application from `deployments/argocd/`.
