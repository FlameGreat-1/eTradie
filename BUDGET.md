
# 🔴 VERDICT: 4 vCPU / 8 GB RAM / 75 GB NVMe is **NOT enough** to run everything on one machine

This is a candid "won't fit" verdict, not a soft "tight squeeze".

## The actual resource budget your codebase declares

I read the actual memory + CPU limits from your `docker-compose.yml`. These are what the application asks for, not guesses:

### Core stack (always-on services)

| Service | Memory (declared limit) | CPU (declared) | Notes |
|---|---|---|---|
| postgres | 256 MB | (shared) | Will need more under real load — see below |
| redis | 128 MB | (shared) | OK |
| chromadb | (no limit!) | (no limit!) | **Vector DB — typically 500MB-2GB depending on knowledge corpus** |
| engine (Python) | **2 GB** | **2.0 vCPU** | Heaviest service. Has torch, transformers, RAG |
| gateway (Go) | 256 MB | (shared) | |
| execution (Go) | 256 MB | (shared) | |
| management (Go) | 256 MB | (shared) | |
| prometheus | 128 MB | (shared) | |
| jaeger | 256 MB | (shared) | |
| grafana | 256 MB | (shared) | |
| **Core subtotal** | **~4.5 GB declared + ~1 GB chromadb + OS overhead** | **2+ vCPU dedicated to engine alone** | |

### MT trading containers (one per active user — read carefully)

Your `docker/mt-node/Dockerfile` builds a **per-user MetaTrader container** with:
- Ubuntu 24.04 base
- Wine64 + Wine32 (32-bit i386 architecture added)
- Xvfb virtual framebuffer
- MetaTrader 4 AND MetaTrader 5 both installed via Wine
- ZeroMQ EA running on port 5555

**Each MT container realistic footprint (Wine + Xvfb + terminal64.exe + EA):**
- RAM: **400-800 MB per active MT instance** (Wine + Xvfb headless MT is famously heavy)
- CPU: 0.2-0.5 vCPU steady-state, spikes higher on indicator recalc
- Disk: ~2 GB per MT container image + per-user terminal data
- Network: per-tick stream from broker

### Frontend (cotradee)

The SPA is **NOT in docker-compose**. It's a Vite/React build that produces static files. Two deployment options based on what I see in `deployments/cloudflare/`:

- **Option A (recommended, free):** Build with `npm run build`, host on Cloudflare Pages / Vercel / Netlify. Zero VPS cost.
- **Option B:** Add nginx container to serve `dist/` → ~30 MB RAM.

Your edge-ingress/envoy chain (the `--profile edge` services) adds another **~3 GB RAM** if you enable it — but that's optional and meant for cluster deployments.

## Hard math against your 4 vCPU / 8 GB / 75 GB resource

### RAM budget
```
OS + Docker daemon ........................  ~800 MB
postgres (under real load, not 256 MB limit)  ~512 MB
redis ......................................  ~128 MB
chromadb (knowledge embeddings loaded) .....  ~800 MB to 1.5 GB
engine (LLM client + torch + RAG + 5 cycles)  ~2 GB (the declared limit)
gateway ....................................  ~256 MB
execution ..................................  ~256 MB
management .................................  ~256 MB
prometheus + jaeger + grafana ..............  ~640 MB
─────────────────────────────────────────────────────
CORE STACK SUBTOTAL ........................  ~5.6 GB to 6.4 GB

That leaves ~1.6 GB to ~2.4 GB for MT containers.

Per MT container ........................... ~500 MB
Max MT containers fittable ................. 3-4 USERS MAX
```

### CPU budget
```
4 vCPU total
engine alone reserves 2.0 vCPU (50% of host)
Each MT instance: 0.2-0.5 vCPU
Postgres + everything else: ~1 vCPU under load
─────────────────────────────────────────────
Realistic concurrent MT containers: 2-4 before CPU saturates
```

### Disk budget (75 GB)
```
Docker base images .......................... ~5 GB
  - python:3.12-slim (engine) ~150 MB
  - golang base ~300 MB × 3 services ~900 MB
  - postgres:16-alpine ~250 MB
  - chromadb ~600 MB
  - prometheus + jaeger + grafana ~800 MB
  - ubuntu:24.04 + Wine + MT installers ~2 GB

Postgres data volume ........................ Grows with users.
                                              Per user: ~5-20 MB/month
                                              Webhook events, audit logs,
                                              analysis records, reservations.

ChromaDB embeddings ......................... ~500 MB for current knowledge corpus
                                              Can grow to 2-5 GB at scale

Prometheus retention (default 15 days) ...... ~2-5 GB
Grafana dashboards .......................... <100 MB
Model cache (~/.cache for engine) ........... 500 MB - 2 GB
  - Sentence-transformers / tokenizer / embedding models

Per MT container persistent volume .......... ~500 MB per user (terminal data,
                                              charts, history, EA logs)

OS + swap + breathing room .................. ~10 GB

EFFECTIVE FREE FOR MT USERS: ~30-40 GB
At 500 MB per MT user: ~60-80 users max disk-wise
```

## What this means in practice

| Scenario | Will it work on 4/8/75? |
|---|---|
| **Development / staging with 1-2 test users** | ✅ Yes, easily |
| **Production with 1-3 paying users** | ⚠️ Yes but tight; engine OOM risk during big LLM responses |
| **Production with 4-10 active users** | ❌ No. MT containers will OOM-kill or swap-thrash |
| **Production with 10+ users** | ❌ Hard no |

## My honest recommendation

**For the architecture you've built (multi-tenant, per-user MT instances on the same machine), you need at minimum:**

### Option 1: Realistic single-VPS sizing
- **8 vCPU / 16 GB RAM / 160 GB NVMe**
- Comfortable for 10-15 active MT users
- Cost: ~€25-40/month on Hetzner, ~$60-80/month elsewhere

### Option 2: Production-grade single-VPS sizing
- **8-12 vCPU / 24-32 GB RAM / 240 GB NVMe**
- Comfortable for 30-50 active MT users
- Cost: ~€50-80/month on Hetzner

### Option 3: Architecturally correct split (best long-term)
- **Backend VPS:** 4 vCPU / 8 GB / 75 GB (your current spec) — runs everything EXCEPT MT containers
- **MT VPS pool:** separate machines that scale horizontally as users grow — one machine can host 10-20 MT instances comfortably with 8 GB RAM
- **Frontend:** Cloudflare Pages (free)

This is what your `helm/` charts are clearly designed for — separate deployments per service, horizontal scaling.

## What's specifically going to break on 4/8/75

1. **OOM kills on engine during LLM responses** — engine declares 2 GB limit; under sustained LLM streaming + RAG retrieval + per-user processor caches, real-world usage hits 2.5-3 GB and Docker will SIGKILL it.

2. **MT containers will fight for RAM** — once you have 3+ active users, Wine processes will swap-thrash on disk, latency explodes, EA disconnects from broker, trade signals miss their windows.

3. **ChromaDB has NO memory limit** — at scale it will eat into engine's budget and trigger cascading OOMs.

4. **Prometheus retention will fill disk** — 15-day default retention with 6+ services scraping every 15s consumes ~5-8 GB over 2 weeks; combined with growing postgres + MT data, you'll hit 75 GB within 60-90 days.

5. **Single-machine = single point of failure** — one MT container crash from a bad EA can cgroup-throttle the whole machine.

## TL;DR

**For development / staging / first paying customer:** 4/8/75 works.

**For real multi-tenant production with per-user MT on the same machine:** you need 16 GB RAM minimum, ideally 32 GB. The MT-per-user architecture is the dominant cost driver — each Wine container is 500MB+ RAM and that adds up fast.

The cleanest path forward is to **deploy the backend stack on the 4/8/75 box and put MT containers on a separate horizontally-scalable pool**, which is exactly what your `helm/` charts are built for.




_________________________________________________________________________________




# Honest sizing breakdown for both VPS tiers

## VPS 20: 6 vCPU / 12 GB RAM / 100 GB NVMe

### RAM budget
```
OS + Docker daemon ........................  ~800 MB
postgres (real load, not 256 MB limit) ....  ~600 MB
redis .....................................  ~128 MB
chromadb (knowledge embeddings loaded) ....  ~1.0 GB
engine (Python: torch + LLM + RAG + caches)  ~2.5 GB (peaks above the 2GB limit on
                                              concurrent multi-user LLM streams)
gateway ...................................  ~256 MB
execution .................................  ~256 MB
management ................................  ~256 MB
prometheus + jaeger + grafana .............  ~640 MB
─────────────────────────────────────────────────────
CORE STACK SUBTOTAL .......................  ~6.4 GB

Free for MT containers: ~5.6 GB
Per MT container: ~500-700 MB (Wine + Xvfb + terminal64.exe + EA)
─────────────────────────────────────────────────────
COMFORTABLE MT CONTAINERS: 6-8 users
ABSOLUTE MAX (with swap risk): 10-11 users
```

### CPU budget
```
6 vCPU total
engine reserves 2.0 vCPU                     ~33% of host
postgres + chromadb + go services .........  ~1.5 vCPU sustained
prometheus scraping overhead ..............  ~0.2 vCPU
Reserved for MT containers .................  ~2.3 vCPU
Per active MT trading: 0.2-0.4 vCPU (peaks on indicator recalc)
─────────────────────────────────────────────
CPU-comfortable concurrent MT users: 5-10
```

### Disk budget (100 GB NVMe)
```
Docker base images ......................... ~5 GB
Postgres data (grows ~10-15 MB/user/month) . starts at ~500 MB
ChromaDB embeddings ........................ ~1 GB now, growing to ~3 GB
Model cache (sentence-transformers, etc.) .. ~1-2 GB
Prometheus 15-day retention ................ ~5-8 GB
Grafana ..................................... <200 MB
MT containers persistent volumes ........... ~500 MB × N users
Logs + journal + system .................... ~5 GB
OS + swap + breathing room ................. ~10 GB
─────────────────────────────────────────────
USABLE FREE FOR GROWTH: ~60-65 GB
At 500 MB/MT user persistent data: ~100+ users disk-wise
Postgres growth: ~150 users for 12 months before approaching limit
```

### Verdict: VPS 20

| Scenario | Will it work on 6/12/100? |
|---|---|
| **Development + staging combined** | ✅ Yes, easily |
| **Beta launch with 1-5 paying users** | ✅ Yes, comfortable |
| **Early production with 5-10 active users** | ✅ Yes, healthy margins |
| **Scaling to 10-15 active users** | ⚠️ Tight; monitor closely |
| **Scaling beyond 15 active users** | ❌ Upgrade time |

**Upgrade trigger signals to watch:**
- `docker stats` consistently shows engine container at 90%+ memory
- Prometheus reports postgres connection pool saturation
- Average system load > 4.5 (75% of 6 vCPU)
- Active MT containers ≥ 10

---

## VPS 30: 8 vCPU / 24 GB RAM / 200 GB NVMe

### RAM budget
```
OS + Docker daemon ........................  ~1 GB
postgres (room to grow, real load) ........  ~1.5 GB (raise shared_buffers)
redis .....................................  ~256 MB (raise maxmemory)
chromadb (large knowledge corpus) .........  ~2 GB
engine (Python, comfortable for 20+ users)  ~3.5 GB (raise limit from 2GB to 4GB)
gateway ...................................  ~512 MB (raise limit)
execution .................................  ~512 MB
management ................................  ~512 MB
prometheus + jaeger + grafana .............  ~1 GB (longer retention)
─────────────────────────────────────────────────────
CORE STACK SUBTOTAL .......................  ~10.8 GB

Free for MT containers: ~13.2 GB
Per MT container: ~500-700 MB
─────────────────────────────────────────────────────
COMFORTABLE MT CONTAINERS: 18-25 users
ABSOLUTE MAX (with disciplined limits): 30 users
```

### CPU budget
```
8 vCPU total
engine reserves 2-4 vCPU (raise from 2.0 limit)
postgres + chromadb + go services .........  ~2 vCPU sustained
prometheus scraping overhead ..............  ~0.3 vCPU
Reserved for MT containers .................  ~3.5 vCPU
Per active MT trading: 0.2-0.4 vCPU
─────────────────────────────────────────────
CPU-comfortable concurrent MT users: 15-25
```

### Disk budget (200 GB NVMe)
```
Docker base images ......................... ~5 GB
Postgres data (~20-30 users, 12 months) .... ~3-5 GB
ChromaDB embeddings (full corpus) .......... ~3-5 GB
Model cache ................................ ~2 GB
Prometheus 30-day retention (recommended) .. ~15-20 GB
Grafana .................................... ~500 MB
MT containers persistent (~25 users) ....... ~15 GB
Logs + journal + system .................... ~10 GB
Backup snapshots (Hetzner-managed) ......... handled separately
OS + swap + breathing room ................. ~15 GB
─────────────────────────────────────────────
USABLE FREE FOR GROWTH: ~125-135 GB
Comfortable for 50+ users / 18+ months of growth before resize
```

### Verdict: VPS 30

| Scenario | Will it work on 8/24/200? |
|---|---|
| **Production with 10-25 active users** | ✅ Comfortable, healthy margins |
| **Production with 25-30 active users** | ✅ Yes, monitor disk + RAM |
| **Production with 30-40 active users** | ⚠️ Approaching limits; plan horizontal split |
| **Production beyond 40 active users** | ❌ Time for architectural split |

---

## Recommended migration path

### Phase 1: Launch on VPS 20 (now)
**You can run the entire stack — backend + MT containers + observability — on this box.**

What to do at install:
1. Deploy with `docker compose up -d --build`
2. Frontend goes on **Cloudflare Pages** (free, separate from VPS) — your `cotradee` builds with `npm run build` and the `dist/` folder uploads to Cloudflare
3. Enable swap (4 GB) as a safety net: `fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`
4. Configure Prometheus retention to 7 days initially to save disk

Set up monitoring alerts at:
- RAM > 80% sustained for 10 min → time to plan upgrade
- Active MT containers ≥ 8 → time to plan upgrade
- Disk usage > 70 GB → time to plan upgrade

### Phase 2: Upgrade to VPS 30 (when you hit ~8-10 active users)
Hetzner / Contabo / most providers let you **resize in place** without re-deploying — VPS shutdowns for ~15 minutes during resize, your docker volumes preserve, everything comes back up automatically.

What changes operationally:
1. Raise engine container limit from 2 GB to 4 GB in `docker-compose.yml`
2. Raise postgres shared_buffers (envvar `POSTGRES_INITDB_ARGS` or postgresql.conf via mount)
3. Raise redis maxmemory from 128 MB to 256 MB
4. Bump Prometheus retention from 7 days to 30 days
5. No code changes; pure config

### Phase 3: When VPS 30 runs out (40+ active users)
**At this scale you split horizontally** — exactly what your `helm/` charts are built for:
- Backend services (engine + gateway + execution + management + postgres + redis + chromadb) on one machine
- MT container pool on a second machine that scales horizontally (10-20 MT per box)
- Frontend stays on Cloudflare
- Database eventually moves to managed Postgres (DigitalOcean / Hetzner Managed DB)

---

## TL;DR

**VPS 20 (6/12/100) at £6.80/month** — perfect to start. Handles your full stack for **5-10 active users comfortably**, up to ~15 stretched.

**VPS 30 (8/24/200) at £13.70/month** — your second milestone. Handles **20-30 active users comfortably**, up to ~40 stretched.

Both pricing options are excellent for the scale of platform you're building. Start on VPS 20, upgrade in-place to VPS 30 the moment you hit consistent 10+ concurrent active users.

**Cost-to-revenue check:** at £13.70/month for VPS 30, if your pro_managed tier sells at even £15/month, **one paying user covers your entire infrastructure**. Margins look healthy.




















