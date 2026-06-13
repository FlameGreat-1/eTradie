# eTradie Deployment Progress Log

> Per-deploy record of progress through [`docs/runbooks/README.md`](README.md).
> A new deploy (different operator, different VPS, different environment)
> starts by copying this file, blanking the per-deploy parameters below,
> and clearing the status board back to `⏸ pending`.
>
> This file does NOT re-document the runbook. README.md is canonical; here
> we only record which phases finished and any deploy-specific outcomes
> a future-you (or a hand-off operator) needs to know to pick up safely.

---

## Per-deploy parameters

| Parameter | Value |
|---|---|
| Target environment | `staging` |
| VPS host | Contabo VPS 30 NVMe — Ubuntu 24.04.4 LTS |
| API hostname (Cloudflare Tunnel public hostname, Phase 6) | `staging-api.exoper.com` |
| SPA host (Vercel; OUT OF SCOPE here) | `staging.exoper.com` |
| GHCR owner / image base | `FlameGreat-1` / `ghcr.io/flamegreat-1/etradie` |

---

## Status board

| Phase | Title | Status |
|---|---|---|
| 0 | Prerequisites | ✅ DONE |
| 1 | VPS host hardening | 🔄 IN PROGRESS |
| 2 | Install K3s | ⏸ pending |
| 2.5 | Build + push mt-node Wine image | ⏸ pending |
| 3 | Vault + Vault Agent Injector | ⏸ pending |
| 4 | External Secrets Operator + ClusterSecretStore | ⏸ pending |
| 5 | Stakater Reloader | ⏸ pending |
| 6 | Cloudflare Tunnel | ⏸ pending |
| 7 | Generate Linkerd mesh CA | ⏸ pending |
| 8 | Bootstrap Vault paths + populate every secret | ⏸ pending |
| 9 | Build + inject envoy WASM filter | ⏸ pending |
| 10 | ArgoCD + AppProjects + root app | ⏸ pending |
| 11 | Provision mt-node tenant Vault infrastructure | ⏸ pending |
| 12 | Sync the platform in dependency order | ⏸ pending |
| 13 | Database migrations (auto via engine init) | ⏸ pending |
| 14 | End-to-end verification | ⏸ pending |
| 14.5 | Hosted-MT per-user provisioning + verification | ⏸ pending |
| 15 | Post-deploy operational notes | ⏸ pending |

---

## Phase 0 — Prerequisites ✅

Executed README.md Phase 0 (0.1–0.4) against the staging tag column.
Every 0.4 line returned `200`; mt-node empty as expected. No deviations.

**Deploy-specific outcomes:**
- Paddle + Lemon Squeezy credentials NOT in hand. Phase 8.9 will write
  random plausibly-formatted values into Vault so the billing service
  passes its startup fail-fast; real values to be swapped in later via
  `vault kv put` + `kubectl rollout restart deployment/etradie-billing`.

---

## Phase 1 — VPS host hardening 🔄

_Filled in when Phase 1 completes end-to-end._
