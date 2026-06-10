# Optional ArgoCD Applications (OFF in the current TABLE 2B profile)

Manifests in this directory are COMPLETE, working ArgoCD Applications
that are deliberately NOT deployed in the current resource profile
(BUDGET.md TABLE 2B, single-node Contabo). They live here - instead of
being deleted - so an operator can turn them back ON without digging
through git history.

Why a directory and not an `enabled` flag: the root app-of-apps
(`deployments/argocd/root-app.yaml`) recursively deploys EVERY manifest
under `deployments/argocd/children/`, and ArgoCD Application resources
have no enable/disable field. Presence in `children/` IS the on switch.

## Turn ON (e.g. when moving to a bigger VPS / multi-node cluster)

Either move the manifest back under GitOps control (preferred,
permanent):

    git mv deployments/argocd/optional/linkerd-viz-production.yaml \
           deployments/argocd/children/linkerd-viz-production.yaml
    # commit + merge; the root app picks it up on the next sync

or apply it directly for a TEMPORARY need (e.g. mesh verification
before enabling linkerdPolicy), then delete when done:

    kubectl apply -f deployments/argocd/optional/linkerd-viz-production.yaml
    # ... verify with `linkerd viz edges` ...
    kubectl -n argocd delete application linkerd-viz-production

## Turn OFF

Move the manifest from `children/` back into this directory and let the
root app prune it (root app uses Prune=confirm, so ArgoCD will ask for
one operator confirmation).

## Current contents

| Application | Why OFF (TABLE 2B) | Cost when ON |
|---|---|---|
| linkerd-viz-production.yaml | Non-critical verification tooling; the mesh + mTLS itself stays ON | ~0.4 CPU / ~1Gi (tap+web+metrics-api + bundled Prometheus) |

NOTE: this manifest pins the HA posture (tap/web/metricsAPI x2). On the
single-node box, reduce the inline `values:` replicas to 1 each when
turning it on temporarily.
