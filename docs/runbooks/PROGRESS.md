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
**Frontend (SPA):** Vercel, canonical staging host **`staging.exoper.com`**
**Backend API host:** `staging-api.exoper.com` (Cloudflare Tunnel -> edge-ingress, set up in Phase 6)

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

### 0.1 Workstation tools installed

On `softverse@Softverse` (Ubuntu 24.04 workstation, not the VPS).

Already present: `git`, `openssl`, `jq`, `curl`, `base64`, `ssh`, `docker`.

Installed:
```bash
sudo apt update && sudo apt install -y curl jq git openssl ca-certificates gnupg lsb-release

# kubectl 1.30.4
curl -LO "https://dl.k8s.io/release/v1.30.4/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl

# helm 3 (3.21.1 was current)
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# HashiCorp APT (terraform 1.15.6 + vault CLI 2.0.2)
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform vault

# Disable the local Vault systemd service — Vault runs in K3s on the VPS,
# not on the workstation.
sudo systemctl disable --now vault 2>/dev/null || true
sudo systemctl mask vault 2>/dev/null || true

# argocd CLI v2.13.3 (matches the runbook's ArgoCD server version)
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/download/v2.13.3/argocd-linux-amd64
sudo install -m 555 argocd /usr/local/bin/argocd && rm argocd

# step CLI (smallstep). The dl.smallstep.com URL in the runbook returns
# 404; pulled the same artifact from GitHub releases instead.
STEP_VER=$(curl -fsSL https://api.github.com/repos/smallstep/cli/releases/latest | jq -r .tag_name | sed 's/^v//')
ASSET_URL=$(curl -fsSL "https://api.github.com/repos/smallstep/cli/releases/latest" \
  | jq -r '.assets[] | select(.name | test("amd64\\.deb$")) | .browser_download_url' \
  | head -n1)
curl -fsSL -o step.deb "$ASSET_URL"
sudo dpkg -i step.deb && rm step.deb
```

Versions installed: `kubectl` v1.30.4, `helm` v3.21.1, `terraform` v1.15.6,
`vault` CLI 2.0.2, `argocd` v2.13.3, `step` v0.30.6, `docker` (Engine CE).
`rustup` deliberately deferred to Phase 9 (envoy WASM build).

### 0.2 Accounts / assets confirmed

| Item | Status |
|---|---|
| Cloudflare zone `exoper.com` active | ✅ |
| MaxMind GeoLite2 `account_id` + `license_key` | ✅ (in operator's `.env`) |
| Anthropic API key + any of OpenAI / Gemini / TwelveData / FRED / CFTC | ✅ (in operator's `.env`) |
| Paddle + Lemon Squeezy credentials | ⚠️ NOT yet available |
| Contabo VPS provisioned (Ubuntu 24.04, 8 vCPU / 24 GB / 200 GB) | ✅ |
| GHCR Personal Access Token (classic) with `write:packages` scope | ✅ (at `~/.ghcr_pat`, mode 0600) |

### 0.3 Repository cloned on the workstation

```bash
cd ~/eTradie
pwd                                # /home/softverse/eTradie
git rev-parse --abbrev-ref HEAD    # main
```

Workstation clone has two remotes: `origin` -> GitHub (`FlameGreat-1/eTradie`),
`gitlab` -> GitLab (`exoper2/exoper`).

### 0.4 GHCR image sanity

The runbook's documented Phase 0.4 check uses anonymous auth, which
returns 401/404 against the (private) GHCR packages. We replaced it
with an authenticated two-step check (basic-auth -> per-repo bearer
token -> manifest fetch). Authenticated tag-list scan returned every
chart-pinned tag for every service. `mt-node` repo is intentionally
empty until Phase 2.5; `envoy` is the upstream `envoyproxy/envoy:v1.28.0`
from Docker Hub, not built by CI.

---

## Phase 1 — VPS host hardening 🔄

_Updated when Phase 1 completes end-to-end._

---

## Open items / known gaps tracked for later phases

- **mt-node CI guard.** `WINEHQ_VERSION` GitHub Actions secret is not
  set. The mt-node matrix job will keep failing on every `main` push
  until either (a) we set it in Phase 2.5 alongside the manual
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
