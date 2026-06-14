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
| 1 | VPS host hardening | ✅ DONE |
| 2 | Install K3s | ✅ DONE |
| 2.5 | Build + push mt-node Wine image | 🟡 in progress |
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

## Phase 1 — VPS host hardening ✅

Executing README.md Phase 1 against the staging VPS. Sub-steps below
are flipped as each one passes its verification.

| Sub-step | Status | Notes |
|---|---|---|
| 1.1 Create non-root sudo user `etradie`, install SSH key | ✅ | Discovered `/root/.ssh/authorized_keys` was empty on the Contabo image (operator had been root-logging in via password). Installed the workstation's `~/.ssh/id_ed25519.pub` into BOTH `/root/.ssh/authorized_keys` and `/home/etradie/.ssh/authorized_keys` so the root escape hatch stays intact until 1.2 verification. Second-terminal `ssh etradie@HOST` succeeded key-only; `sudo whoami` returned `root`. |
| 1.2 Harden sshd via `/etc/ssh/sshd_config.d/10-etradie-hardening.conf` | ✅ | `sshd -T` confirms `passwordauthentication no`, `permitrootlogin no`, `pubkeyauthentication yes`, `kbdinteractiveauthentication no`. Second-terminal verification: password-auth attempt refused (no password prompt at all); `ssh root@HOST` refused; `ssh etradie@HOST` succeeded. |
| 1.3 OS packages + updates | ✅ | `apt -y upgrade` pulled 96 pending packages including a kernel update to `6.8.0-124-generic` (system flagged restart-required). `needrestart` deferred dbus / systemd-logind / unattended-upgrades restarts — cleared by the reboot scheduled after 1.5. All 10 packages (`ca-certificates curl gnupg git make jq unzip ufw chrony fail2ban`) Status: install ok installed. |
| 1.4 Time sync (chrony) | ✅ | `chronyc tracking`: Stratum 2, Leap status Normal, system time within 1ms of NTP. `chronyc sources -v` shows one `^*` selected source + multiple `^+` candidates, all with Reach 377. |
| 1.5 Kernel + ulimit tuning | ✅ | `/etc/sysctl.d/99-etradie.conf` and `/etc/security/limits.d/99-etradie.conf` written exactly per README.md. `sudo sysctl --system` applied the drop-in; runtime verify shows `vm.max_map_count=262144`, `fs.inotify.max_user_watches=524288`, `net.core.somaxconn=65535`, `vm.swappiness=10`. ulimit values via PAM apply only to NEW sessions and to processes not launched by systemd (K3s + Vault + workloads use systemd `LimitNOFILE=` and container runtime per-pod limits, independent of PAM). |
| Reboot to pick up kernel `6.8.0-124-generic` | ✅ | Box came back in ~60s. `uname -r` = `6.8.0-124-generic`, sshd hardening persists (`passwordauthentication no`, `permitrootlogin no`, `pubkeyauthentication yes`), all 4 sysctl values still applied, chrony re-synced (Stratum 3, Leap Normal), `/var/run/reboot-required` cleared. Key-only `ssh etradie@HOST` still works (validates the hardening + ufw inactive precondition for 1.6). |
| 1.6 Firewall — ufw default-deny inbound | ✅ | ufw active; default deny incoming / allow outgoing; only `22/tcp LIMIT IN` (v4+v6) rule. `ss -tlnp` shows sshd on `:22` plus two `systemd-resolved` stub listeners on `127.0.0.54:53` and `127.0.0.53%lo:53` (loopback only, not public-facing). External port probe from workstation against `13.140.164.173`: 22 OPEN; 80, 443, 6443, 8200, 5432 all closed/filtered. Fresh `ssh etradie@HOST` from a second terminal still succeeds. |
| 1.7 fail2ban sshd jail | ✅ | `/etc/fail2ban/jail.d/sshd.local` written per README.md. `systemctl is-active fail2ban` -> `active`; `is-enabled` -> `enabled`. `fail2ban-client status` shows 1 jail (`sshd`); `status sshd` reports `Currently failed: 1` (the deliberate `ssh root@HOST` rejection from 1.2 verification) and `Currently banned: 0` — well under `maxretry = 3`, so no IP is banned. Journal monitoring via systemd (`_SYSTEMD_UNIT=sshd.service`) rather than tailing `/var/log/auth.log` (Ubuntu 24.04 default). Benign `WARNING 'allowipv6' not defined` in journal — fail2ban defaulted to `auto`, IPv6 still covered. |
| 1.8 Verification checklist | ✅ | All 9 checks pass: sshd hardening intact, fail2ban sshd jail active (`Currently banned: 0`; the small `Currently failed` count reflects the 1.2 / 1.8 verification rejections), ufw default-deny with only `22/tcp LIMIT IN` (v4+v6), chrony Stratum 3 / Leap Normal, all 4 sysctl values applied, K3s `:6443` not yet listening (correct pre-Phase-2), `ss -tlnp` confirms NO public listener other than sshd, no reboot pending, `sudo -n whoami` -> `root`. Host is ready for Phase 2 (K3s install). |

### Phase 2 access decision: Option A (SSH local-forward)

The K3s API (`:6443`) stays firewalled inbound by ufw (Tier 11
requirement). `kubectl` from the workstation reaches the API by
running an SSH local-forward through the existing etradie session;
the workstation kubeconfig's `server:` URL is rewritten to
`https://127.0.0.1:6443`. No new ufw rule, no source-IP allowlist,
no public API binding. Exact commands belong to Phase 2.3 in
README.md.

### Post-Phase-1 access model and security measures (this deploy)

**Single way in:**  use  your personal `ssh ` from the workstation.
Key-only. No password prompt. Both `ssh root@HOST` and any
password-based attempt are refused by sshd; the Contabo VNC console
(in the customer panel, password-based) remains the only emergency
fallback.

**Operator must stick to these:**

1. **The workstation private key IS the credential.** `~/.ssh/id_ed25519`
   must stay mode `0600`. If the laptop is lost / disk imaged / key
   copied off-box, rotate immediately: generate a new key pair, replace
   `/home/etradie/.ssh/authorized_keys` (and `/root/.ssh/authorized_keys`)
   on the VPS via VNC console, restart sshd.
2. **Add a passphrase to the private key** (`ssh-keygen -p -f ~/.ssh/id_ed25519`)
   and load it into `ssh-agent` per workstation session. Defence in
   depth against an unencrypted disk image being stolen.
3. **etradie has passwordless sudo** (deployment automation needs it).
   That means SSH-key access = root. Do NOT share the key, do NOT add
   other public keys to `/home/etradie/.ssh/authorized_keys`, do NOT
   run unrelated workloads as etradie.
4. **fail2ban will lock the operator out** on 3 failed SSH attempts
   from one IP within 10 minutes. Initial ban 1h; escalates. Recovery:
   wait it out, or VNC in and `sudo fail2ban-client set sshd unbanip <IP>`.
5. **ufw is the only thing keeping K3s `:6443`, Vault `:8200`, Postgres
   `:5432`, and every other internal service off the public internet.**
   Never run `sudo ufw disable`. For temporary debug access to an
   internal port, allow by source IP only and remove the rule after:
   ```bash
   sudo ufw allow from <WORKSTATION_IP> to any port 5432 proto tcp comment 'temp debug'
   sudo ufw status numbered      # find rule number
   sudo ufw delete <number>      # remove after
   ```
6. **Do not `apt upgrade` casually mid-deploy.** Kernel + openssh
   upgrades can require reboots or sshd restarts; pick a maintenance
   window and check `/var/run/reboot-required` afterwards.
7. **No backups yet.** Phase 15 sets up Postgres B2 backups + Vault Raft
   snapshots. Until then, VPS loss = full data loss.
8. **Contabo root password (welcome email) is still valid** — only
   blocked from SSH by `PermitRootLogin no`, NOT blocked from the VNC
   console. Keep that email safe; the VNC password is your emergency
   recovery credential.

### Security-measure execution status (this deploy)

| Measure | Status | Notes |
|---|---|---|
| 1. Private key mode 0600 | ✅ | `ls -la ~/.ssh/id_ed25519` -> `-rw------- softverse softverse` on the workstation. |
| 2. Passphrase on private key + ssh-agent | ✅ | `ssh-keygen -p -f ~/.ssh/id_ed25519` succeeded; `ssh-keygen -y -f` re-derived the public key only after passphrase entry, confirming encryption. Unencrypted `.bak.*` copies created during the rekey were deleted (`shred`/`rm`). `ssh-agent` started in WSL (pid 446646), key loaded (`ssh-add -l` shows `SHA256:E9D76I53+6XjzKieAFTKSSWyFDhFxOSNc392nhsS04U`). Persistence snippet added to `~/.bashrc` + `~/.ssh/agent.env` (mode 0600) so new terminals reuse the same agent. End-to-end verified: `ssh etradie@13.140.164.173 'echo OK; hostname; whoami; uname -r'` returns `OK / vmi3362776 / etradie / 6.8.0-124-generic` with no passphrase prompt. Re-enter passphrase once per WSL boot (after `wsl --shutdown` or workstation reboot). |
| 3. etradie passwordless sudo, do not share key | 🟡 acknowledged | Standing operator constraint; no action item. |
| 4. fail2ban lockout awareness | 🟡 acknowledged | Recovery path: Contabo VNC + `fail2ban-client set sshd unbanip <IP>`. |
| 5. ufw is the only inbound filter | 🟡 acknowledged | Never `ufw disable`; temp rules by source IP only. |
| 6. No casual `apt upgrade` mid-deploy | 🟡 acknowledged | Next upgrade window: post-Phase-15. |
| 7. No backups yet | 🟡 acknowledged | Phase 15 sets up Postgres B2 + Vault Raft snapshots. |
| 8. Contabo root password still valid for VNC | 🟡 acknowledged | Welcome email retained as emergency recovery credential. |

---

## Phase 2 pre-flight: codebase verification (before running the K3s installer)

The README.md Phase 2.1 install command was cross-checked against the
repo before execution to make sure every flag it sets is one the
charts/Terraform/ArgoCD configs actually rely on, and that nothing the
codebase needs is missing from it. Recorded here so a future operator
can see WHY the command is what it is, not just that we ran it.

| README.md Phase 2.1 flag / setting | Why the code requires it | Source of truth in repo |
|---|---|---|
| `INSTALL_K3S_VERSION=v1.30.4+k3s1` | Linkerd uses native sidecars (`config.linkerd.io/proxy-enable-native-sidecar: "true"`), which is GA only from K8s 1.29. On older K8s the annotation is silently ignored, the proxy starts AFTER init containers, and meshed init-container hops (engine alembic migrate, mt-node Vault Agent init) are refused by the meshed datastores → pods never become Ready. | `infrastructure/cluster/bootstrap/README.md` step 0; `helm/data-layer/values.yaml` (postgres/redis/chromadb podAnnotations); `helm/mt-node/values.yaml` (vault + podAnnotations). |
| `--disable=traefik` | The platform ships its own `edge-ingress` chart (Cloudflare Tunnel + envoy). A second ingress controller would race for `:80`/`:443`. | `helm/edge-ingress/` chart. |
| `--disable=servicelb` | Cloudflare Tunnel is outbound-only — no LoadBalancer is ever needed. The data-layer namespace's ResourceQuota hard-caps `services.loadbalancers: 0`, so any LB attempt would be rejected at admission anyway. | `helm/data-layer/values.yaml::resourceQuota.hard.servicesLoadbalancers=0`; `helm/data-layer/templates/namespace.yaml`. |
| `--kube-apiserver-arg=enable-admission-plugins=NodeRestriction,PodSecurity` | The data-layer chart owns the `etradie-system` namespace and labels it `pod-security.kubernetes.io/warn=restricted` + `audit=restricted` (PSS observe-only mode). The PodSecurity admission plugin must be enabled at the apiserver for those labels to take effect. NodeRestriction limits the kubelet to mutating only its own Node + Pods (CIS K8s Benchmark 1.2.x). | `helm/data-layer/templates/namespace.yaml`. |
| `--kubelet-arg=eviction-hard=memory.available<200Mi` | Single-node 24 GB box (BUDGET.md Table 2B). The default eviction threshold of 100Mi is too tight — a Wine + MT5 recalc spike or a postgres autovacuum can push the node past it and kubelet starts killing healthy pods. 200Mi is the safe floor for this profile. | `BUDGET.md` Table 2B; `helm/mt-node/values.yaml` resource ceilings. |
| `K3S_KUBECONFIG_MODE=644` | Phase 2.3 copies `/etc/rancher/k3s/k3s.yaml` from the VPS to the workstation. Default mode 600 (owned by root) would force every copy to go through sudo and a chown. 644 is safe because the file stays on the VPS root filesystem behind ufw — the operator's etradie account is already root-equivalent via passwordless sudo (Phase 1 measure 3). | README.md Phase 2.3 (Option A SSH local-forward). |
| StorageClass: no `--default-local-storage-class=...` override | K3s ships `local-path-provisioner` as the cluster default StorageClass. The data-layer + mt-node charts BOTH set `storageClassName: ""` (= use cluster default) in every PVC, so the K3s default resolves correctly without further configuration. | `helm/data-layer/values.yaml::postgres.storage.storageClassName=""`, same for redis/chromadb/backup; `helm/mt-node/values.yaml::persistence.storageClass=""`. |

### Two staging-specific consequences operators must keep in mind

1. **PSS is `warn` + `audit` only, NOT `enforce`.** The namespace template
   (`helm/data-layer/templates/namespace.yaml`) deliberately omits
   `pod-security.kubernetes.io/enforce` (its comment: *"The enforce
   cutover is a deliberate, reviewed follow-up MR after one full deploy
   cycle of audit-log events shows no violations."*). Phase 2.1's
   apiserver flag turns the PodSecurity ADMISSION PLUGIN on at the
   cluster, but the namespace itself is in observe-only mode. Phase 14
   verification should grep `kube-apiserver` audit events for
   `pod-security` violations before any future enforce cutover. Do NOT
   add the enforce label inline during this deploy.
2. **PSS rule version is pinned to `v1.30`.** The namespace labels
   `pod-security.kubernetes.io/warn-version: v1.30` (and same for
   `audit-version`). K3s `v1.30.4+k3s1` matches. **If a future operator
   upgrades K3s, they MUST bump this pin in lockstep** — otherwise PSS
   will silently re-evaluate against a different rule version and the
   warn/audit results will change without anyone touching the chart.
3. **Snapshotter is OFF in staging** (`helm/mt-node/values-staging.yaml::snapshotter.enabled=false`).
   K3s `local-path-provisioner` has no CSI VolumeSnapshot support, so
   the Wine-prefix snapshot CronJob cannot run on this box. Re-enable
   only after installing Longhorn (or another snapshot-capable CSI) and
   setting `snapshotter.volumeSnapshotClassName` + `image.repository`.
   No action required at Phase 2 — just don't be surprised when
   `mt-node-staging` renders without the CronJob in Phase 12.

---

## Phase 2 — Install K3s

| Sub-step | Status | Notes |
|---|---|---|
| 2.1 Install K3s `v1.30.4+k3s1` on the VPS | ✅ | Ran the exact README.md Phase 2.1 installer block as etradie. Installer output: downloaded the v1.30.4+k3s1 binary + verified its hash, installed to `/usr/local/bin/k3s`, created `kubectl` / `crictl` / `ctr` symlinks, wrote `/etc/systemd/system/k3s.service`, enabled the unit (`Created symlink /etc/systemd/system/multi-user.target.wants/k3s.service → /etc/systemd/system/k3s.service`), and ended on `[INFO]  systemd: Starting k3s`. No errors. SELinux RPM skipped (correct on Ubuntu 24.04). |
| 2.2 Verify cluster healthy | ✅ | At T+11s: `kubectl get nodes` -> `vmi3362776 Ready control-plane,master 11s v1.30.4+k3s1`. `get pods -A` showed `No resources found` (kubelet still bringing up kube-system). At T+~2 min: all 3 kube-system pods Running 1/1 — `coredns-576bfc4dc7-4wzkw`, `local-path-provisioner-6795b5f9d8-49pqs`, `metrics-server-557ff575fb-xbcrz`. No `helm-install-traefik` Jobs ever appeared because `--disable=traefik` + `--disable=servicelb` skipped them at install time. `get nodes -o wide` confirms INTERNAL-IP `13.140.164.173`, OS-IMAGE `Ubuntu 24.04.4 LTS`, KERNEL-VERSION `6.8.0-124-generic` (the kernel from Phase 1 reboot), CONTAINER-RUNTIME `containerd://1.7.20-k3s1`. `systemctl is-active k3s` -> `active`; `is-enabled k3s` -> `enabled`. |
| 2.2 — K3s ports listening | ✅ | `ss -tlnp` shows `*:6443` (kube-apiserver), `*:10250` (kubelet) bound to all interfaces — ufw STILL blocks them externally (Phase 1.6 verified `:6443` closed/filtered from the workstation's port probe). `127.0.0.1:10256` (kube-proxy healthz) bound loopback-only — K3s default, no operator action. All three are owned by `k3s-server` (pid 2618). |
| 2.2 — StorageClass present and default | ✅ | `kubectl get storageclass` -> `local-path (default) rancher.io/local-path Delete WaitForFirstConsumer false 8s`. The `(default)` marker is the load-bearing piece: every chart in this repo sets `storageClassName: ""` (= cluster default) in its PVCs, so K3s' `local-path` will be picked up automatically in Phase 12 without any chart override. `WaitForFirstConsumer` means PVCs stay `Pending` until a pod actually mounts them — expected K3s behaviour, not a fault. |
| 2.3 Export kubeconfig to workstation via SSH local-forward (Option A) | ✅ | Kubeconfig on the VPS at `/etc/rancher/k3s/k3s.yaml`, mode `-rw-r--r--` (644 from `K3S_KUBECONFIG_MODE=644`), `server: https://127.0.0.1:6443` (loopback URL kept as-is so the workstation tunnel terminates onto the same address). Copied to workstation via `scp etradie@13.140.164.173:/etc/rancher/k3s/k3s.yaml ~/.kube/etradie-contabo.yaml` (~2957 bytes, no passphrase prompt because the WSL ssh-agent had the key cached); workstation file permissions tightened to `-rw------- softverse softverse 2957` (mode 0600 — owner-only; the file embeds a client cert + private key with cluster-admin rights, same posture as the SSH private key). Tunnel opened with `ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173` in a dedicated workstation terminal (pid 452297). End-to-end verified: `kubectl get nodes` through the tunnel returned `vmi3362776 Ready control-plane,master 15m v1.30.4+k3s1`; `Server Version: v1.30.4+k3s1` matches the installed K3s. Tunnel bound LOOPBACK-ONLY on the workstation (`127.0.0.1:6443` v4 + `[::1]:6443` v6, owned by the ssh process — NOT `0.0.0.0:6443`, so the workstation cannot be pivoted via LAN). PUBLIC-side verification: `timeout 5 bash -c '</dev/tcp/13.140.164.173/6443'` -> `PUBLIC 6443 filtered -- good` (ufw still blocks the K3s API on the public IP; the encrypted SSH tunnel is the only path in). `KUBECONFIG=~/.kube/etradie-contabo.yaml` appended to `~/.bashrc` (verified post-hoc — first `grep KUBECONFIG ~/.bashrc` returned empty in a fresh terminal, so an explicit `echo 'export KUBECONFIG=~/.kube/etradie-contabo.yaml' >> ~/.bashrc` was required; subsequent grep confirms the line is now persisted) so every new workstation terminal auto-targets the cluster (and `kubectl` hangs gracefully if the tunnel terminal is closed — the canary that says "reopen the tunnel"). |

### Phase 2 operator gotchas (record so the next operator doesn't trip on them)

**1. `ssh-add` is required once per WSL boot.** The `~/.bashrc` agent
persistence snippet (added at Phase 1 measure 2) correctly reuses the
existing `ssh-agent` across new terminals WITHIN one WSL session.
However, when WSL is fully shut down (`wsl --shutdown` on Windows,
workstation reboot, or the last WSL window closing), every process
inside WSL dies including `ssh-agent`. On the next WSL boot, the
snippet detects the dead agent and spawns a fresh one — but the new
agent has no key loaded yet, so the first `ssh` or `scp` command that
run WILL prompt for the passphrase. The fix is one-time per WSL boot:
```bash
ssh-add ~/.ssh/id_ed25519     # type passphrase once
ssh-add -l                    # confirm key loaded
```
After that, all SSH (including the `ssh -L` tunnel) is passphrase-free
for the rest of the WSL session. This is normal behaviour, not a bug;
agents store decrypted keys in memory only.

**2. The tunnel terminal is load-bearing.** `ssh -N -L 6443:127.0.0.1:6443
etradie@13.140.164.173` is a FOREGROUND process. Closing the terminal
(Ctrl+C, `exit`, or closing the window) tears the tunnel down
immediately. `kubectl` calls after that point will hang for ~30s and
fail with `dial tcp 127.0.0.1:6443: connect: connection refused`. That
hang is the canary that says "reopen the tunnel". For longer-running
work an operator may install `autossh` (`sudo apt install autossh`)
and use `autossh -M 0 -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173 &`
for a self-healing tunnel that reconnects automatically over network
blips. Not done in this deploy; the dedicated-terminal pattern was
sufficient for Phase 2.3.

**3. No public 6443 binding.** The ufw rule from Phase 1.6 (default
deny incoming, only 22/tcp LIMIT) is what keeps the K3s API off the
public internet — NOT any K3s configuration. The kube-apiserver listens
on `*:6443` inside the VPS (all interfaces), and only ufw stops public
reachability. If an operator ever runs `sudo ufw disable` for any
reason, the K3s API becomes publicly reachable in seconds. Never
disable ufw; for temporary debug access use a source-IP-restricted
rule (Phase 1 security measure 5).

---

## Phase 2.5 — Build + push mt-node Wine image (in progress)

### Pre-flight values collected (this deploy)

| Value | Source | Value |
|---|---|---|
| `WINEHQ_VERSION` | `apt-cache policy winehq-stable` in fresh ubuntu:24.04 + WineHQ apt source | `11.0.0.0~noble-1` |
| `MT5_INSTALLER_SHA256` | `sha256sum` of the official MT5 installer | `d437fd760587d24e094864215b86a441cc64ab897cace2b2a21a46614b3f4e36` |
| `MT4_INSTALLER_SHA256` | `sha256sum` of the official MT4 installer | `944720016fae95eba6b5f6035415ddcaac75be91a23bfeb7712e0b4cebbb0622` |
| `EA_EX5_SHA256` | `make mt-node-ea-sha` against committed `.ex5` | `e5dd977af6072077bf2db9a8cf5422ec4df77659aa931f28c998fc4f63cc8ed7` |
| `EA_EX4_SHA256` | `make mt-node-ea-sha` against committed `.ex4` | `6e617cc5e7aa3e9dbd70a66935207dee8132e20992814dd6df79ff2cab9d2129` |
| `MT_NODE_TAG` | `helm/mt-node/values-image.yaml::image.tag` | `0.1.0` |
| Image push target | `helm/mt-node/values-image.yaml::image.repository` + tag | `ghcr.io/flamegreat-1/etradie-mt-node:0.1.0` |

### CI secrets set

`WINEHQ_VERSION=11.0.0.0~noble-1` added as a GitHub Actions repo secret
so the `.github/workflows/ci.yml` production-build guard for mt-node
no longer fails on push to main. The four SHA secrets remain unset for
now (CI defaults each to `"skip"`); add them as repo secrets after the
workstation build to also enforce supply-chain pinning in CI.

### Build + push

- **First attempt** failed at the tini SHA-verification step because
  the Dockerfile downloaded the binary to `/usr/bin/tini` but verified
  it via `sha256sum -c` from `/tmp`, where the file it referenced did
  not exist. **Fixed on `main`** — stage the download at
  `/tmp/tini-${arch}` (matches the .sha256sum file), verify, then
  `install -m 0755` to `/usr/bin/tini`. SHA enforcement preserved.
- **Second attempt** (post-fix) ... pending re-run.
