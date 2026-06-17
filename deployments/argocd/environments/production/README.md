# Parked production app-workload Applications

These 11 ArgoCD `Application` manifests are COMPLETE and valid. They are
deliberately parked here, OUTSIDE `deployments/argocd/children/`, so the
root app-of-apps (`deployments/argocd/root-app.yaml`, which reconciles
`children/` with `directory.recurse: true`) does NOT create them on a
staging cluster.

This is the same pattern the repo already uses for
`deployments/argocd/optional/` (see that directory's README): presence
UNDER `children/` is the on switch; presence here (outside it) is the
off switch.

## Why they are parked

Each `*-production` Application targets the SAME helm `releaseName` and
namespace as its `*-staging` twin (for example, `engine-production` and
`engine-staging` both deploy `releaseName: etradie-engine` into
`etradie-system`). On a single cluster that hosts ONE environment
(BUDGET.md Table 2B: "pick ONE environment per box; staging and
production are not meant to co-reside"), having both sets of Application
objects present lets a manual sync of a `*-production` app overwrite the
shared release with the production values overlay, which the staging
app's `selfHeal` then fights -- a permanent ownership conflict that
flips live workloads between overlays.

Parking the production apps here makes that conflict STRUCTURALLY
impossible on a staging cluster: root-app never sees them, so it never
creates them.

## What is NOT here (stays in children/)

- The 11 `*-staging` Applications -- the live staging environment.
- The 3 `linkerd-*-production` Applications. The Linkerd mesh runs once
  per cluster regardless of environment posture
  (`deployments/linkerd/values.yaml` hardcodes the CA path to
  `/production`; there is no `*-staging` linkerd variant). They are
  correct on a staging OR a production cluster and must stay under
  root-app.

## How to deploy production (on the dedicated production cluster)

Production runs on its OWN cluster (never co-resident with staging). On
that cluster, either:

- point its `root-app` at a source path that includes
  `environments/production/` plus the shared `linkerd-*` apps; or
- `git mv` these 11 files back into `children/` on a production-only
  branch/overlay the production cluster's root-app tracks.

The production cluster is the mirror image of the staging cluster: it
deploys `environments/production/` + the `linkerd-*` apps and parks the
`*-staging` apps.

## CI

Every Application manifest here is still syntax-validated by the
`argocd manifests parse` step in `.github/workflows/ci.yml`, which
recursively validates `*.yaml` under both `children/` and
`environments/`. Moving a file here does NOT remove it from CI coverage.
