# eTradie Deployment Progress Log — Staging on Contabo VPS

> Living record of every phase executed against
> [`docs/runbooks/README.md`](README.md). Updated at the end of each
> phase. Operator may pick up mid-deployment by reading the last
> completed entry and resuming at the next phase.

**Target environment:** `staging`
**Target host:** Contabo VPS 30 NVMe — `13.140.164.173` (Ubuntu 24.04.4 LTS)
**Workstation:** `softverse@Softverse` (Ubuntu, `~/eTradie`)
**Operator GitHub:** `FlameGreat-1`
**Git remotes:** `origin` -> GitHub (`FlameGreat-1/eTradie`), `gitlab` -> GitLab (`exoper2/exoper`)
**Frontend (SPA):** Vercel, canonical staging host **`staging.exoper.com`** (operator decision; see Pre-Phase-1 §2)
**Backend API host:** `staging-api.exoper.com` (Cloudflare Tunnel -> edge-ingress, set up in Phase 6)

---

## Status board

| Phase | Title | Status | Completed |
|---|---|---|---|
| Pre-1 §1 | CI fix: publish chart-pinned tags | ✅ DONE | MR !145 merged + GHCR re-verified |
| Pre-1 §2 | Staging SPA host: `staging-app` → `staging` | ✅ DONE | Commit `8f68ecd5` |
| 0 | Prerequisites | ✅ DONE | Workstation CLIs installed, GHCR images verified |
| 1 | VPS host hardening | ⏳ NEXT | — |
| 2 | Install K3s | ⏸ pending | — |
| 2.5 | Build + push mt-node Wine image | ⏸ pending | — |
| 3 | Vault + Vault Agent Injector | ⏸ pending | — |
| 4 | External Secrets Operator + ClusterSecretStore | ⏸ pending | — |
| 5 | Stakater Reloader | ⏸ pending | — |
| 6 | Cloudflare Tunnel | ⏸ pending | — |
| 7 | Generate Linkerd mesh CA | ⏸ pending | — |
| 8 | Bootstrap Vault paths + populate every secret | ⏸ pending | — |
| 9 | Build + inject envoy WASM filter | ⏸ pending | — |
| 10 | ArgoCD + AppProjects + root app | ⏸ pending | — |
| 11 | Provision mt-node tenant Vault infrastructure | ⏸ pending | — |
| 12 | Sync the platform in dependency order | ⏸ pending | — |
| 13 | Database migrations (auto via engine init) | ⏸ pending | — |
| 14 | End-to-end verification | ⏸ pending | — |
| 14.5 | Hosted-MT per-user provisioning + verification | ⏸ pending | — |
| 15 | Post-deploy operational notes | ⏸ pending | — |

---

## Pre-Phase-1 §1 — CI fix: publish chart-pinned tags ✅

**Problem discovered.** Phase 0.4 GHCR sanity check showed that three
chart-pinned image tags did not exist in GHCR:

| Chart file | Pinned tag | In GHCR pre-fix? |
|---|---|---|
| `helm/gateway/values-staging.yaml` | `staging-0.1.0` | ❌ |
| `helm/billing/values-staging.yaml` | `staging-0.1.0` | ❌ |
| `helm/edge-ingress/values-staging.yaml` | `staging-v0.1.0` | ❌ |
| `helm/edge-ingress/values.yaml` (consumed by production overlay) | `0.2.0` | ❌ |

CI was only ever publishing `${{ github.sha }}` and the shared
`RELEASE_TAG: "0.1.0"`, so staging would have `ImagePullBackOff`'d
for gateway/billing/edge-ingress AND production would have
`ImagePullBackOff`'d for edge-ingress on first ArgoCD sync.

**Fix.** Two surgical edits to `.github/workflows/ci.yml`:

1. New env var `EDGE_INGRESS_RELEASE_TAG: "0.2.0"` alongside
   `RELEASE_TAG: "0.1.0"`.
2. Extended `tags:` block in the `docker/build-push-action` step,
   on `main`-branch pushes only:
   - every service: + `staging-${RELEASE_TAG}`
   - `edge-ingress` only: + `${EDGE_INGRESS_RELEASE_TAG}` (0.2.0)
     and + `staging-v${RELEASE_TAG}`.
   Implemented with conditional `format()` expressions; empty strings
   collapse to blank lines which `docker/build-push-action` ignores.

No chart edits; tag intent stays expressed in the values files.
No PR-time behaviour change. mt-node still gated by `WINEHQ_VERSION`
guard. Cosign signatures unchanged (signing is by digest).

**Merged.** GitLab MR
[`!145`](https://gitlab.com/exoper2/exoper/-/merge_requests/145).

**GitHub propagation.** Operator pulled GitLab `main` and pushed to
GitHub `origin/main`:
```bash
cd ~/eTradie
git fetch gitlab
git checkout main
git pull gitlab main
git push origin main
```
GitHub Actions `CI` workflow then ran and published every chart-pinned
tag.

**Verified.** From the workstation:
```bash
GH_USER=FlameGreat-1
for repo_path in \
  "flamegreat-1/etradie/engine" \
  "flamegreat-1/etradie/gateway" \
  "flamegreat-1/etradie/execution" \
  "flamegreat-1/etradie/management" \
  "flamegreat-1/etradie/billing" \
  "flamegreat-1/etradie/edge-ingress"; do
  echo "=== $repo_path ==="
  TOKEN=$(curl -sS -u "$GH_USER:$(cat ~/.ghcr_pat)" \
    "https://ghcr.io/token?service=ghcr.io&scope=repository:${repo_path}:pull" \
    | jq -r .token)
  curl -sS -H "Authorization: Bearer $TOKEN" \
    "https://ghcr.io/v2/${repo_path}/tags/list" \
    | jq -r '.tags[]?' | grep -v '\.sig$' | sort
  echo
done
```

Result: every chart-pinned tag present.
- 5 services (engine/gateway/execution/management/billing) each carry
  `0.1.0` and `staging-0.1.0`.
- `edge-ingress` carries `0.1.0`, `0.2.0`, `staging-0.1.0`,
  `staging-v0.1.0`.
- `mt-node` repo is empty by design (built in Phase 2.5).
- `envoy` is the upstream `envoyproxy/envoy:v1.28.0` from Docker Hub,
  not built by CI, not in GHCR.

---

## Pre-Phase-1 §2 — Staging SPA host: `staging-app` → `staging` ✅

**Operator decision.** Collapse the staging SPA topology so that
`staging.exoper.com` is the canonical Vercel deployment, and there is
no separate `staging-app.exoper.com` host. Aligns with billing's
existing `publicBaseUrl` (`https://staging.exoper.com`) which already
assumed the SPA lives at the apex staging host.

**Audit.** Repository-wide grep for the old host:
```bash
cd ~/eTradie
grep -rIn --color=never "staging-app\.exoper\.com" . 2>/dev/null
```
Returned exactly 3 hits across 2 files:
- `helm/gateway/values-staging.yaml:31` (comment)
- `helm/gateway/values-staging.yaml:32` (`allowedOrigins` value)
- `NOTE.md:42` (documented Vercel redirect direction)

**Fix.** Direct commit to `main` (`8f68ecd5`):
1. `helm/gateway/values-staging.yaml`: flipped
   `config.gateway.allowedOrigins` to `"https://staging.exoper.com"`
   and updated the adjacent comment so the documented canonical host
   matches the configured one.
2. `NOTE.md`: inverted the documented staging redirect direction so
   the operator-facing Vercel-side text now reads:
   *"`staging.exoper.com` is canonical on Vercel. If
   `staging-app.exoper.com` is ever created, 308-redirect it to
   `staging.exoper.com`."*

No code change in any service. No edge-ingress TLS cert change (API
host stays `staging-api.exoper.com`). No billing change (already used
`staging.exoper.com`).

**Vercel-side action (deferred to Phase 6).** Point the Vercel
staging deployment's primary domain at `staging.exoper.com` and add
DNS at Cloudflare. Tracked there, not here.

---

## Phase 0 — Prerequisites ✅

### 0.1 Workstation tools installed

All on `softverse@Softverse` (Ubuntu 24.04 workstation, not the VPS).

Already present: `git`, `openssl`, `jq`, `curl`, `base64`, `ssh`,
`docker` (Docker Engine - Community).

Installed by us:
```bash
sudo apt update && sudo apt install -y curl jq git openssl ca-certificates gnupg lsb-release

# kubectl 1.30.4
curl -LO "https://dl.k8s.io/release/v1.30.4/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl

# helm 3 (3.21.1 was current)
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# HashiCorp APT (terraform 1.15.6 + vault 2.0.2)
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform vault

# Disable the local Vault systemd service (Vault runs in K3s on the VPS, not here)
sudo systemctl disable --now vault 2>/dev/null || true
sudo systemctl mask vault 2>/dev/null || true

# argocd CLI v2.13.3 (matches runbook's ArgoCD server version)
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/download/v2.13.3/argocd-linux-amd64
sudo install -m 555 argocd /usr/local/bin/argocd && rm argocd

# step CLI (smallstep). Initial install attempt against
# dl.smallstep.com returned 404; pulled from GitHub releases instead.
STEP_VER=$(curl -fsSL https://api.github.com/repos/smallstep/cli/releases/latest | jq -r .tag_name | sed 's/^v//')
ASSET_URL=$(curl -fsSL "https://api.github.com/repos/smallstep/cli/releases/latest" \
  | jq -r '.assets[] | select(.name | test("amd64\\.deb$")) | .browser_download_url' \
  | head -n1)
curl -fsSL -o step.deb "$ASSET_URL"
sudo dpkg -i step.deb && rm step.deb
```

Verified versions (recorded for reproducibility):
- `kubectl` v1.30.4
- `helm` v3.21.1
- `terraform` v1.15.6
- `vault` 2.0.2 (CLI only; the systemd service was disabled+masked)
- `argocd` v2.13.3
- `step` (smallstep) v0.30.6
- `docker` (Docker Engine - Community, already installed)
- `rustup` deliberately NOT installed yet; only needed in Phase 9
  (envoy WASM filter build).

### 0.2 Accounts / assets confirmed

| Item | Status |
|---|---|
| Cloudflare zone `exoper.com` active (operator already manages `exoper.com`, `www.exoper.com`, `app.exoper.com`) | ✅ |
| MaxMind GeoLite2 `account_id` + `license_key` (in operator's `.env`) | ✅ |
| Anthropic API key (in operator's `.env`); plus any of OpenAI / Gemini / TwelveData / FRED / CFTC | ✅ |
| Paddle + Lemon Squeezy credentials | ⚠️ NOT yet available — Phase 8.9 will use plausibly-formatted random strings to pass the billing fail-fast format checks; real values swapped in later with `vault kv put` + `kubectl rollout restart` |
| Contabo VPS provisioned (Ubuntu 24.04, `13.140.164.173`, 8 vCPU / 24 GB / 200 GB) | ✅ |
| GHCR Personal Access Token (classic) with `write:packages` scope | ✅ (PAT belongs to `FlameGreat-1`; stored at `~/.ghcr_pat` on workstation, mode 0600) |

### 0.3 Repository cloned on the workstation

```bash
cd ~/eTradie
pwd                          # /home/softverse/eTradie
git rev-parse --abbrev-ref HEAD   # main
git log -1 --oneline         # cb7d5bc4 (... fix(engine/docker): install torch from PyTorch CPU index ...)
```

The workstation clone is the GitHub repo; we added a second remote
named `gitlab` pointing at `exoper2/exoper` so we can pull merged
GitLab changes and push them onward to GitHub.

### 0.4 GHCR image sanity

The runbook's documented Phase 0.4 check uses anonymous auth, which
returns `401`/`404` for the (private) packages. We replaced it with an
authenticated two-step check (basic-auth -> per-repo bearer token ->
manifest fetch). After Pre-Phase-1 §1 merged and propagated to GitHub,
the authenticated tag-list scan returned the required tags for every
service — see Pre-Phase-1 §1 "Verified." block.

**Phase 0 complete.** Every image the staging deployment needs exists
in GHCR (or in upstream Docker Hub, for envoy). mt-node is
intentionally absent until Phase 2.5.

---

## Open items / known gaps tracked for later phases

- **mt-node CI guard.** `WINEHQ_VERSION` GitHub Actions secret is not
  set, so the mt-node matrix job will keep failing on every `main`
  push until either (a) we set it in Phase 2.5 alongside the manual
  `docker push`, or (b) we set `ETRADIE_ALLOW_PUBLIC_INSTALLER_CDN=true`
  to bypass the supply-chain guard. Decision deferred to Phase 2.5;
  meanwhile the other 6 services build fine because the matrix has
  `fail-fast: false`.
- **Billing dummy credentials.** Plausibly-formatted random strings to
  be generated in Phase 8.9 so the billing service passes its
  startup fail-fast. Webhooks will return signature-verification
  errors (no real Paddle / Lemon Squeezy webhooks point there yet)
  but the pod stays Ready. Real values swapped in later.
- **`staging.exoper.com` DNS + Vercel domain assignment.** Operator
  task during Phase 6 (Cloudflare Tunnel), in parallel with adding
  `staging-api.exoper.com` as a tunnel public hostname.
