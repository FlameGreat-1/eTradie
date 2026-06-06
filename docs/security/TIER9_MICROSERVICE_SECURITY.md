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
- [ ] **Step 3b (NEXT)** — Per-workload injection. DECISION: drive via
      each chart's existing `.Values.podAnnotations` (every deployment.yaml
      already renders `template.metadata.annotations` from podAnnotations
      — confirmed in execution/deployment.yaml). Add `linkerd.io/inject:
      enabled` to podAnnotations in values-production.yaml of: gateway,
      execution, management, engine, data-layer, edge-ingress, envoy,
      mt-node (chart). Per-chart Postgres/Redis opaque-port handling via
      `config.linkerd.io/opaque-ports` ONLY where a service SPEAKS those
      protocols. One chart per commit. STILL TO READ before editing:
      each chart's deployment.yaml annotation block (engine/gateway/
      management/data-layer/edge-ingress/envoy) to confirm podAnnotations
      is rendered; data-layer statefulset annotation block.
- [ ] **Step 3b-verify** — confirm gRPC ports need no opaque-ports
      (h2 native) and init-container `nc` checks still pass under proxy.
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
