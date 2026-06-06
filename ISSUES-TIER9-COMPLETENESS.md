# Tier 9 Mesh Completeness — second-pass fixes

> Branch: `feat/tier9-mesh-completeness`. The merged Tier 9 work fixed
> the 4 services + data-layer + envoy + edge-ingress, but a full-tree
> re-audit found mesh participants and rollout machinery that were
> missed and WILL break when per-service authz is enabled (the intended
> production end-state). All findings traced against `main`. Resume
> from the Progress Tracker.

## Verified facts (no guesses)

- billing SA = `etradie-billing` (fullname=release name; appName pinned).
  billing has a wait-for-deps init (postgres/redis) -> needs native
  sidecar. billing dials postgres:5432 + redis:6379.
- engine rewrap-job carries engine.selectorLabels, dials postgres,
  restartPolicy: Never, NO linkerd annotations (un-meshed).
- mt-node: chart path (mtConnection.enabled=true) renders a
  values-driven NetworkPolicy with egress = DNS + public-internet ONLY
  (no linkerd egress). Runtime path (HostedProvisioner) creates NO
  NetworkPolicy at all (verified in provisioner.py: SA + watchdog CM +
  STS + 2 Services, no NP) -> runtime pods are not default-denied, so
  linkerd egress is not blocked for them; the chart-path NP is still
  wrong and the runtime no-NP is a separate pre-existing gap.
- No linkerd-viz ArgoCD Application exists (only identity/crds/
  control-plane). `linkerd viz edges` (rollout gate) cannot run.
- No staging overlay sets linkerd.io/inject (gw/exec/mgmt/engine/
  billing); data-layer/envoy/edge-ingress/mt-node inject via base
  values -> staging is a half-mesh and the verify-in-staging gate is
  impossible. DECISION: mesh staging fully (services inject in base
  values so staging mirrors prod).
- CI (.github/workflows/ci.yml) renders all 8 helm/ charts but NEVER
  deployments/linkerd -> control-plane proxy.resources schema is
  unvalidated.
- Vault path etradie/platform/linkerd/<env> IS created by terraform
  with trust_anchor_pem/issuer_tls_crt/issuer_tls_key (C3 backing OK).

## Findings -> fixes

- **F1 (CRITICAL)** billing excluded from datastore authz. FIX: mesh
  billing (inject + native sidecar) in base values; add etradie-billing
  to data-layer postgresCallers + redisCallers; add linkerd-ns egress +
  :4191 ingress to billing NetworkPolicy; ship billing
  linkerd-authzpolicy.yaml (Server :8082 -> envoy + gateway; Prometheus
  NetworkAuthentication); add linkerdPolicy block to billing values
  (false base / deliberate enable) + prod overlay.
- **F2 (CRITICAL)** engine rewrap-job denied to postgres under authz.
  FIX: add a postgres NetworkAuthentication admitting the rewrap Job
  (same pattern as postgres-backup) in data-layer authz, keyed to the
  job's source network; the Job stays un-meshed (restartPolicy: Never).
- **F3 (CRITICAL)** mt-node chart NetworkPolicy missing linkerd egress
  + :4191. FIX: add to helm/mt-node values networkPolicy. Note runtime
  no-NP gap.
- **F4 (CRITICAL)** no linkerd-viz Application. FIX: add
  deployments/argocd/children/linkerd-viz-production.yaml (linkerd-viz
  chart, linkerd AppProject, sync-wave -3) + viz values; whitelist viz
  kinds in the linkerd AppProject if needed.
- **F5 (HIGH)** staging not meshed (services). FIX: move
  linkerd.io/inject + native-sidecar (+ opaque/skip where applicable)
  into BASE values for gateway/execution/management/engine/billing so
  staging meshes too; remove the now-duplicated annotations from prod
  overlays (single source of truth).
- **F6 (HIGH)** CI does not validate the linkerd chart. FIX: add a
  helm lint + template step for deployments/linkerd in ci.yml.
- **F7 (MED)** :4191 rules inert without a proxy ServiceMonitor +
  linkerd-viz. Resolved by F4 (viz ships its Prometheus scrape) +
  documented.
- **F8 (LOW)** terraform linkerd_identity bootstrap comment cites the
  old runbook path. FIX: point to docs/runbooks/tier9-linkerd-mesh-rollout.md.

## Progress Tracker

- [x] Step 1 — this tracker.
- [ ] Step 2 (F5 prep + F1) — mesh billing in base values + native
      sidecar; billing linkerdPolicy block.
- [ ] Step 3 (F1) — billing NetworkPolicy linkerd egress + :4191;
      data-layer postgresCallers/redisCallers += etradie-billing.
- [ ] Step 4 (F1) — billing linkerd-authzpolicy.yaml + prod overlay
      enable-flag posture.
- [ ] Step 5 (F2) — data-layer postgres NetworkAuthentication for the
      rewrap Job.
- [ ] Step 6 (F3) — mt-node chart NetworkPolicy linkerd egress + :4191.
- [ ] Step 7 (F5) — move inject+native-sidecar to BASE values for
      gateway/execution/management/engine; drop dup from prod overlays.
- [ ] Step 8 (F4) — linkerd-viz Application + values + AppProject
      whitelist.
- [ ] Step 9 (F6) — CI linkerd chart lint/template.
- [ ] Step 10 (F8) — terraform comment path fix.
- [ ] Step 11 — final reconciliation + runbook update + one MR.
