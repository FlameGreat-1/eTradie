# deployments/argocd

ArgoCD `Application` and `AppProject` manifests that wire the helm
charts in this repository to whichever Kubernetes cluster the
operator brings up (Contabo K3s, OCI OKE, GKE, AKS, kubeadm — the
platform is cluster-agnostic).

## Layout

```text
deployments/argocd/
  appproject.yaml             AppProject scoping RBAC + allowed sources/destinations
  root-app.yaml               App-of-Apps: points at children/ recursively
  children/                   ON SWITCH: every file here is reconciled by root-app
    data-layer-staging.yaml         (sync wave -2)
    engine-staging.yaml             (sync wave -1)
    gateway-staging.yaml            (sync wave 0)
    execution-staging.yaml          (sync wave 0)
    management-staging.yaml         (sync wave 0)
    envoy-staging.yaml              (sync wave 5)
    edge-ingress-staging.yaml       (sync wave 10)
    monitoring-stack-staging.yaml   (sync wave -7)
    observability-logs-staging.yaml (sync wave -2)
    mt-node-staging.yaml            (sync wave -1)
    billing-staging.yaml            (sync wave 1)
    linkerd-identity-production.yaml      (sync wave -6)
    linkerd-crds-production.yaml          (sync wave -5)
    linkerd-control-plane-production.yaml (sync wave -4)
  environments/production/    PARKED: the *-production app-workload Applications.
                              NOT under children/, so root-app does NOT create
                              them on a staging cluster (see that dir's README).
    data-layer-production.yaml      (sync wave -2)
    engine-production.yaml          (sync wave -1)
    gateway-production.yaml         (sync wave 0)
    execution-production.yaml       (sync wave 0)
    management-production.yaml      (sync wave 0)
    envoy-production.yaml           (sync wave 5)
    edge-ingress-production.yaml    (sync wave 10)
    billing-production.yaml         (sync wave 1)
    monitoring-stack-production.yaml
    observability-logs-production.yaml
    mt-node-production.yaml
  optional/                   PARKED: optional add-ons (e.g. linkerd-viz)
```

The three `linkerd-*-production` Applications stay under `children/`
because the Linkerd mesh runs ONCE per cluster regardless of which
environment posture the cluster hosts (the CA path is hardcoded to
`/production` in `deployments/linkerd/values.yaml`; there is no
`*-staging` linkerd variant). They are correct on a staging OR a
production cluster. Only the 11 *app-workload* `*-production`
Applications are parked under `environments/production/`.

Presence under `children/` is the on switch; presence under
`environments/production/` (or `optional/`) is the off switch. This is
the same pattern documented in `optional/README.md` and
`environments/production/README.md`.

## Bootstrap

Once per cluster, after the cluster is reachable and Vault paths
are populated (see `docs/deployment/`):

```bash
kubectl create namespace argocd 2>/dev/null || true
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.12.4/manifests/install.yaml

kubectl -n argocd wait --for=condition=Available \
  deployment/argocd-server --timeout=180s

kubectl apply -f deployments/argocd/appproject.yaml
kubectl apply -f deployments/argocd/root-app.yaml
```

From that point forward, every commit on `main` that touches
`helm/<svc>/` causes ArgoCD to reconcile the cluster. CI does NOT run
`helm upgrade` directly; it pushes images to GHCR (the image tag is
pinned in each chart's `values.yaml`) and ArgoCD takes over.

## Sync waves

The `argocd.argoproj.io/sync-wave` annotation on each child
Application enforces a clean cold-start order:

| Wave | Component | Why this position |
|------|-----------|-------------------|
| -2   | data-layer (postgres, redis, chromadb) | Every other service has these as init-container dependencies; must be Ready first. The data-layer chart also creates the etradie-system Namespace, ResourceQuota and LimitRange. |
| -1   | engine | Reached by gateway/execution/management at boot for the broker bridge. |
|  0   | gateway, execution, management | Mutually dial each other; Kubernetes Services reach Ready in any order. |
|  1   | billing | Reached by gateway billing-client at request time; does not block gateway boot anymore (audit ref: G-H3, DA-H2). |
|  5   | envoy | Backend cluster `gateway-headless` must already exist. |
| 10   | edge-ingress (incl. cloudflared) | Public edge; depends on envoy being reachable. |

Resource-level `argocd.argoproj.io/sync-wave` annotations inside
each chart's templates further order the resources within a single
release (Namespace -> ServiceAccount -> ExternalSecret ->
ConfigMap/Service -> Deployment/StatefulSet -> NetworkPolicy).

## Promotion model

* **Staging** Applications use `syncPolicy.automated.{prune:true,
  selfHeal:true}` and `targetRevision: HEAD`. Every commit on `main`
  auto-rolls staging.

* **Production** Applications use
  `syncPolicy.automated.{prune:false, selfHeal:false}` and
  `targetRevision: main`. Production rollouts require a maintainer
  to click Sync inside the AppProject's business-hours sync window
  (13:00 UTC Mon-Fri, 8h).

  Production app-workload Applications live under
  `environments/production/`, NOT under `children/`, so the
  staging cluster's root-app never creates them (staging and
  production are not meant to co-reside on one cluster per
  BUDGET.md Table 2B). On a dedicated production cluster, point
  that cluster's root-app at a source path that includes
  `environments/production/` plus the shared `linkerd-*` apps.
  See `environments/production/README.md` for the full rationale
  and the production-cluster deploy procedure.

There is no `helm install` or `argocd app set --helm-set` in CI.
Image tags are pinned per chart in `values.yaml` and bumped with
the rest of the chart on each release.

## Why ArgoCD, not Flux

ArgoCD is the standard for Helm + ExternalSecrets + PSS-restricted
on any conformant Kubernetes distribution. Flux v2 is a viable
alternative but its `HelmRelease` CRD adds an extra layer between
the chart and the cluster that ArgoCD's `source.helm.valueFiles`
does not. We picked the simpler model.

## What this directory does NOT cover

* The cluster itself — see `infrastructure/cluster/bootstrap/` for
  Contabo K3s, `infrastructure/cluster/oci/` for OCI OKE.
* Vault path schema — see `infrastructure/cluster/vault-paths/`.
* Cloudflare zone settings + DNS — see `infrastructure/cloudflare/`.
* Operator-installed platform charts (Vault, ESO, ArgoCD itself,
  optional kube-prometheus-stack, optional OTel collector) — see
  the deployment runbooks under `docs/deployment/`.
