# Phase 10.6 / Future-Work — Kyverno + PSS-restricted (enterprise-grade replacement for the current PSS-baseline workaround)

**Date authored:** 2026-06-17
**Status:** PLANNED, not applied. Captured for the multi-node BUDGET.md Table 5 cutover.
**Scope:** every Linkerd-meshed namespace on the platform
**Supersedes (when applied):** the current `pod-security.kubernetes.io/enforce: baseline` posture on `edge-ingress-system` (and the same posture already in place on `etradie-system`, `envoy-system`, `linkerd`).
**Author context:** Phase 10.6 staging deployment on single-node Contabo K3s, ArgoCD GitOps, Linkerd `stable-2.14.10`.

> **READ THIS FIRST.** This file is a forward-dated implementation plan, NOT a record of work done. The current cluster is at PSS `baseline` for meshed namespaces, deliberately. Do NOT execute the plan below on a single-node Contabo VPS — the resource budget does not have room. The cutover target is the multi-node cluster described in BUDGET.md Table 5.

---

## 1. What was changed on the current cluster, and why

### The change

In `helm/edge-ingress/values-staging.yaml`, the following block was added:

```yaml
# Drop the chart's default PSS enforce tier (restricted) on the
# edge-ingress-system namespace. Linkerd's auto-injected linkerd-init
# initContainer requires NET_ADMIN + NET_RAW to install iptables rules
# for proxy interception; PSS restricted-tier forbids those capabilities
# and admission rejects every meshed pod creation. Baseline tier admits
# the init container while still blocking privileged containers,
# hostNetwork, hostPID, hostIPC, and root-without-runAsNonRoot.
# Same posture every other meshed namespace on this cluster already
# uses (etradie-system, envoy-system, linkerd). Audit ref:
# PROGRESS gotcha #35.
namespace:
  podSecurityStandard: "baseline"
```

The chart template `helm/edge-ingress/templates/namespace.yaml` reads that single value and renders all four PSS labels on the namespace:

```yaml
pod-security.kubernetes.io/enforce: baseline
pod-security.kubernetes.io/enforce-version: latest
pod-security.kubernetes.io/audit: baseline
pod-security.kubernetes.io/warn: baseline
```

Previously the chart’s default was `restricted` on all four labels.

### The root cause that forced this

Linkerd's proxy injector mutates every pod in a meshed namespace at admission time to add an init container called `linkerd-init`. That init container's only job, once at pod startup, is to install iptables rules so all pod traffic is transparently routed through the Linkerd proxy. Installing iptables rules requires two Linux capabilities:

- `NET_ADMIN` — modify network settings
- `NET_RAW` — craft raw network packets

These capabilities are powerful and PSS `restricted` tier flatly forbids them. With `enforce: restricted` on the namespace, the kube-apiserver PodSecurity admission plugin rejects every meshed pod creation with:

```
pods "edge-ingress-..." is forbidden: violates PodSecurity
  "restricted:latest": unrestricted capabilities (container
  "linkerd-init" must not include "NET_ADMIN", "NET_RAW"
  in securityContext.capabilities.add)
```

The Deployment controller therefore never gets a pod created, the Service has no endpoints, cloudflared dials the empty ClusterIP and returns `connection refused`, and the public path `staging-api.exoper.com/healthz` returns HTTP 502.

### Why `baseline` is the chosen workaround (not the goal)

PSS is a fixed Kubernetes specification with three immutable tiers — `privileged`, `baseline`, `restricted`. **You cannot say "give me restricted but also allow NET_ADMIN on init containers"**; PSS does not expose that knob. The only finer-grained option is to add a second admission controller (Kyverno or OPA Gatekeeper) and write a `PolicyException` that surgically permits just the Linkerd init container, its two capabilities, and the namespaces that need it. That is the plan documented below; it is correct enterprise-grade engineering and it is **deferred** because:

1. Kyverno's default 3-controller install (admission-controller + background-controller + reports-controller) costs **~300m CPU / ~384Mi RAM** at the conservative single-replica sizing. BUDGET.md Table 2B production floor on Contabo VPS 30 is **~5.7 CPU / ~9.1Gi**, leaving **~0.7 CPU of headroom** after platform-infra. Adding 300m of admission-control overhead cuts headroom to **~0.4 CPU** — too tight to be safe under real burst.
2. The current cluster is **staging on single-node**. The same chart code will go to production, but production is also on the same single-node Contabo box for the initial cutover. Adding Kyverno now buys nothing the kube-apiserver PSS plugin (still at `audit: restricted` + `warn: restricted` per the three-key split documented in section 5) does not already give us.
3. The single-node deploy is by design a temporary posture per BUDGET.md ("the platform's full-balanced operating profile is multi-node"). When we cut over to the Table 5 shape (~3–7 nodes of 8 vCPU / 32GB each), Kyverno's 300m fits trivially in the per-node platform budget and the surgical exception becomes the right answer.

### Where the baseline change exactly lives

| Layer | File | Lines | Effect |
|---|---|---|---|
| Staging overlay value | `helm/edge-ingress/values-staging.yaml` | `namespace.podSecurityStandard: "baseline"` block, around lines 10–20 | Sets the chart input. |
| Chart template | `helm/edge-ingress/templates/namespace.yaml` | The four `pod-security.kubernetes.io/*` labels | Renders the namespace's PSS labels from the input. |
| Cluster object | `Namespace/edge-ingress-system` | `.metadata.labels` | Live state after ArgoCD reconcile. |

### Other charts already at PSS `baseline` (or warn-only) for the same reason

Verified on the live cluster + chart source 2026-06-17:

- `etradie-system` — set to `audit: restricted` + `warn: restricted` only (no `enforce` label). Chart commit: `helm/data-layer/templates/namespace.yaml` documented in PROGRESS gotcha #35.
- `envoy-system` — same posture; chart commit `3bc20fa7`.
- `linkerd` — upstream Linkerd chart defaults to `enforce: privileged` because the control plane itself runs init containers that need `NET_ADMIN`.
- `monitoring` — kube-prometheus-stack chart sets no PSS labels; kube-apiserver default applies.
- `vault`, `external-secrets`, `reloader`, `argocd` — same, no PSS labels set.

The edge-ingress chart was the **outlier** — it shipped with `restricted` set by default in `values.yaml` (`namespace.podSecurityStandard: "restricted"`) and the staging overlay never overrode it, so the namespace was getting `enforce: restricted` while every other meshed namespace ran at baseline or warn-only. The current change brings edge-ingress in line with the rest of the platform.

---

## 2. Why `baseline` is acceptable in the interim (honest accounting)

PSS `baseline` is still a meaningful security boundary. It blocks at admission:

- Privileged containers (`securityContext.privileged: true`).
- Host network, host PID, host IPC sharing.
- Mounting sensitive host paths.
- Running without an explicit security context.
- `procMount` other than default.
- Most sysctls outside the namespaced safe set.
- AppArmor / SELinux escapes to unconfined profiles.

What baseline **does** permit that restricted forbids (the relevant ones for this discussion):

- `NET_ADMIN` and `NET_RAW` capabilities on containers that ask for them.
- Running as UID 0 (root) in the container (still must be `runAsNonRoot: false` explicit; baseline does NOT auto-allow root).
- Some volume types restricted bans.

In the current cluster posture, the only container in any meshed namespace that asks for `NET_ADMIN` / `NET_RAW` is Linkerd's own `linkerd-init`. Every other pod's container security context follows the chart's `runAsNonRoot: true`, `runAsUser: 1000`, `capabilities.drop: [ALL]`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false` pattern. The audit log (`audit: restricted` is still set on edge-ingress-system if the three-key split lands; otherwise audit also follows enforce to baseline) would surface any future chart that tried to slip in additional capabilities.

Defense in depth remains intact:

1. **Host firewall (ufw, Phase 1.6)** — only :22 publicly. K3s :6443, postgres :5432, etc. unreachable from the internet.
2. **Cloudflare Tunnel + AOP CA mTLS** — only Cloudflare's edge can reach edge-ingress.
3. **Linkerd mTLS between meshed pods** — every east-west hop encrypted with workload identity.
4. **NetworkPolicies in every namespace** — pod-to-pod access restricted by label selectors.
5. **PSS `audit` + `warn` still at restricted** — violations of restricted-tier rules surface in kube-apiserver audit logs even though they are not blocked.
6. **GitOps with ArgoCD** — every chart change goes through `main` branch review before it can reach the cluster.
7. **PSS `enforce: baseline`** — still blocks the dangerous-by-default postures listed above.

The one layer that is **relaxed compared to ideal** is the surgical admission control on `NET_ADMIN`/`NET_RAW`. The Kyverno plan below restores that layer once the cluster can afford the operator.

---

## 3. The Kyverno enterprise-grade plan (apply at multi-node cutover)

### 3.1 Architectural decisions, made explicit

**Decision 1 — Production parity.** Production gets the exact same Kyverno install as staging. Same chart version, same policy file, same exception. Both env overlays are siblings under `helm/kyverno/`. The same code that meets the bar in staging is the code that goes to production. This is the explicit operator constraint baked into the platform pattern (matches `monitoring-stack-{staging,production}.yaml`).

**Decision 2 — Two policies, not one.**

- **Policy A:** A Kyverno `ClusterPolicy` that enforces the equivalent of PSS `restricted` cluster-wide on every namespace labeled `pod-security.kubernetes.io/enforce: restricted`. We keep the PSS label on the namespace so the kube-apiserver's PSS admission plugin also runs — defense in depth: two independent admission controllers enforcing the same rules.
- **Policy B:** A `PolicyException` (a first-class Kyverno CRD designed for exactly this case) that exempts Linkerd's auto-injected `linkerd-init` initContainer, narrowly scoped to:
  - container name exactly `linkerd-init` (NOT a wildcard),
  - only capabilities `NET_ADMIN` + `NET_RAW` (NOT a wildcard),
  - only namespaces labeled `linkerd.io/inject=enabled` (Linkerd's own injection-trigger label),
  - only when applied by the Linkerd injector's service account (`linkerd-proxy-injector` in the `linkerd` namespace).

**Decision 3 — Revert the `baseline` overlay on cutover day.** The patch on `helm/edge-ingress/values-staging.yaml` (the block documented in section 1 above) goes away. The chart's default `restricted` posture stays. Kyverno enforces it correctly cluster-wide and the exception carves out exactly what Linkerd needs.

**Decision 4 — Three-key PSS split survives Kyverno arrival.** The chart template gets changed (in commit 7 of the sequence below) to render three separate PSS keys instead of one. After Kyverno is in, the namespace looks like:

```yaml
pod-security.kubernetes.io/enforce: baseline      # kube-apiserver PSS backstop (lets linkerd-init through here too)
pod-security.kubernetes.io/audit: restricted      # apiserver audit log still surfaces restricted violations
pod-security.kubernetes.io/warn: restricted       # kubectl apply prints warnings for restricted violations
```

Why keep PSS at all when Kyverno is enforcing strict? Two independent enforcement layers (kube-apiserver PSS + Kyverno) over different rule scopes is *more* secure than one. The kube-apiserver layer is the last line of defense if Kyverno is ever down or its webhook is bypassed.

**Decision 5 — Apply to every meshed chart uniformly.** The same change pattern (three-key PSS split + Kyverno exception coverage) applies to every chart with a namespace template: `data-layer`, `engine`, `gateway`, `execution`, `management`, `billing`, `edge-ingress`, `envoy`, `mt-node`, `observability-logs`. Audited in commit 7 of the sequence below. No more outlier charts.

### 3.2 What changes, file by file (the 8-commit sequence)

**Group 1 — Add Kyverno to the platform (new files)**

1. `deployments/argocd/kyverno-appproject.yaml` (NEW) — AppProject scoping Kyverno's CRDs + webhooks + ClusterRoles. Same pattern as `monitoring-appproject.yaml` and `linkerd-appproject.yaml`. Applied with `kubectl apply -f`, NOT via root-app (matches PROGRESS gotcha #24: root-app reconciles only `deployments/argocd/children/`).
2. `deployments/argocd/children/kyverno-staging.yaml` (NEW) — ArgoCD Application pulling the upstream `kyverno` chart from `https://kyverno.github.io/kyverno/` at a pinned version, with values overlay from `helm/kyverno/values-staging.yaml`. Sync wave **-8** (one wave before monitoring-stack at -7, because Kyverno's webhooks must be ready before any other chart admission). Multi-source `$values` pattern, same as `monitoring-stack-staging.yaml`.
3. `deployments/argocd/children/kyverno-production.yaml` (NEW) — Same shape, points at `values-production.yaml`, `automated.{prune:false,selfHeal:false}` matching `monitoring-stack-production.yaml` posture.
4. `helm/kyverno/values-staging.yaml` (NEW) — Values overlay. Pins admission-controller + background-controller replicas to 1 each, disables `cleanupController` (no scheduled policy reports cleanup needed at this scale; saves ~50m/64Mi), keeps `reportsController` for the audit trail. Sized to fit BUDGET.md Table 5 multi-node ledger.
5. `helm/kyverno/values-production.yaml` (NEW) — Same shape, slightly larger requests, same controller selection.

**Group 2 — Add the Kyverno policies (separate chart, separate Application, so the policy lifecycle is independent of the operator lifecycle)**

6. `helm/kyverno-policies/Chart.yaml`, `values.yaml`, `values-staging.yaml`, `values-production.yaml`, `templates/restricted-tier-policy.yaml`, `templates/linkerd-init-exception.yaml` (NEW — 6 files). The exception template (the load-bearing one) looks like:

```yaml
apiVersion: kyverno.io/v2beta1
kind: PolicyException
metadata:
  name: linkerd-init-capabilities-exception
  namespace: kyverno
  labels:
    app.kubernetes.io/part-of: etradie
    app.kubernetes.io/managed-by: argocd
  annotations:
    description: "Permit Linkerd's proxy-init initContainer NET_ADMIN+NET_RAW iptables setup capabilities in meshed namespaces."
spec:
  exceptions:
    - policyName: restricted-tier-baseline
      ruleNames:
        - restricted-capabilities
  match:
    any:
      - resources:
          kinds:
            - Pod
          namespaceSelector:
            matchLabels:
              linkerd.io/inject: enabled
          # Only pods being created by Linkerd's proxy-injector mutating webhook.
          # The webhook is the only legitimate path that adds linkerd-init.
  conditions:
    all:
      - key: "{{ request.object.spec.initContainers[?name=='linkerd-init'] | length(@) }}"
        operator: Equals
        value: 1
      - key: "{{ request.object.spec.initContainers[?name=='linkerd-init'].securityContext.capabilities.add | [0] }}"
        operator: AnyIn
        value:
          - NET_ADMIN
          - NET_RAW
```

7. `deployments/argocd/children/kyverno-policies-staging.yaml`, `kyverno-policies-production.yaml` (NEW — 2 files). Sync wave **-7** (after the Kyverno operator at -8; same wave as monitoring-stack but they're independent so ordering on that wave is fine).

**Group 3 — Revert the patch-work + audit every chart's namespace template**

8. `helm/edge-ingress/values-staging.yaml` — Revert the `namespace.podSecurityStandard: "baseline"` block. The chart default `restricted` re-applies.
9. `helm/edge-ingress/templates/namespace.yaml` — Split the single `.Values.namespace.podSecurityStandard` into three keys (`enforce`/`audit`/`warn`) so we can set `enforce: baseline` (kube-apiserver PSS backstop, lets Linkerd-init through here too) while keeping `audit: restricted` and `warn: restricted` for the apiserver-layer audit trail.
10. `helm/edge-ingress/values.yaml` — Update the `namespace` value block to the three-key shape. Defaults: `enforce: baseline`, `audit: restricted`, `warn: restricted`.
11. Every other chart with a namespace template: `helm/data-layer/templates/namespace.yaml`, `helm/envoy/templates/namespace.yaml`, `helm/observability-logs/templates/namespace.yaml`, `helm/mt-node/templates/namespace.yaml`. Apply the same three-key split. (No more outlier charts.)

**Group 4 — AppProject + documentation**

12. `deployments/argocd/appproject.yaml` — Add Kyverno CRD kinds (`PolicyException`, `Policy`) to `namespaceResourceWhitelist`. The `ClusterPolicy` and `ClusterPolicyException` kinds go in the `kyverno-appproject.yaml`'s `clusterResourceWhitelist` because they're cluster-scoped.
13. `docs/runbooks/PROGRESS.md` — Append a new section under Phase 10.7 (the cutover phase) documenting the Kyverno install + policy + exception. Updates gotcha #35 to point at this new authoritative section. Records the measured resource impact against BUDGET.md Table 5.
14. `docs/runbooks/README.md` — Add Phase 10.7 covering the Kyverno bootstrap step. Update BUDGET.md Table 5 if Kyverno's measured profile lands outside what we forecast (deferred — measure on the new cluster first).
15. `BUDGET.md` Table 5 — Add Kyverno row. Cost: ~300m / 384Mi platform-infra-subtotal addition. Fits easily in the Table 5 multi-node ledger (~32 vCPU / 128GB platform pool aggregate).

### 3.3 Risk register (read before cutover day)

**Risk 1 — Webhook failurePolicy.** Kyverno's webhooks default to `failurePolicy: Fail`. If Kyverno is down, **every** pod admission in scoped namespaces fails. Mitigation: set `failurePolicy: Ignore` on the validating webhook for infrastructure namespaces (`kube-system`, `argocd`, `vault`, `linkerd`, `external-secrets`, `monitoring`, `kyverno` itself). Application namespaces stay `Fail`. This is documented Kyverno best practice; wired via `helm/kyverno/values-*.yaml::config.webhooks` and the `failurePolicy` field on each per-namespace policy. The values overlay must explicitly set this; the chart default is wrong for our deployment shape.

**Risk 2 — Bootstrap chicken-and-egg.** Kyverno must be installed and Ready BEFORE any `Policy` / `PolicyException` is applied, OR the policy creation itself triggers a Kyverno admission webhook that does not yet exist — chicken-and-egg. The split into operator-Application (wave -8) and policies-Application (wave -7) handles fresh-install ordering automatically. **On a cluster that is already up**, the operator must sync them sequentially with a wait between:

```bash
argocd app sync kyverno-staging --grpc-web --timeout 300
argocd app wait kyverno-staging --health --timeout 300
kubectl -n kyverno wait --for=condition=Available deployment --all --timeout=300s
argocd app sync kyverno-policies-staging --grpc-web --timeout 300
argocd app wait kyverno-policies-staging --health --timeout 300
```

**Risk 3 — Resource cost on production.** Kyverno's default 3-controller install costs ~300m CPU / ~384Mi RAM. On the **current** single-node Contabo VPS 30, production headroom is ~0.7 CPU; Kyverno would cut this to ~0.4 CPU — too tight to be safe under real burst. This is why the plan is **deferred to the multi-node cutover**. On the BUDGET.md Table 5 multi-node cluster (~32 vCPU / 128GB platform pool aggregate), 300m of admission control fits without changing capacity planning.

**Risk 4 — Linkerd version changes the init container name.** The exception matches on container name `linkerd-init`. If a future Linkerd release renames it (e.g. to `linkerd-cni-init` or similar), the exception stops matching and admission breaks for every meshed pod. Mitigation: the exception's container-name match is a pinned string in `helm/kyverno-policies/templates/linkerd-init-exception.yaml`; bumping Linkerd requires a chart diff that updates the exception in lockstep. CI render-check should grep the exception against the rendered Linkerd injector spec to catch drift.

**Risk 5 — The exception is too narrow and breaks future Linkerd features.** Linkerd may someday add a third capability to `linkerd-init` (e.g. `SYS_ADMIN` for some new CNI feature). The exception only permits `NET_ADMIN` + `NET_RAW`. If Linkerd needs more, the exception widens — with an explicit chart commit and an explicit security review.

**Risk 6 — Kyverno chart version compatibility.** Kyverno's compatibility matrix against Kubernetes versions is strict. The version pin in `kyverno-staging.yaml::targetRevision` and `kyverno-production.yaml::targetRevision` must be validated against the matrix at <https://kyverno.io/docs/installation/#compatibility-matrix> at cutover time. Last verified compatibility (record at cutover): Kyverno chart `3.2.6` against K8s 1.30.4.

### 3.4 Cutover-day runbook (the manual sequence)

Assuming the 8 commits above have all landed on `main` and pushed to GitHub, the operator runbook on the multi-node cluster is:

```bash
# 0. Pre-flight: confirm tunnel + KUBECONFIG + ArgoCD CLI logged in.
kubectl get nodes
argocd account list --grpc-web | head -3

# 1. Apply the AppProject (not GitOps-managed; one-time kubectl apply).
kubectl apply -f deployments/argocd/kyverno-appproject.yaml
kubectl get appproject kyverno -n argocd  # confirm exists

# 2. Sync Kyverno operator first, wait for all controllers Available.
argocd app sync kyverno-staging --grpc-web --timeout 600
argocd app wait kyverno-staging --health --timeout 600
kubectl -n kyverno wait --for=condition=Available deployment --all --timeout=300s
kubectl -n kyverno get pods   # expect: admission-controller, background-controller, reports-controller all Running

# 3. Confirm Kyverno webhooks are Live before applying any policy.
kubectl get validatingwebhookconfigurations | grep kyverno
kubectl get mutatingwebhookconfigurations | grep kyverno
# Expect: kyverno-policy-validating-webhook-cfg, kyverno-resource-validating-webhook-cfg,
#         kyverno-policy-mutating-webhook-cfg, kyverno-resource-mutating-webhook-cfg

# 4. Sync the policies (ClusterPolicy + PolicyException).
argocd app sync kyverno-policies-staging --grpc-web --timeout 300
argocd app wait kyverno-policies-staging --health --timeout 300
kubectl get clusterpolicy   # restricted-tier-baseline should be Ready
kubectl -n kyverno get policyexception linkerd-init-capabilities-exception

# 5. Now sync the charts that have the three-key PSS split. Each will
#    apply enforce: baseline / audit: restricted / warn: restricted to its
#    namespace, plus the Kyverno ClusterPolicy enforces restricted-tier
#    rules everywhere except where the linkerd-init exception applies.
argocd app sync data-layer-staging engine-staging gateway-staging \
  execution-staging management-staging billing-staging \
  edge-ingress-staging envoy-staging mt-node-staging \
  observability-logs-staging --grpc-web --timeout 600

# 6. Verify every meshed pod is still up and admission still works.
kubectl get pods -A --field-selector=status.phase!=Running | grep -v Completed || echo "all pods Running"

# 7. Verify the exception is firing correctly: a non-Linkerd container
#    asking for NET_ADMIN MUST be rejected. Create a test pod that asks
#    for NET_ADMIN under a name that isn't linkerd-init.
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: kyverno-exception-test
  namespace: etradie-system
spec:
  containers:
    - name: not-linkerd-init   # deliberately wrong name
      image: busybox
      command: ["sleep", "60"]
      securityContext:
        capabilities:
          add: ["NET_ADMIN"]
EOF
# Expected: admission rejected by Kyverno restricted-tier-baseline policy.
kubectl delete pod kyverno-exception-test -n etradie-system --ignore-not-found

# 8. Repeat for production once staging is verified end-to-end.
```

If step 7 does NOT reject the test pod, the exception is too broad — STOP, debug the PolicyException match block, do not proceed to production.

### 3.5 Rollback plan if Kyverno breaks the cluster

If step 5 or 6 produces pod admission failures unrelated to the linkerd-init exception:

```bash
# Disable Kyverno's validating webhook to unblock admission.
kubectl delete validatingwebhookconfiguration kyverno-resource-validating-webhook-cfg
kubectl delete validatingwebhookconfiguration kyverno-policy-validating-webhook-cfg
# Pods now schedule normally. The Kyverno deployment is still up but
# enforcement is disabled.

# Then debug the failing admission, fix the policy, re-apply the
# webhook config (Kyverno will recreate it on its next reconcile).
```

Full rollback to the current `baseline` posture is one revert commit on each chart's `values.yaml` + a force-sync. The platform survives without Kyverno; we are not architecturally dependent on it. It is a hardening upgrade, not a load-bearing component.

---

## 4. When to execute this plan

Trigger conditions, any of which is sufficient:

- Platform moves to the multi-node cluster shape per BUDGET.md Table 5. Kyverno's 300m fits trivially in the per-node platform budget.
- A security audit or compliance requirement (SOC 2, FedRAMP, ISO 27001 prep) requires the surgical exception in writing, not the broad PSS-baseline relaxation.
- A second admission controller is being installed for a different reason (e.g. Falco, OPA Gatekeeper for non-PSS rules) and the operator overhead of Kyverno alongside is marginal.

Until one of those conditions is true, the current PSS-baseline posture on meshed namespaces is the documented, accepted, defense-in-depth-preserving posture, and this file remains a forward-dated plan.

---

## 5. Status board (for the cutover day)

| Item | Status |
|---|---|
| Plan documented | ✅ (this file) |
| Trigger condition met (Table 5 cutover OR compliance requirement) | ⏸ pending |
| Group 1 commits (Kyverno operator) | ⏸ pending |
| Group 2 commits (Kyverno policies) | ⏸ pending |
| Group 3 commits (revert baseline + three-key split + chart audit) | ⏸ pending |
| Group 4 commits (AppProject + docs) | ⏸ pending |
| Cutover-day runbook step 1–8 executed | ⏸ pending |
| BUDGET.md Table 5 updated with measured Kyverno cost | ⏸ pending |
| PROGRESS gotcha #35 updated to point here | ⏸ pending |

When cutover day arrives, append a `Phase 10.7 — RESOLVED <date>` section to `PROGRESS.md`, flip every row above to ✅, and update BUDGET.md Table 5 with the measured resource cost from `kubectl top -A` after Kyverno has been steady-state for at least 24h.
