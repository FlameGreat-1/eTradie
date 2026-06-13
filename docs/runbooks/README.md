# eTradie — End-to-End Deployment Runbook (Contabo VPS 30, single-node)

**Scope:** the full backend platform (data layer + 4 services + billing + edge + envoy + observability + Linkerd mesh) onto ONE Contabo VPS 30 NVMe (8 vCPU / 24 GB / 200 GB), profile **BUDGET.md TABLE 2B** (everything ON, single-node lean). **The frontend `cotradee/` is OUT OF SCOPE** (already deployed on Vercel).

**Follow every section in order. Do not skip. Do not reorder.** Each step states what it does and how to verify it before you move on. Values here are verified against the repository (chart values, `ci.yml`, `infrastructure/cluster/vault-paths/main.tf`, ArgoCD manifests). Where the older `docs/deployment/contabo-k3s.md` disagrees, THIS runbook is correct (notably image tags and the Linkerd mesh, which that doc omits).

> Capacity (BUDGET.md Table 2B): this box hosts the full stack + **~1 production MT user**, or **~4–5 staging test users**. CPU requests are the limiter. Pick ONE environment per box; staging and production are not meant to co-reside.

---

## Verified version + image facts

| Item | Value | Source |
|---|---|---|
| App service image tag (engine, gateway, execution, management, billing) | `0.1.0` | each chart `values.yaml` + `ci.yml` `RELEASE_TAG` |
| edge-ingress image tag | `0.2.0` | `helm/edge-ingress/values.yaml` |
| mt-node image tag | `0.1.0` | `helm/mt-node/values-image.yaml` |
| Image registry base | `ghcr.io/flamegreat-1/etradie` | `ci.yml` `IMAGE_BASE` |
| K3s | `v1.30.4+k3s1` (MUST be >= 1.29 for native sidecars) | bootstrap README |
| Environment in this runbook | `production` | replace with `staging` everywhere for a staging box |

---

## Phase 0 — Prerequisites

All Phase 0 work runs on the OPERATOR WORKSTATION (your laptop / dev box). The Contabo VPS itself is not touched until Phase 1.

### 0.1 Workstation tools

Required CLIs and minimum versions (the platform fails closed on older clients): `ssh`, `kubectl` (>=1.29), `helm` (>=3.14), `terraform` (>=1.7), `vault` CLI (>=1.15), `git`, `jq`, `openssl`, `base64`, `curl`, `docker`, `step` (smallstep, for the mesh CA), `argocd` CLI. `rustup` is needed only for Phase 9 (envoy WASM build); install it then.

The block below installs everything from clean Ubuntu 24.04. Other Linux distros: substitute the apt parts; the static binaries (kubectl, helm, argocd, step) install the same way.

```bash
sudo apt update && sudo apt install -y curl jq git openssl ca-certificates gnupg lsb-release

# kubectl 1.30.4
curl -LO "https://dl.k8s.io/release/v1.30.4/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl

# helm 3 (latest stable from the official installer script)
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# HashiCorp APT repo (terraform + vault CLI)
curl -fsSL https://apt.releases.hashicorp.com/gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform vault

# The `vault` apt package also enables a local `vault.service` systemd
# unit that binds 8200 on the workstation. The PLATFORM's Vault runs
# inside K3s on the VPS — the local daemon is unwanted and competes
# for the port. Disable + mask it (we only need the CLI binary).
sudo systemctl disable --now vault 2>/dev/null || true
sudo systemctl mask vault 2>/dev/null || true

# argocd CLI v2.13.3 (matches the ArgoCD server version installed in
# Phase 10; mismatched CLI/server combos refuse to log in).
curl -sSL -o argocd \
  https://github.com/argoproj/argo-cd/releases/download/v2.13.3/argocd-linux-amd64
sudo install -m 555 argocd /usr/local/bin/argocd && rm argocd

# step CLI (smallstep). The legacy `dl.smallstep.com/...latest/` path
# is dead; resolve the actual asset URL from the GitHub release API.
ASSET_URL=$(curl -fsSL https://api.github.com/repos/smallstep/cli/releases/latest \
  | jq -r '.assets[] | select(.name | test("amd64\\.deb$")) | .browser_download_url' \
  | head -n1)
curl -fsSL -o step.deb "$ASSET_URL"
sudo dpkg -i step.deb && rm step.deb
```

**Docker** must already be present (Docker Engine CE on Linux or Docker Desktop on macOS / WSL2). Phase 2.5 builds the mt-node Wine image with it; without Docker, Phase 2.5 cannot complete.

**Verify** every required CLI is on the PATH at an acceptable version:
```bash
for t in kubectl helm terraform vault step argocd docker git jq curl openssl ssh; do
  printf '%-12s ' "$t"; command -v "$t" >/dev/null \
    && "$t" version 2>/dev/null | head -n1 || echo "MISSING"
done
```
All twelve lines must show a version. `MISSING` on any line stops Phase 0 — install it before continuing.

### 0.2 Accounts and assets

Get these in hand BEFORE Phase 1. Any value still missing at the phase that consumes it will hard-block the deployment.

- **Cloudflare** zone for your registrable domain (this runbook uses `exoper.com`), Active in your account. Used in Phase 6 (Tunnel) and Phase 8.5 (AOP CA + Tunnel token in Vault).
- **MaxMind GeoLite2** account: `account_id` + `license_key`. Free sign-up at <https://www.maxmind.com/en/geolite2/signup>. Phase 8.5.
- **Engine LLM / data keys**: Anthropic (required), plus any of OpenAI / Gemini / TwelveData / FRED / CFTC you intend to use. Phase 8.7.
- **Billing provider keys**: Paddle (webhook secret, API key, two price IDs) AND Lemon Squeezy (webhook secret, API key, store ID, two variant IDs). Both required — the billing service fail-closes on startup if any are missing. Phase 8.9.
- **Contabo VPS** provisioned per BUDGET.md Table 2B (8 vCPU / 24 GB / 200 GB NVMe, Ubuntu 24.04). Phase 1 onward.
- **GHCR Personal Access Token (classic)** with `write:packages` scope on the account that owns the published images. Fine-grained PATs do NOT work with GHCR. Phase 2.5 uses it to push the mt-node image. Store at `~/.ghcr_pat`, mode 0600.

### 0.3 Clone the repo

```bash
git clone https://github.com/FlameGreat-1/eTradie.git
cd eTradie
git rev-parse --abbrev-ref HEAD          # main
```

Every `helm`/`terraform`/`kubectl apply -f` invocation later assumes the working directory is the repo root.

### 0.4 Confirm the CI-built images exist in GHCR

The GHCR packages for this project are PRIVATE, so the documented anonymous check returns 401/404 even when every image is present. Use authenticated basic-auth with the PAT from 0.2, exchange for a per-repository bearer token, then fetch the manifest. The mt-node image is intentionally NOT in this check — it is built by hand in Phase 2.5 (its CI guard rejects main-branch builds without `WINEHQ_VERSION`). Note mt-node lives under a DIFFERENT path (`etradie-mt-node`, hyphen), not `etradie/<svc>` (slash); the engine reads the exact path from `MT_NODE_IMAGE`.

Replace `GH_OWNER` with the GitHub login that owns the packages (case-sensitive; here `FlameGreat-1`).

```bash
GH_OWNER=FlameGreat-1
GH_PAT=$(cat ~/.ghcr_pat)

check () {
  local repo=$1 tag=$2
  local token
  token=$(curl -sS -u "$GH_OWNER:$GH_PAT" \
    "https://ghcr.io/token?service=ghcr.io&scope=repository:${repo}:pull" \
    | jq -r .token)
  printf '%-45s -> ' "$repo:$tag"
  curl -sS -o /dev/null -w '%{http_code}\n' \
    -H "Authorization: Bearer $token" \
    -H "Accept: application/vnd.oci.image.manifest.v1+json,application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
    "https://ghcr.io/v2/${repo}/manifests/${tag}"
}

# Pick the tag column that matches the environment you are deploying.
# Production overlays consume the left column; staging overlays consume
# the right column (chart-pinned in helm/<svc>/values-{env}.yaml).
for svc in engine gateway execution management billing; do
  check "flamegreat-1/etradie/$svc" "0.1.0"            # production
  check "flamegreat-1/etradie/$svc" "staging-0.1.0"    # staging
done
check "flamegreat-1/etradie/edge-ingress" "0.2.0"        # production
check "flamegreat-1/etradie/edge-ingress" "staging-v0.1.0"  # staging
```
Every line must end in `200` for the environment you are deploying. Any `404` means CI did not publish that chart-pinned tag — fix the CI job or the chart pin before continuing; do NOT proceed to Phase 1 with a 404.

---

## Phase 1 — VPS host hardening

SSH in as `root`. The companion runbook `docs/runbooks/vps-host-hardening.md` covers the full Tier 11 procedure; the steps below are the authoritative subset every self-managed Contabo / kubeadm / bare-metal box MUST run before Phase 2 (K3s install). They satisfy `infrastructure/cluster/bootstrap/README.md` step 0 *and* the Tier 11 "Server Hardening" + "VPN admin access" checklist (SSH key-only auth, password login disabled, fail2ban, host firewall, private K8s API).

> **Decisions baked into this phase (do not re-derive each deploy):**
>
> - **Firewall tool: `ufw`.** Ubuntu 24.04 ships `ufw` with `nftables` as the backend, so we get the nftables semantics with simpler ergonomics. `vps-host-hardening.md` documents an `nftables` ruleset as an equivalent alternative for operators who prefer authoring rules directly.
> - **`PermitRootLogin no`** (this runbook), not the looser `prohibit-password` the Tier 11 runbook also documents. We use the deploy user `etradie` for everything; no root SSH escape hatch.
> - **sshd drop-in** (`/etc/ssh/sshd_config.d/10-etradie-hardening.conf`) instead of editing `/etc/ssh/sshd_config` directly, so a future `openssh-server` package upgrade cannot silently revert the hardening.
> - **K8s API stays private via firewall + SSH tunnel.** The Tier 11 runbook's K3s install with `--tls-san <PRIVATE_IP> --advertise-address <PRIVATE_IP> --node-ip <PRIVATE_IP>` does NOT apply to a single-NIC Contabo VPS (there is no private IP to bind to). Instead, Phase 1.6's firewall closes 6443 inbound, and Phase 2.3 reaches the API from the workstation through the existing SSH session (`ssh -L` or by editing the exported kubeconfig).

1.1 **Create non-root sudo user `etradie`, install your SSH key, verify before 1.2.**

> **Safety net.** From the moment you start 1.1 until after the 1.2 verification passes, keep at least TWO SSH sessions open: the original `root` (or current-user) session AS A SAFETY NET, and a second session you use for verification. Do not close the safety-net session until 1.2 verification passes — if the new sshd config is broken, that open session is the only way back in without using Contabo's web VNC console. Emergency recovery instructions are at the end of this phase.

```bash
adduser --gecos "" --disabled-password etradie
usermod -aG sudo etradie
echo "etradie ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-etradie
chmod 0440 /etc/sudoers.d/90-etradie
visudo -cf /etc/sudoers.d/90-etradie         # "parsed OK"
install -d -m 0700 -o etradie -g etradie /home/etradie/.ssh

# Install the operator's workstation SSH key into etradie's authorized_keys.
#
# The fresh-Contabo case: /root/.ssh/authorized_keys is shipped as a 0-byte
# file because Contabo's image enables password root login by default.
# Copying that empty file to etradie would silently lock you out at 1.2.
# We therefore validate root's key file first and, if it is empty, prompt
# the operator to install their workstation public key directly.

if [ -s /root/.ssh/authorized_keys ]; then
  # root already has at least one key. Mirror it to etradie.
  install -m 0600 -o etradie -g etradie /root/.ssh/authorized_keys /home/etradie/.ssh/authorized_keys
  echo "Installed $(wc -l < /home/etradie/.ssh/authorized_keys) key(s) into etradie's authorized_keys from root's."
else
  cat >&2 <<'MSG'
FATAL: /root/.ssh/authorized_keys is empty or missing. This is the
       default state on a fresh Contabo image where root logs in via
       password. Cannot derive etradie's key from it.

       Open a SEPARATE terminal on your workstation and run:
           cat ~/.ssh/id_ed25519.pub   # or id_rsa.pub
       Copy the entire single-line output.

       Then, back in THIS root session, install it into BOTH
       /root/.ssh/authorized_keys (so root's escape hatch keeps working
       until 1.2 disables root login) AND /home/etradie/.ssh/authorized_keys:

           cat > /home/etradie/.ssh/authorized_keys <<'EOF'
           ssh-ed25519 AAAA... operator@workstation
           EOF
           chown etradie:etradie /home/etradie/.ssh/authorized_keys
           chmod 0600 /home/etradie/.ssh/authorized_keys

           cat > /root/.ssh/authorized_keys <<'EOF'
           ssh-ed25519 AAAA... operator@workstation
           EOF
           chmod 0600 /root/.ssh/authorized_keys

       Then re-run the verification below.
MSG
  exit 1
fi
```
**Verify from a SECOND terminal** (do NOT close your current safety-net session): `ssh etradie@HOST` succeeds key-only (no password prompt), and `sudo whoami` prints `root`. Only then proceed; if it fails, fix the keys before touching sshd in 1.2.

1.2 **Harden sshd via a drop-in** (not inline edits).
```bash
sudo tee /etc/ssh/sshd_config.d/10-etradie-hardening.conf >/dev/null <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 20
X11Forwarding no
AllowAgentForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

sudo sshd -t                                   # validate before restart
sudo systemctl restart ssh                     # 'sshd' on some distros
```
**Verify from a SECOND terminal**:
```bash
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no etradie@HOST   # must FAIL
ssh root@HOST                                                                       # must FAIL
ssh etradie@HOST                                                                    # must SUCCEED (key)
```

1.3 **OS packages + updates.**
```bash
sudo apt update && sudo apt -y upgrade
sudo apt install -y ca-certificates curl gnupg git make jq unzip ufw chrony fail2ban
```

1.4 **Time sync** (TLS, JWT exp, audit timestamps depend on this):
```bash
sudo systemctl enable --now chrony && chronyc tracking    # Stratum <= 3
```

1.5 **Kernel + ulimit tuning** (Elasticsearch/Postgres/redis common hits):
```bash
sudo tee /etc/sysctl.d/99-etradie.conf >/dev/null <<'EOF'
vm.max_map_count=262144
fs.inotify.max_user_watches=524288
net.core.somaxconn=65535
vm.swappiness=10
EOF
sudo tee /etc/security/limits.d/99-etradie.conf >/dev/null <<'EOF'
*  soft  nofile  65535
*  hard  nofile  65535
*  soft  nproc   65535
*  hard  nproc   65535
EOF
sudo sysctl --system
```
> **What this does NOT change at runtime.** The sysctl values apply
> immediately to the running kernel. The `/etc/security/limits.d/`
> file is evaluated by PAM only at SESSION OPEN — it does not affect
> processes already running (including your current SSH session) and
> does not affect anything started by systemd. K3s, Vault, the Vault
> Agent Injector, and every chart workload use either a systemd unit's
> `LimitNOFILE=` directive or the container runtime's per-container
> limits, independent of these PAM limits. The PAM file we just wrote
> is therefore the floor for interactive shells and non-systemd
> processes only. To see the new limits in your own shell, log out
> and back in (a fresh `ssh etradie@HOST` from a second terminal is
> the simplest way to verify).

1.6 **Firewall — default-deny inbound, allow only SSH.** Cloudflare Tunnel is outbound-only so no application port is opened. K3s 6443 stays closed inbound; operator `kubectl` reaches it through the SSH session set up in Phase 2.3.
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw limit 22/tcp comment 'SSH (rate-limited)'
sudo ufw --force enable
sudo ufw status verbose                              # only 22/tcp inbound
```

1.7 **fail2ban — sshd jail.**
```bash
sudo tee /etc/fail2ban/jail.d/sshd.local >/dev/null <<'EOF'
[sshd]
enabled = true
mode = aggressive
maxretry = 3
findtime = 10m
bantime = 1h
bantime.increment = true
bantime.maxtime = 1w
EOF
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd                     # jail active
```

1.8 **Verification checklist** (every line must hold before moving to Phase 2):
```bash
sudo sshd -T | grep -E 'passwordauthentication|permitrootlogin|pubkeyauthentication'
# expect: passwordauthentication no / permitrootlogin no / pubkeyauthentication yes
sudo fail2ban-client status sshd                     # jail active
sudo ufw status verbose | grep -E 'Status|22/tcp'    # Status: active; only 22/tcp inbound
chronyc tracking | grep Stratum                      # Stratum <= 3
sudo ss -tlnp | grep ':6443' || echo 'API not yet listening (expected pre-Phase-2)'
sudo -n whoami                                       # "root"  (deploy user has passwordless sudo)
sudo ss -tlnp | awk '/LISTEN/ && $4 !~ /127\.0\.|\[::1\]/'  # only sshd on :22 (v4 + v6)
```

### Emergency SSH recovery (if you locked yourself out during Phase 1)

If the 1.2 verification refuses your key AND your safety-net session is
closed, you have not lost the box — Contabo's customer panel provides a
browser-based VNC console that bypasses sshd entirely. Log in at
<https://my.contabo.com>, open your VPS, open the **VNC** tab, and you
get a tty that asks for a password (NOT a key). Enter the root password
from your Contabo welcome email, then either:

- **Re-add your key to both root and etradie's authorized_keys**
  (the `cat > ... <<'EOF'` blocks from 1.1) and re-run 1.2 + verify; or
- **Disable the sshd drop-in** if it's the broken piece:
  ```bash
  mv /etc/ssh/sshd_config.d/10-etradie-hardening.conf /root/10-etradie-hardening.conf.broken
  sshd -t && systemctl restart ssh
  ```
  then fix and reapply.

Until 1.2 verification has succeeded ON A FRESH SECOND SESSION, treat
the VNC console as your guaranteed fallback. After 1.2 is verified, you
may close the safety-net session.

---

## Phase 2 — Install K3s (>= 1.29 REQUIRED for Linkerd native sidecars)

2.1 On the VPS:
```bash
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="v1.30.4+k3s1" \
  K3S_KUBECONFIG_MODE="644" \
  INSTALL_K3S_EXEC="server --disable=traefik --disable=servicelb --write-kubeconfig-mode=644 --kube-apiserver-arg=enable-admission-plugins=NodeRestriction,PodSecurity --kubelet-arg=eviction-hard=memory.available<200Mi" \
  sh -
```
Why: own ingress (no traefik), no LoadBalancer (no servicelb), PSS `restricted` the charts rely on.

2.2 Verify: `sudo k3s kubectl get nodes` Ready; `kube-system` pods Running.

2.3 Export kubeconfig to workstation as `~/.kube/etradie-contabo.yaml`, replace `127.0.0.1` with the VPS public IP:
```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes   # Ready
```
Everything below runs from your workstation.

---

## Phase 2.5 — Build + push the mt-node Wine image (do this BEFORE you rely on Phase 0.4)

The app images (engine/gateway/execution/management/billing/edge-ingress)
are published automatically by the CI `build` job on every push to `main`.
The **mt-node Wine image is different**: a production build is gated on
supply-chain build args and is normally produced only when CI has the
`WINEHQ_VERSION` + installer-SHA secrets set (see `ci.yml` "Production
build guard - mt-node"). If those CI secrets are NOT set, the
`mt-node:0.1.0` tag will be MISSING from GHCR and every hosted-MT
provision will `ImagePullBackOff`. Build + push it explicitly here.

> The mt-node image bakes Wine + the MT5 AND MT4 terminals + the ZeroMQ EA
> into one image. It is large and slow to build (Wine prefix init + two
> installers). Build it on a machine with Docker and good bandwidth, not on
> the Contabo box.

2.5.1 Discover the exact WineHQ apt version to pin (reproducible builds):
```bash
docker run --rm ubuntu:24.04 bash -c '
  apt-get update -qq && apt-get install -y -qq wget gnupg ca-certificates >/dev/null
  install -d -m 0755 /etc/apt/keyrings
  wget -qO- https://dl.winehq.org/wine-builds/winehq.key | gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key
  . /etc/os-release
  echo "deb [signed-by=/etc/apt/keyrings/winehq-archive.key] https://dl.winehq.org/wine-builds/ubuntu/ ${VERSION_CODENAME} main" > /etc/apt/sources.list.d/winehq.list
  apt-get update -qq
  apt-cache policy winehq-stable | sed -n "1,4p"'
# Note the "Candidate:" version string, e.g. 9.0.0.0~noble-1 -> use as WINEHQ_VERSION
```

2.5.2 Compute the committed EA binary SHAs (so CI/build can pin them):
```bash
make mt-node-ea-sha
# Prints EA_EX5_SHA256=<...> and EA_EX4_SHA256=<...> if the .ex4/.ex5 are present.
```

2.5.3 Get the MT5 + MT4 installer SHA256s. Either download once from
MetaQuotes and hash them, OR (recommended for regulated/air-gapped
environments) mirror the installers to your own artifact store and hash
the mirrored blobs:
```bash
curl -fsSL -o /tmp/mt5setup.exe https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
curl -fsSL -o /tmp/mt4setup.exe https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe
sha256sum /tmp/mt5setup.exe /tmp/mt4setup.exe
```

2.5.4 Build (full supply-chain pinning) and push. `make build-mt-node`
wraps `docker build docker/mt-node/` with the build args; `push-mt-node`
builds then pushes:
```bash
echo "$GHCR_PAT" | docker login ghcr.io -u flamegreat-1 --password-stdin
export WINEHQ_VERSION='<from 2.5.1, e.g. 9.0.0.0~noble-1>'
export MT5_INSTALLER_SHA256='<from 2.5.3>'
export MT4_INSTALLER_SHA256='<from 2.5.3>'
export EA_EX5_SHA256='<from 2.5.2>'
export EA_EX4_SHA256='<from 2.5.2 or skip>'
export MT_NODE_TAG='0.1.0'      # MUST equal helm/mt-node/values-image.yaml tag
make push-mt-node
```
Air-gapped variant (own installer mirror) — call docker build directly with
`--build-arg MT5_INSTALLER_URL=` / `MT4_INSTALLER_URL=` pointing at your
mirror (see `docker/mt-node/README.md` "Air-gapped CI").

2.5.5 **Verify the tag now exists** (Phase 0.4's mt-node check must pass):
```bash
docker manifest inspect ghcr.io/flamegreat-1/etradie-mt-node:0.1.0 >/dev/null \
  && echo "mt-node:0.1.0 present" || echo "MISSING - rebuild"
```
> NOTE the registry path difference: the four app services are under
> `ghcr.io/flamegreat-1/etradie/<svc>` (slash), but mt-node is
> `ghcr.io/flamegreat-1/etradie-mt-node` (hyphen), per
> `helm/mt-node/values-image.yaml` and `helm/engine/values-image.yaml`.
> The engine reads this exact string from `MT_NODE_IMAGE` to build tenant pods.

---

## Phase 3 — Vault + Vault Agent Injector

Injector is MANDATORY (per-tenant mt-node credentials are rendered to tmpfs, never a plaintext Secret).

3.1 Install:
```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
kubectl create namespace vault
helm install vault hashicorp/vault \
  --namespace vault --version 0.28.1 \
  --set 'server.standalone.enabled=true' \
  --set 'server.dataStorage.enabled=true' \
  --set 'server.dataStorage.size=10Gi' \
  --set 'server.dataStorage.storageClass=local-path' \
  --set 'injector.enabled=true' \
  --set 'ui.enabled=true'
```

3.2 Init + unseal (STORE `vault-init.txt` OFFLINE — losing it = total data loss):
```bash
kubectl -n vault wait --for=condition=Ready pod/vault-0 --timeout=120s
kubectl -n vault exec -ti vault-0 -- vault operator init -key-shares=5 -key-threshold=3 > vault-init.txt
for i in 1 2 3; do
  KEY=$(grep "Unseal Key $i:" vault-init.txt | awk '{print $4}')
  kubectl -n vault exec -ti vault-0 -- vault operator unseal "$KEY"
done
kubectl -n vault exec -ti vault-0 -- vault status   # Sealed: false
```

3.3 Verify injector:
```bash
kubectl -n vault get pods -l app.kubernetes.io/name=vault-agent-injector   # Running 1/1
```

3.4 Auth + KV mount + ESO policy:
```bash
ROOT_TOKEN=$(grep 'Initial Root Token:' vault-init.txt | awk '{print $4}')
kubectl -n vault port-forward svc/vault 8200:8200 &
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=$ROOT_TOKEN
vault status
vault secrets enable -version=2 -path=secret kv
vault auth enable kubernetes
vault write auth/kubernetes/config kubernetes_host=https://kubernetes.default.svc.cluster.local
vault policy write etradie-eso - <<'EOF'
path "secret/data/etradie/*"     { capabilities = ["read","list"] }
path "secret/metadata/etradie/*" { capabilities = ["read","list"] }
EOF
vault write auth/kubernetes/role/etradie-eso \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=etradie-eso ttl=1h
```

3.5 Token-review SA for the mt-node tenant infra (Phase 11):
```bash
kubectl create serviceaccount -n vault vault-auth 2>/dev/null || true
kubectl create clusterrolebinding vault-auth-delegator \
  --clusterrole=system:auth-delegator --serviceaccount=vault:vault-auth 2>/dev/null || true
```

---

## Phase 4 — External Secrets Operator + ClusterSecretStore

4.1 Install:
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
kubectl create namespace external-secrets
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --version 0.10.4 --set installCRDs=true
kubectl -n external-secrets wait --for=condition=Available deployment/external-secrets --timeout=120s
```

4.2 ClusterSecretStore `vault-backend` (referenced by every chart):
```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "http://vault.vault.svc.cluster.local:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "etradie-eso"
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
EOF
```
**Verify:** `kubectl get clustersecretstore vault-backend -o jsonpath='{.status.conditions[0].reason}'` -> `Valid`.

---

## Phase 5 — Stakater Reloader (REQUIRED)

The mt-node StatefulSet carries `secret.reloader.stakater.com/reload`; without Reloader, ZMQ-token rotation will not roll the pods.
```bash
helm repo add stakater https://stakater.github.io/stakater-charts
helm repo update
helm install reloader stakater/reloader -n reloader --create-namespace
kubectl -n reloader rollout status deployment/reloader-reloader --timeout=120s
```

---

## Phase 6 — Cloudflare Tunnel

6.1 Zero Trust UI -> Networks -> Tunnels -> Create a tunnel -> Cloudflared -> name `etradie-production`. Copy the token (`eyJ...`) — unrecoverable later.
6.2 Public Hostnames tab -> add `api.exoper.com`, Type HTTPS, URL `edge-ingress.edge-ingress-system.svc.cluster.local:443`, leave No TLS Verify UNCHECKED. Repeat for other hosts (e.g. `app`). Cloudflare auto-creates the CNAMEs.
6.3 Note the Tunnel UUID + token.

---

## Phase 7 — Generate the Linkerd mesh CA (mesh is ON)

No cert-manager; CA lives in Vault.
```bash
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca --no-password --insecure
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca --not-after 8760h --no-password --insecure \
  --ca ca.crt --ca-key ca.key
```
Keep `ca.crt` (also passed at control-plane sync, Phase 10.4).

---

## Phase 8 — Bootstrap Vault paths + populate every secret

8.1 Create empty KV paths:
```bash
cd infrastructure/cluster/vault-paths
terraform init
terraform apply -var environment=production -var vault_address=http://127.0.0.1:8200
cd ../../..
```

8.2 Generate shared secrets ONCE (consumers must share identical values):
```bash
DB_PASS=$(openssl rand -hex 32)
REDIS_PASS=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 64)
BROKER_KEY=$(openssl rand -hex 32)
CHROMA_TOKEN=$(openssl rand -hex 32)
ADMIN_PASS=$(openssl rand -hex 24)
ENGINE_SHARED=$(openssl rand -hex 32)
BILLING_SHARED=$(openssl rand -hex 32)
MT_DEFAULT_ZMQ=$(openssl rand -hex 32)
DB_URL_GO="postgres://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=disable"
DB_URL_PY="postgresql+asyncpg://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie"
REDIS0="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/0"
REDIS1="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/1"
```

8.3 Data layer (write FIRST — StatefulSets block without these). Key names EXACT per `vault-paths/main.tf`:
```bash
vault kv put secret/etradie/data-layer/postgres/production \
  postgres_user=etradie postgres_db=etradie postgres_password="${DB_PASS}"
vault kv put secret/etradie/data-layer/redis/production redis_password="${REDIS_PASS}"
# chromadb: SINGLE key 'auth_token' (server + engine both read it)
vault kv put secret/etradie/data-layer/chromadb/production auth_token="${CHROMA_TOKEN}"
```

8.4 Linkerd identity (before control-plane sync):
```bash
vault kv put secret/etradie/platform/linkerd/production \
  trust_anchor_pem=@ca.crt issuer_tls_crt=@issuer.crt issuer_tls_key=@issuer.key
```

8.5 Edge-ingress (AOP CA key MUST be `aop_ca`; MaxMind keys `license_key`+`account_id`):
```bash
vault kv put secret/etradie/services/edge-ingress/production/cloudflare/tunnel \
  tunnel_token='eyJhIjoi...PASTE_FROM_PHASE_6...'
vault kv put secret/etradie/services/edge-ingress/production/cloudflare/aop_ca \
  aop_ca="$(curl -fsS https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem)"
vault kv put secret/etradie/services/edge-ingress/production/maxmind \
  license_key='YOUR_MAXMIND_LICENSE_KEY' account_id='YOUR_MAXMIND_ACCOUNT_ID'
# TLS path empty (Cloudflare terminates public TLS; only needed for cloudProvider=generic)
vault kv put secret/etradie/services/edge-ingress/production/tls \
  api_cert='' api_key='' wildcard_cert='' wildcard_key=''
```

8.6 Gateway (owns JWT + admin password; holds BOTH shared secrets):
```bash
vault kv put secret/etradie/services/gateway/production \
  auth_database_url="${DB_URL_GO}" \
  postgres_user=etradie postgres_password="${DB_PASS}" \
  postgres_host=postgres.etradie-system.svc.cluster.local \
  postgres_port=5432 postgres_db=etradie postgres_sslmode=disable \
  gateway_redis_url="${REDIS0}" \
  auth_jwt_secret="${JWT_SECRET}" auth_admin_password="${ADMIN_PASS}" \
  engine_internal_shared_secret="${ENGINE_SHARED}" \
  billing_internal_shared_secret="${BILLING_SHARED}"
```

8.7 Engine (sole holder of `broker_encryption_key`; chroma token NOT here). Replace provider keys:
```bash
vault kv put secret/etradie/services/engine/production \
  database_url="${DB_URL_PY}" \
  postgres_user=etradie postgres_password="${DB_PASS}" \
  redis_url="${REDIS0}" redis_password="${REDIS_PASS}" \
  broker_encryption_key="${BROKER_KEY}" \
  auth_jwt_secret="${JWT_SECRET}" engine_internal_shared_secret="${ENGINE_SHARED}" \
  cftc_app_token='REPLACE' fred_api_key='REPLACE' twelvedata_api_key='REPLACE' \
  processor_anthropic_api_key='REPLACE' processor_openai_api_key='REPLACE' \
  processor_gemini_api_key='REPLACE' mt5_metaapi_token='REPLACE_OR_OMIT'
```

8.8 Execution + Management (`auth_jwt_secret` AND `engine_internal_shared_secret` MUST equal gateway/engine, else fail-fast when BROKER_MODE=mt5):
```bash
vault kv put secret/etradie/services/execution/production \
  execution_database_url="${DB_URL_GO}" execution_redis_url="${REDIS1}" \
  auth_jwt_secret="${JWT_SECRET}" engine_internal_shared_secret="${ENGINE_SHARED}"
vault kv put secret/etradie/services/management/production \
  management_database_url="${DB_URL_GO}" management_redis_url="${REDIS1}" \
  auth_jwt_secret="${JWT_SECRET}" engine_internal_shared_secret="${ENGINE_SHARED}"
```

8.9 Billing (`internal_shared_secret` MUST equal gateway's `billing_internal_shared_secret`; `billing_redis_url` same Redis the gateway subscribes to). Replace provider values:
```bash
vault kv put secret/etradie/services/billing/production \
  billing_database_url="${DB_URL_GO}" internal_shared_secret="${BILLING_SHARED}" \
  billing_redis_url="${REDIS0}" \
  paddle_webhook_secret='REPLACE' paddle_api_key='REPLACE' \
  paddle_price_pro_byok='REPLACE' paddle_price_pro_managed='REPLACE' \
  lemonsqueezy_webhook_secret='REPLACE' lemonsqueezy_api_key='REPLACE' \
  lemonsqueezy_store_id='REPLACE' \
  lemonsqueezy_variant_pro_byok='REPLACE' lemonsqueezy_variant_pro_managed='REPLACE'
```

8.10 mt-node platform fallback ZMQ token:
```bash
vault kv put secret/etradie/services/mt-node/production default_zmq_auth_token="${MT_DEFAULT_ZMQ}"
```

8.11 Save generated values out-of-band (mode 0600, never commit):
```bash
umask 077
cat > ~/etradie-prod-creds.txt <<EOF
DB_PASS=${DB_PASS}
REDIS_PASS=${REDIS_PASS}
JWT_SECRET=${JWT_SECRET}
ADMIN_PASS=${ADMIN_PASS}
BROKER_KEY=${BROKER_KEY}
CHROMA_TOKEN=${CHROMA_TOKEN}
ENGINE_SHARED=${ENGINE_SHARED}
BILLING_SHARED=${BILLING_SHARED}
EOF
```

---

## Phase 9 — Build + inject the envoy WASM filter

`helm/envoy/values.yaml` ships `wasm.base64: ""`; the chart fails to render until real bytes are supplied, and ArgoCD cannot `--set-file` at sync time, so the bytes must live in a values file the app reads.
```bash
cd src/envoy
rustup target add wasm32-wasi
cargo build --release --target wasm32-wasi
WASM=target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm
cat > ../../helm/envoy/values-production-wasm.yaml <<EOF
wasm:
  base64: "$(base64 -w0 "$WASM")"
  sha256: "$(sha256sum "$WASM" | awk '{print $1}')"
  builtAt: "$(date -u +%FT%TZ)"
EOF
cd ../..
```
Reference the overlay from the envoy production app and push to `main`:
```bash
# Edit deployments/argocd/children/envoy-production.yaml -> source.helm.valueFiles:
#   - values.yaml
#   - values-production.yaml
#   - values-production-wasm.yaml
git add helm/envoy/values-production-wasm.yaml deployments/argocd/children/envoy-production.yaml
git commit -m "deploy: inject production envoy WASM bytes"
git push origin main
```
> The WASM overlay holds compiled filter bytes, no secrets. Prefer a private release branch + `targetRevision` if you do not want it on `main`.

---

## Phase 10 — ArgoCD + both AppProjects + root app

10.1 Install:
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml
kubectl -n argocd wait --for=condition=Available deployment/argocd-server --timeout=180s
```
10.2 Admin password + UI (port-forward only):
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
kubectl -n argocd port-forward svc/argocd-server 8080:443 &   # https://localhost:8080
```
10.2.1 **Log in with the ArgoCD CLI (REQUIRED).** The `argocd app set` in
10.4 and every `argocd app sync` in Phase 12 fail with `not logged in`
without this. Use the port-forward from 10.2 and the password from it:
```bash
ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)
argocd login 127.0.0.1:8080 --username admin --password "$ADMIN_ARGO_PWD" --insecure
argocd account list   # confirms the session works
```
10.3 Apply BOTH AppProjects + root app-of-apps:
```bash
kubectl apply -f deployments/argocd/appproject.yaml
kubectl apply -f deployments/argocd/linkerd-appproject.yaml
kubectl apply -f deployments/argocd/root-app.yaml
```
10.4 Pass the Linkerd trust anchor to the control-plane app (values file leaves it empty by design):
```bash
argocd app set linkerd-control-plane-production --helm-set-file identityTrustAnchorsPEM=ca.crt
```

---

## Phase 11 — Provision mt-node tenant Vault infrastructure

Run AFTER ArgoCD exists. Creates per-tenant Vault auth roles/policies:
```bash
cd infrastructure/cluster/vault-paths
terraform apply \
  -var environment=production -var vault_address=http://127.0.0.1:8200 \
  -var k8s_host=https://kubernetes.default.svc \
  -var k8s_ca_cert="$(kubectl get cm -n kube-system kube-root-ca.crt -o jsonpath='{.data.ca\.crt}')" \
  -var k8s_reviewer_jwt="$(kubectl create token -n vault vault-auth)"
cd ../../..
```

---

## Phase 12 — Sync the platform in dependency order

Production children are manual-sync (`automated.{prune:false,selfHeal:false}`). Sync in EXACT order; wait for Synced+Healthy before the next.

| Order | Application | Wave |
|---|---|---|
| 1 | `linkerd-identity-production` | -6 |
| 2 | `linkerd-crds-production` | -5 |
| 3 | `linkerd-control-plane-production` | -4 |
| 4 | `observability-logs-production` | -2 |
| 5 | `data-layer-production` | -2 |
| 6 | `engine-production` + `mt-node-production` | -1 |
| 7 | `billing-production` | 1 |
| 8 | `gateway-production`, `execution-production`, `management-production` | 0 |
| 9 | `envoy-production` | 5 |
| 10 | `edge-ingress-production` | 10 |

```bash
for app in linkerd-identity-production linkerd-crds-production \
           linkerd-control-plane-production observability-logs-production \
           data-layer-production engine-production mt-node-production \
           billing-production gateway-production execution-production \
           management-production envoy-production edge-ingress-production; do
  echo "=== syncing $app ==="
  argocd app sync "$app" --timeout 600
  argocd app wait "$app" --health --timeout 600
done
```
> The `*-staging` children also exist in `children/`. On a production box, sync ONLY the `*-production` + three `linkerd-*` apps. Do NOT sync `*-staging` on the same cluster (identical namespace/release names).

---

## Phase 13 — Database migrations

The engine deployment's `migrate` init container runs Alembic on every rollout, so a healthy `engine-production` already migrated. Verify:
```bash
kubectl -n etradie-system exec -ti postgres-0 -- psql -U etradie -d etradie -c '\dt'
# Expected: many tables (auth_users, sessions, trades, signals, broker_connections, billing_*, ...)
```
If empty, inspect the init log and fix the cause (usually a wrong `database_url`):
```bash
kubectl -n etradie-system logs deploy/etradie-engine -c migrate
```

---

## Phase 14 — End-to-end verification

14.1 All pods Ready:
```bash
kubectl get pods -A | grep -vE '(Running|Completed)'   # expect empty
```
14.2 Mesh healthy + proxies injected:
```bash
kubectl -n linkerd get pods
kubectl -n etradie-system get pods -o json | jq -r '.items[].spec.containers[].name' | grep -c linkerd-proxy
```
14.3 ESO synced every Secret:
```bash
kubectl get externalsecret -A
```
14.4 Cloudflare Tunnel HEALTHY (Zero Trust UI) and:
```bash
kubectl -n edge-ingress-system logs -l app.kubernetes.io/name=cloudflared --tail=50 | grep -i 'Registered tunnel connection'
```
14.5 Public reachability + auth round-trip:
```bash
ADMIN_PASS=$(vault kv get -field=auth_admin_password secret/etradie/services/gateway/production)
curl -fsS -o /dev/null -w 'edge HTTP %{http_code}\n' https://api.exoper.com/healthz
curl -fsS https://api.exoper.com/api/v1/auth/health
TOKEN=$(curl -fsS -X POST https://api.exoper.com/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"admin\",\"password\":\"${ADMIN_PASS}\"}" | jq -r .access_token)
curl -fsS https://api.exoper.com/api/v1/state/account -H "Authorization: Bearer $TOKEN"
# Expect 200 account JSON (gateway -> execution -> mock broker chain)
```
14.6 Frontend (`cotradee/` on Vercel) reaches `https://api.exoper.com`. The gateway CORS origin is `https://app.exoper.com` (`helm/gateway/values-production.yaml`). If your SPA host differs, update `config.gateway.allowedOrigins` and re-sync gateway.

---

## Phase 14.5 — Hosted-MT (Wine) per-user provisioning + verification

Up to here the **platform** mt-node release is installed (PriorityClass +
platform ExternalSecret + watchdog ConfigMap, from `mt-node-production` in
Phase 12), the Wine image is in GHCR (Phase 2.5), and the per-tenant Vault
auth roles exist (Phase 11). No per-user MT pod exists yet — they are
created **at runtime, on demand**, NOT by ArgoCD.

### 14.5.1 How a tenant pod is created (engine HostedProvisioner)

There is no manual step to create a user's MT terminal in normal operation.
The flow (verified in `src/engine/ta/broker/mt5/hosted/provisioner.py` +
`docker/mt-node/README.md`):

1. A dashboard user adds a broker connection with `connection_type=hosted`.
2. The engine stores `mt5_login` / `mt5_password` / a generated
   `ea_auth_token` (column-encrypted with `broker_encryption_key`) in the
   `broker_connections` row.
3. `HostedProvisioner.provision_account()` then:
   - writes the per-tenant credentials to Vault KV at
     `etradie/data/tenants/mt-node/<connection_id>`
     (keys `mt5_login`, `mt5_password`, `mt5_zmq_auth_token`),
   - creates a per-tenant ServiceAccount `etradie-mt-<id12>` (matches the
     `mt-node-tenant` Vault role's bound-SA glob from Phase 11),
   - creates a `StatefulSet` + ClusterIP `Service` + headless `Service`
     whose labels/selectors/PVC/security context are wire-identical to
     `helm/mt-node/templates/statefulset.yaml`, carrying the Vault Agent
     Injector annotations.
4. The Vault Agent Injector webhook injects `vault-agent-init` (renders
   `/vault/secrets/mt-credentials.env` to tmpfs, exits 0) + `vault-agent`
   (sidecar for rotation). `entrypoint.sh` sources that file; credentials
   never exist as a K8s Secret.
5. `entrypoint.sh` launches Wine + the MT terminal (auto-login from
   `startup.ini`) and loads the ZeroMQ EA with the per-tenant AUTH_TOKEN.
6. `engine.ZmqClient` then dials `<release>.etradie-system.svc:5555`.

**Pre-flight before letting a user pick Hosted MT** (catch the 5xx early):
```bash
# engine SA can create the per-tenant workloads
kubectl auth can-i create statefulsets \
  --as=system:serviceaccount:etradie-system:etradie-engine -n etradie-system
kubectl auth can-i create services \
  --as=system:serviceaccount:etradie-system:etradie-engine -n etradie-system
# platform fallback Secret materialised
kubectl -n etradie-system get externalsecret etradie-mt-node-platform-platform
# engine sees the mt-node image + Vault address
kubectl -n etradie-system get cm etradie-engine-config -o jsonpath='{.data.MT_NODE_IMAGE}{"\n"}{.data.VAULT_ADDR}{"\n"}'
# expect: ghcr.io/flamegreat-1/etradie-mt-node:0.1.0  and  https://vault.vault.svc.cluster.local:8200
```

### 14.5.2 The symbol-resolution two-boot dance (expected, not a fault)

New tenant pods often boot TWICE on purpose. `entrypoint.sh` treats
`MT_SYMBOL=__pending__` as a sentinel:

- **Boot 1 (symbol unresolved):** the entrypoint skips writing the chart
  template / `[Charts]` section and lets MT attach its default chart. The
  EA comes up, the engine queries `GET_ALL_SYMBOLS` against that default
  chart, resolves the broker's actual symbol name (broker symbol names vary,
  e.g. `EURUSD` vs `EURUSD.m`), patches `MT_SYMBOL` on the StatefulSet, and
  K8s rolls the pod once.
- **Boot 2 (symbol resolved):** the entrypoint writes the chart template
  with the real symbol; the EA attaches the intended chart.

So a brand-new hosted connection showing ONE rolling restart shortly after
creation is correct behaviour. A pod stuck rolling repeatedly is not —
see verification below.

### 14.5.3 Verify a hosted-MT tenant (after a user provisions one, or a test connection)
```bash
CONN=<connection-id-prefix>   # first 12 chars of the connection_id; release is etradie-mt-<CONN>
# 1. Pod Ready (mt-node + watchdog + injected vault-agent containers)
kubectl -n etradie-system get pod etradie-mt-${CONN}-0 -o wide
kubectl -n etradie-system get pod etradie-mt-${CONN}-0 \
  -o jsonpath='{range .spec.containers[*]}{.name}{"\n"}{end}'
  # expect: mt-node, watchdog, linkerd-proxy (+ vault-agent as init/sidecar)
# 2. Vault rendered the per-tenant creds onto tmpfs (no plaintext Secret exists)
kubectl -n etradie-system exec etradie-mt-${CONN}-0 -c mt-node -- \
  sh -c 'test -s /vault/secrets/mt-credentials.env && echo creds-present'
# 3. EA health via the watchdog (200 only when mt5_connected=true AND authenticated)
kubectl -n etradie-system port-forward etradie-mt-${CONN}-0 9100:9100 &
curl -fsS http://localhost:9100/healthz && echo OK
curl -s http://localhost:9100/metrics | grep -E 'mt_node_ea_(mt5_connected|authenticated) '
  # both gauges should read 1
# 4. Wine prefix PVC bound (carries the broker 'trusted device' registration)
kubectl -n etradie-system get pvc wine-prefix-etradie-mt-${CONN}-0
# 5. ZMQ bridge reachable from the engine (the engine dials :5555)
kubectl -n etradie-system logs deploy/etradie-engine | grep -i "hosted_" | tail -20
```
De-provision (when a user removes the connection) is also engine-driven
(`HostedProvisioner.delete_account()` deletes the StatefulSet, Services,
Vault path, AND the PVC — StatefulSet GC does not cascade to the PVC).

### 14.5.4 mt-node troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| tenant pod `ImagePullBackOff` | `etradie-mt-node:0.1.0` not in GHCR | complete Phase 2.5 (build+push) |
| pod `Init` on `vault-agent-init` forever | per-tenant Vault role/path missing | re-run Phase 11; confirm SA name matches `etradie-mt-*` glob |
| `/healthz` 503, `mt5_connected=0` | wrong broker creds / server | check `broker_connections` row; broker may need device approval |
| pod rolls repeatedly (not once) | symbol never resolves / EA crash loop | check entrypoint log; broker symbol catalog unreachable |
| dashboard "Hosted MT" returns 5xx | engine SA cannot create workloads | re-run the 14.5.1 `kubectl auth can-i` checks |
| capacity: pod `Pending` | per-user 0.70 CPU exceeds the box (Table 2B ~1 user) | this box hosts ~1 prod MT user; scale hardware for more |

---

## Phase 15 — Post-deploy operational notes

- **Disabled toggles (BUDGET.md Table 2B re-enable index):** HPAs, PDBs, Linkerd `highAvailability`, Linkerd viz, per-service `linkerdPolicy`, snapshotter are intentionally OFF. Each has its re-enable pointer in BUDGET.md. Do not re-enable ad hoc on this box.
- **Mesh verification before per-service authz:** install viz on demand (`git mv deployments/argocd/optional/linkerd-viz-production.yaml deployments/argocd/children/` then sync), run `linkerd viz edges` until every internal edge is SECURED, then set `linkerdPolicy.enabled: true` per service and re-sync. See `docs/runbooks/linkerd-mesh-rollout.md`.
- **Backups:** production postgres backup CronJob + weekly restore drill are ON. Populate the offsite B2 path `etradie/data-layer/postgres-backup/production` (rclone_remote_name, rclone_config, remote_bucket, remote_path_prefix) BEFORE the first 02:00 UTC run. See `docs/runbooks/database-backup-restore.md`.
- **Vault Raft snapshots:** back up Vault out-of-band — it is the source of truth for every secret and the mesh CA.
- **Monitoring (optional):** install kube-prometheus-stack into `monitoring` (AppProject-allowlisted); ServiceMonitors auto-discover via the `prometheus: kube-prometheus` label.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Pod `Pending` forever | ResourceQuota / node ledger full | `kubectl describe pod`; at capacity (Table 2B ~1 prod user) |
| `Init:` > 5 min, init=`wait-for-deps` | dependency not Ready | sync the dependency app first (data-layer -> engine -> gateway) |
| edge-ingress `Init:`, init=`aop-ca-preflight` | AOP CA bytes missing/malformed | re-run Phase 8.5 `aop_ca` |
| `vaultPath is required` render error | a Vault path empty | re-run the matching Phase 8 put |
| ESO `permission denied` | wrong auth role | re-run Phase 3.4 `etradie-eso` role |
| `cloudflared` CrashLoop | wrong tunnel token | re-copy from CF UI, re-write Vault, restart |
| Cloudflare `HTTP 1033` | tunnel not connected | verify outbound :443 from cluster; check token |
| meshed pods never Ready | K3s < 1.29 (no native sidecar) | reinstall K3s >= 1.29 |
| envoy app won't render | WASM bytes missing | complete Phase 9 |

---

## Reference

- Resource profile + capacity: `BUDGET.md` (Table 2B)
- Bootstrap-only steps: `infrastructure/cluster/bootstrap/README.md`
- Vault path schema: `infrastructure/cluster/vault-paths/main.tf`
- Mesh rollout: `docs/runbooks/linkerd-mesh-rollout.md`
- Host hardening: `docs/runbooks/vps-host-hardening.md`
- Backup/restore: `docs/runbooks/database-backup-restore.md`
- Older single-doc guide (image tags there are stale; THIS runbook is authoritative): `docs/deployment/contabo-k3s.md`
