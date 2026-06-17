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

## Daily operator routine (every Phase 3+ command depends on this)

From this point onward, every `kubectl`, `helm`, `argocd`, and `terraform` command in this runbook runs ON YOUR WORKSTATION and reaches the K3s API server on the VPS through an SSH local-forward. The K3s API is firewalled off the public internet by the ufw rules set in Phase 1.6; the SSH tunnel is the only authorized path in.

You must have TWO terminals open at the same time before running any command in Phases 3 onward:

**Terminal 1 — the tunnel terminal.** Opens the encrypted SSH local-forward that carries every `kubectl` / `helm` / `argocd` packet to the K3s API. It is a foreground process and looks frozen (no shell prompt) by design — that is correct. Leave it alone for the entire work session. Closing it (Ctrl+C, `exit`, closing the window) tears the tunnel down immediately and the next `kubectl` call hangs for ~30s and fails with `dial tcp 127.0.0.1:6443: connect: connection refused`.

**Terminal 2 — the working terminal.** This is where every subsequent command in this runbook is typed. You may open additional working terminals (Terminal 3, 4, ...) as needed; they all share the single tunnel from Terminal 1.

### Architecture — where everything actually runs

This is the load-bearing mental model. Every operator on this
platform must internalise it before running any command from
Phase 3 onward.

**The workstation orchestrates. The VPS runs everything.**

When you type `kubectl apply -f ...` or `argocd app sync ...` on
the workstation, you are NOT running anything on the workstation.
You are sending an HTTP request through the SSH tunnel to the K3s
API server on the VPS, which then schedules pods on the VPS,
allocates PVCs from the VPS's disk, and reports results back
through the tunnel to your terminal.

What lives on the workstation:

| File / process | Purpose | Size |
|---|---|---|
| `~/eTradie` (git checkout) | source for `git push`; editing chart values | a few hundred MB |
| `~/.kube/etradie-contabo.yaml` | kubeconfig (cluster URL + client cert) | ~3 KB text |
| `~/vault-init.txt` | Vault unseal keys + root token (Phase 3.2) | ~1 KB, mode 0600 |
| `~/.ghcr_pat`, `~/.ghcr_pull_pat` | GHCR PATs for push + pull | ~50 B each, mode 0600 |
| `~/cloudflare-<env>-tunnel-token.txt` | Cloudflare tunnel connector token | ~200 B, mode 0600 |
| `~/cf-origin-*.{crt,key}` | Cloudflare Origin Certificates | a few KB each, mode 0600 |
| `~/etradie-<env>-creds.txt` | §8.2 generated shared secrets (workstation safety net) | ~1 KB, mode 0600 |
| `~/eTradie/{ca,issuer}.{crt,key}` | Linkerd mesh CA bundle (Phase 7) | a few KB each, mode 0600 |
| `ssh-agent` with the operator's key | unlocks SSH for the tunnel | in-memory |
| Foreground `ssh -N -L 6443 ...` process | the SSH tunnel itself | a few MB resident |
| Foreground `kubectl port-forward ...` processes (ArgoCD, sometimes Prometheus) | ArgoCD CLI + ad-hoc UI access | a few MB each |

What lives on the VPS:

| Resource | Where on the VPS |
|---|---|
| K3s itself (kube-apiserver, controller-manager, scheduler, kubelet, containerd, embedded datastore) | systemd unit `k3s.service` |
| Every pod (Linkerd, Vault, ESO, Reloader, ArgoCD, Prometheus, Grafana, postgres, redis, chromadb, engine, gateway, every workload) | containerd, pod sandbox under `/var/lib/rancher/k3s/` |
| Every PersistentVolume + PVC backing data (postgres 16Gi, redis 8Gi, chromadb 16Gi, Loki 20Gi, Prometheus 20Gi, Vault 10Gi, MT PVCs, etc.) | `/var/lib/rancher/k3s/storage/...` on the VPS NVMe |
| Every Kubernetes Secret + every Vault KV entry | etcd / SQLite (cluster) and Vault PVC (Vault) |
| Every container image pulled from GHCR / Docker Hub | containerd image store on the VPS |
| Every log produced by every container | the VPS journal / pod log files |

What the SSH tunnel actually carries:

When you run `kubectl get pods` on the workstation, this is what
happens:

1. `kubectl` builds a TLS-wrapped HTTPS request locally pointing at
   `https://127.0.0.1:6443` (the workstation loopback).
2. The SSH local-forward (Terminal 1) accepts the TCP connection on
   the workstation's `127.0.0.1:6443`, encrypts the bytes inside
   the existing SSH session, and forwards them to the VPS.
3. On the VPS, `sshd` decrypts and delivers the bytes to
   `127.0.0.1:6443` inside the VPS — which is the K3s API server
   listening on the VPS loopback (ufw blocks it on the public IP).
4. K3s processes the request — looking up pods in its own datastore
   ON THE VPS, scheduling new pods if applicable ON THE VPS,
   touching no resource on the workstation.
5. K3s sends the response back through the same channel; `kubectl`
   renders it to your terminal.

The workstation is a thin client. Its disk, CPU, and RAM usage do
not change meaningfully when 100+ pods spin up on the VPS. The 20Gi
Prometheus PVC, the postgres database, every container image, every
log — all on the VPS.

**Implication for capacity planning.** When BUDGET.md Table 2B says
“staging fits ~4–5 test users on 8 vCPU / 24 GB / 200 GB”, those
are VPS resources. Your workstation is irrelevant to that ledger.

**Implication for failure modes.** If your laptop dies mid-deploy,
the cluster keeps running. If WSL crashes, the cluster keeps
running. If the SSH tunnel drops, your `kubectl` calls fail but the
VPS-side workloads continue undisturbed. Reopening the tunnel is
always safe.

**Implication for security.** Every credential the platform uses
lives in Vault on the VPS. The handful of files on your workstation
are bootstrap-only (kubeconfig, Vault unseal keys, GHCR PATs,
Cloudflare tokens, the mesh CA bundle). Lose the workstation and
you lose access to operate the cluster, but you do not lose any
platform data; the rotation playbook in Phase 15 + Phase 3.4 covers
rebuilding operator access from a fresh workstation.

Run these once per WSL boot, in this order:

```bash
# 1. Unlock the SSH private key into ssh-agent (once per WSL boot).
#    Without this, every ssh / scp / tunnel command prompts for the
#    passphrase. The agent persists across new terminals WITHIN one
#    WSL session (see Phase 1 measure 2 for the ~/.bashrc snippet);
#    a wsl --shutdown / workstation reboot / last-window-closed event
#    kills the agent and you must re-run this on the next WSL boot.
ssh-add ~/.ssh/id_ed25519
ssh-add -l                                              # confirm the key is loaded

# 1b. Ensure KUBECONFIG is exported in THIS shell. The ~/.bashrc
#     export added in Phase 2.3 covers new shells, but a Terminal 2
#     opened BEFORE that change won't have it. Belt-and-braces:
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl config current-context >/dev/null || echo "WARN kubeconfig issue"

# 2. Open the tunnel IN A DEDICATED TERMINAL (Terminal 1).
#    -N: do not run a remote command; just forward.
#    -L 6443:127.0.0.1:6443: forward local 6443 -> VPS 127.0.0.1:6443
#    (the K3s API binds loopback inside the VPS; ufw blocks the
#    public interface; the tunnel terminates onto the loopback that
#    K3s already trusts).
#    Replace 13.140.164.173 with the actual VPS public IP.
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173
#    ^ no prompt returns. Leave this terminal open. Do not Ctrl+C.
```

In a SEPARATE terminal (Terminal 2), verify the tunnel is live before running ANY runbook command:

```bash
kubectl get nodes
# expect: vmi3362776   Ready   control-plane,master   ...   v1.30.4+k3s1
```

If `kubectl get nodes` hangs for ~30s and then fails, the tunnel is down. Re-run the Terminal 1 command. Common causes: Terminal 1 was closed, WSL was shut down, the workstation was rebooted, the network changed (laptop sleep / wifi switch). Reopening the tunnel is always safe.

**Optional — self-healing tunnel.** For long work sessions (a full deploy day) operators may install `autossh` and replace the Terminal 1 command with:

```bash
sudo apt install -y autossh
autossh -M 0 -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173
```

`autossh` watches the tunnel and reconnects automatically over network blips (laptop suspend, wifi switch, NAT timeout). The dedicated-terminal pattern with plain `ssh` works fine for shorter sessions and was used for the staging deploy.

**Safety — do NOT run runbook commands as `root` over a plain `ssh etradie@<host>` shell.** A plain shell on the VPS lacks the workstation tooling (helm, terraform, argocd CLI, the cloned repo) and bypasses the kubeconfig-based RBAC posture this runbook depends on. The tunnel-from-workstation pattern is the canonical operator topology for every phase below.

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

> This phase is environment-independent: the same commands run for
> staging and production. Where the original README used a workstation
> `vault` CLI through `kubectl port-forward`, this revision uses
> `kubectl exec -i vault-0 -- env VAULT_TOKEN=... vault ...` instead.
> The in-pod pattern uses the exact Vault binary the server ships,
> needs no local CLI, and avoids the port-forward staying bound to a
> shell PID. Two reasons matter:
>
> - **No `vault` CLI on the workstation by design.** Phase 0.1 step 2
>   disabled and masked the workstation `vault.service` unit (apt
>   ships server+CLI together; the unit competes with the platform
>   forward on port 8200). The in-pod pattern sidesteps the whole
>   class of CLI-version / port-collision issues.
> - **`kubectl exec -ti` corrupts captured Vault output.** Vault
>   writes ANSI color escapes when stdout is a TTY. Capturing
>   `vault operator init` to a file produces `\x1b[0m...\x1b[0m`
>   framing around each Unseal Key + the root token; `vault operator
>   unseal` then rejects extracted strings with `400 'key' must be a
>   valid hex or base64 string`. This revision drops `-t` from every
>   `exec` and pipes init output through `tr -d '\r' | sed
>   's/\x1b\[[0-9;]*m//g'` at capture time.

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

**Verify before continuing:**
```bash
kubectl -n vault get pods
kubectl -n vault get pvc
```
Expect: `vault-0` Running **0/1** (sealed — readiness gates on `Sealed=false`, this is normal), `vault-agent-injector-...` Running **1/1**, PVC `data-vault-0` Bound 10Gi `local-path`.

3.2 Init + unseal (STORE `vault-init.txt` OFFLINE — losing it = total data loss):
```bash
cd ~
umask 077
# Capture init output with TTY artefacts stripped at write time.
# Dropping -t prevents the ANSI escapes; tr+sed scrub anything that
# slips through. The 'wait' may report timeout because vault-0 is
# sealed (0/1) — that is expected; kubectl exec works on a sealed Vault.
kubectl -n vault wait --for=condition=Ready pod/vault-0 --timeout=120s 2>&1 || true
kubectl -n vault exec -i vault-0 -- vault operator init -key-shares=5 -key-threshold=3 \
  | tr -d '\r' | sed 's/\x1b\[[0-9;]*m//g' > vault-init.txt
chmod 600 vault-init.txt
ls -la ~/vault-init.txt
wc -l ~/vault-init.txt   # 11 lines: 5 unseal keys + blank + root token + blank + 3-line preamble
```

Unseal with the first three Shamir shares (threshold is 3 of 5):
```bash
for i in 1 2 3; do
  KEY=$(awk -v n="$i" '$0 ~ "Unseal Key " n ":" {print $NF}' ~/vault-init.txt)
  kubectl -n vault exec -i vault-0 -- vault operator unseal "$KEY"
done
kubectl -n vault exec -i vault-0 -- vault status   # Initialized true / Sealed false
kubectl -n vault get pods                          # vault-0 now Running 1/1
```

3.3 Verify injector (already covered by 3.1's `get pods`, included for completeness):
```bash
kubectl -n vault get pods -l app.kubernetes.io/name=vault-agent-injector   # Running 1/1
```

3.4 Auth + KV mount + ESO policy + role (all in-pod, no port-forward, no local `vault` CLI):
```bash
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
test -n "$ROOT_TOKEN" && echo "root token captured: ${#ROOT_TOKEN} chars" || { echo "FAILED to capture root token"; exit 1; }
# Vault 1.17 root tokens are 'hvs.' + 24 chars = 28 chars total.

# 3.4.1 — Enable KV-v2 at path 'secret' (dev/test mount).
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault secrets enable -version=2 -path=secret kv 2>/dev/null \
  || echo "secret/ mount already enabled — idempotent, continuing"

# 3.4.1b — Enable KV-v2 at path 'etradie' (CANONICAL platform mount).
# infrastructure/cluster/vault-paths/variables.tf defaults vault_mount
# to 'etradie'; every chart ExternalSecret reads from this mount via
# the ClusterSecretStore (configured in §4.2 to point at this path).
# The dev 'secret/' mount above is intentionally not the canonical
# location — see the variables.tf comment about production posture.
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault secrets enable -version=2 -path=etradie kv 2>/dev/null \
  || echo "etradie/ mount already enabled — idempotent, continuing"

# Verify both mounts exist.
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault secrets list | grep -E '^(secret|etradie)/'
# Expect TWO lines: secret/ and etradie/

# 3.4.2 — Enable Kubernetes auth backend.
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault auth enable kubernetes

# 3.4.3 — Configure Kubernetes auth backend.
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault write auth/kubernetes/config kubernetes_host=https://kubernetes.default.svc.cluster.local

# 3.4.4 — Write the etradie-eso policy via heredoc-to-/tmp/eso.hcl inside the pod
#         (the original `vault policy write etradie-eso - <<EOF` pipes stdin
#         through kubectl exec, which is brittle for multi-line input).
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" sh -c 'cat > /tmp/eso.hcl <<EOF
path "secret/data/etradie/*"     { capabilities = ["read","list"] }
path "secret/metadata/etradie/*" { capabilities = ["read","list"] }
EOF
vault policy write etradie-eso /tmp/eso.hcl
rm -f /tmp/eso.hcl'

# 3.4.5 — Create the Kubernetes auth role bound to the ESO ServiceAccount.
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault write auth/kubernetes/role/etradie-eso \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=etradie-eso ttl=1h
```

**Verify 3.4 stuck:**
```bash
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault secrets list                     # secret/ kv present
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault auth list                        # kubernetes/ present
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault policy read etradie-eso          # 2 path stanzas
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault read auth/kubernetes/role/etradie-eso
# expect: bound_service_account_names=[external-secrets],
#         bound_service_account_namespaces=[external-secrets],
#         policies=[etradie-eso], token_ttl=1h
```

3.5 Token-review SA for the mt-node tenant infra (Phase 11):
```bash
kubectl create serviceaccount -n vault vault-auth 2>/dev/null || true
kubectl create clusterrolebinding vault-auth-delegator \
  --clusterrole=system:auth-delegator --serviceaccount=vault:vault-auth 2>/dev/null || true
kubectl -n vault get sa vault-auth
kubectl get clusterrolebinding vault-auth-delegator
```
The `|| true` is precautionary — the Vault chart MAY auto-create the SA when `injector.enabled=true`, depending on chart version. Whether the chart pre-created it or not, both objects must exist before Phase 11's Terraform runs `kubectl create token -n vault vault-auth`.

> **Alternate path (port-forward + workstation `vault` CLI)** — preserved for operators who already have a properly-installed local Vault CLI and prefer it. NOT the recommended path: it adds a port-forward you must keep alive in a background shell and requires the local binary's version to be compatible with the server. If you take this path, the commands above remain valid up to and including 3.2's unseal; from 3.4 you would run instead:
> ```bash
> ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
> kubectl -n vault port-forward svc/vault 8200:8200 &
> export VAULT_ADDR=http://127.0.0.1:8200
> export VAULT_TOKEN=$ROOT_TOKEN
> vault status
> # then the original `vault secrets enable / auth enable / write / policy / write role` commands.
> ```

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

4.2 ClusterSecretStore `vault-backend` (referenced by every chart).
The `path` field MUST equal the canonical KV-v2 mount from §3.4.1b
(`etradie`), NOT the dev/test mount `secret`. Audit ref:
`infrastructure/cluster/vault-paths/variables.tf::vault_mount`.

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
      path: "etradie"
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
**Verify:**
```bash
kubectl get clustersecretstore vault-backend -o jsonpath='{.spec.provider.vault.path}{"\n"}'
# expect: etradie
kubectl get clustersecretstore vault-backend -o jsonpath='{.status.conditions[0].reason}{"\n"}'
# expect: Valid
```

> **Re-running an existing deploy where the ClusterSecretStore was
> created with `path: secret`?** The staging deploy that produced this
> revision hit exactly that. Patch in place; ESO refreshes within
> the next reconcile interval:
> ```bash
> kubectl patch clustersecretstore vault-backend --type=merge \
>   -p '{"spec":{"provider":{"vault":{"path":"etradie"}}}}'
> kubectl get clustersecretstore vault-backend \
>   -o jsonpath='{.spec.provider.vault.path} {.status.conditions[0].reason}{"\n"}'
> # expect: etradie Valid
> ```

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

Cloudflare control-plane work — no `kubectl`, no VPS access. By the end
of this phase you have:

- a cloudflared tunnel named `etradie-<env>` registered with Cloudflare,
- its single-use connector token saved to a `0600` file on the
  workstation (to be written into Vault in Phase 8.5),
- a tunnel ingress rule pointing the public hostname at the in-cluster
  `edge-ingress` Service,
- a proxied CNAME for that hostname in the `exoper.com` zone,
- and the Tunnel UUID recorded for the Phase 8.5 / 11 / 12 entries
  that consume it.

The tunnel will display `Inactive` in the Cloudflare dashboard at the
end of this phase. That is correct — see 6.3 below for the full
explanation. Do NOT try to bring it Active here.

> **Why this phase uses the Cloudflare REST API for the ingress
> + DNS, not the dashboard UI.** The original runbook (pre staging
> deploy 2026-06-14) said "Public Hostnames tab → add `api.<domain>`".
> Cloudflare has since migrated accounts to the new "Networks"
> Cloudflare One UI, which removed the classic per-tunnel **Public
> Hostname** tab entirely. The surviving in-UI "Hostname routes"
> tab only offers the **private** hostname flow (requires Cloudflare
> One Client on every end-user device — wrong for our public-facing
> `<env>-api.exoper.com`). Direct legacy URLs
> `/<account-id>/access/tunnels/<uuid>` and
> `/<account-id>/networks/tunnels/cfd_tunnel/<uuid>/edit` return
> `We could not find that page.` Drive the configuration via the
> REST API instead. The end-state on Cloudflare's edge is identical
> to what the old UI produced.

> **Production vs staging conventions used below.** This phase is
> environment-aware in TWO places:
> - **Tunnel name**: `etradie-staging` on the staging box, `etradie-production` on the production box. They are independent tunnels with independent UUIDs and independent tokens.
> - **Public hostname**: `staging-api.exoper.com` for staging, `api.exoper.com` for production. The repo's chart values (`helm/edge-ingress/values-staging.yaml` / `values-production.yaml`) already align with these names; do not invent a third pattern.
>
> All commands below use a single `ENV` variable so the same block
> works on either box. Set it ONCE at the top of the phase and leave
> it alone for the rest:
> ```bash
> ENV=staging       # or 'production' for the production deploy
> ```

### 6.1 — Create the tunnel in the Cloudflare dashboard, capture the token

This step is the one part of Phase 6 the UI still handles correctly.

1. Open <https://one.dash.cloudflare.com/>.
2. Left sidebar: **Networks → Tunnels** (the new UI may also expose a
   top-level **Tunnels** entry; either lands on the same page).
3. Click **Create a tunnel**.
4. Tunnel type: **Cloudflared**. Click **Next**.
5. Name: `etradie-<env>` exactly (`etradie-staging` or `etradie-production`).
   The two names must NOT be reused across environments — each tunnel
   has its own UUID + token and points at a different in-cluster
   `edge-ingress` Service in a different namespace.
6. Click **Save tunnel**.
7. The next screen shows installation commands for various OSes.
   **IGNORE the install commands.** `cloudflared` will run as a
   Deployment inside the K3s cluster, shipped by the `edge-ingress`
   Helm chart in Phase 12. Running the install command on the
   workstation would register the workstation itself as the connector,
   which would expose the public hostname from your laptop — the
   opposite of the intended architecture.
8. Scroll down on that screen until you see the token field. The token
   is a single long string starting with `eyJ` (a JWT-style base64
   payload, typically ~180–220 chars). Select **only** the token,
   copy it.

**You only ever see this token once.** Capture it on the workstation
NOW, before clicking Next, into a `0600` file that Phase 8.5 will
read:

```bash
umask 077
cat > ~/cloudflare-${ENV}-tunnel-token.txt
# right-click / Ctrl-Shift-V to paste the eyJ... token
# press Enter once
# press Ctrl-D to close stdin
chmod 600 ~/cloudflare-${ENV}-tunnel-token.txt
```

Verify the file looks sane WITHOUT echoing its content:

```bash
ls -la ~/cloudflare-${ENV}-tunnel-token.txt    # mode 0600, owner-only
wc -c ~/cloudflare-${ENV}-tunnel-token.txt     # expect ~180–230 bytes
head -c 4 ~/cloudflare-${ENV}-tunnel-token.txt; echo  # MUST print: eyJh
tail -c 2 ~/cloudflare-${ENV}-tunnel-token.txt | od -c | head -1
# expect: "  9  \n" or similar — exactly one trailing newline, no stray bytes
```

If `head -c 4` prints anything other than `eyJh`, the paste captured
leading whitespace or part of the surrounding install command — wipe
and retry:

```bash
rm -f ~/cloudflare-${ENV}-tunnel-token.txt
umask 077
cat > ~/cloudflare-${ENV}-tunnel-token.txt
# re-paste, more carefully selecting only the eyJ... bytes
```

The token is still on the Cloudflare screen until you click Next —
re-copying is fine.

Once the file is verified, you may click **Next** in the Cloudflare
UI to leave the install screen. The next page ("Route tunnel") will
offer only the wrong (private-hostname) flow. **Do not configure
anything on that page; just leave it.** Step 6.2 below does that part
via API.

Also copy the **Tunnel UUID** off the dashboard URL while you're on
the tunnel detail page — you need it for 6.2:

```
https://one.dash.cloudflare.com/<account-id>/networks/tunnels/cfd_tunnel/<TUNNEL-UUID>
                                                                          ^^^^^^^^^^^^
                                          36-char string, e.g. 6d46295b-488e-49d6-9b7e-b699b310a1ec
```

It is not a secret. Record it in your scratch notes.

### 6.2 — Wire the public hostname + DNS via the Cloudflare REST API

This step has three parts: mint a scoped bootstrap API token, write
the tunnel ingress, and verify the auto-created CNAME. The token is
short-lived (48h is plenty); shred it from the workstation when
Phase 6 is done.

**6.2.1 — Mint a scoped API token.**

1. Open <https://dash.cloudflare.com/profile/api-tokens>.
2. Click **Create Token** → scroll to **Custom token** → **Get started**.
3. Fill in:
   - **Token name**: `etradie-<env>-tunnel-bootstrap`
   - **Permissions** (three rows; click "+ Add more" between them):
     - `Account` | `Cloudflare Tunnel` | **Edit**
     - `Account` | `Account Settings` | **Read**
     - `Zone` | `DNS` | **Edit**
   - **Account Resources**: `Include` → the account that owns this tunnel.
   - **Zone Resources**: `Include` → `Specific zone` → `exoper.com`.
   - **Client IP Address Filtering**: **leave blank**. Your workstation NAT
     exit IP may change between commands; pinning to today's IP risks
     401-ing the API mid-phase for zero security gain on a 48h credential.
   - **TTL**: Start = today, End = day-after-today (~48h).
4. **Continue to summary** → **Create Token**.
5. Cloudflare displays the token **once** in a green box. Copy it.
6. Capture it on the workstation:
   ```bash
   umask 077
   cat > ~/.cloudflare-${ENV}-api-token.txt
   # paste the token → Enter → Ctrl-D
   chmod 600 ~/.cloudflare-${ENV}-api-token.txt
   ```
7. Verify it works (the verify endpoint exists for exactly this):
   ```bash
   curl -fsS -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
     -H "Authorization: Bearer $(cat ~/.cloudflare-${ENV}-api-token.txt)" \
     -H "Content-Type: application/json" | jq .
   ```
   Expect `"status": "active"` and `"success": true`.

**6.2.2 — Set the shell variables the curl calls reference.**

Gather the four identifiers up front so the rest of 6.2 is a clean
copy-paste. The two `*_ID` values come from your dashboard URL
(account ID is the 32-hex string in `dash.cloudflare.com/<id>/...`)
and from a one-shot API query (zone ID); the tunnel ID is the UUID
you recorded at the end of 6.1; the hostname is the env-specific
name.

```bash
CF_TOKEN=$(cat ~/.cloudflare-${ENV}-api-token.txt)

ACCOUNT_ID="<paste the 32-hex account ID from your dashboard URL>"
TUNNEL_ID="<paste the tunnel UUID from 6.1>"
HOSTNAME="${ENV}-api.exoper.com"        # staging-api.exoper.com or production-api.exoper.com? See note.
ORIGIN_URL="https://edge-ingress.edge-ingress-system.svc.cluster.local:443"

# Look up the zone ID for exoper.com via the API (one less thing to mis-copy)
ZONE_ID=$(curl -fsS -X GET "https://api.cloudflare.com/client/v4/zones?name=exoper.com" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" | jq -r '.result[0].id')

echo "ACCOUNT_ID=$ACCOUNT_ID"
echo "TUNNEL_ID=$TUNNEL_ID"
echo "ZONE_ID=$ZONE_ID"
echo "HOSTNAME=$HOSTNAME"
echo "ORIGIN_URL=$ORIGIN_URL"
```

> **Hostname naming — read this before pasting.** The chart values in
> `helm/edge-ingress/values-staging.yaml` and
> `helm/edge-ingress/values-production.yaml` are the source of truth.
> The staging hostname is `staging-api.exoper.com` (NO `production-api`
> equivalent; production uses the shorter `api.exoper.com`). Set
> `HOSTNAME` accordingly:
>
> | Environment | `HOSTNAME` value |
> |---|---|
> | `staging` | `staging-api.exoper.com` |
> | `production` | `api.exoper.com` |
>
> If you change this, also align `helm/edge-ingress/values-<env>.yaml`
> and the gateway's `allowedOrigins` — a mismatch will surface in
> Phase 14.5 as 4xx CORS rejections, not as anything obvious from
> the tunnel layer.

If `ZONE_ID` is empty or `null`, the token does not have visibility
into the zone. Re-check the token's "Zone Resources" include rule
and redo 6.2.1 before continuing.

**6.2.3 — Write the tunnel ingress configuration (the load-bearing step).**

This is the call that wires `<env>-api.exoper.com` to the in-cluster
edge-ingress Service. Cloudflare's `configurations` endpoint also
auto-creates the matching CNAME in the `exoper.com` zone on first
write, so a separate DNS POST is NOT required.

```bash
curl -fsS -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/configurations" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  --data @- <<JSON | jq .
{
  "config": {
    "ingress": [
      {
        "hostname": "${HOSTNAME}",
        "service": "${ORIGIN_URL}",
        "originRequest": {
          "noTLSVerify": false,
          "http2Origin": false,
          "connectTimeout": 30,
          "tlsTimeout": 10,
          "tcpKeepAlive": 30,
          "keepAliveConnections": 100,
          "keepAliveTimeout": 90
        }
      },
      {
        "service": "http_status:404"
      }
    ]
  }
}
JSON
```

Expected response ends with `"success": true` and a `result.config`
block that echoes the ingress you sent, `result.version: 1` on the
first write (incremented on every subsequent PUT to this tunnel),
and `result.config.warp-routing.enabled: false`.

The trailing `{"service": "http_status:404"}` rule is **mandatory**.
Cloudflare rejects the PUT with `1003 invalid ingress: no catch-all
rule` if the array does not END with a rule that has no `hostname`
field and a `service` value of `http_status:<code>`.

`noTLSVerify: false` is also **mandatory** for Tier 11. The
Authenticated Origin Pull CA bytes (`aop_ca`) written into Vault in
Phase 8.5 only get enforced when this flag is `false`. Setting it
`true` appears to work because Cloudflare still establishes TLS to
edge-ingress — but the cert is never verified, which means anything
that lands on the host network can impersonate edge-ingress and the
tunnel will route traffic to it.

**6.2.4 — Verify the CNAME Cloudflare auto-created.**

```bash
curl -fsS -X GET \
  "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records?name=${HOSTNAME}&type=CNAME" \
  -H "Authorization: Bearer $CF_TOKEN" | jq '.result[] | {id, name, type, content, proxied, ttl, comment}'
```

Expected output (UUID in `content` MUST equal your `TUNNEL_ID`):

```json
{
  "id": "<dns-record-id>",
  "name": "<env>-api.exoper.com",
  "type": "CNAME",
  "content": "<TUNNEL_ID>.cfargotunnel.com",
  "proxied": true,
  "ttl": 1,
  "comment": null
}
```

If you ran an explicit `POST /zones/.../dns_records` against the same
name (e.g. following an older runbook), Cloudflare returns
`81053 An A, AAAA, or CNAME record with that host already exists.`
That error is **harmless** — the auto-created CNAME is already correct
and matches the tunnel. Skip the POST and rely on the GET above to
verify state.

If the UUID in `content` does NOT equal `TUNNEL_ID` (e.g. a stale
CNAME from a deleted tunnel), patch the existing record in place:

```bash
RECORD_ID=$(curl -fsS -X GET \
  "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records?name=${HOSTNAME}&type=CNAME" \
  -H "Authorization: Bearer $CF_TOKEN" | jq -r '.result[0].id')
curl -fsS -X PATCH \
  "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records/${RECORD_ID}" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  --data "{\"content\":\"${TUNNEL_ID}.cfargotunnel.com\",\"proxied\":true,\"ttl\":1}" | jq .
```

**6.2.5 — Verify public DNS resolves to Cloudflare anycast.**

DNS propagation for a brand-new proxied record is usually a few
seconds. Use whatever resolver the workstation has on the PATH:

```bash
# Prefer dig if installed; fall back to getent (always present on Linux).
dig +short "${HOSTNAME}" 2>/dev/null || getent hosts "${HOSTNAME}"
```

Expected result: one or more Cloudflare anycast IPs — IPv4 in
`104.21.0.0/16` or `172.67.0.0/16`, IPv6 in `2606:4700::/32`. NOT the
`*.cfargotunnel.com` target. Cloudflare's proxy is intercepting the
name and answering with its own edge IPs; that is the correct
resolved view from the public internet.

Then confirm reachability with `curl`:

```bash
curl -sS -o /dev/null -w 'http_code=%{http_code} resolved=%{remote_ip}\n' \
  "https://${HOSTNAME}/"
```

**Expected: `http_code=530 resolved=<cloudflare anycast IP>`.** HTTP
530 (or HTML error 1033) is Cloudflare's "origin is unreachable" code,
returned because the in-cluster `cloudflared` Deployment does not yet
exist (Phase 12 is what creates it). The 530 here is the *correct
intermediate state*, not a fault. It proves the entire public path is
wired: DNS → Cloudflare edge → tunnel → (no connector yet) → 530.

**6.2.6 — Shred the bootstrap API token.**

The token's job is done; it is not used anywhere else in the deploy.

```bash
shred -u ~/.cloudflare-${ENV}-api-token.txt
```

The server-side credential still exists at Cloudflare and will
auto-expire on its TTL (the 48h window from 6.2.1). The `shred` step
just ensures it cannot be re-used from this workstation.

### 6.3 — Record the Tunnel UUID + token file location, leave the tunnel Inactive

Write the values into your deploy notes (and, for the staging deploy
that produced this runbook revision, into `docs/runbooks/PROGRESS.md`
under Phase 6):

| Value | Source | Used in |
|---|---|---|
| Tunnel name | Cloudflare dashboard | Phase 14.4 (`cloudflared` log grep) |
| Tunnel UUID (36-char) | dashboard URL `/cfd_tunnel/<UUID>` | (notebook only — the token holds the binding at runtime) |
| Public hostname | the `HOSTNAME` variable above | Phase 14.5 (`curl https://${HOSTNAME}/healthz`) |
| Tunnel token file (0600) | written in 6.1 | Phase 8.5 (`vault kv put .../cloudflare/tunnel tunnel_token=@~/cloudflare-${ENV}-tunnel-token.txt`) |
| Cloudflare account ID + zone ID | from 6.2.2 | (notebook only; not consumed elsewhere) |

**The tunnel will display `Inactive` in the Cloudflare dashboard, with
zero connectors registered and `Uptime: --`, for the entire window
between end-of-Phase-6 and the `edge-ingress-<env>` sync in Phase 12.
That is correct and required.** The architecture is:

1. Phase 6 (now): tunnel object exists, ingress points at
   `edge-ingress.edge-ingress-system.svc.cluster.local:443`, DNS points
   the public hostname at Cloudflare's edge, token is sitting in a 0600
   file on the workstation.
2. Phase 8.5: token bytes get written into Vault at
   `secret/etradie/services/edge-ingress/<env>/cloudflare/tunnel`
   (key `tunnel_token`).
3. Phase 12: ArgoCD syncs `edge-ingress-<env>`, which spins up a
   `cloudflared` Deployment in the `edge-ingress-system` namespace.
   The Deployment reads the token (via ESO → K8s Secret → env var or
   mounted file, per chart), dials Cloudflare's edge over outbound
   :443, registers as the tunnel's connector, and the dashboard
   flips to **Healthy** with Uptime ticking.

**Do NOT try to bring the tunnel Active before Phase 12** by running
`cloudflared service install <token>` on the workstation or anywhere
else. That command registers whichever machine it runs on as the
connector for the tunnel — i.e. it would expose
`<env>-api.exoper.com` from your laptop instead of from the cluster.
Undoing that requires deleting the rogue connector via the
dashboard's Connectors tab; the time cost is minutes, but the
security posture has been broken in the meantime (your home network
was a public origin for a few minutes).

Similarly, the `curl` 530 from 6.2.5 is NOT a Phase 6 failure to
chase. If it returns anything other than 530 / 1033 / a Cloudflare
error page at this point — e.g. a real `2xx` or a non-Cloudflare 5xx
— something is wired wrong (most likely an attacker-controlled
origin has been pointed at the same hostname, or you accidentally ran
cloudflared on the workstation). Stop and debug; do NOT proceed to
Phase 7 with a Cloudflare-side anomaly unresolved.

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

Longest single phase in the runbook. Eleven sub-steps, runs in one
workstation session (~30 minutes including the verification block).
Written staging-canonical; the **production deviations** are called
out inline where they differ (Paddle/LS real creds, postgres-backup
offsite credentials, single `api.exoper.com` hostname instead of
`staging-api` + staging wildcard).

> **Source of truth for every key name in this phase.** Each
> `vault kv put` writes EXACTLY the property names the chart's
> `ExternalSecret` template reads. Property name mismatch — even by
> one character or a typo — silently produces an empty K8s Secret
> value, and the consumer pod CrashLoops at boot with a confusing
> validation error pointing at the application layer instead of the
> Vault layer. Do NOT "clean up" any of the names below to match
> some other naming convention you might be familiar with; the names
> here were extracted directly from the ESO templates by
> `grep -rn 'property:' helm/*/templates/*externalsecret*.yaml` and
> are the canonical contract. Audit ref: end-to-end audit during the
> staging deploy 2026-06-14.

> **Single `ENV` variable for the whole phase.** Set it ONCE at the
> top and leave it for the rest of the phase:
> ```bash
> ENV=staging       # or 'production' for the production deploy
> ```
> Every command below references `${ENV}`; do not hard-code `staging`
> or `production` in any individual line.

### 8.0 — Pre-flight (do this BEFORE the first `vault kv put`)

A mid-phase failure on a missing file or a dead tunnel is far more
painful than a 90-second up-front check.

> **Why each check uses an explicit `|| { echo FAIL; exit 1; }` arm.**
> The earlier pattern `cmd && echo OK` was unsafe: when `cmd` failed,
> the `&& echo OK` branch was skipped silently AND `set -e` did NOT
> exit (because `set -e` ignores failures on the left of `&&` by
> design). Execution continued and the script eventually printed
> "=== All pre-flight checks passed ===" even though required checks
> had failed. Captured as Phase 8 operator gotcha in PROGRESS.md.

```bash
set -e
ENV=staging   # or production
echo "=== Phase 8 pre-flight for ENV=${ENV} ==="

# 0. KUBECONFIG must point at the workstation copy of the K3s
#    kubeconfig. The ~/.bashrc export from Phase 2.3 covers new
#    shells, but a shell opened BEFORE that change never sourced it.
#    Re-export inline so this script self-heals.
if [ -z "$KUBECONFIG" ]; then
  export KUBECONFIG=~/.kube/etradie-contabo.yaml
  echo "OK KUBECONFIG exported inline (~/.bashrc may pre-date Phase 2.3)"
else
  echo "OK KUBECONFIG=$KUBECONFIG"
fi
test -s "$KUBECONFIG" || { echo "FAIL kubeconfig file missing"; exit 1; }

# 1. Phase 2.3 SSH local-forward is alive. Phase 8.1 (terraform) needs
#    kubectl reachability; later sub-steps need kubectl exec into vault-0.
#    EXPLICIT || arms because `&& echo OK` alone is unsafe under set -e.
kubectl get nodes >/dev/null 2>&1 \
  && echo OK "K3s reachable" \
  || { echo "FAIL kubectl get nodes — check tunnel (ss -tln \| grep 6443) and KUBECONFIG"; exit 1; }
phase=$(kubectl -n vault get pod vault-0 -o jsonpath='{.status.phase}' 2>/dev/null)
test "$phase" = Running \
  && echo OK "vault-0 Running" \
  || { echo "FAIL vault-0 phase='${phase}' (expected Running) — check `kubectl -n vault get pods`"; exit 1; }

# 2. Vault root token from Phase 3.2.
test -s ~/vault-init.txt && echo OK "vault-init.txt present" || {
  echo "FAIL ~/vault-init.txt missing — re-run Phase 3.2"; exit 1; }
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
test -n "$ROOT_TOKEN" && echo "OK root token captured (${#ROOT_TOKEN} chars)" || {
  echo "FAIL root token extraction failed"; exit 1; }

# 3. Phase 7 mesh CA files are at the repo root. Phase 8.5 reads them.
cd ~/eTradie
for f in ca.crt ca.key issuer.crt issuer.key; do
  test -s "$f" && echo "OK $f" || { echo "FAIL $f missing — re-run Phase 7"; exit 1; }
done
step certificate verify issuer.crt --roots ca.crt && echo OK "mesh chain valid"

# 4. Phase 6.1 tunnel token file.
test -s ~/cloudflare-${ENV}-tunnel-token.txt && echo OK "tunnel token present" || {
  echo "FAIL ~/cloudflare-${ENV}-tunnel-token.txt missing — re-run Phase 6.1"; exit 1; }

# 5. Cloudflare Origin Certs for edge-ingress TLS. STAGING: two certs
#    (staging-api host + staging wildcard+apex). PRODUCTION DEVIATION:
#    one host cert (api.exoper.com) + one apex+wildcard, saved as
#    ~/cf-origin-api.crt|.key + ~/cf-origin-wildcard.crt|.key.
if [ "$ENV" = staging ]; then
  for f in ~/cf-origin-staging-api.crt ~/cf-origin-staging-api.key \
           ~/cf-origin-wildcard-staging.crt ~/cf-origin-wildcard-staging.key; do
    test -s "$f" && echo "OK $f" || {
      echo "FAIL $f missing — generate Cloudflare Origin Certificates per §8.6"; exit 1; }
  done
else
  for f in ~/cf-origin-api.crt ~/cf-origin-api.key \
           ~/cf-origin-wildcard.crt ~/cf-origin-wildcard.key; do
    test -s "$f" && echo "OK $f" || {
      echo "FAIL $f missing — generate Cloudflare Origin Certificates per §8.6"; exit 1; }
  done
fi

# 6. The .env file holds operator-supplied API keys (MaxMind, FRED,
#    TwelveData, Anthropic, OpenAI, Gemini, MetaApi, CFTC). §8.6/8.7
#    source it. PRODUCTION DEVIATION: same .env also carries the real
#    Paddle + LemonSqueezy keys (staging uses placeholders per the
#    Phase 0 decision).
test -s ~/eTradie/.env && echo OK ".env present" || {
  echo "FAIL ~/eTradie/.env missing — operator-supplied API keys live there"; exit 1; }

# 7. helm/terraform CLIs are on PATH.
for t in terraform helm jq openssl step; do
  command -v "$t" >/dev/null && echo "OK $t" || { echo "FAIL $t missing"; exit 1; }
done

echo "=== All pre-flight checks passed; proceed to 8.1 ==="
```

### 8.1 — Create the Vault path schema (terraform)

The `infrastructure/cluster/vault-paths` module creates every empty
KV-v2 path the chart `ExternalSecret`s reference. It is environment-
segmented: `-var environment=staging` creates the staging-suffixed
paths; a later `-var environment=production` apply creates the
production-suffixed paths. Both can co-exist in one Vault, and
re-applying is idempotent (`lifecycle.ignore_changes` on `data_json`
preserves operator-written values).

**The Linkerd mesh CA path is the one exception** — it is hard-coded
to `etradie/platform/linkerd/production` in
`deployments/linkerd/values.yaml` (single mesh control plane per
cluster; both env postures share it per BUDGET.md Table 2B). The
terraform module creates an `etradie/platform/linkerd/<env>` path
for completeness, but the ESO identity ExternalSecret only ever reads
from `/production`. §8.5 below writes the CA directly to `/production`
with `vault kv put` (KV-v2 auto-creates the path on first write).

```bash
cd ~/eTradie
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="$ROOT_TOKEN"

# Open a port-forward ONLY for the duration of 8.1. HashiCorp's vault
# provider for terraform needs a network path; the in-pod-exec pattern
# used elsewhere in this runbook does not work for terraform.
kubectl -n vault port-forward svc/vault 8200:8200 >/tmp/pf-vault.log 2>&1 &
PF_PID=$!
sleep 2
curl -fsS http://127.0.0.1:8200/v1/sys/health >/dev/null && echo OK "port-forward live"

cd infrastructure/cluster/vault-paths
terraform init
terraform apply -auto-approve \
  -var environment=${ENV} \
  -var vault_address=http://127.0.0.1:8200
cd ../../..

# Tear the port-forward down immediately; subsequent sub-steps use the
# in-pod pattern and do not need :8200 on the workstation.
kill $PF_PID 2>/dev/null || true
wait $PF_PID 2>/dev/null || true
unset VAULT_ADDR VAULT_TOKEN PF_PID
echo "OK terraform applied; port-forward closed"
```

Expected: `Apply complete! Resources: 11 added` on a fresh Vault, or
`Resources: 0 added, 0 changed` on a re-apply. The 11 resources are
the paths enumerated in `outputs.tf::vault_paths`.

> **Helper to keep the rest of Phase 8 readable.** Every subsequent
> `vault kv put` runs via `kubectl exec`. Wrap the pattern in two
> shell functions:
> ```bash
> vkv () { kubectl -n vault exec -i vault-0 -- \
>          env VAULT_TOKEN="$ROOT_TOKEN" vault kv put "$@"; }
> vkv_get () { kubectl -n vault exec -i vault-0 -- \
>          env VAULT_TOKEN="$ROOT_TOKEN" vault kv get "$@"; }
> # Special variant for writes that include @file references (PEM bytes
> # read from the workstation's local filesystem):
> vkv_file () {
>   local path="$1"; shift
>   local -a kv=()
>   while [ "$#" -gt 0 ]; do
>     local k="${1%%=*}"; local v="${1#*=}"
>     if [ "${v#@}" != "$v" ]; then v="$(cat "${v#@}")"; fi
>     kv+=("$k=$v"); shift
>   done
>   kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
>     vault kv put "$path" "${kv[@]}"
> }
> ```
> Every write below uses `vkv` or `vkv_file`; every read uses `vkv_get`.

### 8.2 — Generate shared secrets ONCE (single source of truth)

Nine random values + four constructed DSN/URLs, generated ONCE so the
same bytes flow into every Vault path. The cross-path identity
invariants (verified in §8.11) DEPEND on these being assigned exactly
once in this shell session.

```bash
DB_PASS=$(openssl rand -hex 32)
REDIS_PASS=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 64)            # 128 hex chars; gateway requires ≥32
BROKER_KEY=$(openssl rand -hex 32)            # KEK v1; engine-only consumer (Tier 3)
CHROMA_TOKEN=$(openssl rand -hex 32)
ADMIN_PASS=$(openssl rand -hex 24)            # 48 hex chars; rotate after first login
ENGINE_SHARED=$(openssl rand -hex 32)         # X-Internal-Auth: gateway/exec/mgmt → engine
BILLING_SHARED=$(openssl rand -hex 32)        # X-Internal-Auth: gateway → billing (≥32 per billing config.go)
MT_DEFAULT_ZMQ=$(openssl rand -hex 32)

# DSN construction. sslmode=require is REQUIRED by the engine + billing
# config validators in staging+production (engine config.py::
# _validate_production_secrets, billing config.go::requireTLSDatabaseURL).
# The actual link is mTLS-encrypted by the Linkerd proxy sidecar (mesh
# ON in both env postures per BUDGET.md Table 2B).
DB_URL_GO="postgres://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=require"
DB_URL_PY="postgresql+asyncpg://etradie:${DB_PASS}@postgres.etradie-system.svc.cluster.local:5432/etradie?sslmode=require"
REDIS0="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/0"
REDIS1="redis://:${REDIS_PASS}@redis.etradie-system.svc.cluster.local:6379/1"

# Sanity-check lengths (no value echoed).
echo "DB_PASS=${#DB_PASS} (expect 64) $( [ ${#DB_PASS} -eq 64 ] && echo OK || echo FAIL )"
echo "JWT_SECRET=${#JWT_SECRET} (expect 128) $( [ ${#JWT_SECRET} -eq 128 ] && echo OK || echo FAIL )"
echo "BILLING_SHARED=${#BILLING_SHARED} (expect 64) $( [ ${#BILLING_SHARED} -eq 64 ] && echo OK || echo FAIL )"
echo "ENGINE_SHARED=${#ENGINE_SHARED} (expect 64) $( [ ${#ENGINE_SHARED} -eq 64 ] && echo OK || echo FAIL )"
```

### 8.3 — Persist the generated secrets to a 0600 file FIRST

Written BEFORE any `vault kv put` so a Vault failure mid-phase does
NOT leave the values generated-but-unrecoverable. The file is
gitignored at the repo-root anchor in commit `a24fefac`; saving to
`$HOME` is safe even when CWD is inside the repo.

```bash
umask 077
cat > ~/etradie-${ENV}-creds.txt <<EOF
# eTradie §8.2 generated secrets — ${ENV} — $(date -u +%FT%TZ)
# mode 0600. Workstation safety net until Phase 15 Vault Raft snapshots
# are configured. Vault remains canonical.
DB_PASS=${DB_PASS}
REDIS_PASS=${REDIS_PASS}
JWT_SECRET=${JWT_SECRET}
ADMIN_PASS=${ADMIN_PASS}
BROKER_KEY=${BROKER_KEY}
CHROMA_TOKEN=${CHROMA_TOKEN}
ENGINE_SHARED=${ENGINE_SHARED}
BILLING_SHARED=${BILLING_SHARED}
MT_DEFAULT_ZMQ=${MT_DEFAULT_ZMQ}
EOF
chmod 600 ~/etradie-${ENV}-creds.txt
ls -la ~/etradie-${ENV}-creds.txt
```

### 8.4 — Data-layer paths (postgres + redis + chromadb)

Written FIRST among the Vault writes because the data-layer
StatefulSets are wave -2 in Phase 12 and their pods block in
`Init:0/N` indefinitely if ESO cannot materialise their Secrets.
Key names EXACT per the three `*-externalsecret.yaml` templates.

> **CANONICAL WRITE PATTERN — read this before §8.4 onwards.** Every
> Vault write in §8.4 through §8.11 uses the explicit form:
>
> ```bash
> kubectl -n vault exec -i vault-0 -- \
>   env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
>   etradie/<rest> <kv_pairs>
> ```
>
> The explicit `-mount=etradie` flag plus the full `etradie/<rest>`
> KEY (with the **doubled `etradie/` prefix** — NOT a typo) make the
> path unambiguous and identical to terraform's resource id. The
> `vkv` helper from §8.1 is more concise but takes a positional
> `<mount>/<key>` path that is easy to misread: `vkv etradie/X`
> resolves to mount=etradie, key=X, which is NOT what terraform
> created (terraform names every resource as `etradie/<rest>` with
> mount=etradie, key=etradie/<rest> — chart ExternalSecrets read
> from `etradie/data/etradie/<rest>`). The staging deploy hit this
> the first time; the explicit form below makes the same mistake
> impossible to make. Audit ref: PROGRESS.md operator gotcha #9.

```bash
# 8.4.1 — Postgres: 3 properties.
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/data-layer/postgres/${ENV} \
  postgres_user=etradie \
  postgres_db=etradie \
  postgres_password="${DB_PASS}"

# 8.4.2 — Redis: 1 property.
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/data-layer/redis/${ENV} \
  redis_password="${REDIS_PASS}"

# 8.4.3 — ChromaDB: SINGLE key 'auth_token'. The chromadb
# StatefulSet (reads CHROMA_SERVER_AUTHN_CREDENTIALS) AND the engine
# pod (reads RAG_CHROMA_AUTH_TOKEN) BOTH consume this exact Vault
# property; the engine's chromadbAuthVaultPath pin in
# values-<env>.yaml points HERE.
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/data-layer/chromadb/${ENV} \
  auth_token="${CHROMA_TOKEN}"

# Read-back: confirm version 2 (terraform created v=1 placeholders).
for p in etradie/data-layer/postgres/${ENV} etradie/data-layer/redis/${ENV} etradie/data-layer/chromadb/${ENV}; do
  v=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv metadata get -mount=etradie "$p" 2>&1 | grep '^current_version' | awk '{print $2}')
  echo "  $p  current_version=$v (expect 2)"
done

# DB_PASS hash-compare shell vs vault (no value leaks to scrollback).
shell_hash=$(printf '%s' "${DB_PASS}" | sha256sum | cut -d' ' -f1)
vault_hash=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=postgres_password \
  etradie/data-layer/postgres/${ENV} | sha256sum | cut -d' ' -f1)
[ "$shell_hash" = "$vault_hash" ] && echo "  OK DB_PASS shell==vault" || echo "  FAIL"
```

> **Production deviation — postgres-backup offsite (B2/rclone).** Per
> BUDGET.md Table 2B the postgres-backup CronJob is **OFF in staging**
> and **ON (transient) in production**. On the production deploy,
> ADD these B2/rclone keys after the three writes above (skip on
> staging — the chart does not render the backup-credentials
> ExternalSecret when `postgres.backup.enabled=false`):
> ```bash
> # Production-only.
> vkv secret/etradie/data-layer/postgres-backup/production \
>   rclone_remote_name="b2" \
>   rclone_config="$(cat ~/rclone-b2.conf)" \
>   remote_bucket="etradie-prod-backups" \
>   remote_path_prefix="postgres/"
> ```
> See `docs/runbooks/database-backup-restore.md` for the rclone.conf
> shape.

### 8.5 — Linkerd mesh CA (intentional cross-env path)

The Linkerd mesh runs ONCE per cluster regardless of which env
posture the cluster hosts. `deployments/linkerd/values.yaml`
hard-codes `vaultPath: etradie/platform/linkerd/production` and the
identity Application is named `linkerd-identity-production` for that
reason — there is no `*-staging` variant. Per BUDGET.md Table 2B
("this box runs ONE environment at a time — staging and production
are alternative postures for it, not roommates") this is correct
by design.

**Write the mesh CA to `/production` even on a staging box.** Do NOT
modify the path to `/staging` — the linkerd-identity ExternalSecret
will not find it and Phase 12's `linkerd-control-plane-production`
sync will fail with `issuer secret linkerd-identity-issuer not found`.

```bash
# Read each PEM file into a shell variable so multi-line content
# is passed inline to vault kv put. @file syntax does NOT work
# through kubectl exec (the @ resolution happens INSIDE the pod,
# where the workstation files do not exist).
TRUST_ANCHOR_PEM="$(cat ca.crt)"
ISSUER_TLS_CRT="$(cat issuer.crt)"
ISSUER_TLS_KEY="$(cat issuer.key)"

kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/platform/linkerd/production \
  trust_anchor_pem="$TRUST_ANCHOR_PEM" \
  issuer_tls_crt="$ISSUER_TLS_CRT" \
  issuer_tls_key="$ISSUER_TLS_KEY"

# Round-trip fingerprint verification. The disk fingerprints below
# MUST equal the values recorded in PROGRESS.md §Phase 7.
disk_ca_fp=$(step certificate fingerprint ca.crt)
disk_issuer_fp=$(step certificate fingerprint issuer.crt)
vault_ca_fp=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=trust_anchor_pem \
  etradie/platform/linkerd/production | step certificate fingerprint /dev/stdin)
vault_issuer_fp=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=issuer_tls_crt \
  etradie/platform/linkerd/production | step certificate fingerprint /dev/stdin)
[ "$disk_ca_fp" = "$vault_ca_fp" ] && echo "  OK trust_anchor_pem MATCH" || echo "  FAIL"
[ "$disk_issuer_fp" = "$vault_issuer_fp" ] && echo "  OK issuer_tls_crt MATCH" || echo "  FAIL"

# Issuer cert/key PAIRING check INSIDE Vault. This is what Linkerd's
# identity controller runs at boot; catching a mismatch here surfaces
# the problem as "your write was wrong" instead of as "linkerd-identity
# won't start with invalid issuer cert chain" at Phase 12 sync.
vault_cert=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=issuer_tls_crt etradie/platform/linkerd/production)
vault_key=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=issuer_tls_key etradie/platform/linkerd/production)
cert_pub_sha=$(printf '%s\n' "$vault_cert" | openssl x509 -noout -pubkey | sha256sum | cut -d' ' -f1)
key_pub_sha=$( printf '%s\n' "$vault_key"  | openssl pkey -pubout 2>/dev/null | sha256sum | cut -d' ' -f1)
[ "$cert_pub_sha" = "$key_pub_sha" ] && echo "  OK issuer cert+key PAIRED in Vault" || echo "  FAIL UNPAIRED"

unset TRUST_ANCHOR_PEM ISSUER_TLS_CRT ISSUER_TLS_KEY vault_cert vault_key
```

If any fingerprint differs from the PROGRESS.md §Phase 7 entry, or
the cert/key pairing FAILs, stop. The most common cause is a
trailing-newline transformation on the way through `kubectl exec`.
Do NOT proceed.

### 8.6 — Edge-ingress paths (tunnel, AOP CA, MaxMind, TLS certs)

Four Vault paths. The TLS one carries the actual server certs
edge-ingress presents to cloudflared on every tunnel-routed request.
**Empty strings break the chart** — the edge-ingress Rust binary
panics at TLS handshake setup loading an empty `.crt` file. The
pre-2026-06-14 README wrote empty strings under a misleading comment;
the post-audit procedure writes real Cloudflare Origin Certificates.

```bash
# 8.6.1 — Tunnel connector token (Phase 6.1 output).
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/edge-ingress/${ENV}/cloudflare/tunnel \
  tunnel_token="$(cat ~/cloudflare-${ENV}-tunnel-token.txt)"

# 8.6.2 — Cloudflare Authenticated Origin Pulls CA. Fetch live
# (Cloudflare's canonical PEM URL); write into Vault so edge-ingress
# reads it via ESO at runtime, avoiding a runtime egress dependency.
AOP_CA_PEM=$(curl -fsS https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem)
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/edge-ingress/${ENV}/cloudflare/aop_ca \
  aop_ca="$AOP_CA_PEM"

# 8.6.3 — MaxMind GeoLite. Source the 2 needed keys with subshell
# isolation (same pattern as §8.8 below) to avoid the .env source
# clobbering §8.2 generated vars on shells where .env contains
# stale POSTGRES_PASSWORD / AUTH_JWT_SECRET / BROKER_ENCRYPTION_KEY.
# Audit ref: PROGRESS.md operator gotcha #12.
eval "$(
  set -a
  . ~/eTradie/.env 2>/dev/null
  set +a
  for k in MAXMIND_LICENSE_KEY MAXMIND_ACCOUNT_ID; do
    val=$(eval echo \"\${${k}}\")
    val_esc=$(printf '%s' "$val" | sed "s/'/'\\\\''/g")
    printf "ENV_%s='%s'\n" "$k" "$val_esc"
  done
)"
[ -z "$ENV_MAXMIND_LICENSE_KEY" ] && { echo "FAIL MAXMIND_LICENSE_KEY missing from .env"; }
[ -z "$ENV_MAXMIND_ACCOUNT_ID" ] && { echo "FAIL MAXMIND_ACCOUNT_ID missing from .env"; }

kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/edge-ingress/${ENV}/maxmind \
  license_key="$ENV_MAXMIND_LICENSE_KEY" \
  account_id="$ENV_MAXMIND_ACCOUNT_ID"

# 8.6.4 — TLS certificates. STAGING: 4 properties (staging_api_cert,
# staging_api_key, staging_wildcard_cert, staging_wildcard_key) per
# helm/edge-ingress/values-staging.yaml::externalSecrets.tlsCerts.entries.
# PRODUCTION: 4 different property names (api_cert, api_key,
# wildcard_cert, wildcard_key) per helm/edge-ingress/values.yaml
# base defaults.
if [ "$ENV" = staging ]; then
  STAGING_API_CERT="$(cat ~/cf-origin-staging-api.crt)"
  STAGING_API_KEY="$(cat ~/cf-origin-staging-api.key)"
  STAGING_WILD_CERT="$(cat ~/cf-origin-wildcard-staging.crt)"
  STAGING_WILD_KEY="$(cat ~/cf-origin-wildcard-staging.key)"
  kubectl -n vault exec -i vault-0 -- \
    env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
    etradie/services/edge-ingress/staging/tls \
    staging_api_cert="$STAGING_API_CERT" \
    staging_api_key="$STAGING_API_KEY" \
    staging_wildcard_cert="$STAGING_WILD_CERT" \
    staging_wildcard_key="$STAGING_WILD_KEY"
  unset STAGING_API_CERT STAGING_API_KEY STAGING_WILD_CERT STAGING_WILD_KEY
else
  API_CERT="$(cat ~/cf-origin-api.crt)"
  API_KEY="$(cat ~/cf-origin-api.key)"
  WILD_CERT="$(cat ~/cf-origin-wildcard.crt)"
  WILD_KEY="$(cat ~/cf-origin-wildcard.key)"
  kubectl -n vault exec -i vault-0 -- \
    env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
    etradie/services/edge-ingress/production/tls \
    api_cert="$API_CERT" \
    api_key="$API_KEY" \
    wildcard_cert="$WILD_CERT" \
    wildcard_key="$WILD_KEY"
  unset API_CERT API_KEY WILD_CERT WILD_KEY
fi

unset AOP_CA_PEM ENV_MAXMIND_LICENSE_KEY ENV_MAXMIND_ACCOUNT_ID
```

**Post-write verification.** Tunnel token byte equality (newline-
stripped, since the vault CLI may +/- a trailing newline), AOP CA
cert count parity, TLS cert fingerprint round-trip per pair, and
TLS cert/key pairing INSIDE Vault per pair. The pairing check is
the load-bearing one — it proves edge-ingress will TLS-handshake
cleanly when cloudflared dials it at Phase 12.

```bash
for pair in "staging_api_cert:staging_api_key:cf-origin-staging-api" \
            "staging_wildcard_cert:staging_wildcard_key:cf-origin-wildcard-staging"; do
  cprop=$(echo "$pair" | cut -d: -f1)
  kprop=$(echo "$pair" | cut -d: -f2)
  fbase=$(echo "$pair" | cut -d: -f3)
  # Fingerprint round-trip.
  disk_fp=$(openssl x509 -in ~/${fbase}.crt -noout -fingerprint -sha256 | sed 's/.*=//;s/://g' | tr '[:upper:]' '[:lower:]')
  vault_fp=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv get -mount=etradie -field="$cprop" \
    etradie/services/edge-ingress/${ENV}/tls \
    | openssl x509 -noout -fingerprint -sha256 | sed 's/.*=//;s/://g' | tr '[:upper:]' '[:lower:]')
  [ "$disk_fp" = "$vault_fp" ] && echo "  OK $cprop fingerprint MATCH" || echo "  FAIL $cprop"
  # Cert/key pairing inside Vault.
  vc=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv get -mount=etradie -field="$cprop" etradie/services/edge-ingress/${ENV}/tls)
  vk=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv get -mount=etradie -field="$kprop" etradie/services/edge-ingress/${ENV}/tls)
  c_pub=$(printf '%s\n' "$vc" | openssl x509 -noout -pubkey 2>/dev/null | openssl pkey -pubin -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1)
  k_pub=$(printf '%s\n' "$vk" | openssl rsa  -pubout 2>/dev/null              | openssl pkey -pubin -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1)
  [ "$c_pub" = "$k_pub" ] && [ -n "$c_pub" ] && echo "  OK $cprop/$kprop PAIRED in Vault" || echo "  FAIL $cprop/$kprop UNPAIRED"
done
```

> **Production deviation — Cloudflare Origin Cert generation.** Generate
> two Origin Certificates in the Cloudflare dashboard (zone `exoper.com`
> → SSL/TLS → Origin Server → Create Certificate), RSA 2048, 15-year
> validity:
> - Hostnames: `api.exoper.com` only → `~/cf-origin-api.crt` + `~/cf-origin-api.key` (mode 0600).
> - Hostnames: `exoper.com` and `*.exoper.com` → `~/cf-origin-wildcard.crt` + `~/cf-origin-wildcard.key` (mode 0600).
>
> Verify (must MATCH for each cert/key pair):
> ```bash
> openssl x509 -in ~/cf-origin-api.crt -noout -ext subjectAltName | grep DNS:
> # expect: DNS:api.exoper.com
> openssl x509 -in ~/cf-origin-wildcard.crt -noout -ext subjectAltName | grep DNS:
> # expect: DNS:exoper.com, DNS:*.exoper.com
> diff <(openssl x509 -in ~/cf-origin-api.crt -noout -modulus | openssl sha256) \
>      <(openssl rsa  -in ~/cf-origin-api.key -noout -modulus | openssl sha256)
> # silent + exit 0 = paired
> ```

### 8.7 — Gateway path

The gateway holds the AUTHORITATIVE copies of `auth_jwt_secret`,
`auth_admin_password`, both cross-service shared secrets, and the
full Postgres DSN + the separate `POSTGRES_*` fields the Go envconfig
fallback consumes when `auth_database_url` is empty. Twelve properties.

```bash
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/gateway/${ENV} \
  auth_database_url="${DB_URL_GO}" \
  postgres_user=etradie \
  postgres_password="${DB_PASS}" \
  postgres_host=postgres.etradie-system.svc.cluster.local \
  postgres_port=5432 \
  postgres_db=etradie \
  postgres_sslmode=require \
  gateway_redis_url="${REDIS0}" \
  auth_jwt_secret="${JWT_SECRET}" \
  auth_admin_password="${ADMIN_PASS}" \
  engine_internal_shared_secret="${ENGINE_SHARED}" \
  billing_internal_shared_secret="${BILLING_SHARED}"

# 3-way cross-path equality: postgres_password MUST match shell
# DB_PASS, data-layer/postgres, and gateway. Catching a divergence
# here is much easier than catching it via app-layer 500s at Phase 12.
shell_pgpw=$(printf '%s' "${DB_PASS}" | sha256sum | cut -d' ' -f1)
dlay_pgpw=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=postgres_password \
  etradie/data-layer/postgres/${ENV} | sha256sum | cut -d' ' -f1)
gw_pgpw=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=postgres_password \
  etradie/services/gateway/${ENV} | sha256sum | cut -d' ' -f1)
[ "$shell_pgpw" = "$dlay_pgpw" ] && [ "$dlay_pgpw" = "$gw_pgpw" ] \
  && echo "  OK postgres_password 3-way MATCH" \
  || echo "  FAIL MISMATCH — STOP, investigate before §8.8"
```

### 8.8 — Engine path

The engine is the SOLE consumer of `broker_encryption_key` (the KEK
that seals broker credentials AND LLM API keys in Postgres; gateway/
execution/management do NOT receive it per Tier 3 least-privilege).

LLM keys (Anthropic, OpenAI, Gemini), MetaApi token, and the CFTC
Socrata app token are OPTIONAL at engine boot — `_validate_production_
secrets` requires only `twelvedata_api_key` + `fred_api_key`. The
others default to empty and can be dashboard-managed per `.env.example`
lines 19–21. The staging deploy still writes them all from `.env`
for system callers (RAG ingest, COT scraper, MetaApi provisioner)
that have no user identity at runtime.

```bash
# Source .env keys with SUBSHELL ISOLATION so the §8.2 generated
# values in the working shell are NOT clobbered. The platform's .env
# redefines POSTGRES_PASSWORD, AUTH_JWT_SECRET, BROKER_ENCRYPTION_KEY
# with stale/template values — a naive `set -a; . .env; set +a` would
# overwrite §8.2's DB_PASS / JWT_SECRET / BROKER_KEY in this shell,
# and every subsequent vault kv put would write the wrong values,
# breaking the cross-path equality matrix that Phase 12 depends on.
# Audit ref: PROGRESS.md operator gotcha #12.
#
# The eval "$(...)" pattern runs the .env source in a SUBSHELL,
# extracts only the 7 keys we need, prefixes them with ENV_ so they
# can't collide with §8.2 vars, and emits them as KEY='value' lines
# back to the main shell. Subshell variables die when $(...) closes.
eval "$(
  set -a
  . ~/eTradie/.env 2>/dev/null
  set +a
  for k in TWELVEDATA_API_KEY FRED_API_KEY CFTC_APP_TOKEN \
           PROCESSOR_ANTHROPIC_API_KEY PROCESSOR_OPENAI_API_KEY \
           PROCESSOR_GEMINI_API_KEY MT5_METAAPI_TOKEN; do
    val=$(eval echo \"\${${k}}\")
    val_esc=$(printf '%s' "$val" | sed "s/'/'\\\\''/g")
    printf "ENV_%s='%s'\n" "$k" "$val_esc"
  done
)"

# Safety check: §8.2 variables MUST be unchanged after the source.
# This is the load-bearing isolation check; if it FAILs, do NOT write.
shell_db_pass_post=$(printf '%s' "${DB_PASS}" | sha256sum | cut -d' ' -f1)
[ -n "$DB_PASS" ] && [ ${#DB_PASS} -eq 64 ] \
  && echo "  OK §8.2 DB_PASS preserved (subshell isolation worked)" \
  || { echo "  FAIL §8.2 DB_PASS clobbered — STOP, do not write Vault"; }

# Fail-fast on the 2 engine-required-at-boot keys.
[ -z "$ENV_TWELVEDATA_API_KEY" ] && echo "  FAIL TWELVEDATA_API_KEY missing"
[ -z "$ENV_FRED_API_KEY" ] && echo "  FAIL FRED_API_KEY missing"

# Write — 15 properties at the canonical engine path. The 16th
# property (chromadb auth_token) is read by the engine from a
# DIFFERENT Vault path (`etradie/data-layer/chromadb/${ENV}`) per
# the engine chart's chromadbAuthVaultPath value — §8.4 already
# populated it.
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/engine/${ENV} \
  database_url="${DB_URL_PY}" \
  postgres_user=etradie \
  postgres_password="${DB_PASS}" \
  redis_url="${REDIS0}" \
  redis_password="${REDIS_PASS}" \
  broker_encryption_key="${BROKER_KEY}" \
  auth_jwt_secret="${JWT_SECRET}" \
  engine_internal_shared_secret="${ENGINE_SHARED}" \
  twelvedata_api_key="$ENV_TWELVEDATA_API_KEY" \
  fred_api_key="$ENV_FRED_API_KEY" \
  cftc_app_token="${ENV_CFTC_APP_TOKEN:-}" \
  processor_anthropic_api_key="${ENV_PROCESSOR_ANTHROPIC_API_KEY:-}" \
  processor_openai_api_key="${ENV_PROCESSOR_OPENAI_API_KEY:-}" \
  processor_gemini_api_key="${ENV_PROCESSOR_GEMINI_API_KEY:-}" \
  mt5_metaapi_token="${ENV_MT5_METAAPI_TOKEN:-}"

unset ENV_TWELVEDATA_API_KEY ENV_FRED_API_KEY ENV_CFTC_APP_TOKEN \
      ENV_PROCESSOR_ANTHROPIC_API_KEY ENV_PROCESSOR_OPENAI_API_KEY \
      ENV_PROCESSOR_GEMINI_API_KEY ENV_MT5_METAAPI_TOKEN
```

### 8.9 — Execution + Management paths

**Five properties each** (was four pre-fix). Both services send
`ENGINE_SHARED` in `X-Internal-Auth` on every `/internal/broker/*`
call. Both refuse to boot in staging/production with `BROKER_MODE=mt5`
if either of the cross-service secrets is empty. The staging overlay
sets `brokerMode: "mock"` so that guard is dormant in staging, but
writing the values is still required because the production posture
flips it to `mt5`.

**`auth_database_url` AND `auth_admin_password`** are load-bearing:
the shared `src/auth` package (consumed by gateway + execution +
management) reads `AUTH_DATABASE_URL` and `AUTH_ADMIN_PASSWORD` via
envconfig prefix `AUTH` and validates BOTH as required in
production/staging. Without either property in Vault the execution +
management ExternalSecrets render their K8s Secrets without the key
and the pods fail fast at startup with one of:

```
fatal: auth config: validation: AUTH_DATABASE_URL must be set in
       staging; the auth store cannot start without a valid DSN
```

```
fatal: auth config: validation: AUTH_ADMIN_PASSWORD must be set in
       staging; refusing to seed the initial admin user with an
       empty password
```

`DB_URL_GO` and `ADMIN_PASS` from §8.2 are the same shared values used
by the gateway path (§8.7); all three services dial the same Postgres,
the auth tables are shared, and the seeded admin user is one row that
every service agrees on.

```bash
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/execution/${ENV} \
  auth_database_url="${DB_URL_GO}" \
  auth_admin_password="${ADMIN_PASS}" \
  execution_database_url="${DB_URL_GO}" \
  execution_redis_url="${REDIS1}" \
  auth_jwt_secret="${JWT_SECRET}" \
  engine_internal_shared_secret="${ENGINE_SHARED}"

kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/management/${ENV} \
  auth_database_url="${DB_URL_GO}" \
  auth_admin_password="${ADMIN_PASS}" \
  management_database_url="${DB_URL_GO}" \
  management_redis_url="${REDIS1}" \
  auth_jwt_secret="${JWT_SECRET}" \
  engine_internal_shared_secret="${ENGINE_SHARED}"
```

### 8.10 — Billing path

**Eighteen properties** — the previous README said "Fourteen" but the
chart's `helm/billing/templates/externalsecret.yaml` lists 18
explicit `data:` entries: `billing_database_url` + 6 `POSTGRES_*`
fields + `internal_shared_secret` + `billing_redis_url` + 4 Paddle
keys + 5 LemonSqueezy keys = **18**. The 6 `POSTGRES_*` fallback
fields the original block was missing are required because billing's
`config.go` validates them on startup when `BILLING_DATABASE_URL` is
unset; without all 6, ESO synthesises an empty Secret and the
billing pod CrashLoops. `config.go::Load()` also marks every Paddle
+ LemonSqueezy field as `required:"true"` and applies a `>=32 char`
length check to `BILLING_INTERNAL_SHARED_SECRET`. An empty value for
any required field fails the pod at boot with `billing config:
required key X missing value`.

Staging writes **plausibly-formatted placeholders** per the Phase 0
decision ("Paddle + Lemon Squeezy credentials NOT in hand. Phase 8.9
will write random plausibly-formatted values into Vault so the
billing service passes its startup fail-fast; real values to be
swapped in later via `vault kv put` + `kubectl rollout restart`").
The placeholders satisfy the length + non-empty checks; the webhook
endpoints then reject real provider traffic with HMAC verification
errors, which is the correct posture for staging.

```bash
# Placeholder shapes match real provider value sizes. Distinct
# random values per provider (not shared between Paddle and LS) so
# leaks/forensics distinguish which provider the value came from.
PLACEHOLDER_PADDLE_WEBHOOK=$(openssl rand -hex 32)
PLACEHOLDER_PADDLE_APIKEY=$(openssl rand -hex 32)
PLACEHOLDER_PADDLE_PRICE_BYOK="pri_placeholder_$(openssl rand -hex 6)"
PLACEHOLDER_PADDLE_PRICE_MANAGED="pri_placeholder_$(openssl rand -hex 6)"
PLACEHOLDER_LS_WEBHOOK=$(openssl rand -hex 32)
PLACEHOLDER_LS_APIKEY=$(openssl rand -hex 32)
PLACEHOLDER_LS_STORE="$(( RANDOM % 90000 + 10000 ))"
PLACEHOLDER_LS_VARIANT_BYOK="$(( RANDOM % 9000000 + 1000000 ))"
PLACEHOLDER_LS_VARIANT_MANAGED="$(( RANDOM % 9000000 + 1000000 ))"

kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/billing/${ENV} \
  billing_database_url="${DB_URL_GO}" \
  postgres_user=etradie \
  postgres_password="${DB_PASS}" \
  postgres_host=postgres.etradie-system.svc.cluster.local \
  postgres_port=5432 \
  postgres_db=etradie \
  postgres_sslmode=require \
  internal_shared_secret="${BILLING_SHARED}" \
  billing_redis_url="${REDIS0}" \
  paddle_webhook_secret="${PLACEHOLDER_PADDLE_WEBHOOK}" \
  paddle_api_key="${PLACEHOLDER_PADDLE_APIKEY}" \
  paddle_price_pro_byok="${PLACEHOLDER_PADDLE_PRICE_BYOK}" \
  paddle_price_pro_managed="${PLACEHOLDER_PADDLE_PRICE_MANAGED}" \
  lemonsqueezy_webhook_secret="${PLACEHOLDER_LS_WEBHOOK}" \
  lemonsqueezy_api_key="${PLACEHOLDER_LS_APIKEY}" \
  lemonsqueezy_store_id="${PLACEHOLDER_LS_STORE}" \
  lemonsqueezy_variant_pro_byok="${PLACEHOLDER_LS_VARIANT_BYOK}" \
  lemonsqueezy_variant_pro_managed="${PLACEHOLDER_LS_VARIANT_MANAGED}"

# Verify the asymmetric pair: gateway:billing_internal_shared_secret
# == billing:internal_shared_secret. Different KEY names, SAME VALUE.
shell_bs=$(printf '%s' "${BILLING_SHARED}" | sha256sum | cut -d' ' -f1)
g_biss=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=billing_internal_shared_secret \
  etradie/services/gateway/${ENV} | sha256sum | cut -d' ' -f1)
b_iss=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -field=internal_shared_secret \
  etradie/services/billing/${ENV} | sha256sum | cut -d' ' -f1)
[ "$shell_bs" = "$g_biss" ] && [ "$g_biss" = "$b_iss" ] \
  && echo "  OK asymmetric pair MATCH (gateway/billing_internal_shared_secret == billing/internal_shared_secret)" \
  || echo "  FAIL MISMATCH — STOP"
```

> **Production deviation — real Paddle + LemonSqueezy creds.** On the
> production deploy, source the real values from `.env` instead of
> generating placeholders:
> ```bash
> # Production-only. Use the subshell-isolated .env source pattern
> # so the 9 .env-sourced billing keys do NOT clobber §8.2 vars.
> eval "$(
>   set -a
>   . ~/eTradie/.env 2>/dev/null
>   set +a
>   for k in PADDLE_WEBHOOK_SECRET PADDLE_API_KEY \
>            PADDLE_PRICE_PRO_BYOK PADDLE_PRICE_PRO_MANAGED \
>            LEMONSQUEEZY_WEBHOOK_SECRET LEMONSQUEEZY_API_KEY \
>            LEMONSQUEEZY_STORE_ID LEMONSQUEEZY_VARIANT_PRO_BYOK \
>            LEMONSQUEEZY_VARIANT_PRO_MANAGED; do
>     val=$(eval echo \"\${${k}}\")
>     val_esc=$(printf '%s' "$val" | sed "s/'/'\\\\''/g")
>     printf "ENV_%s='%s'\n" "$k" "$val_esc"
>   done
> )"
> kubectl -n vault exec -i vault-0 -- \
>   env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
>   etradie/services/billing/production \
>   billing_database_url="${DB_URL_GO}" \
>   postgres_user=etradie postgres_password="${DB_PASS}" \
>   postgres_host=postgres.etradie-system.svc.cluster.local \
>   postgres_port=5432 postgres_db=etradie postgres_sslmode=require \
>   internal_shared_secret="${BILLING_SHARED}" \
>   billing_redis_url="${REDIS0}" \
>   paddle_webhook_secret="${ENV_PADDLE_WEBHOOK_SECRET:?required}" \
>   paddle_api_key="${ENV_PADDLE_API_KEY:?required}" \
>   paddle_price_pro_byok="${ENV_PADDLE_PRICE_PRO_BYOK:?required}" \
>   paddle_price_pro_managed="${ENV_PADDLE_PRICE_PRO_MANAGED:?required}" \
>   lemonsqueezy_webhook_secret="${ENV_LEMONSQUEEZY_WEBHOOK_SECRET:?required}" \
>   lemonsqueezy_api_key="${ENV_LEMONSQUEEZY_API_KEY:?required}" \
>   lemonsqueezy_store_id="${ENV_LEMONSQUEEZY_STORE_ID:?required}" \
>   lemonsqueezy_variant_pro_byok="${ENV_LEMONSQUEEZY_VARIANT_PRO_BYOK:?required}" \
>   lemonsqueezy_variant_pro_managed="${ENV_LEMONSQUEEZY_VARIANT_PRO_MANAGED:?required}"
> ```

### 8.11 — mt-node platform path + cross-path verification (closes Phase 8)

Last write: the platform-level mt-node fallback ZMQ token. Per-tenant
tokens are managed by the engine's `HostedProvisioner` at runtime; this
is the default the EA uses when no per-tenant override exists.

```bash
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/services/mt-node/${ENV} \
  default_zmq_auth_token="${MT_DEFAULT_ZMQ}"
```

**Cross-path identity verification.** Reads each shared value from
every path that holds it, hashes with `sha256sum` (so the secret
never appears in scrollback), and prints aligned columns. All
hash columns under one heading MUST be identical. Mismatch = the
same value was NOT written to every required path (most often a
property-name typo, or a re-run of a partial sub-step after the
variable was redefined). Catch it now; Phase 12 surfaces these as
confusing app-layer errors much later.

```bash
# Helper to keep the matrix readable.
vg () { kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
          vault kv get -mount=etradie -field="$1" "$2" | sha256sum | cut -d' ' -f1; }

echo "=== Matrix 1: auth_jwt_secret across gateway/engine/execution/management (4-way) ==="
for path in \
    etradie/services/gateway/${ENV} \
    etradie/services/engine/${ENV} \
    etradie/services/execution/${ENV} \
    etradie/services/management/${ENV}; do
  printf '  %-50s  %s\n' "$path" "$(vg auth_jwt_secret "$path")"
done

echo "=== Matrix 2: engine_internal_shared_secret across same 4 (4-way) ==="
for path in \
    etradie/services/gateway/${ENV} \
    etradie/services/engine/${ENV} \
    etradie/services/execution/${ENV} \
    etradie/services/management/${ENV}; do
  printf '  %-50s  %s\n' "$path" "$(vg engine_internal_shared_secret "$path")"
done

echo "=== Matrix 3: billing asymmetric pair (different KEY names, SAME VALUE) ==="
g=$(vg billing_internal_shared_secret etradie/services/gateway/${ENV})
b=$(vg internal_shared_secret         etradie/services/billing/${ENV})
printf '  %-50s  %s\n' "gateway:billing_internal_shared_secret" "$g"
printf '  %-50s  %s\n' "billing:internal_shared_secret"         "$b"
[ "$g" = "$b" ] && echo "  OK pair MATCH" || echo "  FAIL pair MISMATCH"

echo "=== Matrix 4: postgres_password across data-layer + gateway + engine + billing (4-way) ==="
for path in \
    etradie/data-layer/postgres/${ENV} \
    etradie/services/gateway/${ENV} \
    etradie/services/engine/${ENV} \
    etradie/services/billing/${ENV}; do
  printf '  %-50s  %s\n' "$path" "$(vg postgres_password "$path")"
done

echo "=== Matrix 5: redis_password across data-layer + engine (2-way) ==="
for entry in "etradie/data-layer/redis/${ENV}:redis_password" \
             "etradie/services/engine/${ENV}:redis_password"; do
  printf '  %-50s  %s\n' "$entry" "$(vg "${entry##*:}" "${entry%:*}")"
done

echo "=== Matrix 6: shell-vs-vault byte equality for the 8 §8.2 generated secrets ==="
shell_db=$(printf '%s' "${DB_PASS}" | sha256sum | cut -d' ' -f1)
shell_rd=$(printf '%s' "${REDIS_PASS}" | sha256sum | cut -d' ' -f1)
shell_jwt=$(printf '%s' "${JWT_SECRET}" | sha256sum | cut -d' ' -f1)
shell_bk=$(printf '%s' "${BROKER_KEY}" | sha256sum | cut -d' ' -f1)
shell_ct=$(printf '%s' "${CHROMA_TOKEN}" | sha256sum | cut -d' ' -f1)
shell_es=$(printf '%s' "${ENGINE_SHARED}" | sha256sum | cut -d' ' -f1)
shell_bs=$(printf '%s' "${BILLING_SHARED}" | sha256sum | cut -d' ' -f1)
shell_mt=$(printf '%s' "${MT_DEFAULT_ZMQ}" | sha256sum | cut -d' ' -f1)
for entry in \
    "DB_PASS:$shell_db:$(vg postgres_password etradie/data-layer/postgres/${ENV})" \
    "REDIS_PASS:$shell_rd:$(vg redis_password etradie/data-layer/redis/${ENV})" \
    "JWT_SECRET:$shell_jwt:$(vg auth_jwt_secret etradie/services/gateway/${ENV})" \
    "BROKER_KEY:$shell_bk:$(vg broker_encryption_key etradie/services/engine/${ENV})" \
    "CHROMA_TOKEN:$shell_ct:$(vg auth_token etradie/data-layer/chromadb/${ENV})" \
    "ENGINE_SHARED:$shell_es:$(vg engine_internal_shared_secret etradie/services/gateway/${ENV})" \
    "BILLING_SHARED:$shell_bs:$(vg internal_shared_secret etradie/services/billing/${ENV})" \
    "MT_DEFAULT_ZMQ:$shell_mt:$(vg default_zmq_auth_token etradie/services/mt-node/${ENV})"; do
  v="${entry%%:*}"; rest="${entry#*:}"; sh="${rest%%:*}"; vh="${rest##*:}"
  status="OK"; [ "$sh" != "$vh" ] && status="FAIL"
  printf '  %-18s shell=%s vault=%s  %s\n' "$v" "${sh:0:12}..." "${vh:0:12}..." "$status"
done

echo "=== All 14 KV paths present (current_version check) ==="
# Linkerd path is /production EVEN on staging (operator gotcha #10);
# the v=1 on it is correct (first write, no terraform placeholder).
for p in \
    etradie/data-layer/postgres/${ENV} \
    etradie/data-layer/redis/${ENV} \
    etradie/data-layer/chromadb/${ENV} \
    etradie/platform/linkerd/production \
    etradie/services/edge-ingress/${ENV}/cloudflare/tunnel \
    etradie/services/edge-ingress/${ENV}/cloudflare/aop_ca \
    etradie/services/edge-ingress/${ENV}/maxmind \
    etradie/services/edge-ingress/${ENV}/tls \
    etradie/services/gateway/${ENV} \
    etradie/services/engine/${ENV} \
    etradie/services/execution/${ENV} \
    etradie/services/management/${ENV} \
    etradie/services/billing/${ENV} \
    etradie/services/mt-node/${ENV}; do
  v=$(kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv metadata get -mount=etradie "$p" 2>&1 | grep '^current_version' | awk '{print $2}')
  printf '  %-60s current_version=%s\n' "$p" "$v"
done
```

Every heading's hash column MUST be uniform. Any mismatch — re-write
the offending path before Phase 9.

**Phase 8 teardown.** Unset the in-shell secrets:

```bash
unset DB_PASS REDIS_PASS JWT_SECRET BROKER_KEY CHROMA_TOKEN \
      ADMIN_PASS ENGINE_SHARED BILLING_SHARED MT_DEFAULT_ZMQ \
      ROOT_TOKEN \
      PLACEHOLDER_LONG PLACEHOLDER_API_KEY \
      PLACEHOLDER_PRICE_BYOK PLACEHOLDER_PRICE_MANAGED \
      PLACEHOLDER_LS_STORE PLACEHOLDER_LS_VARIANT_BYOK \
      PLACEHOLDER_LS_VARIANT_MANAGED
history -c 2>/dev/null || true
```

Proceed to Phase 9.

<!-- Original Phase 8.1–8.11 retained below for diff archaeology;
     superseded by the staging-canonical procedure above. -->

<!-- The pre-2026-06-14 §8 procedure (production-flavored, with the
     defects this rewrite addresses) is preserved in git history.
     Recover with `git log -p docs/runbooks/README.md`. -->

<!-- LEGACY_PHASE_8_REMOVED_BELOW

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

END_REMOVED_SUPERSEDED_PHASE_8 -->

---

## Phase 9 — Build + inject the envoy WASM filter

`helm/envoy/values.yaml` ships `wasm.base64: ""`; the chart fails to
render until real bytes are supplied (`templates/configmap-wasm.yaml`
does `{{- if not .Values.wasm.base64 }}{{- fail "..." -}}{{- end -}}`).
ArgoCD cannot `--set-file` cleanly at sync time on a multi-source or
self-healing Application without creating drift, so the bytes live in
a committed values overlay file the chart `valueFiles` reads.

> **Workstation-only phase. No `kubectl`, no Vault, no VPS access.**
> The VPS will only see this change at Phase 12 when ArgoCD's
> repo-server pod pulls the updated repo from GitHub.

> **Single `ENV` variable for the whole phase.** Set it ONCE at the
> top and leave it for the rest of the phase:
> ```bash
> ENV=staging       # or 'production' for the production deploy
> ```
> Every command below references `${ENV}`; this keeps the procedure
> environment-symmetric (staging and production wire their WASM bytes
> through analogous `values-${ENV}-wasm.yaml` files into analogous
> `envoy-${ENV}.yaml` Applications).

### 9.0 — Pre-flight (reuse existing artefact if valid; rebuild only if needed)

A fresh release build of this workspace takes ~5–10 minutes on a
cold cache. If a `.wasm` from a previous local build is on disk,
verify it and skip `cargo build` entirely — the release profile
(`opt-level="z"`, `lto=true`, `codegen-units=1`, `panic="abort"`,
`strip=true` in `src/envoy/Cargo.toml`) is deterministic, so the
same source produces the same binary.

```bash
cd ~/eTradie
WASM=src/envoy/target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm

if [ -s "$WASM" ]; then
  echo "=== artefact present — verifying validity ==="
  head -c 4 "$WASM" | xxd | grep -q '0061 736d' && echo "  OK magic bytes (\\0asm)"
  file "$WASM" | grep -q 'WebAssembly' && echo "  OK file type"
  echo "  sha256: $(sha256sum "$WASM" | awk '{print $1}')"
  echo "  size:   $(wc -c < "$WASM") bytes"
  echo "  → SKIP cargo build; go straight to §9.2"
else
  echo "=== no artefact — will rebuild in §9.1 ==="
fi
```

### 9.1 — Build (skip if §9.0 verified an existing artefact)

The `rust-toolchain.toml` at `src/envoy/rust-toolchain.toml` pins the
workspace to `channel = "1.75.0"` with `targets = ["wasm32-wasi",
"wasm32-unknown-unknown"]` and triggers automatic toolchain +
target install on first `cd` and `cargo` invocation. No explicit
`rustup target add wasm32-wasi` is needed.

```bash
cd ~/eTradie/src/envoy
cargo build --release --target wasm32-wasi
cd ~/eTradie
WASM=src/envoy/target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm
test -s "$WASM" && echo "OK build complete ($(wc -c < "$WASM") bytes)" || echo "FAIL build"
```

### 9.2 — Encode + write `helm/envoy/values-${ENV}-wasm.yaml`

```bash
cd ~/eTradie
WASM=src/envoy/target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm
WASM_SHA256=$(sha256sum "$WASM" | awk '{print $1}')
WASM_BUILT_AT=$(date -u +%FT%TZ)

cat > helm/envoy/values-${ENV}-wasm.yaml <<EOF
# Staging or production WASM filter bytes — Phase 9.
# Source: src/envoy/target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm
#
# To rotate:
#   cd src/envoy && cargo build --release --target wasm32-wasi && cd ../..
#   WASM=src/envoy/target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm
#   sed -i "s|^  base64: .*|  base64: \"\$(base64 -w0 \$WASM)\"|" helm/envoy/values-${ENV}-wasm.yaml
#   sed -i "s|^  sha256: .*|  sha256: \"\$(sha256sum \$WASM | awk '{print \$1}')\"|" helm/envoy/values-${ENV}-wasm.yaml
#   sed -i "s|^  builtAt: .*|  builtAt: \"\$(date -u +%FT%TZ)\"|" helm/envoy/values-${ENV}-wasm.yaml
#   git add helm/envoy/values-${ENV}-wasm.yaml && git commit -m "envoy: rotate ${ENV} WASM filter"
#
# The chart's deployment.yaml carries
#   checksum/wasm: {{ .Values.wasm.base64 | sha256sum }}
# as a pod-template annotation, so a new base64 above rolls the pods
# automatically on the next ArgoCD reconcile.
wasm:
  base64: "$(base64 -w0 "$WASM")"
  sha256: "$WASM_SHA256"
  builtAt: "$WASM_BUILT_AT"
EOF

ls -la helm/envoy/values-${ENV}-wasm.yaml
```

### 9.3 — Wire the overlay into the ArgoCD Application

Add `values-${ENV}-wasm.yaml` to `valueFiles` right after
`values-${ENV}.yaml`. Idempotent: skip if already present.

```bash
APP=deployments/argocd/children/envoy-${ENV}.yaml
if grep -q "values-${ENV}-wasm.yaml" "$APP"; then
  echo "already wired — no change needed"
else
  awk -v ENV="$ENV" '
    $0 ~ "- values-" ENV ".yaml" && !done {
      print
      match($0, /^[[:space:]]*/)
      print substr($0, 1, RLENGTH) "- values-" ENV "-wasm.yaml"
      done=1; next
    }
    { print }
  ' "$APP" > "${APP}.new"
  mv "${APP}.new" "$APP"
fi

grep -A3 'valueFiles:' "$APP"
# expect 3 entries: values.yaml, values-${ENV}.yaml, values-${ENV}-wasm.yaml
```

### 9.4 — Commit + push (GitHub is the load-bearing push)

**ArgoCD reads ONLY from GitHub.** Every Application's `repoURL` is
`https://github.com/FlameGreat-1/eTradie.git`. Pushing only to GitLab
(or another mirror) silently leaves the platform on the old code.

```bash
git add helm/envoy/values-${ENV}-wasm.yaml deployments/argocd/children/envoy-${ENV}.yaml
git commit -m "envoy(${ENV}): inject WASM filter bytes via values-${ENV}-wasm.yaml overlay (Phase 9)"

# If you have a `gitlab` remote that the MCP integration writes to,
# pull any docs commits from there first so local main is current:
git pull --rebase gitlab main 2>/dev/null || true

# THE LOAD-BEARING PUSH. ArgoCD pulls from here at Phase 12.
git push origin main

# Mirror to GitLab (optional, only if you maintain that remote).
git push gitlab main 2>/dev/null || true

git log --oneline -5
```

> The WASM overlay holds compiled filter bytes, no secrets. The
> filter source itself is committed in `src/envoy/`; committing the
> encoded bytes is equivalent to committing the source.

> Prefer a private release branch + `targetRevision` if you do not
> want it on `main`.

---

## Phase 10 — ArgoCD + both AppProjects + root app

> **Pre-flight (Phase 10.0) is REQUIRED before §10.1.** The cluster
> needs the per-namespace `ghcr-pull` Secret in place BEFORE root-app
> at §10.3 creates the staging Applications; otherwise every staging
> pod fails its first image pull. The Linkerd trust anchor must also
> be committed to `deployments/linkerd/control-plane-values.yaml`
> BEFORE §10.3 (the previous README pattern of `argocd app set
> --helm-set-file` is fragile against root-app's `selfHeal` and has
> been replaced with the values-file commit — see audit ref:
> PROGRESS.md §Phase 10 pre-flight decision points).

### 10.0 — Pre-flight: namespaces + `ghcr-pull` Secret + Linkerd trust anchor

**GHCR pull credentials (Option B: private packages + per-namespace
Secret).** Enterprise supply-chain hygiene: packages stay PRIVATE
on GHCR; K8s `containerd` pulls them with a `docker-registry` Secret.

```bash
# 10.0.1 — Tunnel sanity (must precede every kubectl call).
[ -z "$KUBECONFIG" ] && export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes
# expect: vmi3362776 Ready control-plane,master ... v1.30.4+k3s1

# 10.0.2 — Create the two namespaces that need ghcr-pull. The
# data-layer chart re-creates etradie-system at Phase 12, but
# pre-creating is idempotent (CreateNamespace=true syncOption is a
# no-op on existing namespace).
for ns in etradie-system edge-ingress-system; do
  kubectl get ns "$ns" >/dev/null 2>&1 \
    && echo "  $ns already exists" \
    || kubectl create namespace "$ns"
done

# 10.0.3 — Generate a READ-ONLY GHCR PAT for in-cluster pulls.
# Browser: https://github.com/settings/tokens → Generate new token
# (classic) → Note: etradie-${ENV}-ghcr-pull, Expiration: 90d,
# Scopes: ONLY `read:packages` (NOTHING ELSE). Save to a 0600 file:
umask 077
cat > ~/.ghcr_pull_pat
# (paste the ghp_... token, Enter, Ctrl-D)
chmod 600 ~/.ghcr_pull_pat
# Confirm the scopes line shows ONLY read:packages.
curl -sSI -u "<gh-username>:$(cat ~/.ghcr_pull_pat)" https://api.github.com/user \
  | grep -i 'x-oauth-scopes'
# expect: x-oauth-scopes: read:packages

# 10.0.4 — Create the docker-registry Secret in each namespace.
# Idempotent (delete-if-exists then create). The email field is
# a docker-registry format requirement but not validated by GHCR;
# use the canonical placeholder.
GHCR_PAT=$(cat ~/.ghcr_pull_pat)
for ns in etradie-system edge-ingress-system; do
  kubectl -n "$ns" delete secret ghcr-pull --ignore-not-found
  kubectl -n "$ns" create secret docker-registry ghcr-pull \
    --docker-server=ghcr.io \
    --docker-username=<gh-username> \
    --docker-password="$GHCR_PAT" \
    --docker-email=not-needed@github.com
done
unset GHCR_PAT

# Verify (decode the dockerconfigjson).
for ns in etradie-system edge-ingress-system; do
  echo "--- $ns ---"
  kubectl -n "$ns" get secret ghcr-pull -o jsonpath='{.type}{"\n"}'
  # expect: kubernetes.io/dockerconfigjson
done
```

**The 6 charts that need `ghcr-pull` already reference it** in their
`values-staging.yaml` via:
```yaml
imagePullSecrets:
  - name: ghcr-pull
```
Charts: engine, gateway, execution, management, billing, edge-ingress.
mt-node staging skipped because `mtConnection.enabled=false` in the
staging Application (chart's StatefulSet does not render at Phase 12;
per-tenant mt-node pods are created at runtime by the engine's
`HostedProvisioner` in Phase 14.5 — will need analogous handling).

**Linkerd trust anchor delivery (Option A: commit PUBLIC PEM to chart
values).** The trust anchor is the PUBLIC half of the mesh root CA
(no private key); committing it to git is byte-for-byte safe and
avoids `argocd app set --helm-set-file` drift that root-app's
`selfHeal` would revert on every reconcile. The PRIVATE issuer
cert/key stay in Vault at `etradie/platform/linkerd/production` from
§8.5; only the PUBLIC trust anchor PEM is committed:

```bash
# Embed the PEM (~/eTradie/ca.crt content) as a YAML block scalar:
python3 <<'PYEOF'
with open('deployments/linkerd/control-plane-values.yaml') as f:
    content = f.read()
with open('ca.crt') as f:
    pem = f.read().rstrip('\n')
pem_indented = '\n'.join('  ' + line for line in pem.split('\n'))
new = content.replace('identityTrustAnchorsPEM: ""',
                       f'identityTrustAnchorsPEM: |\n{pem_indented}')
open('deployments/linkerd/control-plane-values.yaml', 'w').write(new)
PYEOF
git add deployments/linkerd/control-plane-values.yaml
git commit -m "phase10 pre-flight: embed Linkerd trust anchor PEM"
git push origin main
```

The chart's `linkerd-control-plane-production.yaml` still carries a
sentinel `identityTrustAnchorsPEM` parameter in `spec.sources[0].helm.parameters`;
that parameter is now inert because the values-file value wins. Do
NOT remove the parameter — it serves as a fail-loud sentinel if the
values-file commit ever gets reverted.

### 10.1 — Install ArgoCD v2.13.3

```bash
kubectl create namespace argocd 2>/dev/null || true
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml
kubectl -n argocd wait --for=condition=Available deployment/argocd-server --timeout=300s
# typically returns `condition met` in ~30–60 seconds on first install.

kubectl -n argocd get pods   # 7 pods, all Running 1/1
```

Expected pods (1 StatefulSet + 6 Deployments): `argocd-application-controller-0`,
`argocd-applicationset-controller-*`, `argocd-dex-server-*`,
`argocd-notifications-controller-*`, `argocd-redis-*`,
`argocd-repo-server-*`, `argocd-server-*`.

### 10.2 — Admin password + port-forward + argocd CLI login (REQUIRED)

The `argocd login` step is REQUIRED: every `argocd app sync` in
§10.5 and Phase 12 fails with `not logged in` without it.

```bash
ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d)
echo "admin password length: ${#ADMIN_ARGO_PWD} chars (no value echoed)"

# Port-forward in a dedicated terminal (leave it running):
kubectl -n argocd port-forward svc/argocd-server 8080:443 &
sleep 2

# CLI login.
argocd login 127.0.0.1:8080 --username admin --password "$ADMIN_ARGO_PWD" --insecure
argocd account list   # confirms the session works
unset ADMIN_ARGO_PWD
```

### 10.3 — Apply both AppProjects + root app-of-apps

**IMPORTANT: `root-app.yaml` cascades immediately.** Once applied,
ArgoCD reconciles every YAML under `deployments/argocd/children/`
as its own Application. Staging children have
`automated.{prune:true, selfHeal:true}` so they start auto-sync at
once; production children stay `OutOfSync` until manually synced
inside the AppProject's business-hours window (13:00 UTC Mon-Fri).

**Staging children pods will hang in Pending until §10.5 syncs the
Linkerd Applications** (their proxy sidecars cannot be injected
without the Linkerd webhook running).

```bash
kubectl apply -f deployments/argocd/appproject.yaml
kubectl apply -f deployments/argocd/linkerd-appproject.yaml
kubectl apply -f deployments/argocd/root-app.yaml

# Verify the AppProjects + root-app exist before §10.5.
argocd proj list
# expect: etradie + linkerd
argocd app list | grep -E '(etradie-root|linkerd-)'
```

### 10.5 — Manually sync the 3 Linkerd Applications in wave order (REQUIRED)

The 3 `linkerd-*` Applications are `automated.{prune:false,
selfHeal:false}` (manual sync only) and the staging children's
meshed pods need the proxy injector webhook running to come up.
Sync them in wave order — the chart's `argocd.argoproj.io/sync-wave`
annotations dictate the order:

```bash
# Wave -6: creates the linkerd-identity-issuer Secret from Vault
# (etradie/platform/linkerd/production via the chart's ExternalSecret).
argocd app sync linkerd-identity-production
argocd app wait linkerd-identity-production --health

# Wave -5: installs Linkerd CRDs.
argocd app sync linkerd-crds-production
argocd app wait linkerd-crds-production --health

# Wave -4: installs the control plane (identity controller, destination,
# proxy injector). identityTrustAnchorsPEM comes from the values-file
# commit at §10.0; identity issuer cert/key comes from the
# linkerd-identity-issuer Secret materialised at wave -6.
argocd app sync linkerd-control-plane-production
argocd app wait linkerd-control-plane-production --health

# Verify the proxy injector is ready.
kubectl -n linkerd get pods
# expect: linkerd-destination-*, linkerd-identity-*, linkerd-proxy-injector-* all Running

# The staging children's NEXT reconcile (default poll = 3 min) finds
# the mesh up and their proxy sidecars inject cleanly. To force the
# reconcile sooner:
argocd app sync data-layer-staging
# (and so on through the wave order; Phase 12 documents the full set)
```

If `linkerd-control-plane-production` ever fails with `invalid
issuer cert chain`, the byte-level fingerprint MATCH from §8.5
(PROGRESS.md §Phase 7 captures) is the place to confirm Vault holds
the right bytes — do NOT regenerate the CA; troubleshoot the
Vault → ESO → K8s Secret pipeline first.

### 10.6 — Install kube-prometheus-stack (REQUIRED before staging-children sync, per BUDGET.md Table 2B)

> **Session-resume entry point.** If you are picking up Phase 10 mid-flight on an existing cluster, read PROGRESS.md “Phase 10.6 in-flight checkpoint” FIRST. The checkpoint section supersedes every earlier resume block in PROGRESS.md and records the exact cluster state, the open defects, the verification commands to run before any fix, and the closeout TODO order. The procedure below is the steady-state canonical install; the checkpoint covers any state where the install has partially completed.

**Why this is REQUIRED, not optional.** Every staging chart
(`data-layer`, `engine`, `gateway`, `execution`, `management`,
`billing`, `edge-ingress`, `envoy`, `observability-logs`)
unconditionally ships `ServiceMonitor` and/or `PrometheusRule`
objects on staging (their `serviceMonitor.enabled` /
`prometheusRule.enabled` toggles default to `true` in each chart's
`values.yaml` and the staging overlays do not override them).
BUDGET.md Table 2B "Staging on Contabo, everything ON" carries five
kube-prometheus-stack rows in the staging floor — `Prometheus`
(200m / 768Mi), `Grafana` (100m / 128Mi), `kube-state-metrics`
(50m / 64Mi), `node-exporter` (50m / 64Mi), `prometheus-operator`
(50m / 96Mi) — all marked `ON` (~0.45 CPU / ~1.1Gi total requests,
already counted in the Table 2B staging floor of ≈ 4.1 CPU / ≈
7.3Gi). The kube-prometheus-stack is part of the Table 2B staging
floor, not an optional add-on.

Without this step, every staging child fails ArgoCD's
`ServerSideApply` dry-run with `the server could not find the
requested resource` for `monitoring.coreos.com/ServiceMonitor` and
`monitoring.coreos.com/PrometheusRule`, and `ApplyOutOfSyncOnly=true`
+ wave-ordering prevents the rest of the resources from being
applied. (`mt-node-staging` is the only staging child that ships no
Prometheus Operator objects, and is therefore the only one that
reports `Healthy` in this failure mode — independent confirmation
that the diagnosis is correct.)

**Sub-step layout.** A new ArgoCD `Application` under
`deployments/argocd/children/monitoring-stack-staging.yaml` at sync
wave `-7` (before the Linkerd `-6` so the CRDs land before any
chart that references them), targeting the `monitoring` namespace
(already whitelisted in the `etradie` AppProject's `destinations`),
sourced from the official `prometheus-community` Helm repo at
`https://prometheus-community.github.io/helm-charts`, chart
`kube-prometheus-stack`. A staging values overlay at
`helm/monitoring-stack/values-staging.yaml` sizes every component to
BUDGET.md Table 2B's staging row.

**AppProject layout decision.** Mirrors the Linkerd pattern: a
dedicated `monitoring` AppProject at
`deployments/argocd/monitoring-appproject.yaml` whitelisting the
cluster-scoped CRDs the stack installs
(`apiextensions.k8s.io/CustomResourceDefinition`, the
`admissionregistration.k8s.io` webhooks, the cluster-scoped
`ClusterRole`/`ClusterRoleBinding`/`PriorityClass` rows) plus the
namespace-scoped kinds the chart renders into `monitoring`. The
`etradie` AppProject already whitelists the namespace as a
destination, but extending its `clusterResourceWhitelist` with the
full kube-prometheus-stack surface would over-privilege the
app-workload project. Same blast-radius isolation rationale as the
Linkerd separation. Applied via direct `kubectl apply -f` (the
root-app's `directory.recurse` does NOT include AppProject files —
see PROGRESS.md operator gotcha #24).

**Apply + sync.**

```bash
# 1. Apply the new AppProject (one-shot, not GitOps-reconciled per
#    the root-app source-path limitation).
kubectl apply -f deployments/argocd/monitoring-appproject.yaml

# 2. The root-app's next reconcile (default 3 min) picks up the new
#    Application file under children/. Force it sooner:
argocd app sync etradie-root

# 3. Manually sync the monitoring-stack-staging Application. (Its
#    automated.{prune:true, selfHeal:true} fires on the next
#    reconcile too, but a manual sync makes the order explicit.)
argocd app sync monitoring-stack-staging --timeout 600
argocd app wait monitoring-stack-staging --health --timeout 600

# 4. Verify the CRDs exist on the cluster.
kubectl get crds | grep monitoring.coreos.com
# expect: servicemonitors / podmonitors / prometheusrules / probes /
#         alertmanagerconfigs / alertmanagers / prometheuses /
#         prometheusagents / scrapeconfigs / thanosrulers (10 total)

# 5. Verify the pods are Running 1/1 in the monitoring namespace.
kubectl -n monitoring get pods
# expect: kube-prometheus-stack-operator-...               1/1 Running
#         prometheus-kube-prometheus-stack-prometheus-0    2/2 Running (prometheus + config-reloader)
#         alertmanager-kube-prometheus-stack-alertmanager-0 2/2 Running (alertmanager + config-reloader)
#         kube-prometheus-stack-grafana-...                3/3 Running (grafana + sidecars)
#         kube-prometheus-stack-kube-state-metrics-...     1/1 Running
#         kube-prometheus-stack-prometheus-node-exporter-* 1/1 Running (DaemonSet, one per node)
```

### 10.7 — Phase 10 closeout (after staging public path verified GREEN)

After the kube-prometheus-stack + the chart-render unblocks of
Phase 10.6 land, the staging public path needs end-to-end
verification BEFORE Phase 10 is declared done:

```bash
for i in 1 2 3; do
  curl -sS -o /dev/null -w 'attempt %{http_code} in %{time_total}s\n' \
    https://staging-api.exoper.com/healthz
done
# expect: 3x HTTP 200 in ~0.5–1.0s. The path traverses
# Browser → Cloudflare edge → cloudflared tunnel → edge-ingress
# (TLS, mTLS-optional in tunnel mode per the chart’s
# client_auth.required: false on staging+production overlays)
# → envoy (/healthz answered by direct_response 200) → gateway.
```

If the probe returns 502 / a Cloudflare error page / Argo Tunnel
"error 1033", consult the Troubleshooting table at the bottom of
this runbook (specifically the four `Phase 10 closeout` rows for
edge-ingress mTLS, Helm `| default` falsy, kubelet image cache,
and envoy `/healthz` 404).

**Residual staging posture on Phase 10 closeout.** This bring-up
left Linkerd mesh DISABLED on 5 staging workloads (engine + the 4
Go services: gateway, execution, management, billing). The
canonical record of WHAT is disabled, WHY, HOW to verify, and HOW
to re-enable is in [PHASE10.6-MESH-DISABLED-CHECKPOINT.md](PHASE10.6-MESH-DISABLED-CHECKPOINT.md).
The data layer (postgres / redis / chromadb), edge-ingress, and
envoy stay meshed. cloudflared is intentionally never meshed.
Production overlays are UNTOUCHED — production must run mesh-on.
Re-enable on staging is operational follow-up, not a Phase 11+
blocker.

**Now the 10 staging children's next reconcile finds the CRDs and
clears their dry-run.** Force the reconcile sooner if you don't
want to wait 3 minutes:

```bash
for app in data-layer engine gateway execution management billing \
           mt-node edge-ingress envoy observability-logs; do
  argocd app sync ${app}-staging --timeout 600 || true
done
argocd app list --grpc-web | grep staging
# expect: every staging child Synced/Healthy (or Synced/Progressing
# while pods come up; mt-node-staging stays Synced/Healthy because
# its chart renders no resources with mtConnection.enabled=false).
```

If any staging child still fails after the kube-prometheus-stack is
healthy, capture the exact error with `argocd app get <name>
--grpc-web` before re-trying — at this point a remaining failure is
a chart-specific defect, not a missing-CRD problem.

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

## Phase 14.6 — Google OAuth 2.0 sign-in ("Continue with Google")

> This phase is **optional**. If `AUTH_GOOGLE_OAUTH_ENABLED=false` (chart base default), the SPA's social-sign-in button stays hidden and the gateway's `/auth/oauth/google/*` routes return 404. Username + password sign-in works without any of the work below. Run this phase when the operator wants users to be able to sign in with Google.

### 14.6.0 — What you're wiring

The full OAuth 2.0 sign-in chain has six independent pieces that ALL have to align byte-for-byte:

1. **GCP OAuth Client** (Google Cloud Console) — holds the client ID, client secret, list of Authorized JavaScript Origins, list of Authorized Redirect URIs. Single source of truth for what redirects Google will accept.
2. **Vault** (`etradie/services/gateway/<env>`) — holds 4 keys: `google_client_id`, `google_client_secret`, `google_redirect_uri`, `google_link_redirect_uri`. The two URIs MUST exist as Authorized Redirect URIs in GCP or token exchange fails with `redirect_uri_mismatch`.
3. **Gateway ConfigMap** (`AUTH_GOOGLE_OAUTH_ENABLED=true`) — the non-secret enable toggle. Off-by-chart-base; flipped on per-environment overlay (`helm/gateway/values-<env>.yaml::config.auth.googleOAuthEnabled: "true"`).
4. **Gateway NetworkPolicy egress** — the gateway must reach `oauth2.googleapis.com:443`, `www.googleapis.com:443` (JWKS), and `accounts.google.com:443`. The chart base ships an `ipBlock: 0.0.0.0/0` rule with `except` for K3s pod + service CIDRs (10.42.0.0/16, 10.43.0.0/16) on ports 80/443. Without this rule the gateway's outbound HTTPS is dropped and the SPA shows `connection refused` on the callback.
5. **SPA env vars** (Vercel project Environment Variables): `VITE_GOOGLE_OAUTH_ENABLED=true` + `VITE_OAUTH_CALLBACK_PATH=/auth/callback/google`. The flag controls whether the "Continue with Google" button renders; the path controls what URL the SPA's router serves.
6. **CSP header** (`vercel.json::headers[*].Content-Security-Policy::connect-src`) — must include the backend origin the SPA POSTs the callback to. Already covers `https://staging-api.exoper.com` AND `https://api.exoper.com` (broadened in commit `71ddecf1` for both environments).

If any one of the six is misaligned, the flow fails with a confusing error in either the gateway log or the browser console. The verification block at the end of this phase tests all six.

### 14.6.1 — GCP OAuth Client setup (one-time per Google account)

The Google Cloud Console OAuth Client is provider-side configuration that ANY environment of this platform shares. Local dev + staging + production all use the SAME client object; what differs is the list of authorized URIs.

1. Open <https://console.cloud.google.com/apis/credentials> in a browser logged in as the GCP project owner.
2. If a client doesn't exist: **Create Credentials → OAuth Client ID → Web Application**. Pick a clear name (e.g. `Exoper`).
3. **Authorized JavaScript origins** — add one entry per public SPA host that calls `gapi.signIn()`-style endpoints. For this platform:
   - `http://localhost:5173` (local dev with the Vite proxy)
   - `https://exoper.com`, `https://www.exoper.com`, `https://app.exoper.com` (production SPA hosts)
   - `https://staging.exoper.com` (staging SPA alias; harmless to include even though traffic 307s to app.exoper.com immediately)
4. **Authorized redirect URIs** — add `/auth/callback/google` AND `/settings/oauth/callback/google` under EACH of the SPA host origins above. Two URIs per host because the sign-in flow and the link-account flow have distinct redirect targets (per `src/auth/config.go::validate` which refuses to start the gateway with the two URIs equal).
5. **Save**. Google warns "It may take 5 minutes to a few hours for settings to take effect" — in practice usually under 60 seconds.
6. Copy the **Client ID** (long string ending in `.apps.googleusercontent.com`) and **Client Secret** (`GOCSPX-...`, 35 chars) from the client's detail view. Keep these tab open while you run 14.6.3.

### 14.6.2 — Decide which redirect URI Vault should hold

This is the single biggest operator trap. The Vault `google_redirect_uri` value MUST be the URL Google will redirect the BROWSER to, NOT the URL the operator typed into the browser address bar. If the Vercel project is configured with a 307 redirect from one SPA host to another (e.g. `staging.exoper.com` 307-redirects to `app.exoper.com`), then:

- User types `https://staging.exoper.com/` → Vercel 307s to `https://app.exoper.com/`
- Browser sees `app.exoper.com` as its origin throughout the OAuth flow
- When the user clicks "Continue with Google", the SPA POSTs `/auth/oauth/google/start` to the backend; the gateway returns an authorize URL with `redirect_uri=<the value from Vault>`
- Google redirects the browser back to that exact URI on the consent grant
- The browser must land at a URL where a SPA route exists AND that matches an Authorized Redirect URI in GCP

Verify what the Vercel domain config actually does:

```bash
curl -sS -L --max-redirs 5 -D - -o /dev/null \
  -w '\nFINAL: code=%{http_code} url=%{url_effective}\n' \
  'https://<staging-host>/auth/callback/google?code=TEST&state=TEST' 2>&1 \
  | grep -iE '^HTTP|^location|^FINAL'
```

- If `FINAL.url` equals `https://<staging-host>/auth/callback/google?code=TEST&state=TEST` (no redirect) → use `<staging-host>` in Vault.
- If `FINAL.url` equals `https://<redirect-target>/auth/callback/google?code=TEST&state=TEST` (307 preserves path+query) — the case for this staging deploy — use `<redirect-target>` in Vault. The browser will only ever land at the redirect target, so the GCP Authorized Redirect URI must be the redirect-target form, and Vault must match.
- If `FINAL.url` equals `https://<redirect-target>/` (path+query stripped on redirect) — the OAuth flow is broken with this Vercel configuration; either remove the redirect (assign the staging host to a separate Vercel project) or change Vercel's redirect rule to preserve path+query.

The current staging deploy uses the middle case: `staging.exoper.com` 307-preserves path+query to `app.exoper.com`. Vault therefore holds `https://app.exoper.com/auth/callback/google`.

### 14.6.3 — Write the 4 OAuth keys into Vault

Vault path: `etradie/services/gateway/<env>`. The 4 keys are added on top of the 12 existing gateway keys via `vault kv patch` (preserves the rest). Copy the Client ID and Client Secret from the GCP Console tab (14.6.1 step 6) and paste at the `read` prompts so they never appear in shell history:

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)

read -p "Paste GOOGLE_CLIENT_ID: " GOOGLE_CLIENT_ID
read -s -p "Paste GOOGLE_CLIENT_SECRET (input hidden): " GOOGLE_CLIENT_SECRET
echo
echo "  Client ID length:     ${#GOOGLE_CLIENT_ID} (expect ~72 ending in .apps.googleusercontent.com)"
echo "  Client Secret length: ${#GOOGLE_CLIENT_SECRET} (expect 35 starting with GOCSPX-)"

# Choose the redirect-URI host per 14.6.2 above.
REDIRECT_HOST=https://app.exoper.com

kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv patch -mount=etradie services/gateway/<env> \
  google_client_id="$GOOGLE_CLIENT_ID" \
  google_client_secret="$GOOGLE_CLIENT_SECRET" \
  google_redirect_uri="${REDIRECT_HOST}/auth/callback/google" \
  google_link_redirect_uri="${REDIRECT_HOST}/settings/oauth/callback/google"

# Verify (no values echoed)
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -format=json services/gateway/<env> \
  | jq -r '.data.data | keys | length as $n | "gateway/<env> now has \($n) keys (was 12, expect 16)"'

unset ROOT_TOKEN GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET REDIRECT_HOST
history -c 2>/dev/null || true
```

### 14.6.4 — Flip the chart-side toggle in the staging overlay

```yaml
# helm/gateway/values-<env>.yaml
config:
  auth:
    # ... existing keys ...
    googleOAuthEnabled: "true"
```

Commit, push to GitHub (`origin`), sync ArgoCD, restart the gateway pod so it picks up the new env vars from the regenerated K8s Secret:

```bash
git add helm/gateway/values-<env>.yaml
git commit -m "gateway(<env>): enable Google OAuth"
git push origin main

export KUBECONFIG=~/.kube/etradie-contabo.yaml
argocd app sync gateway-<env> --grpc-web --timeout 300
kubectl -n etradie-system annotate externalsecret etradie-gateway-secrets \
  force-sync=$(date +%s) --overwrite
sleep 8
kubectl -n etradie-system rollout restart deploy/etradie-gateway
kubectl -n etradie-system rollout status deploy/etradie-gateway --timeout=180s
```

### 14.6.5 — Update Vercel env vars + rebuild the SPA

In the Vercel project's **Settings → Environment Variables** (Production scope), add or confirm:

```
VITE_API_URL=https://<env>-api.exoper.com   # or https://api.exoper.com for production
VITE_API_WS_URL=wss://<env>-api.exoper.com
VITE_GOOGLE_OAUTH_ENABLED=true
VITE_OAUTH_CALLBACK_PATH=/auth/callback/google
```

Then trigger a rebuild (push any commit OR Settings → Deployments → ⋯ on latest → **Redeploy**). Wait 60-120 seconds for Vercel to publish.

### 14.6.6 — Verify the chain end-to-end (canonical 9-hop trace)

This is the single block that verifies all six pieces from 14.6.0 are aligned. Paste each line and check the pass criterion. Substitute `<env>` and `<staging-host>` / `<redirect-target>` per your deploy.

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)

echo "=== HOP 1: Browser → Cloudflare → tunnel → edge-ingress → envoy ==="
for path in /healthz /health /readiness; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' "https://<env>-api.exoper.com${path}")
  printf '  %-15s %s\n' "$path" "$code"
done
# Pass: all three 200.

echo
echo "=== HOP 2: gateway pod env vars + NetworkPolicy ==="
GW_POD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-gateway \
  --field-selector=status.phase=Running -o jsonpath='{.items[-1].metadata.name}')
kubectl -n etradie-system exec "$GW_POD" -- env 2>/dev/null \
  | grep -E '^AUTH_GOOGLE' | awk -F= '{print "    " $1}' | sort
kubectl -n etradie-system get networkpolicy etradie-gateway-network-policy -o json \
  | jq -r '.spec.egress[] | select(.to[]?.ipBlock? != null) | "    ipBlock=\(.to[0].ipBlock.cidr) except=\(.to[0].ipBlock.except) ports=\(.ports | map("\(.protocol):\(.port)") | join(","))"'
# Pass: 5 AUTH_GOOGLE_* env vars + ipBlock 0.0.0.0/0 with except [10.42.0.0/16, 10.43.0.0/16] on TCP:443,TCP:80.

echo
echo "=== HOP 3: gateway pod can reach Google endpoints ==="
kubectl -n etradie-system exec "$GW_POD" -c gateway -- nslookup oauth2.googleapis.com 2>&1 | head -8
# Pass: resolves to two IPs (one IPv4 in 142.251.0.0/16, one IPv6 in 2a00:1450::/32).
# Full reachability test (probe pod):
# Run a curl probe pod with the gateway's labels so the same NetworkPolicy applies:
#   kubectl run gw-probe -n etradie-system --rm -i --restart=Never --image=curlimages/curl:8.7.1 \
#     --labels='app.kubernetes.io/name=etradie-gateway,probe=true' \
#     --command -- sh -c 'curl -sS -m 10 -o /dev/null -w "%{http_code}\n" https://oauth2.googleapis.com/token; curl -sS -m 10 -o /dev/null -w "%{http_code}\n" https://www.googleapis.com/oauth2/v3/certs'
# Pass: 404 (correct GET reject from token endpoint) and 200 (JWKS).

echo
echo "=== HOP 4: Vault holds correct OAuth values ==="
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -mount=etradie -format=json services/gateway/<env> \
  | jq -r '.data.data | {
      google_redirect_uri,
      google_link_redirect_uri,
      google_client_id_suffix: (.google_client_id | tostring | (length as $l | .[($l-32):]))
    }'
# Pass: redirect URIs end with /auth/callback/google and /settings/oauth/callback/google;
# client_id ends with .apps.googleusercontent.com.

echo
echo "=== HOP 5: OAuth start endpoint builds valid authorize URL ==="
RESP=$(curl -sS -X POST 'https://<env>-api.exoper.com/auth/oauth/google/start' \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://<redirect-target>' \
  -d '{"return_to":"/"}')
AUTHURL=$(echo "$RESP" | jq -r '.authorize_url')
REDIR_URI=$(echo "$AUTHURL" | grep -oE 'redirect_uri=[^&]*' | cut -d= -f2 \
  | python3 -c "import urllib.parse, sys; print(urllib.parse.unquote(sys.stdin.read().strip()))")
echo "  Authorize URL host:  $(echo "$AUTHURL" | awk -F'?' '{print $1}')"
echo "  redirect_uri:        $REDIR_URI"
echo "  state length:        $(echo "$RESP" | jq -r '.state | length')"
# Pass: host = https://accounts.google.com/o/oauth2/v2/auth;
# redirect_uri = https://<redirect-target>/auth/callback/google; state length = 43.

echo
echo "=== HOP 6: Vercel SPA at <redirect-target> → backend ==="
curl -sS -D - -o /dev/null https://<redirect-target>/ 2>/dev/null \
  | grep -i 'content-security-policy' | tr ';' '\n' | grep -i connect-src | head -1
HTML=$(curl -sS -L https://<redirect-target>/ 2>/dev/null)
JS_FILE=$(echo "$HTML" | grep -oE '/assets/index[^"]*\.js' | head -1)
curl -sS -L "https://<redirect-target>${JS_FILE}" 2>/dev/null \
  | grep -oE '(staging-api\.exoper\.com|api\.exoper\.com)' | sort -u
# Pass: CSP includes both backends; bundle references the env-correct backend host.

echo
echo "=== HOP 7: Vercel 307 preserves OAuth callback URL ==="
curl -sS -L --max-redirs 5 -D - -o /dev/null \
  -w '\n  FINAL: code=%{http_code} url=%{url_effective}\n' \
  'https://<staging-host>/auth/callback/google?code=TESTCODE&state=TESTSTATE' 2>&1 \
  | grep -iE '^HTTP|^location|^  FINAL'
# Pass: FINAL url is https://<redirect-target>/auth/callback/google?code=TESTCODE&state=TESTSTATE
# (path AND query preserved).

echo
echo "=== HOP 8: Cookie cross-subdomain attributes ==="
# Use the admin password to test the cookie path (any valid login works)
ADMIN_PASS=$(grep ^ADMIN_PASS ~/etradie-<env>-creds.txt | cut -d= -f2-)
BODY=$(jq -nc --arg u admin --arg p "$ADMIN_PASS" '{username:$u, password:$p}')
JAR=$(mktemp)
curl -sS -c "$JAR" -X POST https://<env>-api.exoper.com/auth/login \
  -H 'Origin: https://<redirect-target>' \
  -H 'Content-Type: application/json' -d "$BODY" \
  -D - -o /dev/null 2>&1 \
  | grep -i 'set-cookie:' \
  | sed -E 's/(access_token|refresh_token|csrf_token)=[^;]+/\1=<value>/g' \
  | sed 's/^/    /'
rm -f "$JAR"
unset ADMIN_PASS BODY JAR
# Pass: 3 Set-Cookie headers, all with Domain=exoper.com (or .exoper.com); Secure; SameSite=None; HttpOnly
# on the access/refresh cookies; the csrf_token cookie is JS-readable (no HttpOnly).

echo
echo "=== HOP 9: gateway log shows recent OAuth attempts ==="
kubectl -n etradie-system logs "$GW_POD" --since=15m 2>&1 \
  | grep -iE 'oauth|google|token request|callback' | tail -20
# Pass after a real sign-in test: log shows oauth_flow_started → oauth_token_exchanged →
# oauth_user_resolved → oauth_session_created. Empty = no attempts yet.

unset ROOT_TOKEN GW_POD RESP AUTHURL REDIR_URI HTML JS_FILE
```

### 14.6.7 — Browser test (the actual end-to-end sign-in)

1. Open a **fresh incognito window** (avoids stale cookies / localStorage).
2. Open **DevTools → Network tab** BEFORE navigating; check "**Preserve log**" so cross-document redirects don't wipe the log.
3. Navigate to `https://<staging-host>/`. Browser receives 307 → lands at `https://<redirect-target>/`.
4. SPA loads. Login page renders with the **"Continue with Google"** button visible.
5. Click the button. Watch the Network tab:
   - `POST https://<env>-api.exoper.com/auth/oauth/google/start` `{return_to:"/"}` → `200` with JSON `{authorize_url, state, expires_in:600}`.
   - SPA navigates browser to `https://accounts.google.com/o/oauth2/v2/auth?...` (the `authorize_url` from the response).
   - Google account picker appears — select your account.
   - Google redirects browser to `https://<redirect-target>/auth/callback/google?code=<authcode>&state=<state>`.
   - SPA's `OAuthCallbackPage` mounts; extracts code+state from URL.
   - `POST https://<env>-api.exoper.com/auth/oauth/google/callback` `{code, state}` → `200` with `{user:{...,role:"etradie",auth_provider:"google",...}, return_to:"/"}` AND 3 `Set-Cookie` headers (access_token, refresh_token, csrf_token), all with `Domain=exoper.com; SameSite=None; Secure`.
   - SPA redirects to `/` (the dashboard).
   - `GET https://<env>-api.exoper.com/auth/me` (cookies attached automatically by the browser) → `200` with the same user JSON.
6. Dashboard loads with the signed-in user.

### 14.6.8 — Promote OAuth-signed-in user to admin (operator-only)

The `/auth/register` and `/auth/oauth/google/callback` endpoints both default to `role='etradie'` for newly-created users; promoting to `role='admin'` is direct SQL (no privilege-escalation API surface):

```bash
kubectl -n etradie-system exec postgres-0 -c postgres -- \
  psql -U etradie -d etradie -c "
    UPDATE auth_users
    SET role='admin'
    WHERE email='<your-google-email>'
    RETURNING username, email, role, auth_provider, email_verified, created_at;"
```

The new JWT picks up `role='admin'` on the user's next sign-in (or on the next refresh_token rotation — access tokens are short-lived, 15 min default).

### 14.6.9 — Phase 14.6 closeout TODOs

The staging deploy that produced this section closed at the end of step 7 with a working sign-in. Outstanding operational follow-ups for any production cutover:

1. Repeat 14.6.1-14.6.5 for the production environment (production-specific Vault path `etradie/services/gateway/production`, production Vercel project's env vars, production GCP Authorized origins/URIs). The gateway chart's egress rule from this commit is environment-independent so no production-specific NetworkPolicy work is needed.
2. Consider configuring a production-only GCP OAuth Client separate from staging's, OR (simpler) use the same client with both staging + production Authorized URIs listed. Single-client model is the current posture per the GCP `Exoper` client's URI list.
3. The signed-in user's profile picture, email-verified status, and Google subject ID are written to the `auth_oauth_identities` table. Inspect for debugging:
   ```sql
   SELECT u.username, u.email, u.role, u.auth_provider, oi.provider_subject, oi.picture, oi.email_verified
   FROM auth_users u
   LEFT JOIN auth_oauth_identities oi ON u.id = oi.user_id
   ORDER BY u.created_at;
   ```
4. If the gateway log shows `oauth: token exchange failed: status=401 error=invalid_client`, the Vault `google_client_secret` is wrong or stale. Re-paste from GCP Console; in extreme cases (operator suspects compromise) reset the client secret in GCP Console and re-write Vault.

---

## Phase 15 — Post-deploy operational notes

- **Disabled toggles (BUDGET.md Table 2B re-enable index):** HPAs, PDBs, Linkerd `highAvailability`, Linkerd viz, per-service `linkerdPolicy`, snapshotter are intentionally OFF. Each has its re-enable pointer in BUDGET.md. Do not re-enable ad hoc on this box.
- **Mesh verification before per-service authz:** install viz on demand (`git mv deployments/argocd/optional/linkerd-viz-production.yaml deployments/argocd/children/` then sync), run `linkerd viz edges` until every internal edge is SECURED, then set `linkerdPolicy.enabled: true` per service and re-sync. See `docs/runbooks/linkerd-mesh-rollout.md`.
- **Backups:** production postgres backup CronJob + weekly restore drill are ON. Populate the offsite B2 path `etradie/data-layer/postgres-backup/production` (rclone_remote_name, rclone_config, remote_bucket, remote_path_prefix) BEFORE the first 02:00 UTC run. See `docs/runbooks/database-backup-restore.md`.
- **Vault Raft snapshots:** back up Vault out-of-band — it is the source of truth for every secret and the mesh CA.
- **Monitoring stack operational notes:** the kube-prometheus-stack itself was installed at Phase 10.6 (REQUIRED step, per BUDGET.md Table 2B's staging floor). Post-install operational items: rotate the Grafana admin password (default `prom-operator` from the chart) on first login; Prometheus retention is 7d / 20Gi PVC per Table 2B (raise both with a values overlay edit + re-sync if the soak shows higher cardinality); every chart's `ServiceMonitor`/`PrometheusRule` is auto-discovered via the `prometheus: kube-prometheus` label set on each object by the platform charts. Mute alerts during a planned outage by silencing them in the Alertmanager UI rather than turning the rule off.

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
| staging children `OutOfSync/Missing`, `argocd app get` shows `the server could not find the requested resource` for `monitoring.coreos.com/ServiceMonitor` or `PrometheusRule` | kube-prometheus-stack CRDs missing on the cluster | complete Phase 10.6 (REQUIRED per BUDGET.md Table 2B); staging children auto-sync on the next reconcile |
| Phase 10 closeout: public probe of `https://<env>-api.exoper.com/healthz` returns `502` from a Cloudflare anycast IP; edge-ingress log shows `TLS handshake failed ... peer sent no certificates` from cloudflared peer IP (e.g. `10.42.0.x`) | edge-ingress is enforcing mTLS (Cloudflare AOP client-cert verification) but cloudflared has no field in its `originRequest` schema to present a client cert. AOP toggles in the Cloudflare dashboard (Global / Zone-level / Per-hostname) apply only to standard proxy-mode traffic; tunnel-routed traffic ignores them. | Set `clientAuth.required: false` in `helm/edge-ingress/values-<env>.yaml` (both staging and production overlays in this repo do this because both use Cloudflare Tunnel). Rust binary supports the field via `config.tls.clientAuth.required: bool` (`src/edge-ingress/crates/tls/src/config.rs`); chart renders it verbatim in the configmap. CI rebuild required. Trust boundary becomes the tunnel JWT + ufw + Linkerd mesh on cluster-internal hops + the gateway's trusted-proxy-CIDR honor of `CF-Connecting-IP`. |
| Phase 10 closeout: chart overlay sets `clientAuth.required: false` but rendered ConfigMap still shows `required: true` and edge-ingress still demands the cert | Helm `\| default true` pipeline silently swallows the `false` override — Go's pipeline truth test treats `false` as falsy. The template renders `false \| default true` → `true`. | Drop the `\| default` from the template; render verbatim. The chart base `values.yaml` already declares the field with the desired default so it is never nil. Audit ref: `helm/edge-ingress/templates/configmap.yaml`, commit `402480d7`. |
| Phase 10 closeout: staging chart change + CI rebuild succeeded, but pod still runs the OLD code (`docker manifest inspect` shows a new digest in GHCR; the live pod's `imageID` is the old one) | Staging chart base default `imagePullPolicy: IfNotPresent` means the kubelet keeps the cached image as long as the tag string is unchanged. Staging re-uses the same tag (`staging-v0.1.0`) across rebuilds. | Set `image.pullPolicy: Always` in `helm/<service>/values-staging.yaml`. Production overlay keeps `IfNotPresent` because production rolls with explicit tag bumps. Audit ref: edge-ingress `a3633434`, engine `f033386b`. |
| Phase 10 closeout: edge-ingress logs `health check completed status:404 Not Found is_healthy:false` against envoy on every interval; cluster eventually 502s the public path | envoy has no `/healthz` route in its `route_config.virtual_hosts[].routes`; the path falls through the catch-all `prefix: "/"` to `gateway_cluster`, and gateway's health endpoint is `/health` (not `/healthz`). edge-ingress hardcodes `/healthz` in its upstream health-checker (`src/edge-ingress/crates/upstream/src/health.rs::check_endpoint`). | Add a `direct_response: status: 200` route on envoy at `path: "/healthz"`, declared BEFORE the catch-all so envoy matches it first. envoy answers its own probe locally without depending on the upstream being route-aware; envoy retains its own separate `http_health_check` on each cluster (e.g. `gateway_cluster` probes gateway's `/readiness`) for the upstream side. Audit ref: `helm/envoy/templates/configmap.yaml`, commit `34a01588`. |
| Go service pods (gateway/execution/management/billing) `1/2 CrashLoopBackOff` with `tls error: read tcp ...: connection reset by peer` or `server does not support SSL, but SSL was required` at first DB call | postgres pod does not serve TLS but every app config enforces `sslmode=require` in prod/staging (src/auth/config.go, src/billing/config/config.go, src/execution/internal/config/config.go, src/engine/config.py). Verify with `kubectl -n etradie-system exec postgres-0 -c postgres -- psql -U etradie -d etradie -c 'SHOW ssl;'` — must return `on`, not `off`. | confirm `helm/data-layer/values.yaml::postgres.tls.enabled=true` is rendered; check the `tls-cert-init` initContainer in `postgres-0` ran to completion; the postgres container args MUST include `-c ssl=on -c ssl_cert_file=... -c ssl_key_file=...`. After postgres comes up TLS-enabled, force-restart the Go service pods so they re-handshake against the now-TLS server. Engine pods also need `config.database.nativeTls: "true"` in their overlay so asyncpg switches from MESH mode (ssl=False) to NATIVE mode (ssl='require'). |
| Phase 14.6: SPA shows `Sign-in failed: google oauth: token request transport: Post "https://oauth2.googleapis.com/token": dial tcp <ip>:443: connect: connection refused` after clicking "Continue with Google" | Gateway NetworkPolicy egress permits only intra-cluster traffic (linkerd, postgres, redis, internal services); the gateway has no outbound HTTPS path to Google's OAuth/OIDC endpoints. Same root cause as the earlier engine egress fix `aff0e645`. | Add `ipBlock: 0.0.0.0/0` egress rule with `except` for the K3s pod CIDR (10.42.0.0/16) and service CIDR (10.43.0.0/16) on ports 80/443 to `helm/gateway/values.yaml::networkPolicy.egress`. NetworkPolicy changes take effect immediately on the next reconcile — no pod restart needed. Audit ref: Phase 14.6 ; commit that landed this for the gateway. |
| Phase 14.6: Google sign-in returns `redirect_uri_mismatch` from Google's consent page | The `google_redirect_uri` value in Vault does not match any URI in the GCP OAuth Client's Authorized Redirect URIs list. Vercel's 307 redirects (e.g. staging.exoper.com → app.exoper.com) mean the BROWSER lands at the post-redirect host, so the Vault URI must be the post-redirect host AND that exact URI must be Authorized in GCP. | Confirm where Vercel actually lands the browser with `curl -L /auth/callback/google?code=TEST&state=TEST` and read the FINAL url. Update Vault `google_redirect_uri` and `google_link_redirect_uri` to match that host. Add the matching URIs to GCP Console → Credentials → OAuth Client → Authorized redirect URIs. Audit ref: Phase 14.6.2. |
| Phase 14.6: SPA's "Continue with Google" button does not render even though VITE_GOOGLE_OAUTH_ENABLED=true is set in Vercel | Vercel hasn't rebuilt the SPA bundle with the new env var. Vite bakes env vars in at build time, not at runtime. | Trigger a Vercel rebuild: Settings → Deployments → ⋯ on latest → Redeploy, OR push any trivial commit to main. Wait 60-120 seconds. Verify the new bundle name (in `<head>`) is different from before. |
| Phase 14.6: Gateway pod won't start with `GOOGLE_CLIENT_ID must be set when GOOGLE_OAUTH_ENABLED=true` (or `_SECRET` / `_REDIRECT_URI` / `_LINK_REDIRECT_URI` variant) | Chart toggle is on (`googleOAuthEnabled: "true"` in values overlay) but Vault is missing one or more of the 4 required OAuth keys; ESO renders an empty value into the K8s Secret; `src/auth/config.go::validate()` rejects the pod start. | Re-run the Vault patch (14.6.3) ensuring all 4 keys are non-empty; force-refresh ESO; restart the gateway pod. |

---

## Environment & Identity Reference (READ FIRST when picking up an in-flight deploy)

> The eTradie platform is split across three providers (Cloudflare DNS/Tunnel, Contabo VPS for K3s, Vercel for the SPA), one third-party identity provider (Google OAuth), and two git remotes (GitHub canonical + GitLab MCP mirror). This section is the operator's single index of every URL, hostname, account, and credential file the deploy depends on — organised by category. Every entry cites the chart value, Vault path, or commit where the configuration lives so a new operator can verify state from the repo rather than from memory.

### Registrable domain + zone

| Item | Value | Source of truth |
|---|---|---|
| Registrable domain | `exoper.com` | DNS registrar |
| Domain registrar | Porkbun | (account: operator personal) |
| Authoritative DNS | Cloudflare | (zone added to operator's Cloudflare account; nameservers delegated from Porkbun to Cloudflare's `ns1.cloudflare.com` / `ns2.cloudflare.com`) |
| Cloudflare account ID | recorded in `PROGRESS.md` Phase 6 per-deploy values | dashboard URL |
| Cloudflare zone ID for `exoper.com` | recorded in `PROGRESS.md` Phase 6 | `GET /zones?name=exoper.com` |

### Cloudflare DNS records (read top-to-bottom; proxy state matters)

The `exoper.com` zone holds the following records. **Proxy state** is the critical operational attribute — do NOT flip it without understanding the impact.

| Record name | Type | Target | Proxy | Purpose |
|---|---|---|---|---|
| `exoper.com` (apex) | A | `76.76.21.21` | DNS only | Vercel SPA apex; serves the production SPA build |
| `app.exoper.com` | CNAME | `cname.vercel-dns.com` | DNS only | Vercel SPA production user-facing host |
| `www.exoper.com` | CNAME | `cname.vercel-dns.com` | DNS only | Vercel SPA www alias |
| `staging.exoper.com` | CNAME | `<vercel-project-id>.vercel-dns-NNN.com` | DNS only | Vercel SPA staging hostname — currently configured as a 307 alias that redirects to `app.exoper.com` (preserves path+query). See "Vercel project model" below. |
| `api.exoper.com` | (not yet) | — | — | Production backend tunnel — **not deployed yet** (no production K3s cluster exists). Will be added when production deploy starts. |
| `staging-api.exoper.com` | CNAME | `<tunnel-uuid>.cfargotunnel.com` | **Proxied** | Staging backend Cloudflare Argo Tunnel — auto-created by `PUT /accounts/<id>/cfd_tunnel/<id>/configurations` during Phase 6.2.3. Routes through Cloudflare edge → cloudflared connector in the K3s cluster → edge-ingress on `edge-ingress.edge-ingress-system.svc.cluster.local:443`. **MUST stay Proxied** — the entire tunnel transport depends on Cloudflare's anycast network terminating the public TLS. |
| `_acme-challenge.exoper.com` | TXT | (two entries) | DNS only | Let's Encrypt ACME validation tokens; used by Vercel for TLS cert provisioning. Do not delete. |
| `_vercel.exoper.com` | TXT | `vc-domain-verify=staging.exoper.com,<id>,dc` | DNS only | Vercel domain-ownership verification record — required for `staging.exoper.com` custom domain to validate in Vercel. |
| `exoper.com` | TXT | `v=spf1 include:_spf.porkbun.com ~all` | DNS only | SPF record — authorises Porkbun's mail-forward servers to send email From: `@exoper.com`. |
| `exoper.com` | MX (prio 10) | `fwd1.porkbun.com` | DNS only | Porkbun email forwarding |
| `exoper.com` | MX (prio 20) | `fwd2.porkbun.com` | DNS only | Porkbun email forwarding backup |

**Mixing proxy modes within one zone is intentional and correct**:
- `staging-api.exoper.com` is Proxied (the tunnel itself depends on Cloudflare terminating TLS)
- All Vercel-fronted records are DNS-only (Vercel terminates its own TLS via Let's Encrypt; double-proxying would break cert chains)
- `_acme-challenge` / `_vercel` / `MX` / SPF records are DNS-only (validation + email; proxy is meaningless for non-HTTP records)

### Cloudflare Tunnel (`etradie-staging`)

| Item | Value | Source |
|---|---|---|
| Tunnel name | `etradie-staging` | Created in Phase 6.1 via Cloudflare Zero Trust UI |
| Tunnel UUID | recorded in `PROGRESS.md` Phase 6 "Deploy-specific values captured" | dashboard URL `/cfd_tunnel/<UUID>` |
| Ingress public hostname | `staging-api.exoper.com` | `PUT /accounts/<id>/cfd_tunnel/<id>/configurations` (Phase 6.2.3) |
| Origin service URL | `https://edge-ingress.edge-ingress-system.svc.cluster.local:443` | same |
| Connector | `cloudflared` Deployment in `edge-ingress-system` namespace | `helm/edge-ingress/templates/cloudflared-deployment.yaml` |
| Tunnel JWT token | Vault path `etradie/services/edge-ingress/staging/cloudflare/tunnel`, key `tunnel_token` | `kubectl -n vault exec ... vault kv get` |
| Workstation backup of token | `~/cloudflare-staging-tunnel-token.txt` (mode 0600) | Phase 6.1 capture |
| Production tunnel | not yet created | will be `etradie-production` when production deploy starts |

### Contabo VPS (the K3s host)

| Item | Value | Source |
|---|---|---|
| Provider | Contabo (account: operator personal) | https://my.contabo.com |
| VPS profile | VPS 30 NVMe (8 vCPU / 24 GB / 200 GB NVMe) | `BUDGET.md` Table 2B |
| Public IP | recorded in `PROGRESS.md` Phase 1 | Contabo dashboard |
| Hostname | `vmi3362776` | `hostname` on the box |
| OS | Ubuntu 24.04.4 LTS | recorded in Phase 2 status |
| Kernel | `6.8.0-124-generic` (post Phase 1.3 apt upgrade + reboot) | `uname -r` |
| Operator SSH user | `etradie` (passwordless sudo) | Phase 1.1 |
| Root SSH | **disabled** (`PermitRootLogin no` in sshd hardening drop-in) | `/etc/ssh/sshd_config.d/10-etradie-hardening.conf` |
| Emergency recovery | Contabo VNC console (browser-based, password from welcome email) | Phase 1 "Emergency SSH recovery" |
| Workstation SSH key | `~/.ssh/id_ed25519` (passphrase-protected; ssh-agent loaded per WSL boot) | Phase 1 measure 2 |
| VPS firewall | ufw default-deny inbound + `22/tcp LIMIT IN` only | Phase 1.6 |
| K3s API access | SSH local-forward `ssh -N -L 6443:127.0.0.1:6443 etradie@<vps-ip>` (dedicated terminal) | Phase 2.3 |
| Workstation kubeconfig | `~/.kube/etradie-contabo.yaml` (mode 0600; `server: https://127.0.0.1:6443`) | Phase 2.3 |

### Backend hostnames (HTTP/HTTPS endpoints)

| Hostname | Environment | State | Where the chart points |
|---|---|---|---|
| `staging-api.exoper.com` | staging | **LIVE** | `helm/edge-ingress/values-staging.yaml`; gateway CORS `allowedOrigins` in `helm/gateway/values-staging.yaml` matches the SPA hosts that reach it |
| `api.exoper.com` | production | **NOT YET DEPLOYED** | `helm/edge-ingress/values-production.yaml` references this hostname; tunnel + DNS will be added when production cluster is provisioned |

Both hosts answer the same surfaces when live:
- `/healthz` → envoy direct_response 200 (synthetic edge probe)
- `/health` → gateway `handleHealth` (always 200, no deps)
- `/readiness` → gateway `handleReadiness` (200 only when redis + engine HTTP + own gRPC are all reachable)
- `/auth/*` → gateway public auth routes (login, register, refresh, logout, password reset, OAuth start/callback)
- `/api/v1/*` → gateway protected dashboard routes (require JWT cookie + CSRF header)
- `/webhooks/paddle` → envoy direct route to billing service
- `/webhooks/lemonsqueezy` → envoy direct route to billing service

### Frontend hostnames (Vercel SPA)

| Hostname | Vercel domain config | What loads in the browser |
|---|---|---|
| `app.exoper.com` | Custom domain on the (only) Vercel project | The SPA build (Vite-bundled React) |
| `staging.exoper.com` | Custom domain on the same Vercel project, configured as **307 redirect to `app.exoper.com`** preserving path + query | Browser redirected immediately to `app.exoper.com`; SPA loads from app.exoper.com |
| `www.exoper.com` | Custom domain on the same project, 307 redirect to `app.exoper.com` | Same redirect behaviour |
| `exoper.com` (apex) | Custom domain on the same project, 307 redirect to `app.exoper.com` | Same |
| `<project>.vercel.app` | Default Vercel hostname for the project | The SPA build (used for previews / fallback) |

This is a deliberate "one Vercel project, multiple domain aliases" model. The SPA is built **once** with the env vars set in the Vercel project's Production environment, and the resulting bundle is served at every aliased host. The 307 redirects collapse all user-facing entry points to the canonical `app.exoper.com`.

**Implication**: the bundle's `VITE_API_URL` is one value. While staging is the current live environment, that value is set to `https://staging-api.exoper.com`. When production is later deployed, the same project's env var flips to `https://api.exoper.com` and the next Vercel build picks up the change.

### Vercel project

| Item | Value | Source |
|---|---|---|
| Provider | Vercel (account: operator personal) | https://vercel.com/dashboard |
| Repository connected | `FlameGreat-1/eTradie` (GitHub) | Vercel project settings → Git |
| Project root directory | `cotradee/` (the SPA lives in a subdirectory of the monorepo) | Vercel project settings → General |
| Framework preset | Vite | auto-detected |
| Build command | `npm run build` (Vite default) | `cotradee/package.json` |
| Output directory | `dist` (Vite default) | same |
| Environment variables | see below — set per Vercel "Production" environment scope | Vercel project settings → Environment Variables |

**Vercel environment variables (Production scope) — staging-aligned (current live state):**

| Variable | Current value | Audit ref |
|---|---|---|
| `VITE_API_URL` | `https://staging-api.exoper.com` | `cotradee/src/config/env.ts` reads it via `import.meta.env.VITE_API_URL` |
| `VITE_API_WS_URL` | `wss://staging-api.exoper.com` | same |
| `VITE_GOOGLE_OAUTH_ENABLED` | `true` | `cotradee/src/config/env.ts::googleOAuthEnabled` |
| `VITE_OAUTH_CALLBACK_PATH` | `/auth/callback/google` | `cotradee/src/config/env.ts::oauthCallbackPath` |

**When production deploy runs**, these flip to `https://api.exoper.com` / `wss://api.exoper.com`. The OAuth flag + callback path stay the same.

### CSP (Content Security Policy) header

The SPA's `vercel.json` defines a CSP header for every response Vercel serves. Current `connect-src` directive (per commit `71ddecf1`):

```
connect-src 'self' https://api.exoper.com wss://api.exoper.com https://staging-api.exoper.com wss://staging-api.exoper.com
```

The single CSP covers BOTH production and staging backend origins so the same bundle can be served at the same Vercel project regardless of which environment's `VITE_API_URL` it was built with. Other CSP directives (`script-src 'self'`, `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`, `frame-ancestors 'none'`, etc.) are environment-independent.

### Email + identity

| Item | Value | Source |
|---|---|---|
| Email forwarding | Porkbun (registrar service) | MX records in zone |
| Admin email | `admin@exoper.com` | gateway `handleRegister` seeded value |
| Admin username | `admin` | `auth_users.username` row |
| Admin password | rotated to a 4-of-4-char-class value during Phase 14.5 admin-seed step; stored in Vault `etradie/services/gateway/staging` key `auth_admin_password` and on workstation at `~/etradie-staging-creds.txt` (mode 0600) | Phase 14.5; PROGRESS gotcha #44 |
| SPF | `v=spf1 include:_spf.porkbun.com ~all` (covers Porkbun forwarding) | DNS TXT record on zone apex |

### Google OAuth 2.0 client

| Item | Value | Source |
|---|---|---|
| Provider | Google Cloud Console | https://console.cloud.google.com/apis/credentials |
| Client name | `Exoper` | GCP Console |
| Client type | OAuth 2.0 Client ID (Web application) | GCP Console |
| Client ID | stored in Vault at `etradie/services/gateway/staging` key `google_client_id`; format: `<numeric>-<random>.apps.googleusercontent.com` (~72 chars) | Phase 14 frontend connection step 3 |
| Client Secret | stored in Vault at `etradie/services/gateway/staging` key `google_client_secret`; format: `GOCSPX-<28 chars>` | same |
| Authorised JavaScript origins (in GCP Console) | `http://localhost:5173` (dev), `https://exoper.com`, `https://www.exoper.com`, `https://app.exoper.com`, `https://staging.exoper.com` | GCP Console |
| Authorised redirect URIs (in GCP Console) | `http://localhost:5173/auth/callback/google` and `/settings/oauth/callback/google` (dev); `https://exoper.com/auth/callback/google` and `/settings/...`; same pattern for `www.exoper.com`, `app.exoper.com`, `staging.exoper.com` | GCP Console |
| Sign-in redirect URI sent to Google (staging deploy) | `https://app.exoper.com/auth/callback/google` | Vault key `google_redirect_uri`; rendered into K8s Secret as `AUTH_GOOGLE_REDIRECT_URI`. The browser ends up at app.exoper.com (not staging.exoper.com) because the staging.exoper.com 307 collapses to app.exoper.com. |
| Link-account redirect URI (staging) | `https://app.exoper.com/settings/oauth/callback/google` | Vault key `google_link_redirect_uri`; rendered as `AUTH_GOOGLE_LINK_REDIRECT_URI`. Must differ from the sign-in URI per `src/auth/config.go::validate()`. |
| Gateway OAuth toggle | `helm/gateway/values-staging.yaml::config.auth.googleOAuthEnabled: "true"` | rendered into ConfigMap as `AUTH_GOOGLE_OAUTH_ENABLED` |

### Git remotes

| Remote | URL | Purpose |
|---|---|---|
| `origin` (canonical) | `https://github.com/FlameGreat-1/eTradie.git` | ArgoCD reads chart manifests from THIS remote; Vercel watches THIS remote for SPA rebuilds |
| `gitlab` (MCP mirror) | `https://gitlab.com/exoper2/exoper.git` | The MCP integration's authoring target for docs commits (PROGRESS.md, README.md). Operator manually `git pull --rebase gitlab main` to fold MCP commits back, then `git push origin main` to land them where ArgoCD + Vercel will see them. |

**Load-bearing rule**: every chart change OR SPA change MUST end up on GitHub `origin` to take effect. PROGRESS gotcha #15 records this.

### Container registry (GHCR — GitHub Container Registry)

| Item | Value | Source |
|---|---|---|
| Registry | `ghcr.io/flamegreat-1` | GitHub account that owns the packages |
| Image base | `ghcr.io/flamegreat-1/etradie` (5 service images) + `ghcr.io/flamegreat-1/etradie-mt-node` (hosted-MT Wine image) | `ci.yml` `IMAGE_BASE`; `helm/mt-node/values-image.yaml::image.repository` |
| Package visibility | **Private** | per Phase 10.0 pre-flight decision |
| Push PAT | `~/.ghcr_pat` (workstation, mode 0600) — GitHub classic PAT with `repo + write:packages` scope | Phase 0.2; consumed by Phase 2.5 `docker push` and by the GitHub Actions CI build |
| Pull PAT | `~/.ghcr_pull_pat` (workstation, mode 0600) — GitHub classic PAT with `read:packages` ONLY (separation of duties) | Phase 10.0.3 |
| In-cluster pull Secret | `ghcr-pull` in `etradie-system` AND `edge-ingress-system` namespaces (`type: kubernetes.io/dockerconfigjson`) | Phase 10.0.4; referenced by each chart's `imagePullSecrets: [{name: ghcr-pull}]` |

### Vault (the canonical secret store)

| Item | Value | Source |
|---|---|---|
| Vault location | In-cluster: `vault-0` StatefulSet pod in `vault` namespace | Phase 3 |
| Unseal model | Shamir 5-of-3 (`-key-shares=5 -key-threshold=3`) | Phase 3.2 |
| Unseal keys file | `~/vault-init.txt` (workstation, mode 0600) | Phase 3.2 |
| Root token | extract via `awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt`; format: `hvs.<24 chars>` = 28 chars total | Phase 3.2 |
| KV-v2 mount | `etradie` (canonical) and `secret` (dev/test — not used by charts) | Phase 3.4.1b |
| Path schema | every path lives directly under the mount (single-prefix). PROGRESS gotcha #23 (corrected by gotcha #9 inline note) records the ESO `buildPath` behaviour that drives this layout. | `infrastructure/cluster/vault-paths/main.tf` |
| Audit log | **disabled** (was enabled mid-Phase-10 debug; disabled post-cleanup; gotcha #29) | `vault audit list` returns "No audit devices are enabled." |

**Vault paths the operator interacts with most often** (all under the `etradie` mount):

| Path | What it holds |
|---|---|
| `data-layer/postgres/staging` | `postgres_user`, `postgres_db`, `postgres_password` |
| `data-layer/redis/staging` | `redis_password` |
| `data-layer/chromadb/staging` | `auth_token` (read by both chromadb server AND engine — single source of truth) |
| `platform/linkerd/production` | `trust_anchor_pem`, `issuer_tls_crt`, `issuer_tls_key` (mesh CA — PROGRESS gotcha #10 explains why `/production` is canonical even on a staging box) |
| `services/gateway/staging` | 16 keys: 6 postgres + 6 auth (`auth_database_url`, `auth_jwt_secret`, `auth_admin_password`, `engine_internal_shared_secret`, `billing_internal_shared_secret`, `gateway_redis_url`) + 4 Google OAuth (`google_client_id`, `google_client_secret`, `google_redirect_uri`, `google_link_redirect_uri`) |
| `services/engine/staging` | 15 keys: postgres + redis + KEK + JWT + LLM API keys (twelvedata, fred, anthropic, openai, gemini, metaapi, cftc) |
| `services/execution/staging` | 6 keys |
| `services/management/staging` | 6 keys |
| `services/billing/staging` | 18 keys (postgres + Paddle + LemonSqueezy; staging holds placeholder Paddle/LS creds per Phase 0 decision) |
| `services/edge-ingress/staging/tls` | 7 TLS PEMs (`staging_api_cert/key`, `staging_wildcard_cert/key`, plus 3 internal certs) |
| `services/edge-ingress/staging/cloudflare/tunnel` | `tunnel_token` |
| `services/edge-ingress/staging/cloudflare/aop_ca` | `aop_ca` (Cloudflare AOP CA bundle) |
| `services/edge-ingress/staging/maxmind` | `license_key`, `account_id` |
| `services/mt-node/staging` | `default_zmq_auth_token` (platform fallback for the hosted-MT ZMQ EA) |
| `tenants/mt-node/<sa>` | Per-tenant hosted-MT credentials — written by engine `HostedProvisioner` at user-broker-connect time; one path per tenant ServiceAccount. No paths exist until a user provisions a hosted MT account. |

**Workstation operator credential safety net**: `~/etradie-staging-creds.txt` (mode 0600) holds plaintext copies of the §8.2-generated secrets (DB_PASS, REDIS_PASS, JWT_SECRET, BROKER_KEY, CHROMA_TOKEN, ADMIN_PASS, ENGINE_SHARED, BILLING_SHARED, MT_DEFAULT_ZMQ) AND the Google OAuth client id + secret. This is the operator-side fallback in case Vault becomes unreachable. Vault is the runtime source of truth; this file is the bootstrap reference.

### Cookie + CORS topology (cross-subdomain auth)

The SPA at `app.exoper.com` (or any other host that 307s to it) calls the backend at `staging-api.exoper.com`. For cookies to flow across the subdomain boundary the gateway is configured with:

| Setting | Value | Source |
|---|---|---|
| `AUTH_COOKIE_DOMAIN` | `.exoper.com` (leading dot = registrable-domain scope) | `helm/gateway/values-staging.yaml::config.auth.cookieDomain` |
| `AUTH_COOKIE_SAMESITE` | `None` (required for cross-site cookie attachment) | same |
| `AUTH_COOKIE_SECURE` | `true` (browsers reject SameSite=None without Secure) | same |
| `AUTH_RETURN_TOKENS_IN_BODY` | `false` (cookie-only auth; JWTs are NOT echoed in the JSON response body — PROGRESS gotcha #46) | same |
| `GATEWAY_ALLOWED_ORIGINS` | `https://staging.exoper.com,https://app.exoper.com` (both SPA hosts that may reach the backend; pre-redirect + post-redirect origins) | same (commit `07457e51`) |
| CSRF header name | `X-CSRF-Token` | same; SPA sends the cookie's value back in this header on every mutating method |

Result: when the SPA at `app.exoper.com` POSTs `/auth/login` to `staging-api.exoper.com`, the gateway responds with 3 cookies (`access_token`, `refresh_token`, `__Secure-csrf_token`), all scoped to `Domain=.exoper.com; SameSite=None; Secure; HttpOnly` (the CSRF one is JS-readable to enable the double-submit pattern). Browsers attach them automatically to every subsequent request to `staging-api.exoper.com` AND `staging.exoper.com` AND `app.exoper.com` (anything under the registrable domain).

### Per-deploy parameters (current live state)

Mirrors `PROGRESS.md` per-deploy parameters table for quick lookup:

| Parameter | Value |
|---|---|
| Target environment | `staging` |
| VPS host | Contabo VPS 30 NVMe (Ubuntu 24.04) |
| K3s version | `v1.30.4+k3s1` |
| Backend public hostname | `staging-api.exoper.com` |
| Frontend public hostname (user-facing) | `staging.exoper.com` (307 alias) → `app.exoper.com` (where the SPA actually loads) |
| Vercel staging-vs-production model | Single Vercel project; multiple custom domains; one build with `VITE_API_URL=https://staging-api.exoper.com` while staging is the live posture |
| Admin user (logged-in surface) | `admin` / `admin@exoper.com` / role=`admin` |
| GHCR owner / image base | `FlameGreat-1` / `ghcr.io/flamegreat-1/etradie` |
| Linkerd mesh | ON for: postgres, redis, chromadb, edge-ingress, envoy. OFF (temporary, staging-only) for: engine, gateway, execution, management, billing per [`PHASE10.6-MESH-DISABLED-CHECKPOINT.md`](PHASE10.6-MESH-DISABLED-CHECKPOINT.md) |
| Linkerd mesh on cloudflared | NEVER (cloudflared dials Cloudflare edge over QUIC; mesh injection would break the QUIC handshake) |

### When a future operator picks this up

1. **Read `PROGRESS.md` from the bottom first** — the most recent operator entries are at the tail and reflect the current live state.
2. **Then this section** — gives you the URLs, accounts, and credential locations you need to verify state.
3. **Then [`PHASE10.6-MESH-DISABLED-CHECKPOINT.md`](PHASE10.6-MESH-DISABLED-CHECKPOINT.md)** — the one outstanding production-blocking debt before this staging deploy is fully promotable.
4. **For the workstation operator routine** (tunnel + KUBECONFIG + ArgoCD CLI login) re-read the `Daily operator routine` section near the top of this README.

---

## Reference

- Resource profile + capacity: `BUDGET.md` (Table 2B)
- Bootstrap-only steps: `infrastructure/cluster/bootstrap/README.md`
- Vault path schema: `infrastructure/cluster/vault-paths/main.tf`
- Mesh rollout: `docs/runbooks/linkerd-mesh-rollout.md`
- Host hardening: `docs/runbooks/vps-host-hardening.md`
- Backup/restore: `docs/runbooks/database-backup-restore.md`
- Older single-doc guide (image tags there are stale; THIS runbook is authoritative): `docs/deployment/contabo-k3s.md`
