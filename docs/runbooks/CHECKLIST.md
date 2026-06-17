No — **you do NOT need to enable the mesh before users start provisioning MT terminals.** Hosted-MT provisioning works today on staging exactly as it is. Let me explain clearly what the mesh actually does and what its current state means for you.

## What Linkerd mesh actually does — in plain English

Imagine your cluster is a city with many buildings (services: gateway, engine, postgres, redis, chromadb, billing, etc.). Inside the city, these buildings constantly talk to each other — gateway sends messages to engine, engine asks postgres for data, billing emails webhooks to gateway.

**Without a service mesh**, those messages travel through plain unmarked roads. Anyone with access to the road network (anyone inside the city walls) can read the contents of any message, or impersonate a building.

**With Linkerd mesh**, each building gets a small armored mailroom attached to it (the `linkerd-proxy` sidecar container that sits next to each app container). Every message in and out has to go through that mailroom first. The mailroom does four things automatically:

### 1. mTLS encryption — every conversation is sealed

Every message between two meshed buildings is wrapped in a tamper-proof envelope (mutual TLS encryption). Even if someone got into the city, they could see envelopes moving around but they couldn't read what's inside. This is the **encryption** benefit.

Concrete example: when meshed gateway sends a query to meshed postgres, the bytes on the wire are encrypted. If an attacker dumped network traffic on the VPS, they'd see encrypted noise, not the SQL query containing user credentials.

### 2. mTLS identity verification — every building checks who they're talking to

Each mailroom has a cryptographic ID badge (the Linkerd identity cert). When mailroom A sends a message to mailroom B, B verifies A's badge before opening the envelope. If a fake building tries to impersonate gateway and send a fraudulent query to postgres, postgres's mailroom rejects the connection because the badge doesn't match.

Concrete example: if some attacker pod somehow got admin in the cluster and tried to call `engine`'s `/internal/broker/*` endpoint pretending to be `gateway`, engine's mailroom would say "your badge says you're attacker-pod, not gateway, request rejected."

### 3. Observability — every message is logged and counted

The mailrooms record statistics: how many requests went where, how long each took, which ones failed. This feeds into Prometheus + Grafana so you can see traffic patterns and find slow services.

Concrete example: you can see at a glance "gateway → engine is averaging 50ms p99, gateway → postgres is averaging 5ms, gateway → billing is timing out 10% of the time."

### 4. Per-route authorization — fine-grained access policy

With Linkerd `Server` and `AuthorizationPolicy` resources, you can say "only the gateway pod is allowed to call engine's `/internal/broker/account_info` endpoint, and only execution and management can call engine's `/internal/broker/place_order`." Anything else gets rejected at the proxy layer before reaching the application code.

(This is the `linkerdPolicy.enabled` setting in the chart values — currently OFF in staging, per BUDGET.md Table 2B. Enabling per-route authz is a separate hardening step after mesh is healthy.)

## Where the mesh stands right now in your cluster

This is the picture:

| Workload | Mesh state | Why |
|---|---|---|
| `postgres-0` | ✅ Meshed (2 containers + 1 sidecar = 3/3) | Phase 10 |
| `redis-0` | ✅ Meshed (3/3) | Phase 10 |
| `chromadb-0` | ✅ Meshed (2/2) | Phase 10 |
| `edge-ingress` | ✅ Meshed (2/2) | Phase 10 |
| `etradie-envoy` | ✅ Meshed (2/2) | Phase 10 |
| `etradie-engine` | ❌ Mesh disabled (1/1) | Phase 10.6 staging-only — explained below |
| `etradie-gateway` | ❌ Mesh disabled (1/1) | same |
| `etradie-execution` | ❌ Mesh disabled (1/1) | same |
| `etradie-management` | ❌ Mesh disabled (1/1) | same |
| `etradie-billing` | ❌ Mesh disabled (1/1) | same |
| `cloudflared` | ⏸ Never meshed (intentional) | dials Cloudflare edge over QUIC; mesh would break QUIC |
| Linkerd control plane (destination, identity, proxy-injector) | ✅ Running | The mesh's own brain |

## Why those 5 services have mesh disabled (and why it's fine on staging)

During the Phase 10.6 bring-up, there was a cold-start race condition: when an app pod started up, the mesh proxy and the app container both went up at roughly the same time. The app would try to dial postgres in its first ~30ms of life, and the proxy wasn't fully warmed up yet for outbound. The dial would fail with "connection reset by peer," the app would crash, Kubernetes would restart it, the race would repeat.

Rather than block the whole staging deploy on fixing this race, the prior operator (you, with my help) disabled mesh injection on those 5 services as a temporary unblock. Everything else stayed meshed.

This is documented in `PHASE10.6-MESH-DISABLED-CHECKPOINT.md` with the exact fix that should land before production (add a retry-with-backoff loop in each service's startup code so it tolerates the first ~5 seconds of "connection reset" before declaring failure).

## What you LOSE with those 5 services mesh-disabled

Reading from `PHASE10.6-MESH-DISABLED-CHECKPOINT.md`:

> *"Service-identity mTLS on east-west calls leaving the 5 services. Their outbound to postgres / redis / chromadb / each other is plaintext on the pod network. Inside the K3s cluster network namespace this is still gated by ufw + NetworkPolicies, but the cryptographic identity binding the mesh provides is absent for these hops."*

In other words: when gateway-without-mesh talks to postgres-with-mesh, the gateway's side of the conversation is plaintext. The bytes are still safe because:

1. They travel over the K3s pod network, which only exists inside one VPS box
2. That VPS's `ufw` firewall denies all inbound traffic except SSH (port 22)
3. NetworkPolicies inside the cluster enforce who-can-talk-to-whom at the IP level
4. Postgres has TLS on at the application layer (Phase 10.6 postgres TLS fix), so the actual gateway→postgres SQL queries ARE encrypted by libpq even without mesh

So defense-in-depth is preserved. What's missing is the cryptographic identity binding (the badge check) and the observability for those 5 services. Acceptable for staging; not acceptable for production at scale.

## Why this has NOTHING to do with hosted-MT provisioning

The hosted-MT provisioning flow is:

1. User clicks "Add Hosted MT Broker" in the dashboard
2. SPA POSTs to gateway → engine (gateway is one of the 5 disabled-mesh services, but engine reaching the user's request still works)
3. Engine's `HostedProvisioner` calls the K8s API to create a per-tenant StatefulSet `etradie-mt-<id>`
4. The NEW per-tenant pod is created **with mesh injection enabled** (the `mt-node` chart sets `linkerd.io/inject: enabled` on its pod template)
5. The user's MT terminal runs inside that meshed Wine pod
6. Engine dials `<tenant-pod>.etradie-system.svc:5555` to talk to the EA running inside

The per-tenant pods are **independent** of the 5 disabled services. They have their own mesh injection setting in `helm/mt-node/values.yaml`, which is `linkerd.io/inject: enabled` (with `opaque-ports: "5555"` so the ZMQ TCP traffic tunnels through the mesh raw rather than getting parsed as HTTP).

The engine still creates the StatefulSet successfully (mesh-disabled engine talks to the K8s API directly via the ServiceAccount token — no mesh dependency). The tenant pod still mTLS's the rest of the meshed services it needs to reach (postgres for credential decryption, redis for state). Everything works.

## The actual answer to your question

**Hosted-MT user provisioning works today, with the current mesh-disabled posture on the 5 services.** A user can sign up via Google or username/password right now, add a hosted broker connection, and the engine will provision their per-tenant Wine pod with mesh on. The pod will mTLS-talk to postgres+redis+chromadb cleanly.

The mesh-disabled state on the 5 services is **operational debt for production cutover**, not a blocker for hosted-MT or any other user feature. The platform is fully functional for users.

## When to actually fix the mesh-disabled state

Two scenarios warrant fixing it:

**Scenario 1 — before promoting staging to production.** Production-grade deploys should have mesh on across the board. The retry-with-backoff fix in each service's startup code goes into a sprint, gets tested in staging, then mesh gets re-enabled on the 5 services with `kubectl rollout restart`. This is the Phase 10.6 closeout TODO that's been on the list.

**Scenario 2 — you decide to harden staging itself.** No urgency for this; staging is a non-production environment by definition. But if you're using staging to soak-test multi-user scenarios, having full mesh telemetry on every hop would help you find perf issues.

Neither scenario blocks today's hosted-MT user flow. Per `PHASE10.6-MESH-DISABLED-CHECKPOINT.md` step 5 in the re-enable plan:

> *"Production overlay sanity. Confirm helm/{engine,gateway,execution,management,billing}/values-production.yaml does NOT carry linkerd.io/inject: \"disabled\". Production must be mesh-on end-to-end."*

Production deploys will always start mesh-on (the chart base is `linkerd.io/inject: enabled`, only the staging overlays carry the disable). When you eventually deploy production, those services will be meshed from minute one.

## TL;DR

- Mesh is a security/observability layer that wraps service-to-service traffic in encryption + identity verification
- Currently 5 services have mesh OFF on staging (intentional, temporary, documented)
- Hosted-MT provisioning is fully functional with current state — no mesh enablement needed first
- Mesh re-enable is a "before-production-cutover" task, not a "before-hosted-MT-works" task
- The per-tenant Wine pods that get created when a user provisions hosted MT are themselves meshed (their chart has mesh ON)

You can proceed with whatever you want next — hosted-MT user provisioning testing, production deploy planning, or just leaving staging running for users to start using. Nothing about the mesh state blocks any of these.