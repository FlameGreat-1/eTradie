# deployments/argocd

ArgoCD `Application` and `AppProject` manifests that wire the helm
charts in this repository to the EKS cluster provisioned by
`infrastructure/cluster/`.

## Layout

```text
deployments/argocd/
  appproject.yaml         AppProject scoping RBAC + allowed sources/destinations
  root-app.yaml           App-of-Apps: points at children/ recursively
  children/
    edge-ingress-staging.yaml
    edge-ingress-production.yaml
    envoy-staging.yaml
    envoy-production.yaml
    gateway-staging.yaml
    gateway-production.yaml
```

## Bootstrap

Once per cluster, after `infrastructure/cluster/` applies and Vault
paths are populated:

```bash
kubectl create namespace argocd 2>/dev/null || true
helm install argocd argo/argo-cd -n argocd \
  --set server.service.type=ClusterIP \
  --set configs.params."server\.insecure"=false

kubectl apply -n argocd -f deployments/argocd/appproject.yaml
kubectl apply -n argocd -f deployments/argocd/root-app.yaml
```

From that point forward, every commit on `main` that touches
`helm/<svc>/` causes ArgoCD to reconcile the cluster. The CI pipeline
does NOT run `helm upgrade` directly; it pins the Application's
`targetRevision` to the new git SHA and ArgoCD takes over.

## Sync waves

Resources are ordered with `argocd.argoproj.io/sync-wave` annotations
to guarantee a clean cold-start:

| Wave | What |
|------|------|
| 0    | Namespace + RBAC (ServiceAccount, Role, RoleBinding) |
| 1    | ExternalSecrets (Vault must be reachable) |
| 2    | ConfigMaps + Services |
| 3    | Deployment + HPA + PDB |
| 4    | NetworkPolicies (last - placing them first would block ESO from reaching Vault) |

## Promotion model

Production Applications use
`argocd.argoproj.io/sync-options: ApplyOutOfSyncOnly=true` and
`syncPolicy.automated` is gated by a sync window. A staging deploy is
automatic; a production deploy requires a maintainer to click Sync.

Image tags are pinned per environment in the helm `values-<env>.yaml`
files, with CI rewriting them on each merge to `main` (staging) or
on each tag (production).

## Why not Helm direct + GitOps Engine

ArgoCD is the standard for Helm + ExternalSecrets + PSS-restricted on
EKS. Flux v2 is a viable alternative but its `HelmRelease` CRD adds
an extra layer between the chart and the cluster that ArgoCD's
`source.helm.valueFiles` does not. We picked the simpler model.
