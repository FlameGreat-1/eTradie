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
- [ ] **Step 3a** — Linkerd CRDs + control-plane (+ linkerd-viz optional)
      as ArgoCD Applications at a sync-wave BEFORE workloads; AppProject
      whitelist for linkerd.io CRDs + namespaces.
- [ ] **Step 3b** — Namespace/workload injection annotations per chart
      (etradie-system + data-layer + edge-ingress namespaces), one chart
      per commit, with correct port config annotations.
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
