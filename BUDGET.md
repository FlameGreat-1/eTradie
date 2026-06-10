
#### TABLE 1 — EVERYTHING ON (observability + monitoring + mesh + Jaeger), shipped production replica counts

Reserved = request × min replicas. All app/data/observability numbers verified from values files; Linkerd marked (est).

| Component | Req CPU/pod | Req Mem/pod | Replicas | Reserved CPU | Reserved Mem |
|---|---|---|---|---|---|
| edge-ingress | 1 | 1Gi | 5 | 5.0 | 5Gi |
| cloudflared (in edge) | 100m | 64Mi | 2 | 0.2 | 0.13Gi |
| envoy | 2 | 4Gi | 5 | **10.0** | **20Gi** |
| gateway | 1 | 1Gi | 5 | 5.0 | 5Gi |
| engine | 1 | 2Gi | 3 | 3.0 | 6Gi |
| execution | 500m | 512Mi | 3 | 1.5 | 1.5Gi |
| management | 500m | 512Mi | 1 | 0.5 | 0.5Gi |
| billing | 200m | 384Mi | 3 | 0.6 | 1.15Gi |
| postgres | 500m | 1Gi | 1 | 0.5 | 1Gi |
| postgres backup | 250m | 256Mi | 1 | 0.25 | 0.25Gi |
| redis | 250m | 768Mi | 1 | 0.25 | 0.75Gi |
| chromadb | 500m | 1Gi | 1 | 0.5 | 1Gi |
| Loki | 250m | 512Mi | 1 | 0.25 | 0.5Gi |
| Promtail (per node) | 100m | 128Mi | 1+ | 0.1 | 0.13Gi |
| OTel collector | 200m | 256Mi | 2 | 0.4 | 0.5Gi |
| Jaeger | 200m | 512Mi | 1 | 0.2 | 0.5Gi |
| Linkerd control-plane (est) | — | — | ~3 HA | ~1.5 | ~1.5Gi |
| Linkerd viz + its Prometheus (est) | — | — | ~7 | ~1.5 | ~2Gi |
| Linkerd proxy sidecars (est, ~28 app pods) | 100m | 20Mi | 28 | ~2.8 | ~0.6Gi |
| **TOTAL (0 users)** | | | | **≈ 34.8 CPU** | **≈ 48Gi** |
| **+ each MT user** (+ proxy + watchdog) | | | | +2.6 | +2.1Gi |

**Verdict for Contabo 8 vCPU / 24GB:** Impossible. ~35 CPU / 48GB reserved before one user. **Does not fit on staging or production on this box.** This profile needs a multi-node cluster.

#### TABLE 2 — EVERYTHING OFF (no observability, no monitoring, no mesh, no Jaeger), tuned to FIT the current Contabo (8 vCPU / 24GB / 200GB)

This is a deliberately reduced **single-node** profile: replicas cut to 1, envoy/edge-ingress shrunk hard (they don't need 2 CPU/4Gi for a handful of users), mesh + observability not deployed.

**STAGING on Contabo (target ~3–5 test users):**

| Component | Req CPU | Req Mem | Limit CPU | Limit Mem | Replicas | Reserved CPU | Reserved Mem |
|---|---|---|---|---|---|---|---|
| edge-ingress | 150m | 256Mi | 750m | 512Mi | 1 | 0.15 | 0.25Gi |
| envoy | 250m | 256Mi | 1 | 512Mi | 1 | 0.25 | 0.25Gi |
| gateway | 250m | 256Mi | 1 | 512Mi | 1 | 0.25 | 0.25Gi |
| engine | 250m | 512Mi | 1 | 1Gi | 1 | 0.25 | 0.5Gi |
| execution | 150m | 256Mi | 500m | 512Mi | 1 | 0.15 | 0.25Gi |
| management | 150m | 256Mi | 500m | 512Mi | 1 | 0.15 | 0.25Gi |
| billing | 150m | 256Mi | 500m | 512Mi | 1 | 0.15 | 0.25Gi |
| postgres | 250m | 512Mi | 1 | 1Gi | 1 | 0.25 | 0.5Gi |
| redis | 100m | 256Mi | 500m | 512Mi | 1 | 0.1 | 0.25Gi |
| chromadb | 250m | 512Mi | 1 | 1Gi | 1 | 0.25 | 0.5Gi |
| **Staging floor** | | | | | | **≈ 2.0 CPU** | **≈ 3.25Gi** |
| each MT user | 300m | 512Mi | 1 | 768Mi | 1/user | +0.3 | +0.5Gi |

Staging at 5 users ≈ **3.5 CPU / 5.75Gi reserved** → fits easily in 8/24.

**PRODUCTION on Contabo (target ~5 real users):**

| Component | Req CPU | Req Mem | Limit CPU | Limit Mem | Replicas | Reserved CPU | Reserved Mem |
|---|---|---|---|---|---|---|---|
| edge-ingress | 300m | 384Mi | 1 | 768Mi | 1 | 0.3 | 0.38Gi |
| cloudflared | 100m | 64Mi | 500m | 256Mi | 1 | 0.1 | 0.06Gi |
| envoy | 500m | 512Mi | 1.5 | 1Gi | 1 | 0.5 | 0.5Gi |
| gateway | 500m | 512Mi | 1.5 | 1Gi | 1 | 0.5 | 0.5Gi |
| engine | 500m | 1Gi | 2 | 2Gi | 1 | 0.5 | 1Gi |
| execution | 300m | 512Mi | 1 | 1Gi | 1 | 0.3 | 0.5Gi |
| management | 300m | 512Mi | 1 | 1Gi | 1 | 0.3 | 0.5Gi |
| billing | 200m | 384Mi | 1 | 768Mi | 1 | 0.2 | 0.38Gi |
| postgres | 500m | 1Gi | 2 | 2Gi | 1 | 0.5 | 1Gi |
| redis | 250m | 512Mi | 1 | 1Gi | 1 | 0.25 | 0.5Gi |
| chromadb | 300m | 512Mi | 1 | 1Gi | 1 | 0.3 | 0.5Gi |
| **Production floor** | | | | | | **≈ 3.75 CPU** | **≈ 5.8Gi** |
| each MT user | 500m | 1Gi | 1.5 | 2Gi | 1/user | +0.5 | +1Gi |

Production at 5 users ≈ **6.25 CPU / 10.8Gi reserved** → fits in 8/24 with headroom for burst. **Disk**: trim postgres/chromadb PVCs to 16Gi, drop the on-cluster 64Gi backup (use offsite B2), MT PVCs at 4Gi → fits 200GB.

**Verdict for Contabo:** ✅ Both staging and production FIT with everything-off + single-node lean, for ~5 users. Production CPU burst is the limiter beyond ~5–6 users.

#### TABLE 3 — FULL BALANCED OPERATION (everything ON, normal/healthy) on a properly-sized future VPS

This is the shipped production posture (Table 1) running normally with room to burst and serve a real user base (target ~30–50 MT users).

| Layer | Reserved CPU | Reserved Mem | Notes |
|---|---|---|---|
| Full platform floor (Table 1 total) | ~35 | ~48Gi | all services + data + observability + mesh |
| Burst headroom (HPAs scale up) | +~20 | +~30Gi | engine→6, gateway→10, envoy→10, edge→ up |
| 30 MT users (×2.6 CPU / 2.1Gi) | +78 | +63Gi | per-user, can't co-locate >1/node |
| **Approx total at 30 users, balanced** | **≈ 113 CPU** | **≈ 111Gi** | + ~500Gi disk |

**Recommended future infrastructure for full balanced operation:** This is explicitly a **multi-node cluster**, the shipped config's anti-affinity *forbids* stacking replicas on one node. Realistic shape:
- **3–4 nodes** of roughly **8 vCPU / 32GB each** for the platform/control plane + observability + mesh (~32 vCPU / 128GB aggregate), **plus**
- **a scalable MT node pool**: since each production MT user wants ~1.5 CPU/2Gi burst and can't share a node with another MT pod under the current `required` anti-affinity, you either relax that to `preferred` (recommended, lets ~4 MT pods share an 8-core node) or provision ~1 small node per few users.
- With anti-affinity relaxed to `preferred` + the leaner MT sizing, ~30 users fit on roughly **a 32 vCPU / 96GB pool** for MT, on top of the platform pool.

So **full balanced = ~5–7 VPS nodes of 8 vCPU/32GB, or a couple of large 16–32 core boxes**, not one Contabo VPS 30.

#### Honest caveats (where I'm certain vs estimating)

- **Certain (read from repo):** edge-ingress, envoy, gateway, engine, execution, management, billing, postgres, redis, chromadb, Loki, Promtail, OTel, Jaeger, cloudflared. envoy's 2 CPU/4Gi × 5 is the single biggest line and is verified.
- **Estimated:** Linkerd control-plane + viz resource requests (live in upstream Helm charts not in your repo; your files only set replica counts and HA mode). The ~5–6 CPU / ~4Gi I attributed to the full mesh is an informed industry estimate. Since you'd run mesh OFF on Contabo, it doesn't affect Tables 2.
- **cert-manager / ESO / ArgoCD / Prometheus-Operator:** the repo references ESO (`vault-backend` ClusterSecretStore), ArgoCD, and a `monitoring` namespace Prometheus+Grafana, but their sizing is **not in your repo** (they're external platform installs). For Table 1/3 add a rough **+2–4 CPU / +4–8GB** for these. I flag this rather than invent exact numbers.
- All app numbers are **declared requests, not measured.** Your soak still sets the real MT/engine values, which could lower Tables 2/3 further.

#### Bottom line

1. **Everything ON: needs a multi-node cluster (~35 CPU/48GB floor). Will NOT run on one Contabo VPS 30.**
2. **Everything OFF + single-node lean: FITS the Contabo VPS 30 for ~5 users**, both staging and production (Table 2).
3. **Full balanced (everything on, real users): ~5–7× 8-core/32GB nodes or equivalent**, with MT anti-affinity relaxed.








#### TABLE 4 — BALANCED STAGING (everything reasonable for staging, on a right-sized VPS)

Staging doesn't need the mesh or full HA. Recommended single box: **Contabo Cloud VPS (or similar) 16 vCPU / 32GB / 400GB**. Replicas kept low (1–2), observability light (Loki+Promtail+OTel+Jaeger ON, mesh OFF).

| Component | Req CPU | Req Mem | Limit CPU | Limit Mem | Replicas | Reserved CPU | Reserved Mem |
|---|---|---|---|---|---|---|---|
| edge-ingress | 250m | 384Mi | 1 | 768Mi | 1 | 0.25 | 0.38Gi |
| envoy | 500m | 512Mi | 1.5 | 1Gi | 1 | 0.5 | 0.5Gi |
| gateway | 500m | 512Mi | 1.5 | 1Gi | 2 | 1.0 | 1Gi |
| engine | 500m | 1Gi | 2 | 2Gi | 2 | 1.0 | 2Gi |
| execution | 300m | 512Mi | 1 | 1Gi | 1 | 0.3 | 0.5Gi |
| management | 300m | 512Mi | 1 | 1Gi | 1 | 0.3 | 0.5Gi |
| billing | 200m | 384Mi | 1 | 768Mi | 1 | 0.2 | 0.38Gi |
| postgres | 500m | 1Gi | 2 | 2Gi | 1 | 0.5 | 1Gi |
| redis | 250m | 512Mi | 1 | 1Gi | 1 | 0.25 | 0.5Gi |
| chromadb | 300m | 512Mi | 1 | 1Gi | 1 | 0.3 | 0.5Gi |
| Loki | 250m | 512Mi | 1 | 1Gi | 1 | 0.25 | 0.5Gi |
| Promtail | 100m | 128Mi | 500m | 384Mi | 1 | 0.1 | 0.13Gi |
| OTel collector | 200m | 256Mi | 500m | 512Mi | 1 | 0.2 | 0.25Gi |
| Jaeger (in-memory, no PVC) | 200m | 256Mi | 1 | 1Gi | 1 | 0.2 | 0.25Gi |
| **Staging floor** | | | | | | **≈ 5.65 CPU** | **≈ 9.9Gi** |
| each MT user | 300m | 512Mi | 1 | 768Mi | 1/user | +0.3 | +0.5Gi |

At ~10 staging users: ~8.65 CPU / ~14.9Gi reserved → **fits 16 vCPU / 32GB comfortably** with burst room. Disk: small PVCs (postgres 16Gi, chromadb 16Gi, Loki 20Gi, MT 4Gi) fit 400GB. Mesh OFF (staging doesn't need mTLS verification load).

#### TABLE 5 — BALANCED PRODUCTION (everything ON: observability + monitoring + mesh + Jaeger, healthy HA)

This is the shipped production posture running **normally with burst headroom and HA**, the config an operator switches to on real infrastructure. This is **multi-node** (the anti-affinity requires it). Recommended: **a Kubernetes cluster of 4 worker nodes, each 16 vCPU / 32GB / 200GB NVMe** (≈ 64 vCPU / 128GB aggregate) for platform+observability+mesh, **plus a scalable MT node pool** sized to user count.

| Component | Req CPU | Req Mem | Limit CPU | Limit Mem | Min replicas | Reserved CPU | Reserved Mem |
|---|---|---|---|---|---|---|---|
| edge-ingress | 1 | 1Gi | 2 | 2Gi | 3 | 3.0 | 3Gi |
| cloudflared | 100m | 64Mi | 500m | 256Mi | 2 | 0.2 | 0.13Gi |
| envoy | 1 | 2Gi | 4 | 8Gi | 3 | 3.0 | 6Gi |
| gateway | 1 | 1Gi | 2 | 2Gi | 3 | 3.0 | 3Gi |
| engine | 1 | 2Gi | 2 | 4Gi | 3 | 3.0 | 6Gi |
| execution | 500m | 512Mi | 2 | 1Gi | 3 | 1.5 | 1.5Gi |
| management | 500m | 512Mi | 2 | 1Gi | 1 | 0.5 | 0.5Gi |
| billing | 200m | 384Mi | 1 | 768Mi | 3 | 0.6 | 1.15Gi |
| postgres | 1 | 2Gi | 2 | 4Gi | 1 | 1.0 | 2Gi |
| postgres backup | 250m | 256Mi | 1 | 512Mi | 1 | 0.25 | 0.25Gi |
| redis | 250m | 768Mi | 1 | 1.5Gi | 1 | 0.25 | 0.75Gi |
| chromadb | 500m | 1Gi | 2 | 2Gi | 1 | 0.5 | 1Gi |
| Loki | 250m | 512Mi | 2 | 2Gi | 1 | 0.25 | 0.5Gi |
| Promtail (per node, ~4) | 100m | 128Mi | 500m | 384Mi | 4 | 0.4 | 0.5Gi |
| OTel collector | 200m | 256Mi | 1 | 1Gi | 2 | 0.4 | 0.5Gi |
| Jaeger (durable Badger) | 200m | 512Mi | 2 | 2Gi | 1 | 0.2 | 0.5Gi |
| Linkerd control-plane (est) | — | — | — | — | 3 HA | ~1.5 | ~1.5Gi |
| Linkerd viz + Prometheus (est) | — | — | — | — | ~7 | ~1.5 | ~2Gi |
| Linkerd proxy sidecars (est, ~28 pods) | 100m | 20Mi | — | — | 28 | ~2.8 | ~0.6Gi |
| **Production floor (0 users)** | | | | | | **≈ 24 CPU** | **≈ 32Gi** |
| each MT user (proxy+watchdog incl.) | ~700m | ~1.1Gi | 1.5+ | 2Gi+ | 1/user | +0.7 | +1.1Gi |

Floor ~24 CPU / 32GB reserved. With burst (HPAs to max) the platform can demand ~50+ CPU. At 30 MT users add ~21 CPU / ~33GB. So a **64 vCPU / 128GB aggregate cluster (4× 16/32 nodes) holds the platform + observability + mesh + ~30 users at healthy reserved levels with burst headroom.** Scale the MT node pool linearly beyond that (~10 users per extra 16/32 node with anti-affinity relaxed to `preferred`).

**Add for external platform installs not in your repo** (cert-manager, ESO, ArgoCD, kube-prometheus+Grafana): budget **+3–5 CPU / +6–10GB** on the platform pool.

#### Summary of what runs where

| Profile | Mesh | Observability | Replicas | VPS / cluster | Fits? |
|---|---|---|---|---|---|
| **Table 1** (shipped prod, everything on) | ON | ON | shipped (3/5/5...) | multi-node only | ❌ not on 1 VPS |
| **Table 2** (contabo lean, all off) | OFF | OFF | 1 each | 1× Contabo 8/24 | ✅ ~5 users |
| **Table 4** (balanced staging) | OFF | light ON | 1–2 | 1× 16 vCPU/32GB | ✅ ~10 users |
| **Table 5** (balanced production) | ON | ON | HA (3 each) | 4× 16 vCPU/32GB cluster | ✅ ~30 users, scale MT pool |

#### Exact VPS recommendations for the operator to target

- **Staging:** one **16 vCPU / 32GB / 400GB** VPS (e.g. Contabo Cloud VPS L/XL tier). Run Table 4.
- **Production (balanced, full stack):** a **4-node K8s cluster, each 16 vCPU / 32GB / 200GB NVMe** (≈ 64 vCPU / 128GB / 800GB total), plus a **scalable MT worker pool** (add 16/32 nodes as users grow, ~10 users/node with `preferred` anti-affinity). Run Table 5.

#### Honest caveats

- Tables 4 and 5 are **starting allocations to confirm with your soak**, not measured truth. envoy especially: I lowered it from the shipped 2 CPU/4Gi to 1 CPU/2Gi request in Table 5 because 2/4 × 5 was sized for very high TLS throughput you won't have early; verify under load.
- Linkerd control-plane/viz rows remain **estimates** (upstream chart sizing).
- cert-manager/ESO/ArgoCD/kube-prometheus are **not in your repo**; their footprint is added as a flagged allowance, not a verified number.





# Straight answer: No, the cost is NOT because of K8s/Helm

The cost is because **MetaTrader 5 is a Windows desktop app**. To run it on Linux servers, you need Wine + Xvfb (a fake screen) + a full Windows graphics stack — per user. **That's the 2 CPU + 2 GB minimum, and it doesn't matter what orchestrates it.**

If you wrote a pure Go/Python orchestrator that spawned MT5 processes directly with `os.exec`, **each MT5 process would still need 2 CPU + 2 GB**. K8s adds maybe 50 MiB of overhead per Pod for the kubelet. That's it. The cost is **the app, not the platform**.

#### What if we ditched K8s and used pure Go/Python?

Let's be honest about both paths.

**Pure Go/Python orchestrator (no K8s):**
- You'd write code that runs `docker run --name user-123-mt5 ...` for each user.
- You'd write code to restart crashed containers (we have this — it's the watchdog).
- You'd write code to assign ports, manage networks, mount volumes per user.
- You'd write code to handle a server reboot and bring all 100 users back up.
- You'd write code to load-balance across multiple servers when one fills up.
- You'd write code to roll out a new MT5 image without dropping users.
- You'd write code to handle secrets (broker passwords) safely.
- You'd write code to monitor each container's health and alert on failures.
- You'd write code to enforce CPU/RAM limits per container so one user can't starve others.
- You'd write code to do TLS, DNS, and service discovery between engine ↔ user Pods.

**You'd end up reinventing Kubernetes, badly, in 6 months of work.** That's literally what K8s is — a Go program that does all of the above. Google wrote it because they got tired of writing it from scratch for every project.

#### What K8s/Helm actually buy you

Six concrete things, in plain English:

**1. Self-healing.** If a user's MT5 Pod crashes at 3 AM, K8s restarts it. If the whole server dies, K8s moves all Pods to a healthy server. Without K8s, you write a daemon to do this and pray it doesn't have bugs.

**2. Resource isolation.** When you tell K8s "this Pod gets 2 CPU + 2 GB," the Linux kernel enforces it via cgroups. User A's MT5 going crazy cannot slow down user B's MT5. Without K8s, one runaway user kills everyone on the box.

**3. Multi-server scaling.** When your one VPS fills up, you add a second VPS to the cluster and K8s automatically schedules new users to whichever server has room. Without K8s, you write a custom scheduler — and it will be worse than Google's.

**4. Zero-downtime deploys.** When you ship a new mt-node image, K8s replaces old Pods one at a time. Users stay connected to working Pods while the rest update. Without K8s, you either drop all users during a deploy or write rolling-update logic yourself.

**5. Declarative config (this is what Helm does).** Helm lets you say "this environment has 8 GB engine, 100 users, 4Gi PVCs." One file, version-controlled, reproducible. Without Helm, you have shell scripts and a Notion page titled "How to deploy production (DO NOT LOSE)."

**6. Secrets, networking, monitoring already wired.** Vault integration, Prometheus scraping, network policies, service mesh — all standard K8s primitives. Without K8s, you wire each one manually and they don't talk to each other cleanly.

#### Where you're right to push back

K8s is **overkill for a 10-user MVP** running on one VPS. For that stage, `docker-compose` + a single Go supervisor program would genuinely be simpler and run on cheaper hardware. The complexity tax of K8s is real — operators, control plane RAM (~1-2 GB), and the learning curve.

**But:** you already paid that tax. The chart is written, the provisioner works, the watchdog is in place, the audit is done. Ripping it out to save £20/month on infrastructure would cost you 2-3 months of rewrite and lose everything in points 1-6 above.
