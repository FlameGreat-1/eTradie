# Tier 9 — Mesh Rollout Hardening (staging/production finalisation)

> Single source of truth + progress anchor. Nothing here is in
> production yet; this series finalises the Linkerd mTLS mesh for the
> staging -> production cut. Every finding below was traced against the
> live `main` tree (NOT diffs/history). Resume from the Progress Tracker.
>
> Branch: `feat/tier9-mesh-rollout-hardening`.

---

## Verified cluster facts (drive the fixes; traced, not assumed)

- **K8s version (provisioned):** OKE default `v1.32.1`, ENHANCED_CLUSTER
  (`infrastructure/cluster/oci/{main,variables}.tf`). 1.32 has the
  SidecarContainers feature GA (stable since 1.29). The OKE main.tf
  comment explicitly lists "native sidecar containers" as a relied-upon
  feature. => the init-ordering fix is **Linkerd native sidecar**.
  Bootstrap floor is raised to **>= 1.29** to keep native sidecar valid
  on non-OKE (Contabo K3s / kubeadm) installs.
- **`linkerd` namespace label:** created by ArgoCD `CreateNamespace=true`
  (no chart Namespace object). On K8s >= 1.22 `NamespaceDefaultLabelName`
  admission auto-applies `kubernetes.io/metadata.name: linkerd`. The
  etradie-system Namespace objects also carry that label explicitly
  (engine + data-layer namespace.yaml). => the C2 egress
  `namespaceSelector: kubernetes.io/metadata.name: linkerd` WILL match.
- **Service NetworkPolicy templates** (gateway/execution/management/
  engine) render `.Values.networkPolicy.{ingress,egress}` VERBATIM =>
  C2/C4 service rules go in the values lists.
- **Data-layer NetworkPolicy** is hardcoded in the template (not values)
  => C2/C4 datastore rules go in `helm/data-layer/templates/networkpolicy.yaml`.
- **postgres/redis readiness probes** use a unix socket / exec (NOT TCP
  via the proxy) => no probe<->mesh interaction. chromadb (HTTP) still
  to confirm before the data-layer commit.

---

## Findings (severity-ordered; all confirmed on main)

### CRITICAL

- **M1 — init-container / proxy ordering deadlock.** Standard
  initContainers run BEFORE the linkerd-proxy in non-native-sidecar
  mode. Affected: engine `wait-for-deps` + `migrate` (postgres/redis);
  gateway/execution/management `wait-for-deps`; runtime mt-node pods
  carry `vault.hashicorp.com/agent-init-first: "true"` + linkerd inject
  (provisioner.py merges MT_NODE_POD_ANNOTATIONS_JSON). On 1.32 the fix
  is native sidecar: `config.linkerd.io/proxy-enable-native-sidecar:
  "true"` (control-plane default + per-workload where the proxy must be
  up during init). FIX = native sidecar everywhere meshed.
- **C1 — defaultAllowPolicy: all-authenticated** blackholes un-meshed
  Prometheus (`monitoring`) + postgres-backup CronJob during the
  mesh-on/authz-off window. FIX = `all-unauthenticated` bootstrap
  (still encrypts meshed<->meshed; per-service Servers are the real
  enforcement).
- **C2 — NetworkPolicies have NO egress to the `linkerd` namespace.**
  Default-deny egress + no linkerd allow => injected proxies cannot
  reach identity/destination/policy => pods never Ready. Datastores are
  DNS-only egress (worst). FIX = egress to ns `linkerd` (all ports;
  control plane is trusted) on all 7 meshed pods.
- **C3 — identity trust anchor never delivered to control plane.**
  `identityTrustAnchorsPEM: ""` + no helm parameter on the control-plane
  Application => GitOps sync starts identity with empty anchor =>
  crashloop. FIX = wire the anchor via the control-plane child app
  `helm.parameters` / values, fail-loud.
- **C4 — CORRECTED.** Original claim (allow :4143 ingress) was WRONG.
  Linkerd's redirect to the inbound proxy (:4143) happens inside the
  destination pod netns, AFTER the CNI NetworkPolicy check; the proxy
  also dials the destination on its ORIGINAL app port. So NetworkPolicy
  sees original app ports on both ends (5432/6379/8000/8080/50052..),
  NOT 4143 -> the existing app-port rules already suffice for the data
  plane. The ONLY real additions needed are: (a) C2 egress to the
  `linkerd` namespace [done], and (b) :4191 proxy-admin ingress from
  Prometheus so it can scrape the proxy's own metrics. The :4143
  ingress rules added earlier are dead and are being removed.

### HIGH

- **H3 — `linkerdPolicy.enabled: true` committed in every prod overlay.**
  Authz enforces on the SAME sync that first meshes pods (contradicts
  the phased "mesh -> verify 100% mTLS -> then enforce" design). FIX =
  `enabled: false` in prod overlays; deliberate follow-up flip after
  staging verification.

### MEDIUM

- **MED-1 — trust-anchor ExternalSecret dead/misleading.** Identity ESO
  materialises `linkerd-identity-trust-anchor` Secret (comment calls it
  a ConfigMap) that nothing consumes. Resolve as part of C3.
- **MED-2 — false comment** in envoy/values-production.yaml: "Envoy
  speaks HTTP/2 to gateway". Actual: envoy gateway_cluster has no
  http2_protocol_options => HTTP/1.1 (matches the gateway Server
  proxyProtocol HTTP/1). Fix the comment only.

### LOW

- **LOW-1 — identity ExternalSecret hardcodes sync-wave `-5`** (== CRDs)
  while the identity Application is wave -6. Functionally fine (both
  precede -4). Align to -6 for consistency.

### PRE-EXISTING (in blast radius; not to be ignored)

- **PRE-1 — etradie-system Namespace double-ownership.** BOTH
  `helm/data-layer/templates/namespace.yaml` AND
  `helm/engine/templates/namespace.yaml` render the `etradie-system`
  Namespace. The engine chart's own comment says only one chart may own
  it. data-layer is the documented owner (sync-wave -2). FIX = set
  `engine.namespace.create: false` (data-layer owns ns + quota +
  limitrange) and verify no label/PSS regression.

---

## Verified CORRECT (checked, not skipped)

- SA identities match callers across all 5 charts (release name =
  etradie-<svc> = fullname = SA name; gateway grpc callers exec+mgmt,
  http caller etradie-envoy@envoy-system).
- Ports/protocols consistent: gw 50052/8080, exec 50053/8080, mgmt
  50054/8083, engine 8000, pg 5432 opaque, redis 6379 opaque, chroma
  8000 HTTP.
- Linkerd Server.podSelector (single name label) is a subset match of
  the real pod labels — matches.
- engine opaque 5555 + skip 4317; edge-ingress meshed + skip-inbound 443
  (base values); envoy meshed, SA etradie-envoy.
- LimitRange min 50m/64Mi (data-layer namespace.yaml) cleared by
  control-plane proxy/proxy-init requests.
- postgres-backup un-meshed + NetworkAuthentication; mt-node runtime
  inject merge confirmed in provisioner.py.
- sync-wave order -6/-5/-4/-2/-1/0 correct.
- edge-ingress init containers do NOT touch meshed services (no M1 risk).

---

## Progress Tracker (update after each commit)

- [x] **Step 1** — this authoritative tracker (recoverable anchor). No
      manifest changed.
- [x] **Step 2 (C1)** — DONE. control-plane-values.yaml
      defaultAllowPolicy -> all-unauthenticated (+ corrected comment).
- [x] **Step 3 (M1)** — DONE. config.linkerd.io/proxy-enable-native-
      sidecar="true" added beside linkerd.io/inject on EVERY meshed
      workload: gateway/execution/management/engine prod overlays;
      data-layer postgres/redis/chromadb; helm/mt-node; engine
      config.mtNode.scheduling.podAnnotations (runtime path); edge-
      ingress; envoy. Verified: chromadb HTTP probe proxy-bypassed; pg/
      redis exec probes unaffected; mt-node/runtime carry Vault Agent
      init so native sidecar is REQUIRED there. STILL TODO in Step 3:
      raise bootstrap README floor to K8s >= 1.29.
- [x] **Step 4 (C2/C4 services)** — DONE. linkerd-namespace egress +
      :4191 proxy-admin ingress on gateway/execution/management/engine
      base values. The initially-added :4143 ingress was REMOVED after
      the C4 correction (NetworkPolicy sees original app ports). All
      four prod overlays verified to NOT define a networkPolicy block,
      so base values are authoritative. Comments cleaned (no tracker
      tags).
- [x] **Step 5 (C2/C4 data-layer + edge/envoy)** — DONE. linkerd-ns
      egress + :4191 ingress on postgres/redis/chromadb (template),
      envoy, and edge-ingress. :4143 rules removed. chromadb HTTP probe
      confirmed proxy-bypassed.
- [x] **Step 6 (C3 + MED-1)** — DONE. Trust anchor wired via the
      control-plane Application helm.parameters (forceString sentinel
      that fails loud; operator overrides with --helm-set-file from
      Vault at promote). Dead linkerd-identity-trust-anchor ExternalSecret
      removed; stale ConfigMap comments corrected. Issuer ESO unchanged.
      LOW-1: issuer ESO sync-wave -5 is CORRECT (precedes control plane
      -4; the identity Application reconciles at -6 then its ESO applies)
      — no change needed; not a bug.
- [ ] **Step 7 (H3)** — linkerdPolicy.enabled: false in prod overlays +
      document the deliberate post-verification enable.
- [ ] **Step 8 (PRE-1 + MED-2)** — engine.namespace.create: false;
      fix the envoy HTTP/2 comment.
- [ ] **Step 9** — final reconciliation read-through + open ONE MR;
      update runbook (TIER9_ROLLOUT_RUNBOOK.md) to match every change.
