# Tier 9 — Microservice Security (Linkerd mTLS) — Progress Tracker

> **CHECKLIST Section 9 — Microservice Security.** Branch:
> `feat/tier9-microservice-security-mtls`. Single source of truth; the
> next engineer resumes from the **Progress Tracker** below.

---

## 1. Audit baseline (traced on `main`, verified)

| Tier 9 item | Pre-state | Action |
|---|---|---|
| mTLS between services (G9-1) | ⛔ plaintext: gateway↔execution/management gRPC use `insecure.NewCredentials()`; all→engine over `http://`. No cert-manager, no mesh, no internal CA (only edge Cloudflare AOP). | Linkerd automatic mTLS on every pod-to-pod hop. |
| Service identity verification | ⚠ app-layer only (JWT svc tokens + ONE shared `ENGINE_INTERNAL_SHARED_SECRET`). | Add per-pod SPIFFE identity (Linkerd) + per-service authz. |
| Service-specific permissions / zero-trust (G9-2/G9-3) | ⚠ shared secret = any holder fully trusted; trust rests on network position. | `Server` + `ServerAuthorization` per service so only the legitimate caller SA may reach each port. |
| Internal-only services / restricted ports / east-west (Section 3) | ✅ DONE — ClusterIP-only, Cloudflare-Tunnel edge, default-deny NetworkPolicies per chart. | LEAVE INTACT. Linkerd composes with NetworkPolicies (both enforce). |

## 2. Design decision (Option A: Linkerd)

- **Why Linkerd:** automatic mTLS for ALL meshed pod-to-pod traffic with
  near-zero application change, per-pod SPIFFE identity, and
  `Server`/`ServerAuthorization` for per-service L7 authz. Closes
  G9-1/G9-2/G9-3 without rewriting the Go/Python services.
- **Not Istio** (operationally heavy) / **not cert-manager+native gRPC
  TLS** (large code surface across 3 Go services + engine; the
  `insecure.NewCredentials()` call sites would all change and every
  service would need cert mounts + rotation).
- **No dashboard wiring.** Transport security is operator/GitOps
  (ArgoCD + helm + Linkerd), never admin/client dashboard controlled.
- **Composes with, does NOT replace, the existing NetworkPolicies.**

## 3. CRITICAL correctness constraints (must hold or production breaks)

1. **Sync order:** Linkerd CRDs -> control plane -> THEN workloads.
   ArgoCD sync-waves must install Linkerd before any meshed workload
   rolls, else injected pods start before the proxy/identity is ready.
2. **Skip-ports:** init-container `nc` readiness probes, and the
   data-layer (Postgres 5432 / Redis 6379 / Chroma 8000) — decide
   per-port whether Linkerd proxies or skips. Postgres/Redis CAN be
   meshed but the data-layer pods must ALSO be injected for mTLS to
   apply; if data-layer is NOT meshed, those ports must be in
   `config.linkerd.io/skip-outbound-ports` on the clients or the
   handshake fails. DECISION: mesh the data-layer too (full mTLS).
3. **mt-node runtime pods:** created by the engine HostedProvisioner
   (Python `kubernetes_asyncio`) at runtime — the generated StatefulSet
   pod template MUST carry `linkerd.io/inject: enabled` or those pods
   join un-meshed and the engine's ZmqClient :5555 dial breaks under
   ServerAuthorization. This is a CODE change in provisioner.py.
4. **Edge chain:** cloudflared -> edge-ingress -> envoy -> gateway must
   keep working; the tunnel inbound and envoy listener ports need
   correct skip/opaque handling.
5. **gRPC is HTTP/2:** Linkerd handles h2 natively (good for per-route
   authz), but the gateway↔execution↔management gRPC ports must be
   marked so Linkerd treats them as gRPC (default detection works;
   verify no `opaque-ports` needed).

## 4. Progress Tracker (update as each step lands)

- [x] **Step 1** — THIS tracker (recoverable anchor). No code changed.
- [ ] **Step 2 (read-only trace)** — deployments/argocd/* (root-app,
      appproject, per-svc Applications, sync-waves); every chart's
      deployment.yaml pod-annotation block + serviceaccount.yaml +
      service.yaml; _helpers label scheme; envoy + edge-ingress charts;
      data-layer chart; engine HostedProvisioner spec-builder. NO mesh
      files until this is complete and reported.
- [x] **Step 2 (read-only trace)** — DONE. Confirmed facts:
      * App-of-apps: root-app recurses `deployments/argocd/children/`;
        new mesh apps go there as child Applications.
      * Sync waves: data-layer **-2**, engine **-1**, gateway **0**.
        => Linkerd identity **-6**, CRDs **-5**, control plane **-4**.
      * `etradie` AppProject destinations did NOT allow linkerd ns and
        its resource whitelist lacked policy.linkerd.io + webhook/CRD
        kinds => created a SEPARATE `linkerd` AppProject; added
        policy.linkerd.io kinds to the `etradie` project for Step 3c.
      * No cert-manager on platform => identity via Vault+ESO
        (kubernetes.io/tls issuer Secret + trust-anchor), mirroring the
        existing secret pattern.
      * Child app format: helm source, releaseName, valueFiles,
        prune/selfHeal=false in prod, sync-wave annotation.
      * mt-node runtime pods built by engine HostedProvisioner
        (kubernetes_asyncio); pod template needs linkerd.io/inject
        => CODE change in provisioner.py (Step 3d). Spec-builder
        location still to be pinpointed in the 1759-line file.
- [x] **Step 3a** — DONE. linkerd-appproject.yaml; child apps
      linkerd-identity(-6) / linkerd-crds(-5) / linkerd-control-plane(-4);
      deployments/linkerd chart (identity ExternalSecret + trust anchor);
      control-plane-values.yaml; etradie AppProject policy.linkerd.io
      whitelist; Vault path etradie/platform/linkerd/<env> in terraform.
      Control plane only — NO workload injected yet (services unaffected).
- [x] **Step 3b (core)** — DONE for the 4 services + data-layer:
      * gateway/execution/management: linkerd.io/inject in
        values-production.yaml podAnnotations (gRPC h2 native, no
        opaque-ports).
      * engine: inject + opaque-ports 5555 (ZMQ to mt-node) +
        skip-outbound-ports 4317 (OTLP collector may be un-meshed).
      * data-layer (base values, all envs): postgres inject + opaque
        5432; redis inject + opaque 6379; chromadb inject (HTTP native).
      * FIXED PROD-BREAKER: namespace LimitRange (min 50m/64Mi) would
        reject Linkerd's default proxy-init (20Mi). Set proxyInit +
        proxy resources in control-plane-values.yaml to clear min.
        Verified ResourceQuota (32cpu/64Gi prod) has headroom.
- [x] **Step 3b (edge)** — DONE. envoy injected (HTTP/2 native to
      gateway). edge-ingress injected + skip-inbound-ports "443"
      (Cloudflare AOP mTLS terminates there; Linkerd must not touch the
      tunnel listener). Full chain CF->(AOP)->edge-ingress->(mTLS)->
      envoy->(mTLS)->gateway.
- [x] **Step 3b (mt-node)** — DONE via DATA path (no provisioner.py
      change): linkerd inject + opaque 5555 added to
      helm/engine config.mtNode.scheduling.podAnnotations (merged onto
      every runtime StatefulSet by HostedProvisioner) AND
      helm/mt-node/values.yaml podAnnotations (chart path). Verified the
      provisioner merges MT_NODE_POD_ANNOTATIONS_JSON -> merged_annotations.
- [ ] **Step 3b (cronjobs) NEXT** — OLD edge-decision note retained below:
      edge-ingress (Rust, :443 TLS + :9902), envoy (:8080 + :9901),
      cloudflared. These are in envoy-system / edge-ingress-system
      namespaces (NOT etradie-system). MUST read helm/edge-ingress +
      helm/envoy values + deployment templates FIRST. Likely approach:
      mesh envoy<->gateway hop; edge-ingress terminates external TLS so
      its :443 inbound is skip-inbound (Cloudflare AOP mTLS already
      covers edge). cloudflared is a 3rd-party image — inject only if it
      composes cleanly. DO NOT break the Cloudflare tunnel chain.
- [ ] **Step 3b (cronjobs)** — postgres-backup CronJob + mt-node
      snapshot CronJob: a meshed Job/CronJob pod never terminates
      because the proxy keeps running. MUST set
      `config.linkerd.io/proxy-enable-native-sidecar: "true"` (k8s>=1.28
      native sidecar) OR exclude these from the mesh
      (linkerd.io/inject: disabled). DECISION PENDING on cluster k8s
      version; default to inject:disabled for batch pods (they only
      talk to in-namespace postgres + offsite S3, already covered by
      NetworkPolicy) unless native sidecar is confirmed available.
- [ ] **Step 3d** — HostedProvisioner: stamp linkerd.io/inject + the
      same opaque-ports(5555) on the runtime mt-node StatefulSet pod
      template (code change). Locate _build_statefulset in
      provisioner.py first.
- [ ] **Step 3c** — per-service Server + ServerAuthorization (G9-2)
      AFTER all workloads confirmed meshed (linkerd viz edges = 100% TLS).
- [ ] **Step 3c** — Per-service Server + ServerAuthorization (per-service
      authz; closes G9-2) keyed to real SA names + ports.
- [ ] **Step 3d** — HostedProvisioner: stamp linkerd.io/inject on the
      runtime-provisioned mt-node StatefulSet pod template (code).
- [ ] **Step 3e** — Edge chain skip/opaque-port handling + verification.
- [ ] **Step 3f** — Docs + phased rollout runbook + finalise tracker.

## 5. Rollout posture (phased, safe)

Linkerd injection is enabled per-namespace/per-workload. Roll mesh in
before flipping ServerAuthorization to a default-deny (`authz` policy
must start permissive, then tighten) so a missed annotation does not
blackhole the money path. ServerAuthorization is added AFTER every
workload is confirmed meshed and mTLS'd (linkerd `edges`/`stat` show
100% TLS), exactly like the Tier 8 warn-only->enforce rollout.

## 6. Definition of done

- `linkerd viz edges` shows mTLS (√) on EVERY internal edge:
  gateway↔execution, gateway↔management, {gateway,execution,management}→engine,
  engine→{postgres,redis,chroma,mt-node}.
- Per-service ServerAuthorization: only execution's SA may hit
  execution gRPC; only gateway's SA may hit engine /internal/*; etc.
- Runtime mt-node pods join the mesh automatically.
- Edge chain unaffected. NetworkPolicies intact. No dashboard change.
- No dead manifests, no placeholder values, no duplicate annotations.
