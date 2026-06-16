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
| 2.5 | Build + push mt-node Wine image | ✅ DONE |
| 3 | Vault + Vault Agent Injector | ✅ DONE |
| 4 | External Secrets Operator + ClusterSecretStore | ✅ DONE |
| 5 | Stakater Reloader | ✅ DONE |
| 6 | Cloudflare Tunnel | ✅ DONE |
| 7 | Generate Linkerd mesh CA | ✅ DONE |
| 8 | Bootstrap Vault paths + populate every secret | ✅ DONE |
| 9 | Build + inject envoy WASM filter | ✅ DONE |
| 10 | ArgoCD + AppProjects + root app | 🟡 in progress (control plane HEALTHY; staging children OutOfSync/Missing — diagnosis TBC) |
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

### Build + push attempts

| Attempt | Outcome | Failed step | Root cause + fix |
|---|---|---|---|
| 1 | ❌ | 3/16 (tini) | Dockerfile downloaded tini directly to `/usr/bin/tini` but verified via `sha256sum -c tini.sha256` from `/tmp`. The .sha256sum file references `tini-${arch}` by name, so `sha256sum -c` looked for `/tmp/tini-amd64` which did not exist (`FAILED open or read`). Fixed on `main`: stage the download at `/tmp/tini-${arch}`, verify, then `install -m 0755` into `/usr/bin/tini`. SHA enforcement preserved. Step 2/16 (apt + Wine `11.0.0.0~noble-1` install, ~993s) completed successfully before the failure, proving the `WINEHQ_VERSION` pin works. |
| 2 | ❌ | 4/16 (non-root user creation) | Ubuntu 24.04 base ships a default `ubuntu` user/group at UID/GID 1000. `groupadd --gid 1000 mt` then fails with `GID '1000' already exists` (exit code 4). UID/GID 1000 contract is load-bearing: `helm/mt-node/values.yaml::podSecurityContext.runAsUser=1000` pins it. Fixed on `main`: `userdel -r ubuntu \|\| true` and `groupdel ubuntu \|\| true` BEFORE `groupadd --gid 1000 mt`. Idempotent for future base images that drop the default account. |
| 3 | ✅ | — | Build completed end-to-end in 723.8s (~12 min). Image built as `sha256:4354861ed0627451e9295c3f75b7a6f11a0268dfb092ef08204b5a7779cfaf10`, tagged `ghcr.io/flamegreat-1/etradie-mt-node:0.1.0`. Push to GHCR started with default parallel-upload behaviour; three large layers (`32953adcee64` 1.486 GB, `4da240735395` 1.484 GB, `32b5d27e3da8` 2.756 GB) saturated the workstation upload bandwidth and the parallel push appeared to stall for >15 minutes with no `ss` connections active to GHCR. Switched to `max-concurrent-uploads: 1` in `~/.docker/config.json` and re-ran `docker push`; serial upload completed cleanly. **Final state:** manifest digest `sha256:92225a1f561b77b5fdbcd3c85ff6e4808af8911815a198baddeef07d73b5e26d`, manifest size 3676 bytes. Phase 0.4-style pull verification: `curl ... https://ghcr.io/v2/flamegreat-1/etradie-mt-node/manifests/0.1.0` returns `200`. Image is now consumable by `helm/mt-node` at the path pinned in `helm/mt-node/values-image.yaml`. |

### Operator gotcha recorded for the next deploy

**Default `docker push` parallelism saturates home upload bandwidth on multi-GB images.** With three concurrent layer uploads each carrying 1.5–2.8 GB, the workstation's upstream is divided three ways and individual layer progress appears stalled even when the connection is alive. After ~15 minutes of apparent stall, `ss -tn | grep -E ':443.*ESTAB'` showed NO active TCP connections to GHCR — the parallel push had silently died (likely NAT-side connection-track timeout on the long-running upload). Solution: set `"max-concurrent-uploads": 1` in `~/.docker/config.json` (one layer at a time, each getting full upload bandwidth) and re-run `docker push <tag>`. Docker queries GHCR for layer existence first, so already-pushed layers show `Layer already exists` and only the truly unfinished ones re-upload. No `make build-mt-node` rebuild required — just `docker push <tag>` directly. Future deploys with large images (mt-node, future Linkerd-viz / Prometheus stacks) should pre-emptively set this config before the first push.

---

## Phase 3 — Vault + Vault Agent Injector ✅

Executed against the staging cluster (single-node K3s on the Contabo
VPS) via `kubectl` through the Phase 2.3 SSH local-forward. Every
command ran on the workstation; the SSH tunnel terminal stayed
untouched the whole phase. The CI failure surfaced just before this
phase (`Production build guard - mt-node`) was resolved by setting
the `ETRADIE_ALLOW_PUBLIC_INSTALLER_CDN=true` GitHub Actions repo
secret as a staging-only opt-in; a Cloudflare R2 mirror is deferred
until pre-production cutover.

| Sub-step | Status | Notes |
|---|---|---|
| 3.1 Install Vault chart 0.28.1 (standalone, dataStorage 10Gi `local-path`, injector + ui on) | ✅ | `helm install` succeeded first try. Pods scheduled within ~30s: `vault-0` Running **0/1** (sealed, readiness gates on `Sealed=false`), `vault-agent-injector-7bcc447788-xv7p4` Running **1/1**. PVC `data-vault-0` Bound 10Gi RWO `local-path`. Took the 0/1 on `vault-0` as the expected pre-unseal state and moved to 3.2 immediately. |
| 3.2 Init + unseal | ✅ (after README hardening) | **Hit twice in succession**: (a) original README used `kubectl exec -ti vault-0 -- vault operator init > vault-init.txt` — captured CRLF line endings (`^M$` in `cat -A`); (b) even after `tr -d '\r'` cleanup, every key/line was framed by ANSI color escapes (`^[[0m...^[[0m`) that Vault writes when stdout is a TTY. Both `awk '{print $4}'` and `awk '{print $NF}'` then extracted strings containing embedded escape bytes; `vault operator unseal` returned `400 Bad Request: 'key' must be a valid hex or base64 string` three times in a row, once per attempted unseal. Diagnosed via `sed -n '1p' ~/vault-init.txt \| cat -A`. Fix: replaced the init line with a piped capture `kubectl -n vault exec -i vault-0 -- vault operator init ... \| tr -d '\r' \| sed 's/\\x1b\\[[0-9;]*m//g' > vault-init.txt` (drop `-t`, strip CR + ANSI codes at capture time). Unseal loop similarly switched from `exec -ti` to `exec -i` and from `awk '{print $4}'` to `awk -v n="$i" '$0 ~ "Unseal Key " n ":" {print $NF}'`. After fix: 3 unseals reported progress `1/3 -> 2/3 -> 0/3 + Sealed false`, `vault status` showed `Initialized true / Sealed false / Total Shares 5 / Threshold 3`, `vault-0` flipped to Running **1/1**. README §3.2 patched in lockstep so a future operator never re-encounters this. |
| 3.3 Verify injector | ✅ | Already covered by 3.1's `get pods`: `vault-agent-injector-7bcc447788-xv7p4` Running 1/1 throughout. |
| 3.4 Auth + KV mount + ESO policy + role | ✅ (in-pod pattern, README hardened) | Original README used `kubectl -n vault port-forward svc/vault 8200:8200 &` + workstation `vault` CLI. The workstation has no `vault` CLI (it was masked in Phase 0.1 step 2). Switched to the in-pod pattern: `kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault ...`. All five `Success!` confirmations returned cleanly: `Enabled the kv secrets engine at: secret/`, `Enabled kubernetes auth method at: kubernetes/`, `Data written to: auth/kubernetes/config`, `Uploaded policy: etradie-eso`, `Data written to: auth/kubernetes/role/etradie-eso`. Policy write used heredoc-to-`/tmp/eso.hcl` inside the pod (the original `vault policy write etradie-eso - <<EOF` is brittle through stdin-piping). Verification: `vault secrets list` shows `secret/ kv`, `vault auth list` shows `kubernetes/`, `vault policy read etradie-eso` returns the two path stanzas verbatim, `vault read auth/kubernetes/role/etradie-eso` confirms `bound_service_account_names=[external-secrets]`, `bound_service_account_namespaces=[external-secrets]`, `policies=[etradie-eso]`, `token_ttl=1h`. README §3.4 patched: replaced the port-forward block with the in-pod pattern (the alternate path is mentioned but discouraged). |
| 3.5 Token-review SA `vault-auth` + ClusterRoleBinding `vault-auth-delegator` | ✅ | Both objects created cleanly (`serviceaccount/vault-auth created`, `clusterrolebinding.rbac.authorization.k8s.io/vault-auth-delegator created`). The `\|\| true` on each line is precautionary; the Vault chart did NOT pre-create the SA on this deploy (the chart auto-creates it only when `injector.enabled=true` AND no `vault-auth` exists; chart version 0.28.1 may have changed this contract). Phase 11 Terraform's `-var k8s_reviewer_jwt=$(kubectl create token -n vault vault-auth)` will now succeed. |

### Phase 3 open security debt for this deploy

During the 3.2 ANSI-corruption diagnostic, the following Vault secrets
were copied into the assistant chat session:

- **Unseal Key 1** (one of five Shamir shares; threshold 3 of 5)
- **Initial Root Token** (Vault 1.17 root token, 28 chars)

For STAGING this is accepted: no real user data is in Vault yet, no
production credentials are stored, the platform charts are not yet
wired to this Vault, and the threshold of 3 of 5 means a single leaked
share is not sufficient to unseal. The remaining four Unseal Keys are
uncompromised.

**Rotation MUST run before any production cutover** (and before any
production-grade secret is written to Vault). Procedure (record exact
commands in a pre-production runbook entry):

  1. `vault operator generate-root -init` then complete the OTP flow
     to mint a fresh root token (HashiCorp docs:
     https://developer.hashicorp.com/vault/docs/commands/operator/generate-root).
  2. `vault operator rekey -init -key-shares=5 -key-threshold=3` to
     re-Shamir-split with new shares, invalidating the disclosed
     Unseal Key 1.
  3. `vault token revoke <old-root-token>` to revoke the exposed root.
  4. Replace `~/vault-init.txt` with the new bundle, `chmod 600`, move
     offline.

Tracked here so a future operator picking up this PROGRESS.md sees the
debt before treating staging-Vault credentials as production-grade.

### Phase 3 operator gotchas recorded for the next deploy

**1. `kubectl exec -ti` corrupts captured Vault output.** Any command
that writes Vault state to stdout (notably `vault operator init`)
emits ANSI color codes when stdout is a TTY. Capturing those bytes
into a file produces strings that `vault operator unseal` rejects
with `400 'key' must be a valid hex or base64 string`. Diagnosis is
non-obvious from the error alone; the only visible clue is `cat -A`
on the saved file showing `^[[0m...^[[0m^M$` framing around each
key/token. The README §3.2 fix is to drop `-t` and pipe the stream
through `tr -d '\r' | sed 's/\\x1b\\[[0-9;]*m//g'` at capture time.
Apply the same `-i`-only pattern to any future `exec` that captures
Vault output to a variable or file.

**2. No `vault` CLI on the workstation; in-pod execution is
preferred.** Phase 0.1 step 2 explicitly disabled and masked the
workstation's `vault.service` systemd unit. The apt `vault` package
ships server+CLI together; the systemd unit was binding 8200 on the
workstation and competing with the platform port-forward. The
cleanest workaround is to drop the README's `port-forward + local
vault` step entirely and use `kubectl -n vault exec -i vault-0 --
env VAULT_TOKEN=... vault ...` throughout. The in-pod binary is by
definition compatible with the server and the forward is no longer
needed.

**3. `awk '{print $4}'` is brittle.** The original README used it to
extract Unseal Keys and the root token. `awk -v n="$i" '$0 ~ "Unseal
Key " n ":" {print $NF}'` is robust to trailing whitespace, robust to
the line containing fewer than four fields, and explicit about which
line it matches. README §3.2 has been switched to `$NF` for every
key/token extraction. Also note: Vault 1.17 root tokens are `hvs.` +
24 chars = **28 chars total** (not the ~95-char shape used by older
Vault releases). The README's verification line `${#ROOT_TOKEN} chars`
should print exactly `28`; a different number means the extraction
picked up bytes adjacent to the token.

---

## Phase 4 — External Secrets Operator + ClusterSecretStore ✅

Executed the README block verbatim. No deviation, no gotcha.

| Sub-step | Status | Notes |
|---|---|---|
| 4.1 Install ESO chart 0.10.4 with `installCRDs=true` | ✅ | All three deployments scheduled within ~80s and Available: `external-secrets-747cb48d85-z2gnj` (controller), `external-secrets-cert-controller-694f9c5b84-hd7rc`, `external-secrets-webhook-7cc8d8ddb4-fj4pl`. All Running 1/1. `kubectl -n external-secrets wait --for=condition=Available` reported `deployment.apps/external-secrets condition met`. The 6 CRDs the platform consumes are present: `clusterexternalsecrets`, `clustersecretstores`, `externalsecrets`, `pushsecrets`, `secretstores`, `vaultdynamicsecrets`. Chart 0.10.4 also installs the `generators.external-secrets.io` family (`acraccesstokens`, `ecrauthorizationtokens`, `fakes`, `gcraccesstokens`, `githubaccesstokens`, `passwords`, `uuids`, `webhooks`) which the platform does not currently use — harmless. |
| 4.2 Apply `ClusterSecretStore vault-backend` | ✅ | Applied via heredoc per README. `kubectl get clustersecretstore vault-backend` returned `STATUS: Valid / CAPABILITIES: ReadWrite / READY: True` on first reconciliation (< 1s). Status conditions: `reason=Valid`, `message=store validated`. This is the load-bearing confirmation that ESO can (a) reach `http://vault.vault.svc.cluster.local:8200` via in-cluster DNS, (b) authenticate as `external-secrets/external-secrets` SA against the `etradie-eso` Vault Kubernetes auth role from Phase 3.4, and (c) read+write on the `secret/` KV-v2 mount. Every chart's `ExternalSecret` in Phases 12+ references `secretStoreRef: { name: vault-backend, kind: ClusterSecretStore }` and will resolve through this object. |

No Phase 4 operator gotchas. The README block is correct as-shipped
(post Phase 3 fixes; Phase 3.4 had to be in-pod for Phase 4.2 to
resolve, and that is now the canonical path).

---

## Phase 5 — Stakater Reloader ✅

Executed the README block verbatim. No deviation, no gotcha.

| Sub-step | Status | Notes |
|---|---|---|
| 5.1 Install Reloader chart | ✅ | `helm repo add stakater + helm install reloader stakater/reloader -n reloader --create-namespace` succeeded first try. `kubectl -n reloader rollout status deployment/reloader-reloader --timeout=120s` returned `successfully rolled out` in ~24s. Single pod `reloader-reloader-c7d8d988-hpj92` Running 1/1, deployment `reloader-reloader   1/1   1   1`. Reloader will watch every Secret carrying `secret.reloader.stakater.com/reload: <secret-name>` (notably the mt-node platform Secret that holds `DEFAULT_ZMQ_AUTH_TOKEN`) and roll the dependent workloads on rotation. |

No Phase 5 operator gotchas. The README block is correct as-shipped.

---

## Phase 6 — Cloudflare Tunnel ✅

Pure Cloudflare control-plane work — no `kubectl`, no VPS access. The
Cloudflare dashboard's classic **Public Hostname** tab for cloudflared
tunnels has been removed from this account (and from accounts on the
new "Networks" Cloudflare One UI generally); the surviving in-UI
"Hostname routes" tab only offers the **private** hostname flow, which
requires the Cloudflare One Client on every end user's device — wrong
for our public-facing `staging-api.exoper.com`. We therefore drove the
tunnel ingress and DNS through the Cloudflare REST API. End state is
identical to what the old UI would have produced; the only difference
is the transport.

### Deploy-specific values captured (NOT secrets — recorded so Phase 8.5 / 11 do not have to rediscover them)

| Value | Source | Value |
|---|---|---|
| Cloudflare Account ID | dashboard URL `/<account-id>/...` | `38431fae78ce23adc3b933633a9abdd0` |
| Cloudflare Zone ID for `exoper.com` | `GET /zones?name=exoper.com` | `0642ff7fa8153bf7dc31b8db692dc79a` |
| Tunnel name | Cloudflare dashboard | `etradie-staging` |
| Tunnel UUID | dashboard URL of the tunnel detail page | `6d46295b-488e-49d6-9b7e-b699b310a1ec` |
| Public hostname | wired into the tunnel ingress | `staging-api.exoper.com` |
| Origin service URL | tunnel ingress (in-cluster DNS) | `https://edge-ingress.edge-ingress-system.svc.cluster.local:443` |
| Tunnel ingress `noTLSVerify` | API PUT body | `false` (mTLS-style verify on; AOP CA bytes go into Vault in Phase 8.5 to make it succeed at runtime) |
| Auto-created DNS record id | `GET /zones/.../dns_records?name=staging-api.exoper.com` | `d318ada0ea8eda04ccc9053cccf61951` |
| Configurations version | PUT response | `2` (Cloudflare increments per write; `1` was created server-side at tunnel-create time) |
| Tunnel token file (workstation, 0600) | written in 6.1 | `~/cloudflare-staging-tunnel-token.txt` (185 bytes, starts `eyJh`) |

### Sub-step status

| Sub-step | Status | Notes |
|---|---|---|
| 6.1 Create tunnel `etradie-staging` (Cloudflared type, copy single-use token) | ✅ | Created in the new "Networks → Tunnels" UI; token (`eyJ...`, 185 bytes) captured directly off the install screen via `cat > ~/cloudflare-staging-tunnel-token.txt` then `chmod 600`. Verification: `head -c 4` returned `eyJh` (correct JWT-ish base64 prefix), `wc -c` returned `185` (within the expected 180–230 byte range for a cloudflared remote-managed token), `tail -c 2 \| od -c` returned `9 \n` (exactly one trailing newline, no stray bytes). The install command itself was deliberately NOT run on the workstation — `cloudflared` will run as a Deployment inside the cluster, shipped by the `edge-ingress` Helm chart in Phase 12, and the token gets written into Vault at `secret/etradie/services/edge-ingress/staging/cloudflare/tunnel` in Phase 8.5. Tunnel status displayed as **Inactive** in the dashboard for the entire phase — correct: no connector has registered yet because the in-cluster cloudflared does not yet exist. |
| 6.2 Add public hostname `staging-api.exoper.com -> https://edge-ingress.edge-ingress-system.svc.cluster.local:443` | ✅ (via API — UI path no longer available) | The dashboard wizard's step 4/4 ("Route tunnel") landed on a screen that only offered private-hostname routes (the form's helper text explicitly required Cloudflare One Client on end-user devices). Direct legacy URLs `/<account-id>/access/tunnels/<uuid>` and `/<account-id>/networks/tunnels/cfd_tunnel/<uuid>/edit` both returned `We could not find that page.` — the classic Public Hostname tab is fully gone from this account. Drove the configuration via REST API instead: minted a scoped token (Cloudflare Tunnel:Edit + Account Settings:Read + DNS:Edit, account-scoped + zone-scoped to `exoper.com`, 48h TTL); `PUT /accounts/.../cfd_tunnel/<uuid>/configurations` with an `ingress` array containing one rule for `staging-api.exoper.com -> https://edge-ingress.edge-ingress-system.svc.cluster.local:443` (`noTLSVerify: false`, `http2Origin: false`, conservative keepalive/timeout values) plus the mandatory `http_status:404` catch-all terminator. API returned `success: true`, `version: 2`. Cloudflare's configurations endpoint AUTO-CREATES the matching CNAME on first PUT (new behaviour in the Networks UI; the explicit `POST /zones/.../dns_records` for the same name failed with the expected `81053 record already exists`). Read-back via `GET /zones/.../dns_records?name=staging-api.exoper.com&type=CNAME` confirmed `content: 6d46295b-488e-49d6-9b7e-b699b310a1ec.cfargotunnel.com` (UUID matches tunnel UUID exactly), `proxied: true`, `ttl: 1` (auto). Public DNS verified via `getent hosts staging-api.exoper.com` returning two Cloudflare anycast IPv6 addresses (`2606:4700:3032::ac43:b39c` + `2606:4700:3037::6815:1fc2`, both in Cloudflare's `2606:4700::/32` block) — proves the CNAME exists, propagated, and the proxy is intercepting (returning Cloudflare's edge IPs rather than the `*.cfargotunnel.com` target). API token shredded post-write (`shred -u ~/.cloudflare-staging-api-token.txt`); server-side TTL expires 2026-06-15 23:59:59Z regardless. |
| 6.3 Record the Tunnel UUID | ✅ | UUID `6d46295b-488e-49d6-9b7e-b699b310a1ec`, read directly from the dashboard URL on the tunnel detail page (`/<account-id>/networks/tunnels/cfd_tunnel/<UUID>`). Captured into the deploy-specific values table above. |

### Expected end state through to Phase 12

The tunnel will remain `Inactive` in the Cloudflare dashboard, with zero
connectors registered and `Uptime: --`, until Phase 12 syncs the
`edge-ingress-staging` ArgoCD app and the in-cluster `cloudflared`
Deployment comes online. A request to `https://staging-api.exoper.com`
at this point will return Cloudflare's Argo Tunnel error page (HTTP
530 or HTML error 1033). That is the correct intermediate state, not a
fault — every component is wired, only the connector is missing.

### Phase 6 operator gotchas recorded for the next deploy

**1. The classic "Public Hostname" tab is gone for new Cloudflare One
accounts.** The README's Phase 6.2 was written against the old Zero
Trust UI that exposed `Networks → Tunnels → <tunnel> → Public Hostname`
as a dedicated tab. That tab no longer exists in accounts on the
"Networks" UI; the surviving "Hostname routes" tab is for private
hostnames only (requires Cloudflare One Client end-user enrollment).
Do not use it — it will misconfigure the tunnel for our public-facing
use case. Drive cloudflared tunnel ingress via the REST API instead
(`PUT /accounts/<account-id>/cfd_tunnel/<tunnel-id>/configurations`).
The configurations endpoint also auto-creates the matching CNAME in
the target zone on first write, so a separate
`POST /zones/<zone-id>/dns_records` call is no longer required (and
will fail with the harmless `81053 record already exists`).

**2. The mandatory `http_status:404` catch-all terminator.** Cloudflare
rejects the configurations PUT with `1003 invalid ingress: no
catch-all rule` if the `ingress` array does not END with a rule that
has no `hostname` field and a `service` value of `http_status:<code>`,
`http_status:404` being the conventional one. Easy to miss when
templating the JSON body; if Phase 6.2's PUT returns 400 with that
error, append the terminator and retry.

**3. `noTLSVerify: false` is load-bearing.** Setting it to `true`
appears to "just work" in early testing because Cloudflare establishes
TLS to the in-cluster `edge-ingress` Service either way. But the
Phase 8.5 Authenticated Origin Pull CA bytes (`aop_ca`) only get
enforced when `noTLSVerify: false`, and Tier 11 requires that
enforcement to keep the tunnel from being trivially impersonated by
anything that gains a foothold on the host network. Always `false`.

**4. Do not run `cloudflared service install <token>` on the
workstation just because the Cloudflare wizard suggests it.** That
command registers the workstation itself as a connector for the
tunnel, which would expose `staging-api.exoper.com` from the laptop —
the opposite of the architecture. The token's only purpose is to be
written into Vault in Phase 8.5 so the in-cluster cloudflared
Deployment can use it. Until Phase 8.5 + 12, the token sits idle in
`~/cloudflare-staging-tunnel-token.txt` (0600).

**5. The bootstrap API token can be a short-TTL scoped token.** The
three permissions actually needed for Phase 6 are `Cloudflare
Tunnel:Edit` (PUT configurations), `Account Settings:Read` (for the
token verify endpoint), and `DNS:Edit` (for the read-back GET; the
explicit POST is unnecessary now per gotcha #1). Account scope: the
single account that owns the tunnel. Zone scope: just `exoper.com`.
TTL: 48h is generous; the actual API surface usage took ~3 minutes.
Client-IP filtering should be left blank — pinning to today's NAT
exit IP adds nothing on a 48h credential and risks bricking the
session if the ISP rotates the lease.

---

## Phase 7 — Linkerd mesh CA ✅

Workstation-only step. No `kubectl`, no VPS access, no Cloudflare.
Ran `step certificate create` twice (root + intermediate) at the repo
root (`~/eTradie`) so the four output files land where Phase 8.4
(`@ca.crt`, `@issuer.crt`, `@issuer.key`) and Phase 10.4
(`--helm-set-file identityTrustAnchorsPEM=ca.crt`) expect them.

### Deploy-specific values captured (NOT secrets — fingerprints only)

These fingerprints are public-info digests of the certificates, NOT
the private keys. They exist so Phase 8.4 can verify Vault holds the
exact bytes generated here. After Phase 8.4 writes the PEMs into
Vault and the on-disk files are shredded, regenerating the CA bundle
is the only way to recompute these — so capturing them here while
the files still exist is cheap insurance against the trailing-newline
class of Vault round-trip corruption.

| Value | Source | Value |
|---|---|---|
| `step` CLI version used | `step version` | `Smallstep CLI/0.30.6 (linux/amd64)` |
| Root CA Subject | `step certificate inspect ca.crt --short` | `root.linkerd.cluster.local` |
| Root CA Issuer | same | `root.linkerd.cluster.local` (self-signed) |
| Root CA validity | same | `2026-06-14T10:43:13Z` → `2036-06-11T10:43:13Z` (10 yr) |
| Root CA key type | same | ECDSA P-256 |
| Root CA SHA-256 cert fingerprint | `step certificate fingerprint ca.crt` | `dedfbeff9e57759d58834cfc528f5aa937d24ecbe7b1c9929c084d7d4e5e7fff` |
| Root CA SPKI SHA-256 (public-key fingerprint) | `openssl x509 -in ca.crt -noout -pubkey \| openssl pkey -pubin -outform DER \| sha256sum` | `863a54a3b10a4504513d9db02cfa980dee6bd5335e963fb7f10e2cd385662537` |
| Issuer Subject | `step certificate inspect issuer.crt --short` | `identity.linkerd.cluster.local` |
| Issuer signed by | same | `root.linkerd.cluster.local` (via `ca.crt`/`ca.key`) |
| Issuer validity | same | `2026-06-14T10:43:28Z` → `2027-06-14T10:43:28Z` (1 yr = 8760h) |
| Issuer key type | same | ECDSA P-256 |
| Issuer SHA-256 cert fingerprint | `step certificate fingerprint issuer.crt` | `69e886e01bbc0a274e7ea24c5685c7e9e5de3709694c13102b89e32b1b9af943` |
| Issuer SPKI SHA-256 | `openssl x509 -in issuer.crt -noout -pubkey \| openssl pkey -pubin -outform DER \| sha256sum` | `24b594a816f797a6c8f0b69b4d85ad1249e0343a2f0c17d0164240327103abf4` |
| On-disk file inventory (mode 0600 on `.key` files) | `ls -la` + `stat -c '%a %n'` | `-rw------- ca.crt 599b` · `-rw------- ca.key 227b` · `-rw------- issuer.crt 648b` · `-rw------- issuer.key 227b` |

### Sub-step status

| Sub-step | Status | Notes |
|---|---|---|
| 7.1 `step certificate create root.linkerd.cluster.local ca.crt ca.key --profile root-ca --no-password --insecure` | ✅ | Output: `Your certificate has been saved in ca.crt. / Your private key has been saved in ca.key.` Both files at mode 0600 immediately on creation (`step` default for `--no-password` output). `--insecure` here is `step`'s required ack that `--no-password` produces an unencrypted PEM; not actually insecure given Phase 8.4 moves the security boundary to Vault and the on-disk PEMs are shredded right after. |
| 7.2 `step certificate create identity.linkerd.cluster.local issuer.crt issuer.key --profile intermediate-ca --not-after 8760h --no-password --insecure --ca ca.crt --ca-key ca.key` | ✅ | Output: `Your certificate has been saved in issuer.crt. / Your private key has been saved in issuer.key.` `--not-after 8760h` = 1 year, matching the README and Linkerd's recommended issuer TTL. The intermediate carries `pathlen 0` from the `intermediate-ca` profile — it can issue end-entity certs (the per-workload Linkerd identity certs that `linkerd-identity` mints at runtime, ~24h TTL each, auto-rotated) but not further CAs. |
| Verify the signing chain | ✅ | `step certificate verify issuer.crt --roots ca.crt` produced no output and returned exit code 0 (silence = success). This is the load-bearing check that the root signed the issuer correctly. If this had failed, Phase 12 would have failed in `linkerd-control-plane-staging` sync with a confusing "invalid issuer cert chain" error and the operator would be debugging the wrong layer. |
| Verify `.gitignore` covers the four files | ✅ (after ↑ gap closed) | Commit `a24fefac` added the safety-net block. Verified post-commit: `git check-ignore -v ca.crt ca.key issuer.crt issuer.key` returned 4 matching rules (`.gitignore:89:/ca.crt   ca.crt`, etc.), `git status` reports `nothing to commit, working tree clean`. The 4 files still exist on disk for Phase 8.4 to consume but are no longer in git's untracked list, so an accidental `git add .` cannot stage them. See operator gotcha #1 below. |

### Phase 7 operator gotchas recorded for the next deploy

**1. The repo's `.gitignore` did NOT cover the four mesh CA files
out of the box.** Running Phase 7 verbatim leaves `ca.crt`, `ca.key`,
`issuer.crt`, `issuer.key` as Untracked at the repo root — one
accidental `git add .` away from staging both Linkerd private keys.
`git check-ignore -v ca.crt ca.key issuer.crt issuer.key` returned
no matches (exit 1 per file) before commit `a24fefac` added the
safety-net block. The block is repo-root-anchored (leading `/`) so
legitimate certificate fixtures under `helm/*/templates/` or
`tests/*` are unaffected. Commit `a24fefac` also added safety-net
rules for `vault-init.txt`, `etradie-<env>-creds.txt`, the
cloudflared tunnel token, and the short-lived Cloudflare API
bootstrap token — same posture (kept at `$HOME` per the runbook,
rule catches the case where an operator runs the command from
inside the repo).

**2. Capture the fingerprints BEFORE shredding the on-disk files in
Phase 8.4.** The fingerprints recorded in the table above are the
only way to verify, in Phase 8.4 and again in Phase 12, that Vault
holds the exact PEM bytes generated by `step`. Skipping the capture
is silently dangerous: a trailing-newline-stripped or whitespace-
truncated copy of the cert in Vault still decodes as a valid X.509
object but produces a *different* SHA-256 fingerprint, and surfaces
in Phase 12 as `linkerd-identity` failing to start with a confusing
"invalid issuer cert chain" error that points at the cert layer
rather than the storage layer. The Phase 8.4 verification pattern:
```bash
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv get -field=trust_anchor_pem secret/etradie/platform/linkerd/staging \
  | step certificate fingerprint /dev/stdin
# MUST equal: dedfbeff9e57759d58834cfc528f5aa937d24ecbe7b1c9929c084d7d4e5e7fff
```
Same pattern for `issuer_tls_crt` (must equal
`69e886e01bbc0a274e7ea24c5685c7e9e5de3709694c13102b89e32b1b9af943`).
The `issuer_tls_key` cannot be fingerprint-verified the same way
(it's a private key, not a cert), but the issuer-cert match is
sufficient: Linkerd refuses to start if the issuer key does not
match the issuer cert's public key, so any key corruption surfaces
the same way.

**3. `--no-password --insecure` is the correct flag combination
here, not a security compromise.** `step` requires `--insecure` as a
run-time acknowledgement that `--no-password` produces an
unencrypted PEM private key on disk. That is what we want: Phase 8.4
reads the key with `@issuer.key` (Vault's flat-PEM file-load syntax)
and an encrypted PEM would force interactive password entry in the
middle of `vault kv put`. The security boundary is moved to Vault
immediately after the write, and the on-disk PEMs are
`shred -u`'d. If the flag is dropped, `step` prompts for a
passphrase, the operator types one to make the command proceed,
and the same passphrase becomes a new secret to track that nothing
in the runbook actually consumes — worse posture, not better.

**4. ECDSA P-256 is what the chart and Linkerd both expect; do not
switch to RSA "because it's the default elsewhere".** The Linkerd
2.x control plane assumes ECDSA P-256 issuer keys; the
`linkerd-control-plane` Helm chart's `identity.issuer.scheme:
kubernetes.io/tls` consumes whatever PEM you give it, but a
workload-cert signing path that uses RSA-2048 produces ~5x larger
proxy-to-proxy handshake payloads and Linkerd's docs explicitly
recommend ECDSA P-256 for this reason. `step` defaults `root-ca`
and `intermediate-ca` profiles to ECDSA P-256, which is correct;
overriding with `--kty RSA --size 2048` is a foot-gun that surfaces
only as mesh latency regressions in Phase 14.5 load testing, not
as an obvious error.

### Expected end state at end of Phase 7

- Four files at the repo root (`~/eTradie`): `ca.crt` (599b),
  `ca.key` (227b, mode 0600), `issuer.crt` (648b),
  `issuer.key` (227b, mode 0600).
- `.gitignore` covers all four; `git status` reports
  `working tree clean`.
- Fingerprints captured in this PROGRESS entry above.
- Phase 8 has not started yet — the SSH tunnel terminal from
  Phase 2.3 will be needed again for Phase 8.1 (`terraform apply`
  needs `kubectl` reachability to the K3s API), so the operator
  should keep that tunnel open.

---

## Phase 8 — Bootstrap Vault paths + populate every secret 🟡 in progress

> **⚠️ BLOCKING ACTION before §8.2 onwards on the staging cluster.**
> The ClusterSecretStore in this deploy was created by Phase 4.2
> (pre-this-revision) pointing at the `secret/` mount, but Phase 8.1
> terraform wrote the platform secrets under `etradie/` (the
> canonical mount per `infrastructure/cluster/vault-paths/variables.tf`).
> Until the ClusterSecretStore is patched, chart `ExternalSecret`s in
> Phase 12 will silently fail to find any of the paths we are about
> to populate.
>
> Run ONCE on the staging cluster (already fixed in README §4.2 for
> future deploys):
> ```bash
> kubectl patch clustersecretstore vault-backend --type=merge \
>   -p '{"spec":{"provider":{"vault":{"path":"etradie"}}}}'
> kubectl get clustersecretstore vault-backend \
>   -o jsonpath='{.spec.provider.vault.path} {.status.conditions[0].reason}{"\n"}'
> # expect: etradie Valid
> ```
> Then proceed to §8.2 (generate shared secrets) and onward.


Largest single phase in the runbook. Eleven sub-steps. The README §8
rewrite (commits `699b382c` → `fc3086e8`) is the canonical procedure
this deploy executes; this PROGRESS entry tracks WHICH sub-steps have
run, what state Vault holds, and what state the workstation files
are in. A future operator picking this deploy back up should
**re-read README §8 first**, then resume at whichever sub-step is
marked pending below.

### Pre-resume checklist (read these 3 things if you are taking over)

1. **README.md §8 is the canonical procedure.** It was rewritten in
   commit `699b382c` (staging-canonical with inline production
   deviations) following an end-to-end audit of every ESO template
   + chart values overlay. The pre-audit procedure carried four
   real defects (empty-string TLS, wrong Linkerd path on staging,
   `[REDACTED]` placeholders, no cross-path equality verification);
   those are all fixed in the new §8.
2. **The `auth_jwt_secret`, `engine_internal_shared_secret`,
   `billing_internal_shared_secret`, postgres password, redis
   password, chromadb token, and mt-node default ZMQ token MUST be
   generated ONCE per environment.** Do NOT regenerate them mid-phase
   if you resume — the cross-path equality check in §8.11 will fail
   and Phase 12 will surface confusing 401s between services. The
   workstation's `~/etradie-staging-creds.txt` is the recovery
   reference (created in §8.3 before any `vault kv put` runs).
3. **The Linkerd mesh CA path is `etradie/platform/linkerd/production`
   even on a staging box.** This is intentional (single mesh control
   plane per cluster; `deployments/linkerd/values.yaml` hard-codes
   the path). Do not "fix" it to `staging`.

### Pre-flight values + decisions captured (this deploy)

| Decision / value | Source | Outcome for this deploy |
|---|---|---|
| Environment | per-deploy parameters | `staging` |
| Linkerd Vault path | `deployments/linkerd/values.yaml` hardcode | `etradie/platform/linkerd/production` (intentional cross-env) |
| Postgres backup CronJob | BUDGET.md Table 2B | OFF in staging — do NOT write `etradie/data-layer/postgres-backup/staging` |
| Wine-prefix snapshotter | `helm/mt-node/values-staging.yaml::snapshotter.enabled=false` | OFF in staging |
| Billing creds | Phase 0 decision | Staging placeholders (real values added later via `vault kv put` + `kubectl rollout restart deployment/etradie-billing`) |
| Engine LLM keys (Anthropic/OpenAI/Gemini), MetaApi, CFTC | engine `config.py::_validate_production_secrets` requires only TwelveData + FRED at boot | All present in operator `.env`; will be written for system-caller availability (RAG ingest, COT scraper, MetaApi provisioner) |
| MaxMind GeoLite | edge-ingress geoipupdate sidecar | License + account ID both present in `.env` |
| Cloudflare Origin Certs (2) | Cloudflare dashboard → SSL/TLS → Origin Server | Generated 2026-06-14: `staging-api.exoper.com` host cert + `staging.exoper.com` apex+wildcard cert (RSA 2048, 15yr) |
| `.env` variable mapping | grep across `helm/*/templates/*externalsecret*.yaml` `property:` lines | Cross-referenced 1:1; all 9 README-referenced `.env` names exist with correct shape (no naming drift) |

### Workstation files in hand before §8.0

| File | Origin | State |
|---|---|---|
| `~/.kube/etradie-contabo.yaml` | Phase 2.3 SSH local-forward kubeconfig copy | 2957 bytes, mode 0600 |
| `~/vault-init.txt` | Phase 3.2 Vault init output | 901 bytes, mode 0600. Holds 5 unseal keys + Initial Root Token (Vault 1.17 root tokens are 28 chars, `hvs.` + 24 chars). |
| `~/cloudflare-staging-tunnel-token.txt` | Phase 6.1 capture from Cloudflare UI | 185 bytes, mode 0600. `eyJh...` JWT-style token. |
| `~/cf-origin-staging-api.crt` / `.key` | Cloudflare Origin Server certificate creation 2026-06-14 | 1664 / 1705 bytes, mode 0600. SAN `staging-api.exoper.com`. |
| `~/cf-origin-wildcard-staging.crt` / `.key` | Cloudflare Origin Server certificate creation 2026-06-14 | 1689 / 1705 bytes, mode 0600. SAN `staging.exoper.com, *.staging.exoper.com`. |
| `~/eTradie/ca.crt` / `ca.key` / `issuer.crt` / `issuer.key` | Phase 7 `step certificate create` | 599 / 227 / 648 / 227 bytes, all mode 0600. Mesh chain verified (`step certificate verify issuer.crt --roots ca.crt` exit 0). Fingerprints captured in this PROGRESS entry §Phase 7. |

### Sub-step status

| Sub-step | Status | Notes |
|---|---|---|
| 8.0 Pre-flight (7 checks per README §8.0) | ✅ | All 20 OK lines printed: K3s reachable, vault-0 Running, vault-init.txt present, root token captured (28 chars), 4 mesh CA files + chain verified, tunnel token present, 4 Cloudflare Origin Certs present, .env present, 5 CLIs on PATH (terraform/helm/jq/openssl/step). `ROOT_TOKEN` exported in the working terminal shell. See operator gotcha #1 below — the script had a silent-failure bug that this deploy surfaced; commit fixed the bug in README §8.0 in lockstep with closing this checkpoint. |
| 8.1 Terraform apply (env-segmented Vault path schema + mt-node tenant auth infrastructure) | ✅ | Final `Apply complete! Resources: 18 added, 1 changed, 0 destroyed.` Took 4 attempts to land cleanly — every failure mode captured in the operator gotchas below. **End state in Vault** (read via `vault kv list -mount=etradie etradie/`): 3 top-level prefixes (`data-layer/`, `platform/`, `services/`) plus the `tenants/` prefix from `mt_node_tenant_secrets.tf`. 13 KV paths total, each holding the terraform `bootstrap: placeholder` value (§8.4–8.10 will overwrite). The Kubernetes auth backend's `tune` block was modified from Phase 3.4 defaults to terraform's declared 15m/1h/unauth values (1 changed); the auth backend itself was IMPORTED from Phase 3.4's `vault auth enable kubernetes` (operator gotcha #4). **Phase 11 effectively done**: the same terraform module creates both the KV schema AND the mt-node tenant auth roles + policies, so when we reach Phase 11 a re-apply will report `0 added, 0 changed, 0 destroyed`. |
| 8.2 Generate shared secrets ONCE | ✅ | 9 random values (DB_PASS=64, REDIS_PASS=64, JWT_SECRET=128, BROKER_KEY=64, CHROMA_TOKEN=64, ADMIN_PASS=48, ENGINE_SHARED=64, BILLING_SHARED=64, MT_DEFAULT_ZMQ=64) + 4 derived URL strings (DB_URL_GO=154, DB_URL_PY=164, REDIS0=119, REDIS1=119) generated ONCE in the working terminal. All 9 length sanity checks printed OK. |
| 8.3 Persist generated secrets to `~/etradie-staging-creds.txt` (mode 0600) | ✅ | 950 bytes, `-rw-------`. Written BEFORE the first `vault kv put` so a Vault failure mid-phase would not have left values generated-but-unrecoverable. Vault remains canonical; this file is the workstation safety net until Phase 15 Vault Raft snapshots. |
| 8.4 Data-layer paths (postgres + redis + chromadb) | ✅ (after path-prefix fix) | First attempt wrote to the WRONG path (mount=etradie, key=data-layer/<svc>/staging → API path `etradie/data/data-layer/<svc>/staging`). Terraform names every resource as `etradie/<rest>` so the chart ExternalSecrets read from `etradie/data/etradie/data-layer/<svc>/staging`. **Fix**: switched the write pattern to `kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN=$ROOT_TOKEN vault kv put -mount=etradie etradie/data-layer/<svc>/staging ...` for every subsequent write. The 3 canonical paths now hold real secrets at version 2 (terraform's bootstrap-placeholder version 1 was superseded). Orphan sibling paths from the first attempt destroyed with `vault kv metadata delete -mount=etradie data-layer/<svc>/staging`. DB_PASS shell-vs-vault sha256 = `61f37c14c80f2235a540b73b9c968abf32ec7e5e0b1a468ac44723547b97d5de`, MATCH across data-layer + gateway + engine + billing (verified in §8.11). See operator gotcha #9 below. |
| 8.5 Linkerd mesh CA → `etradie/platform/linkerd/production` | ✅ | Single write at the canonical /production path (chart hardcodes this regardless of env, per BUDGET.md Table 2B "this box runs ONE environment at a time"). 3 properties: `trust_anchor_pem`, `issuer_tls_crt`, `issuer_tls_key`. Round-trip cert fingerprints both MATCH the PROGRESS §Phase 7 captures (ca=`dedfbeff...`, issuer=`69e886e0...`). Issuer cert/key pairing INSIDE Vault: cert pubkey sha == key pubkey sha == `5539d25a105e1625852b48d609afe10a9484c34f8e1daae0a69f51ad29ca0de4` → Linkerd identity controller will boot cleanly at Phase 12. Path stored at version 1 (first write; no terraform placeholder existed at `/production` — terraform created `/staging` per `-var environment=staging`, see linkerd divergence note in operator gotcha #10 below). |
| 8.6 Edge-ingress (tunnel token + AOP CA + MaxMind + staging TLS) | ✅ | 4 paths written: cloudflare/tunnel (1 property, JWT-token sha256 MATCH stripped-newline = `df186461bc4a8afe41c6a42944301aaf77b81e659324ac2fcd5f2ee8f8638489`), cloudflare/aop_ca (1 property, 1 cert in bundle, Subject `CN=origin-pull.cloudflare.net` — Cloudflare's canonical Origin Pull CA), maxmind (license_key=40 chars + account_id=7 chars), tls (4 PEM properties). TLS cert fingerprints MATCH on-disk (staging_api=`1d2e9db3...`, staging_wildcard=`9d201828...`). Cert/key PAIRED inside Vault for both pairs (api cert+key pubkey sha=`e6cbad2e368a653f2b06e470c223fe947773a8a8a4d61d2ea77be21684f4d464`, wildcard cert+key=`400e46353bb22e1a696f3df8751430997607d0f5be071c010c848d086c8121b2`) → edge-ingress will TLS-handshake cleanly at Phase 12 when cloudflared dials it. |
| 8.7 Gateway | ✅ | 12 properties at `etradie/services/gateway/staging`. All 12 read-back lengths correct (auth_database_url=154 = DB_URL_GO, JWT=128, ADMIN=48, ENGINE_SHARED=64, BILLING_SHARED=64). postgres_password 3-way MATCH (shell DB_PASS == data-layer == gateway). 4 shell-vs-vault hash checks OK (JWT_SECRET=`bcf86dd9a95e...`, ENGINE_SHARED=`6037ddef7ab8...`, BILLING_SHARED=`ecc9fd2596cf...`, ADMIN_PASS=`334621330c48...`). |
| 8.8 Engine (15 properties; 9 from §8.2 + 6 from .env) | ✅ (subshell-isolated .env source) | 15 properties at `etradie/services/engine/staging`. README listed 16 but the 16th (chromadb token) is read from a DIFFERENT path (`etradie/data-layer/chromadb/staging` populated in §8.4) per the engine chart's `chromadbAuthVaultPath` value. **Critical refinement**: naive `set -a; . ~/eTradie/.env; set +a` would clobber §8.2 shell vars (.env defines stale POSTGRES_PASSWORD/AUTH_JWT_SECRET/BROKER_ENCRYPTION_KEY). Switched to subshell-isolated extraction: `eval "$(set -a; . ~/.env 2>/dev/null; for k in TWELVEDATA_API_KEY ...; do printf 'ENV_%s=...\n' "$k" "$VAL"; done)"`. Post-source DB_PASS sha verified == `61f37c14c80f...` (§8.2 vars preserved). 2 required-at-boot keys (twelvedata/fred) present, 5 optional keys (cftc, 3× LLM, mt5_metaapi) populated. postgres_password 3-way MATCH (data-layer + gateway + engine). auth_jwt_secret 2-way MATCH (gateway + engine). engine_internal_shared_secret 2-way MATCH (gateway + engine). See operator gotcha #12. |
| 8.9 Execution + Management | ✅ | 4 properties each, 8 total. All 4 lengths correct (db_url=154, redis_url=119, jwt=128, engine_shared=64). **4-way cross-path matrix**: auth_jwt_secret IDENTICAL across gateway + engine + execution + management (all `bcf86dd9a95e...`); engine_internal_shared_secret IDENTICAL across the same 4 (all `6037ddef7ab8...`); Go-DSN IDENTICAL across shell + gateway/auth_database_url + execution/execution_database_url + management/management_database_url (all `2ea31dd2...`). |
| 8.10 Billing (staging placeholders for Paddle + LemonSqueezy) | ✅ (18 properties — README said 14) | Real values for postgres/redis/shared_secret (9 properties from §8.2); plausibly-formatted random placeholders for Paddle (4 properties: webhook_secret=64, api_key=64, 2× pri_placeholder_<12hex>) and LemonSqueezy (5 properties: webhook_secret=64, api_key=64, 5-digit store_id, 2× 7-digit variant IDs). 18 total properties, not the 14 README §8.10 had stated — chart `externalsecret.yaml` lists 18 explicit data entries. **Asymmetric pair MATCH**: shell BILLING_SHARED == gateway:billing_internal_shared_secret == billing:internal_shared_secret (all `ecc9fd2596cf...`) — different KEY names, same VALUE, as designed. postgres_password 4-way MATCH (data-layer + gateway + engine + billing). Real provider credentials to be swapped in later via `vault kv put` + `kubectl rollout restart deployment/etradie-billing -n etradie-system` (Stakater Reloader picks up the K8s Secret refresh). See operator gotcha #13. |
| 8.11 mt-node platform fallback ZMQ token + cross-path equality verification + teardown | ✅ | Single property write (`default_zmq_auth_token`=`e2ca123e8f9e...`, MT_DEFAULT_ZMQ from §8.2). **FINAL CROSS-PATH IDENTITY MATRIX — all PASS**: (1) auth_jwt_secret IDENTICAL across all 4 services; (2) engine_internal_shared_secret IDENTICAL across all 4 services; (3) billing asymmetric pair (`billing_internal_shared_secret` ↔ `internal_shared_secret`) MATCH; (4) postgres_password IDENTICAL across data-layer + gateway + engine + billing; (5) redis_password IDENTICAL across data-layer + engine; (6) shell-vs-vault byte equality for all 8 §8.2 generated secrets OK; (7) all 14 KV paths present and current. **Teardown**: 9 §8.2 secrets + 4 URL strings unset; `history -c` cleared in-memory bash history; ROOT_TOKEN kept (Phase 10+ still uses it); vkv/vkv_get/vkv_file helpers kept. |

### Phase 8 cross-path identity matrix (final verification surface)

All hashes are sha256 of the value bytes (no value ever appeared in
scrollback). Captured here so a future operator can reproduce the
verification against staging Vault without re-deriving from
`~/etradie-staging-creds.txt`:

| Cross-path value | sha256 | Paths verified identical |
|---|---|---|
| auth_jwt_secret | `bcf86dd9a95e7c31db1a0d5517fd9631e51619e591657ebdc27a6ec396f58eaa` | gateway + engine + execution + management |
| engine_internal_shared_secret | `6037ddef7ab866295145b9aea83ff095fb857e5dff0a5a13f3c9d8e368e7f517` | gateway + engine + execution + management |
| billing shared secret (asymmetric pair) | `ecc9fd2596cfd767990a0b0a4c95ed329a9f607b691ac2a50adabb75e4001db6` | gateway:billing_internal_shared_secret + billing:internal_shared_secret |
| postgres_password | `61f37c14c80f2235a540b73b9c968abf32ec7e5e0b1a468ac44723547b97d5de` | data-layer/postgres + gateway + engine + billing |
| redis_password | `bdb743bf551f1f1c50bfe7d662a537ba963b881a6f9b0ac870c51725dd11458e` | data-layer/redis + engine |
| chroma auth_token | `e0675e34e492...` (truncated) | data-layer/chromadb (engine reads from this same path) |
| broker_encryption_key | `881c7e8066b2...` (truncated) | engine ONLY (Tier 3 least-privilege; gateway/execution/management deliberately do NOT hold this) |
| default_zmq_auth_token | `e2ca123e8f9e...` (truncated) | mt-node platform |

### Vault state at end of Phase 8 — 14 KV paths

| Path | current_version | Source of write |
|---|---|---|
| `etradie/data-layer/postgres/staging` | 2 | §8.4 (terraform v=1 placeholder superseded) |
| `etradie/data-layer/redis/staging` | 2 | §8.4 |
| `etradie/data-layer/chromadb/staging` | 2 | §8.4 |
| `etradie/platform/linkerd/production` | 1 | §8.5 (first write; terraform created `/staging` not `/production` — see operator gotcha #10) |
| `etradie/services/edge-ingress/staging/cloudflare/tunnel` | 2 | §8.6 |
| `etradie/services/edge-ingress/staging/cloudflare/aop_ca` | 2 | §8.6 |
| `etradie/services/edge-ingress/staging/maxmind` | 2 | §8.6 |
| `etradie/services/edge-ingress/staging/tls` | 2 | §8.6 |
| `etradie/services/gateway/staging` | 2 | §8.7 |
| `etradie/services/engine/staging` | 2 | §8.8 |
| `etradie/services/execution/staging` | 2 | §8.9 |
| `etradie/services/management/staging` | 2 | §8.9 |
| `etradie/services/billing/staging` | 2 | §8.10 |
| `etradie/services/mt-node/staging` | 2 | §8.11 |

Plus the terraform-managed `etradie/platform/linkerd/staging` path
still holding the bootstrap placeholder at v=1 — see operator
gotcha #10. The orphan sibling paths
`etradie/data-layer/{postgres,redis,chromadb}/staging` (mount=etradie,
key=`data-layer/...` without the doubled `etradie/` prefix) from the
first §8.4 attempt were destroyed with `vault kv metadata delete` —
`vault kv get` against them now returns `No value found`.

### Phase 8 §8.2–§8.11 operator gotchas recorded for the next deploy

**9. `vkv etradie/X` resolves to the WRONG Vault path.** The `vkv`
helper README §8.1 defines is:
```bash
vkv () { kubectl -n vault exec -i vault-0 -- \
         env VAULT_TOKEN="$ROOT_TOKEN" vault kv put "$@"; }
```
`vault kv put` takes a single positional path argument that it
parses as `<mount>/<key>`. So `vkv etradie/data-layer/postgres/staging`
resolves to mount=`etradie`, key=`data-layer/postgres/staging`, which
Vault writes at the API path `etradie/data/data-layer/postgres/staging`.
BUT terraform's `infrastructure/cluster/vault-paths/main.tf` names
every resource as `etradie/<rest>` (mount=etradie, key=etradie/<rest>),
so the canonical chart-read path is `etradie/data/etradie/<rest>`. The
first §8.4 attempt wrote to the WRONG location; chart ExternalSecrets
would have found only terraform's `bootstrap: placeholder`. **The
canonical write pattern is**:
```bash
kubectl -n vault exec -i vault-0 -- \
  env VAULT_TOKEN="$ROOT_TOKEN" vault kv put -mount=etradie \
  etradie/<rest> <kv_pairs>
```
The explicit `-mount=etradie` flag plus the full `etradie/<rest>`
KEY (with the doubled `etradie/` prefix, NOT an accident) make the
path unambiguous and identical to terraform's resource id. §8.4 was
re-run with this pattern; KV-v2 created version 2 at each canonical
path, ESO reads only the latest version so the placeholder was
superseded. Orphan sibling paths from the first attempt were
destroyed via `vault kv metadata delete -mount=etradie data-layer/<svc>/staging`.
The README §8.4–§8.11 update lands in a sibling commit replacing
every `vkv secret/etradie/...` pattern with the explicit
`kubectl ... -mount=etradie etradie/...` form so the next deploy
does not re-encounter this.

**10. The Linkerd Vault path is `etradie/platform/linkerd/production`
EVEN on a staging box, and terraform's env-segmented behaviour
creates a dead `/staging` path.** Terraform's
`vault_kv_secret_v2.linkerd_identity` resource names the path
`etradie/platform/linkerd/${var.environment}`. The staging apply
(`-var environment=staging`) therefore created a placeholder at
`/staging` that NO chart will ever read — `deployments/linkerd/values.yaml`
hardcodes `vaultPath: etradie/platform/linkerd/production`, and only
a single ArgoCD Application `linkerd-identity-production.yaml` exists
(no `*-staging` variant). The §8.5 write went to the canonical
`/production` path which terraform did NOT create (KV-v2 auto-creates
on first write). End state: `/staging` holds the bootstrap placeholder
at v=1 (terraform-owned, dead); `/production` holds the real CA at
v=1 (operator-owned, canonical). Not a blocker; flagged so a future
operator does not try to "clean up" `/production` thinking it's
orphaned, or write to `/staging` thinking it's the staging path.

**11. `.env` malformed lines spam "command not found" but are
otherwise harmless.** The staging deploy's `~/eTradie/.env` had 3
non-`KEY=value` lines: a GHCR PAT note (`GHCR = ghp_uN...` — invalid
shape due to spaces around `=`), a Windows cloudflared install
command (`cloudflared.exe service install eyJh...` — the install
command Cloudflare's dashboard suggests but which the runbook
explicitly says to IGNORE), and a stale Cloudflare tunnel token
(`cfut_...` — old token, the current one is in
`~/cloudflare-staging-tunnel-token.txt`). When `.env` is sourced
with `set -a; . ~/.env; set +a`, bash tries to execute these as
commands and they fail with "command not found". Zero shell
variables are defined from these lines, and none of the values
are consumed anywhere in Phase 8+. **The GHCR PAT and the current
Cloudflare tunnel token both live in dedicated 0600 files** (per
README §0.2 and §6.1), not in `.env`. Cleanup is purely cosmetic;
leave the `.env` alone or comment the three lines.

**12. Subshell isolation is REQUIRED when sourcing `.env` for
§8.8.** The platform's `.env` defines `POSTGRES_PASSWORD`,
`AUTH_JWT_SECRET`, `BROKER_ENCRYPTION_KEY` with stale/template
values. Naive `set -a; . ~/.env; set +a` in the working shell
CLOBBERS the §8.2 generated values — every subsequent `vault kv put`
would then write the stale `.env` values, breaking the cross-path
equality matrix that Phase 12 depends on. **The fix is a subshell
extraction pattern**:
```bash
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
```
The subshell variables die when `$(...)` closes; only the
`ENV_*=...` printed assignments come back to the main shell. After
the §8.8 source we verified `DB_PASS` sha matched the pre-source
value, confirming the subshell isolation worked. README §8.8 will
be updated in the sibling commit with this pattern.

**13. Billing chart reads 18 properties, not 14 (README discrepancy).**
README §8.10 stated "Fourteen properties" but the chart's
`helm/billing/templates/externalsecret.yaml` template lists 18
explicit `data:` entries: billing_database_url + 6 POSTGRES_* fields
+ internal_shared_secret + billing_redis_url + 4 Paddle keys + 5
LemonSqueezy keys = 18. The first 9 carry real values (from §8.2);
the 9 provider keys carry plausibly-formatted placeholders for
staging. Real provider credentials to be swapped in later via
`vault kv put -mount=etradie etradie/services/billing/staging
paddle_webhook_secret=... ...` + `kubectl rollout restart
deployment/etradie-billing -n etradie-system`. Stakater Reloader
(Phase 5) picks up the K8s Secret refresh and rolls the pod
automatically.

**14. Phase 8 wall time: ~30 minutes including the verification
block**, matching README §8 header estimate. The path-prefix
recovery at §8.4 added ~5 minutes; the subshell-isolation
refinement at §8.8 added ~3 minutes. Both contingencies are now
baked into the README's sibling commit so the next deploy runs
first-attempt-clean.

---

## Phase 9 — Build + inject the envoy WASM filter ✅

Workstation-only phase. No `kubectl`, no Vault, no VPS access. The
VPS will only see this change at Phase 12 when ArgoCD's repo-server
reaches out to GitHub and pulls the updated repo.

### Pre-flight values captured

| Value | Source | Outcome for this deploy |
|---|---|---|
| Rust toolchain | `rustup --version` | 1.28.2 already installed; the 1.75.0 toolchain pinned by `src/envoy/rust-toolchain.toml` is already present alongside `stable` (1.93.1) and 1.88.0 |
| `wasm32-wasi` target on 1.75.0 | `rustup target list --toolchain 1.75.0-x86_64-unknown-linux-gnu --installed` | Already installed (alongside `wasm32-unknown-unknown` + `x86_64-unknown-linux-gnu`); auto-installed at first `cd src/envoy && cargo build` per `rust-toolchain.toml::targets` |
| Pre-existing build artefact | `ls src/envoy/target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm` | 217566 bytes, mtime Jun 12 21:26, mode 0755 |
| WASM magic bytes (validity) | `head -c 4 … \| xxd` | `00000000: 0061 736d` (“\0asm” header) ✔ |
| `file` output | `file … .wasm` | `WebAssembly (wasm) binary module version 0x1 (MVP)` ✔ |
| Binary sha256 | `sha256sum … .wasm` | `fcad85bfd0a0bcb7dccf317def1bc436211dff700b4c2fc11063aab8e6682fbb` |
| Base64-encoded size | `base64 -w0 … \| wc -c` | 290088 chars (= 217566 × 4/3, no padding overhead) |

### Sub-step status

| Sub-step | Status | Notes |
|---|---|---|
| 9.1 Verify toolchain + target | ✅ | rustup/rustc/cargo present; toolchain 1.75.0 + `wasm32-wasi` target both pre-installed. No `rustup target add` invocation needed. |
| 9.2 `cargo build --release --target wasm32-wasi` | ✅ SKIPPED | Pre-existing artefact from a previous local build is byte-identical to what a rebuild would produce. Phase 8 + recent PROGRESS/README commits touched no `src/envoy/` code; the release profile strips build timestamps so rebuild yields the same binary. Verified valid (magic bytes + `file` + sha256 captured above). |
| 9.3 Encode to base64 | ✅ | 290088-char single-line base64 of the 217566-byte `.wasm`. |
| 9.4 Write `helm/envoy/values-staging-wasm.yaml` | ✅ | New file. Contains the 3 fields the chart consumes: `wasm.base64` (the encoded bytes — chart's `configmap-wasm.yaml` writes these to a K8s ConfigMap `binaryData.integration-filter.wasm`, Helm decodes transparently), `wasm.sha256` (rendered as ConfigMap annotation `sha256: ...` for audit), `wasm.builtAt` (UTC timestamp annotation). The deployment.yaml carries `checksum/wasm: {{ .Values.wasm.base64 \| sha256sum }}` as a pod-template annotation so future rotations roll the pods automatically. |
| 9.5 Wire overlay into ArgoCD Application | ✅ | Added `- values-staging-wasm.yaml` to `deployments/argocd/children/envoy-staging.yaml::spec.source.helm.valueFiles` AFTER `values-staging.yaml`. The Application now reads three value files in order: `values.yaml` → `values-staging.yaml` → `values-staging-wasm.yaml`. The WASM overlay is the only one that supplies a non-empty `wasm.base64`, which is what passes the chart's `fail "wasm.base64 is required"` template guard at `configmap-wasm.yaml` render time. |
| 9.6 Commit + push | ✅ | Local commit `b49b03e6` (Chinwe Iziogo author), 2 files / 7 insertions. Pulled the two pending MCP commits from GitLab (`ab83d40a` PROGRESS + `8f1ae81a` README) onto local main via `pull --rebase gitlab main` first; then pushed to **GitHub `origin`** (HEAD `5c306498`, what ArgoCD will read at Phase 12) and **GitLab `gitlab`** (HEAD `5c306498`, MCP mirror). |

### Phase 9 architectural choice — Option A (git-committed overlay) vs Option B (`argocd app set --helm-set-file`)

The comment inside `envoy-staging.yaml` suggested Option B (CI-time
`argocd app set --helm-set-file`). That pattern was rejected for
staging because:

1. **`argocd app set` modifies `spec.source.helm.parameters` on the
   in-cluster Application object.** Root-app's `automated.selfHeal:
   true` would see drift from git and try to revert the injection on
   every reconcile. Workarounds (`ignoreDifferences` on
   `/spec/source/helm/parameters`, or pre-Phase-12 sync-ordering
   gymnastics) are fragile.
2. **The root-app's `directory.recurse: true` is GitOps-pure.** Every
   YAML under `deployments/argocd/children/` is reconciled
   declaratively; adding `values-staging-wasm.yaml` as a committed
   `valueFiles` entry is byte-identical to the "spec lives in git"
   posture used by every other Application in the platform.
3. **The base64-encoded WASM is NOT a secret.** The filter source is
   in `src/envoy/` in the same repo; committing the encoded bytes is
   equivalent to committing the source.
4. **README §9 (production-flavoured) already picks Option A** (a
   committed `values-production-wasm.yaml` file). Picking Option A
   for staging keeps the two environments wiring-identical.

### Production deviation captured for future operator

When the production deploy runs Phase 9, repeat with:
  - `helm/envoy/values-production-wasm.yaml` (analogous overlay)
  - `deployments/argocd/children/envoy-production.yaml` (analogous
    edit — add `- values-production-wasm.yaml` to its `valueFiles`)

Both files would contain the SAME bytes if built from the same git
SHA (the filter is environment-agnostic; only sizing differs
between production and staging at the chart-values layer, not the
WASM-binary layer).

### Vault + K8s state

**Unchanged.** Phase 9 touched only git (workstation + GitHub +
GitLab). The VPS will only see these changes at Phase 12 when
ArgoCD's repo-server pod pulls the updated repo from GitHub via
outbound HTTPS to `github.com/FlameGreat-1/eTradie.git`.

### Phase 9 operator gotchas

**15. ArgoCD reads ONLY from GitHub.** Every
`repoURL` in every Application points at
`https://github.com/FlameGreat-1/eTradie.git`. GitLab is purely a
backup/mirror for the MCP integration to write into (PROGRESS.md +
README.md commits land there directly because the MCP tool has
push rights to GitLab; manually-driven workstation commits land on
GitHub first because that's the canonical `origin`). The deploy
sequence is therefore:

  1. (Optional) Pull any MCP-driven docs commits from GitLab onto
     local main: `git pull --rebase gitlab main`.
  2. Make the actual deploy commit locally.
  3. **`git push origin main` — LOAD-BEARING.** This is what
     ArgoCD reads. Without this push, the VPS-side platform stays
     on the old code.
  4. `git push gitlab main` — mirror so MCP stays in sync.

If an operator pushes only to GitLab and forgets GitHub, every
ArgoCD reconcile keeps reading the old code; symptoms surface as
"my chart change isn't applying" with no obvious cause.

**16. The pre-existing `.wasm` artefact from a previous local build
is byte-identical to a fresh rebuild.** Rust's release profile in
this workspace pins `opt-level = "z"`, `lto = true`,
`codegen-units = 1`, `panic = "abort"`, `strip = true`. With
`strip = true` the build timestamps are removed from the binary,
and all other inputs (source, deps in `Cargo.lock`, profile flags)
are deterministic. So `cargo build --release` on the same workspace
produces the same bytes — the verification block (magic + `file` +
sha256) is sufficient to trust the artefact without rebuilding.

**17. The base64-encoded WASM line in `values-staging-wasm.yaml`
is very long (~290000 chars on one line).** YAML allows arbitrarily
long scalar values on a single line, and `git diff` handles them
cleanly. A naive editor with hard line wrapping at 80 chars would
mangle the file; if an operator ever opens the file in such an
editor, the chart will fail at render time because Helm's base64
decoder rejects line breaks in the encoded string. Use `cat`/`less`
to view; never edit by hand (use the encode-from-binary recipe in
the file's own header comment).

**18. Phase 9 commit author appears on git history as the
workstation operator (Chinwe Iziogo), NOT as `Nwudele Kendo`** like
the MCP-driven PROGRESS + README commits. This is intentional: the
workstation does the Rust build and produces the binary locally,
so the commit reflects the workstation operator. MCP-driven
follow-up docs commits (this PROGRESS entry + the README sibling
commit) author as `Nwudele Kendo` because the MCP integration's
access token is tied to that GitLab user.

---

## Phase 10 — ArgoCD + both AppProjects + root app 🟡 in progress

In-progress checkpoint. Pre-flight + §10.0 + §10.1 complete; §10.2–1§0.5
pending. The cluster runs ArgoCD v2.13.3; the staging children
Applications have NOT yet been created (root-app not yet applied).
Vault state from Phase 8 unchanged; the 14 KV paths remain canonical.

### Phase 10 pre-flight (commit `fc9e0042`)

Two prior decisions baked into git BEFORE §10.0:

| Decision point | Choice | Why | Where it landed |
|---|---|---|---|
| GHCR pull credentials | Option B: keep packages PRIVATE; per-namespace `ghcr-pull` Secret | Supply-chain hygiene; aligns with Tier 11 + ufw posture. `write:packages`-scoped PATs are not used in-cluster (least privilege). | 6 chart `values-staging.yaml` files: engine, gateway, execution, management, billing, edge-ingress. mt-node skipped (`mtConnection.enabled=false` in staging Application; chart's StatefulSet does not render at Phase 12). |
| Linkerd trust anchor delivery | Option A: commit PUBLIC `ca.crt` PEM to chart values | GitOps-pure; the trust anchor is public (no private key); avoids `argocd app set --helm-set-file` drift that root-app's `selfHeal` would otherwise fight. | `deployments/linkerd/control-plane-values.yaml::identityTrustAnchorsPEM` as YAML block scalar. Chart's pre-existing sentinel parameter in `linkerd-control-plane-production.yaml` is now inert. Private issuer cert/key stay in Vault. |

### §10.0 — Pre-flight on the cluster (namespaces + `ghcr-pull` Secret) ✅

| Sub-step | Status | Notes |
|---|---|---|
| 10.0.1 Tunnel + KUBECONFIG sanity | ✅ | Tunnel terminal reopened (pid 595974, `ssh -N -L 6443 etradie@13.140.164.173`). `kubectl get nodes` returns `vmi3362776 Ready control-plane,master 16h v1.30.4+k3s1`. The `ssh-add` snippet in `~/.bashrc` did NOT pre-load the key in this fresh WSL session — the operator typed the passphrase once at tunnel reopen. For next deploy, the README's daily-operator-routine step (`ssh-add ~/.ssh/id_ed25519` once per WSL boot) keeps subsequent tunnels passphrase-free. |
| 10.0.2 Create namespaces `etradie-system` + `edge-ingress-system` | ✅ | Both created idempotently (`kubectl create namespace`). The data-layer chart re-creates `etradie-system` at Phase 12, but `CreateNamespace=true` syncOption is a no-op on existing namespace, so this pre-create is safe. |
| 10.0.3 Create read-only GHCR PAT | ✅ | New classic PAT on `flamegreat-1` with **`read:packages` scope ONLY** (separation of duties from the existing `write:packages`-scoped `~/.ghcr_pat` used for Phase 2.5 push). Saved to `~/.ghcr_pull_pat` (mode 0600, 41 bytes, `ghp_` prefix). `curl /user X-OAuth-Scopes` confirms exactly `read:packages`. **Future hardening (Phase 15.x TODO)**: move the PAT into Vault at `etradie/platform/ghcr-pull:pat`, render via ESO `ExternalSecret` into the K8s `ghcr-pull` Secret per namespace. Same chart-side reference (`imagePullSecrets: [{name: ghcr-pull}]`); only the Secret's provenance changes. |
| 10.0.4 Create `ghcr-pull` Secret in both namespaces | ✅ | `kubectl create secret docker-registry ghcr-pull --docker-server=ghcr.io --docker-username=flamegreat-1 --docker-password=$(cat ~/.ghcr_pull_pat) --docker-email=not-needed@github.com` in each. Idempotent (delete-if-exists then create). Both verified type `kubernetes.io/dockerconfigjson`; dockerconfigjson decoded to confirm server, username, 40-char password, email all correct. |

### §10.1 — Install ArgoCD v2.13.3 ✅

| Sub-step | Status | Notes |
|---|---|---|
| 10.1.1 Create `argocd` namespace | ✅ | `kubectl create namespace argocd`. |
| 10.1.2 Apply ArgoCD v2.13.3 install manifest | ✅ | `kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/install.yaml`. Yielded: ArgoCD CRDs (Application, ApplicationSet, AppProject), ServiceAccounts, Roles/RoleBindings, ClusterRoles/ClusterRoleBindings, 4 ConfigMaps, 2 Secrets (argocd-secret + argocd-notifications-secret), 6 Services (applicationset-controller, dex-server, metrics, notifications-controller-metrics, redis, repo-server, server, server-metrics), 6 Deployments (applicationset-controller, dex-server, notifications-controller, redis, repo-server, server), 1 StatefulSet (application-controller), and 7 NetworkPolicies (ArgoCD's own zero-trust ingress posture). |
| 10.1.3 Wait for argocd-server Available | ✅ | `kubectl -n argocd wait --for=condition=Available deployment/argocd-server --timeout=300s` returned `condition met` after ~32 seconds. |
| 10.1.4 Final state | ✅ | 7 pods all Running 1/1: `argocd-application-controller-0` (StatefulSet), `argocd-applicationset-controller-66db6984c8-rrtj9`, `argocd-dex-server-647484ccbb-fcn7p`, `argocd-notifications-controller-7f955f9677-nvvxf`, `argocd-redis-6f68b7d98f-dkrp4`, `argocd-repo-server-7d677cd7c5-82xtp`, `argocd-server-564b8cdd98-qw5ct`. All 6 Deployments 1/1 Available. |

### Remaining Phase 10 sub-steps (pending)

| Sub-step | Status | Notes |
|---|---|---|
| 10.2 Admin password + port-forward + argocd CLI login | ⏸ pending | `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' \| base64 -d` to retrieve admin password; `kubectl -n argocd port-forward svc/argocd-server 8080:443 &` in a dedicated terminal; `argocd login 127.0.0.1:8080 --username admin --password "$PWD" --insecure`. |
| 10.3 Apply both AppProjects + root-app.yaml | ⏸ pending | `kubectl apply -f deployments/argocd/appproject.yaml` (etradie AppProject) + `kubectl apply -f deployments/argocd/linkerd-appproject.yaml` (linkerd AppProject) + `kubectl apply -f deployments/argocd/root-app.yaml`. Root-app then **immediately creates every Application** under `deployments/argocd/children/` (directory.recurse: true). Staging Applications start auto-sync because their `automated.{prune:true, selfHeal:true}` config. **Their pods will fail until §10.5 completes** because the Linkerd proxy injector webhook is not running yet — every meshed pod has `linkerd.io/inject: enabled` and will hang in Pending without it. |
| 10.4 (formerly `argocd app set --helm-set-file identityTrustAnchorsPEM=ca.crt`) | **REMOVED** | The pre-flight commit `fc9e0042` embedded the PEM directly into `deployments/linkerd/control-plane-values.yaml`. No CLI override needed. |
| 10.5 (NEW) Manual sync the 3 `linkerd-*` Applications in wave order | ⏸ pending | `argocd app sync linkerd-identity-production` (wave -6, creates linkerd-identity-issuer Secret from Vault) → `argocd app sync linkerd-crds-production` (wave -5) → `argocd app sync linkerd-control-plane-production` (wave -4, brings up proxy injector + identity controller). After this, the staging children's next reconcile (~3 min) finds the mesh up and their proxy sidecars inject cleanly. |

### Pre-Phase-10.2 session-resume recovery (read this if the session ended)

To pick up at §10.2 from a clean workstation session:

1. **Tunnel**: in a dedicated terminal,
   - `ssh-add ~/.ssh/id_ed25519` (passphrase once per WSL boot)
   - `ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173`
2. **KUBECONFIG**: `export KUBECONFIG=~/.kube/etradie-contabo.yaml`
3. **Cluster sanity**: `kubectl get nodes` returns `vmi3362776 Ready ... v1.30.4+k3s1`
4. **ArgoCD up**: `kubectl -n argocd get pods` shows 7 pods Running 1/1
5. **Pre-flight artefacts present on cluster**:
   - `kubectl get ns etradie-system edge-ingress-system` → both Active
   - `kubectl -n etradie-system get secret ghcr-pull -o jsonpath='{.type}'` → `kubernetes.io/dockerconfigjson`
   - `kubectl -n edge-ingress-system get secret ghcr-pull -o jsonpath='{.type}'` → `kubernetes.io/dockerconfigjson`
6. **Pre-flight artefacts present on workstation**:
   - `~/.ghcr_pull_pat` — mode 0600, 41 bytes, `ghp_` prefix (read-only GHCR PAT)
   - `~/eTradie/ca.crt` — Linkerd root CA PEM (also now committed to `deployments/linkerd/control-plane-values.yaml`; workstation copy retained as recovery reference)
   - `~/etradie-staging-creds.txt` — mode 0600, holds the 8 §8.2 secret values
   - `~/vault-init.txt` — mode 0600, holds the Vault unseal keys + root token
7. **Git state**: HEAD on `main` is at this checkpoint commit. Both GitHub (`origin`) and GitLab (`gitlab`) at the same SHA. ArgoCD reads from GitHub at Phase 10.3 onwards.
8. **Resume**: proceed to Phase 10.2 per the next README §10 entry.

### Phase 10 operator gotchas (so far)

**19. The tunnel terminal needs an active ssh-agent at reopen time.**
The staging deploy's tunnel terminal closed (likely a WSL sleep). On
reopen, `ssh -N -L 6443:127.0.0.1:6443 etradie@HOST` prompted for the
passphrase because the new shell did not have an `ssh-agent`
running. Quick fix at reopen: `ssh-add ~/.ssh/id_ed25519` first,
then reopen the tunnel. Or accept the one-time passphrase typing on
reopen.

**20. GHCR PAT separation of duties — ENTERPRISE PATTERN.** The
existing `~/.ghcr_pat` has `repo, write:packages` scope (used to
push the mt-node image at Phase 2.5). Using a `write:packages`-scoped
PAT as an in-cluster `ghcr-pull` Secret is over-privileged: a Secret
leak via etcd / pod exfil / `get secrets` RBAC gives the attacker
PUSH ability to GHCR, not just PULL. The staging deploy created a
**second** PAT with `read:packages` ONLY, kept in `~/.ghcr_pull_pat`,
and used THIS one for the in-cluster Secret. Different blast radius
on compromise; ~90 seconds of one-time setup cost.

**21. Pre-creating `etradie-system` is idempotent.** The data-layer
chart will re-create it at Phase 12 sync via `CreateNamespace=true`,
but on an existing namespace this is a no-op. The pre-create here
is necessary because we need to drop the `ghcr-pull` Secret into
the namespace BEFORE root-app spins up the data-layer Application
(if root-app reaches the engine/gateway/etc. Applications and they
try to pull images before the Secret exists, every pod fails with
`ErrImagePull` and we'd be debugging the wrong layer).

**22. ArgoCD's own zero-trust posture.** The v2.13.3 install manifest
ships 7 NetworkPolicies in the `argocd` namespace (one per
component). These admit only the in-cluster IPs that ArgoCD itself
needs (controller ↔ repo-server ↔ redis ↔ server). If a chart
NetworkPolicy ever needs to talk INTO argocd (e.g. a sync-hook), the
chart-side NetworkPolicy needs explicit egress to the argocd
namespace. The platform's existing NetworkPolicies do not, so this
is not currently a problem; flagged in case a future chart adds a
sync-hook.

### Phase 8 operator gotchas recorded for the next deploy

**1. The README §8.0 pre-flight script silently passed two failed
checks until commit (this checkpoint) fixed it.** The original
script used the pattern:
```bash
kubectl get nodes >/dev/null && echo OK "K3s reachable"
kubectl -n vault get pod vault-0 ... | grep -qx Running && echo OK "vault-0 Running"
```
When `kubectl get nodes` fails (e.g. KUBECONFIG empty), the `&& echo OK`
branch is skipped without printing OK, AND `set -e` does NOT exit
because the failed command is the LEFT operand of `&&` — which `set -e`
explicitly ignores by design (treating `cmd && other` as a conditional
expression, not an unhandled failure). Execution falls through to
the next step. The script eventually prints "=== All pre-flight
checks passed ===" — a lie. The fix is to add an explicit `||
{ echo FAIL; exit 1; }` arm to each kubectl check. The corrected
script prints OK on success and FAIL+exit on failure. Patched into
README §8.0 in the same commit that creates this checkpoint.

**2. KUBECONFIG empty in the working shell was the root cause this
deploy hit gotcha #1.** The `~/.bashrc` export from Phase 2.3
(`export KUBECONFIG=~/.kube/etradie-contabo.yaml`) is sourced on new
shell start, but the operator's already-open Terminal 2 had been
opened BEFORE the `.bashrc` edit during Phase 2.3. The shell never
re-sourced the file. Diagnosis: `echo "KUBECONFIG=$KUBECONFIG"`
printed `KUBECONFIG=` (empty); `grep KUBECONFIG ~/.bashrc` showed the
export line was present. Fix for this shell: `export KUBECONFIG=~/.kube/etradie-contabo.yaml`.
The Daily Operator Routine in README has also been amended to
include this export as the third per-WSL-boot step, belt-and-braces
with the `.bashrc` persistence.

**3. `kubectl get nodes` failure mode is loud.** A dead tunnel or
empty KUBECONFIG produces a 10-line burst of
`E... memcache.go:265 ... connection refused ... localhost:8080`
errors on stderr before failing. The errors are noisy enough that
an operator skimming output COULD miss them between OK lines if the
terminal scrollback is short. The new fail-loud script prints a
single `FAIL ...` line and exits, leaving the terminal at the prompt
with a clear cause.

**4. `ss-tln | grep ':6443'` is the canonical "is the tunnel alive"
check.** Expected output (when alive):
```
LISTEN 0  128  127.0.0.1:6443  0.0.0.0:*
LISTEN 0  128      [::1]:6443    [::]:*
```
If this returns no lines, the tunnel terminal was closed. Reopen
it in a dedicated terminal (`ssh -N -L 6443:127.0.0.1:6443
etradie@<IP>`); do NOT try to fix kubectl by changing kubeconfig.

**5. The terraform vault provider needs `VAULT_TOKEN` exported in
the apply shell.** ROOT_TOKEN alone is not enough — the terraform
vault provider reads from `VAULT_TOKEN` specifically. On the staging
deploy the apply failed on every resource with `Error: no vault
token set on Client` until we ran `export VAULT_TOKEN="$ROOT_TOKEN"`
before the apply. The fix is in the operator's shell, not the
terraform code; the README §8.1.A block now exports VAULT_TOKEN
as part of opening the port-forward and continues to keep it in
the same shell through §8.1.B.

**6. The 'etradie/' KV-v2 mount must be enabled BEFORE terraform
apply.** The terraform module's `variables.tf` defaults
`vault_mount = "etradie"`, but Phase 3.4 (pre-this-revision) only
enabled `secret/`. Apply failed with `Code 404: no handler for
route "etradie/data/etradie/..."` until we ran
`vault secrets enable -version=2 -path=etradie kv` against vault-0.
Fix in README §3.4.1b (sibling commit): enable BOTH mounts at
Phase 3.4 (secret/ for dev/test, etradie/ for the canonical
platform writes). Both `enable` calls now `|| echo idempotent`
so re-running is safe.

**7. The 'kubernetes/' auth backend already exists from Phase 3.4.**
Terraform's `vault_auth_backend.kubernetes` resource tries to
re-enable it and Vault rejects with `Code 400: path is already in
use at kubernetes/`. The fix is `terraform import
vault_auth_backend.kubernetes kubernetes` BEFORE re-applying.
The staging deploy did this once; subsequent re-applies (and
production's first apply on an already-Phase-3.4'd Vault) need
the same import. The README's Phase 11 section will be amended
to include the import as a pre-apply step on environments where
Phase 3.4 has already run.

**8. ClusterSecretStore mount mismatch (pre-this-revision).** The
ReadME §4.2 (pre-this-revision) created the ClusterSecretStore
with `path: "secret"`. Combined with gotcha #6, that meant chart
ExternalSecrets would have looked at the WRONG mount. Fixed in
§4.2 (sibling commit) by changing the default to `path: "etradie"`
and adding an inline `kubectl patch` recipe for in-place fixup on
an already-deployed cluster (the staging deploy needs that
patch executed before §8.4 onwards). Audit trail: the deploy
that surfaced this is logged in this checkpoint.

---

## Phase 10 — continuation 2026-06-15 (Vault path defect + Linkerd mesh up + staging children pending)

This section continues the Phase 10 timeline AFTER the prior
checkpoint that closed §10.0 + §10.1. The next session resumes
at the bottom of this section.

### Headline state at end of this session

- **ArgoCD healthy.** 7 pods Running. CLI logged in via `127.0.0.1:8080` port-forward.
- **All 3 AppProjects + root-app applied.** 22 child Applications discovered.
- **3 linkerd-* Applications synced; Linkerd control plane Running.** Identity, destination, and proxy-injector pods all up with sidecars (2/2 or 4/4 Ready).
- **14 Vault KV paths aligned with chart ExternalSecret keys.** ESO resolves every chart key to a real Vault secret; verified on `linkerd-identity-issuer` (SecretSynced/True, fresh lastTransitionTime, K8s Secret of type `kubernetes.io/tls` with `tls.crt` + `tls.key`).
- **STAGING CHILDREN STILL Missing.** 10 staging Applications (`data-layer-staging`, `engine-staging`, `gateway-staging`, `execution-staging`, `management-staging`, `billing-staging`, `mt-node-staging`, `edge-ingress-staging`, `envoy-staging`, `observability-logs-staging`) all show `OutOfSync / Missing` with empty `etradie-system` / `edge-ingress-system` / `envoy-system` namespaces. Not yet diagnosed — the next session starts here.

### What broke in this session

#### Defect: ESO Vault path resolution silently strips the leading mount-name segment

**Root cause traced to external-secrets v0.10.4 source at `pkg/provider/vault/client_get.go::buildPath()`:**

When the ClusterSecretStore has `spec.provider.vault.path: etradie` (the KV-v2 mount name) AND the ExternalSecret's `remoteRef.key` starts with `etradie/`, ESO strips the leading `etradie/` segment, then prepends `etradie/data/`. The effective API path for a chart key `etradie/services/engine/staging` is `etradie/data/services/engine/staging` — NOT `etradie/data/etradie/services/engine/staging`.

But `infrastructure/cluster/vault-paths/main.tf` (pre-this-revision) created every `vault_kv_secret_v2` resource with both `mount = "etradie"` AND `name = "etradie/services/..."`. KV-v2 writes that to API path `etradie/data/etradie/services/...` — doubled-prefix.

**Net effect:** every chart ExternalSecret resolved to the single-prefix path; Phase 8 wrote data ONLY at the doubled-prefix path. Every read returned `Secret does not exist`. Undetected through Phase 8 because Phase 8 only WROTE; Phase 10 is the first phase that READS via ESO.

**Empirically verified** with two test ExternalSecrets on the live cluster:
- Key `platform/linkerd/test1` + data at `etradie/data/platform/linkerd/test1` → SecretSynced/True ✓
- Key `etradie/platform/linkerd/test2` + data at `etradie/data/etradie/platform/linkerd/test2` → SecretSyncedError / Secret does not exist ✗

The second case is exactly what every chart was experiencing. The first case is what we need.

PROGRESS.md gotcha #9 from the previous Phase 8 entry — which documented the doubled-prefix as intentional — was **incorrect**. A separate correction commit is TODO.

### What was fixed in this session

#### 1. ArgoCD pre-flight commits (in order)

| Commit | Subject | What it fixes |
|---|---|---|
| `40676e7c` | remove stale identityTrustAnchorsPEM parameter sentinel | Helm `--set` override would have clobbered the values-file PEM at sync time; identity controller would fail with invalid issuer cert chain |
| `c0fb63d8` | add argocd namespace to etradie AppProject destinations | root-app places Application children into `argocd` ns; project must whitelist that destination |
| `42cb67e9` | fix Linkerd Helm repoURL to `/stable` | Upstream restructured the chart index; bare `https://helm.linkerd.io/index.yaml` returns 404 |

#### 2. Terraform fix — commit `3410f13e`

Dropped the redundant `etradie/` prefix from the `name` attribute of every `vault_kv_secret_v2` resource in `infrastructure/cluster/vault-paths/main.tf`. `mount` stays `etradie`. After this commit a fresh terraform apply will write secrets at the correct (single-prefix) location:

```
services/edge-ingress/${env}/tls
services/edge-ingress/${env}/cloudflare/aop_ca
services/edge-ingress/${env}/cloudflare/tunnel
services/edge-ingress/${env}/maxmind
services/gateway/${env}
services/engine/${env}
services/execution/${env}
services/management/${env}
services/billing/${env}
data-layer/postgres/${env}
data-layer/redis/${env}
data-layer/chromadb/${env}
platform/linkerd/${env}    # always /production even on staging
services/mt-node/${env}
```

**Chart `vaultPath` values keep their `etradie/services/...` form — intentional.** ESO's `buildPath` silently strips the leading `etradie/` segment when it matches the CSS path; chart keys `etradie/services/engine/staging` and `services/engine/staging` are functionally identical at resolution time. A separate cosmetic cleanup PR may drop the redundant prefix from chart values later; not a blocker.

**mt-node-tenant subsystem — NO CHANGE NEEDED.** Single-prefix paths throughout (`tenants/mt-node/<sa>`) on the same mount; not affected by the terraform fix.

#### 3. Live Vault data migration (executed via Vault HTTP API)

For each of the 14 Phase-8 secrets at the doubled-prefix path, read the JSON payload, write it to the corrected single-prefix path via Vault's `POST /v1/etradie/data/<dst>` endpoint, then byte-verify by sha256 comparison of jq-sorted `.data.data`.

Why HTTP API instead of `vault kv put`: the CLI's flag parser rejects `-` as a value sentinel + the placeholder string contained leading hyphens, and the doubled-jq-escape needed to feed `key=value` pairs hit a brick wall in nested kubectl exec. The HTTP API takes a single JSON body — no quoting issues.

**14/14 paths migrated. Phase B verification: 14/14 byte-perfect.** Doubled-prefix originals NOT deleted (safety net until §10.5 succeeded; can be cleaned in a later commit).

#### 4. ESO + ClusterSecretStore + token_reviewer_jwt repairs

Mid-debug, three Vault-auth issues surfaced and were repaired in place:

- **`etradie-eso` policy:** updated to grant `read,list` on `etradie/data/*` + `etradie/metadata/*` paths.
- **`vault-auth` SA `token_reviewer_jwt`:** the original JWT bound to Vault's `kubernetes/config` had expired. Minted a new 24h TTL token. **TODO before Phase 10 closeout:** mint a non-expiring legacy Secret-bound token (the enterprise pattern). Otherwise ESO will start 403'ing again at the 24h mark.
- **ClusterSecretStore `vault-backend`:** deleted and recreated mid-session. Current spec: `path: etradie`, `version: v2`, k8s auth role `etradie-eso`. Status: `Valid`.
- **ESO controller restarted** to clear cached path-resolution state.

#### 5. AppProject whitelist commit `af9a1536`

Added `batch/CronJob` to the `linkerd` AppProject's `namespaceResourceWhitelist`. The Linkerd control-plane chart renders a `CronJob linkerd-heartbeat` by default. Without this entry, ArgoCD refused to create the CronJob and aborted the entire wave; every other resource was left OutOfSync/Missing as a downstream effect.

With the whitelist updated, the chart renders unchanged from upstream defaults.

#### 6. Direct kubectl apply of `deployments/argocd/linkerd-appproject.yaml`

After the `af9a1536` commit landed on GitHub, a root-app sync reported `Synced` but the `linkerd` AppProject on the live cluster STILL did not contain `batch/CronJob`. Diagnosis: root-app's source path is `deployments/argocd/children`, but the AppProject files live at `deployments/argocd/` (one directory up). Root-app's `directory.recurse: true` only reconciles files UNDER `children/`; the AppProjects are out of scope.

The fix was a direct `kubectl apply -f deployments/argocd/linkerd-appproject.yaml`. The AppProject is Git-canonical but **not GitOps-managed** in the current repo layout. New PROGRESS gotcha.

#### 7. §10.5 manual sync — waves -6, -5, -4 in order

After all the above fixes:

```
§10.5.1 argocd app sync linkerd-identity-production       → OutOfSync/Healthy
§10.5.2 argocd app sync linkerd-crds-production           → Synced/Healthy (7 CRDs)
§10.5.3 argocd app sync linkerd-control-plane-production  → OutOfSync/Healthy
```

Final pod state in `linkerd` namespace:

```
linkerd-destination-79865f5b4-qd7b9       4/4 Running
linkerd-identity-759f6d955-jssdj          2/2 Running
linkerd-proxy-injector-7c87f4fc86-5lzzl   2/2 Running
```

### About the `OutOfSync / Healthy` lines on the linkerd-* Apps

Two of the three Linkerd Applications show `OutOfSync` even though they are Healthy. These are **expected, by-design** behaviors and NOT blockers:

1. **`linkerd-identity-production: OutOfSync / Healthy`.** The `ExternalSecret linkerd-identity-issuer` is server-side-applied by ESO using its own field-manager. ArgoCD sees the field-manager delta vs the chart-rendered spec and reports OutOfSync. The K8s Secret the ExternalSecret manages is correctly populated. No action needed.
2. **`linkerd-control-plane-production: OutOfSync / Healthy`.** The 3 webhook TLS Secrets (`linkerd-policy-validator-k8s-tls`, `linkerd-proxy-injector-k8s-tls`, `linkerd-sp-validator-k8s-tls`) and the 2 Deployments that consume them are **mutated at runtime** by Linkerd's identity controller (rotates the webhook certs on a schedule). ArgoCD sees the runtime drift vs the chart template and reports OutOfSync. Leave as-is.

### What is NOT yet diagnosed (the next session's first task)

10 staging Applications show `OutOfSync / Missing`:

```
data-layer-staging         OutOfSync  Missing  Auto-Prune  etradie-system
engine-staging             OutOfSync  Missing  Auto-Prune  etradie-system
gateway-staging            OutOfSync  Missing  Auto-Prune  etradie-system
execution-staging          OutOfSync  Missing  Auto-Prune  etradie-system
management-staging         OutOfSync  Missing  Auto-Prune  etradie-system
billing-staging            OutOfSync  Missing  Auto-Prune  etradie-system
mt-node-staging            OutOfSync  Healthy  Auto-Prune  etradie-system
edge-ingress-staging       OutOfSync  Missing  Auto-Prune  edge-ingress-system
envoy-staging              OutOfSync  Missing  Auto-Prune  envoy-system
observability-logs-staging OutOfSync  Missing  Auto-Prune  etradie-observability
```

All namespaces empty (`No resources found`). Auto-sync has not fired.

**`mt-node-staging` shows `Healthy`** because `mtConnection.enabled=false` in staging means the chart renders no resources — confirms this is an auto-sync trigger issue, not a chart-render issue.

Most likely causes (in priority order):

1. **Backoff state from earlier failed reconciles**. The staging Applications were created by root-app during §10.3 BEFORE the mesh was up. Their first reconcile attempts likely failed (pods would have been Pending waiting for proxy injector that didn't exist). ArgoCD entered backoff and has not retried in the 4 minutes since the mesh came up.
2. **Another AppProject whitelist gap** — this time in the `etradie` AppProject (staging apps belong to `etradie`, not `linkerd`). Possible missing kinds: `NetworkPolicy`, `PodDisruptionBudget`, `Job`, `CronJob`, `HorizontalPodAutoscaler`, etc.
3. **Helm template render error** on one of the values overlays.

**Diagnostic plan for next session:**

```bash
# 1. Get the actual reason from data-layer-staging (wave -1, others depend on it)
argocd app get data-layer-staging --grpc-web
kubectl -n argocd get application data-layer-staging \
  -o jsonpath='{.status.operationState}' | jq .

# 2. Check controller logs for staging-related sync errors
kubectl -n argocd logs statefulset/argocd-application-controller \
  --tail=500 | grep -iE 'staging|data-layer|error|fail'

# 3. Confirm etradie AppProject syncWindows don't block staging
kubectl -n argocd get appproject etradie \
  -o jsonpath='{.spec.syncWindows}' | jq .

# 4. After fixing, refresh all 10 staging apps:
for app in data-layer engine gateway execution management billing \
           mt-node edge-ingress envoy observability-logs; do
  kubectl -n argocd annotate application ${app}-staging \
    argocd.argoproj.io/refresh=hard --overwrite
done
sleep 30
argocd app list --grpc-web | grep staging
```

Do NOT issue a blind hard-refresh-everything before knowing the root cause; a true permission failure stays a failure after refresh, and we lose signal on what was wrong.

### Phase 10 (continuation) operator gotchas

**23. ESO `buildPath` silently strips the leading mount-name segment.** This is the load-bearing fact behind the whole Phase 10 debug arc. If the ClusterSecretStore has `path: <X>` AND the ExternalSecret key starts with `<X>/`, ESO strips the `<X>/` prefix and prepends `<X>/data/`. Verified in external-secrets v0.10.4 source at `pkg/provider/vault/client_get.go::buildPath()`. PROGRESS gotcha #9 (Phase 8 entry) is incorrect and needs an in-place correction in a follow-up commit.

**24. Root-app source path is `deployments/argocd/children`, NOT `deployments/argocd`.** AppProject files (`appproject.yaml`, `linkerd-appproject.yaml`) live one directory up, OUTSIDE root-app's scope. AppProject changes require direct `kubectl apply -f`. Long-term TODO; for this deploy use the direct apply.

**25. ArgoCD port-forward dies silently across WSL sleep / focus changes.** Symptoms: `argocd <any-command>` returns `connection reset by peer` or `connection refused`. Fix: reopen the `kubectl -n argocd port-forward svc/argocd-server 8080:443` command in a dedicated, never-closed terminal. Each reopen also invalidates the argocd CLI's auth token; re-login with `argocd login 127.0.0.1:8080 ...` after each reopen.

**26. ArgoCD `app sync` operations stay `Phase: Running` even after the CLI disconnects.** A killed port-forward mid-sync leaves the server-side operation in flight; subsequent sync commands fail with `another operation is already in progress`. Fix: `argocd app terminate-op <app-name>` before retrying.

**27. Linkerd-heartbeat CronJob.** The Linkerd control-plane Helm chart renders a `batch/CronJob linkerd-heartbeat` by default. Daily anonymous telemetry to api.linkerd.io. NOT load-bearing; cannot reach the upstream from inside ufw egress posture. Kept as upstream-default for shape-parity. AppProject must whitelist `batch/CronJob` for the chart to render (commit `af9a1536`).

**28. ESO `token_reviewer_jwt` lifetime trap.** ESO authenticates to Vault as the `vault-auth` ServiceAccount using a JWT issued from that SA's token. Modern Kubernetes (>=1.24) issues ServiceAccount tokens with bounded TTLs by default; long-running ESO controllers will start 403'ing once the JWT expires. The staging deploy hit this mid-session and minted a 24h TTL token as a stopgap. **Enterprise-grade fix:** mint a non-expiring legacy Secret-bound token for the `vault-auth` SA. TODO before Phase 10 declared closed.

**29. Vault audit log left enabled at `/tmp/vault-audit.log`.** Enabled mid-debug to trace ESO's API calls; accumulates fast. Disable at start of next session:
```bash
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault audit disable file
```

**30. Watch Health column, not just Sync column.** The `OutOfSync / Healthy` rows on `linkerd-*` Applications are by-design; the `OutOfSync / Missing` rows on staging children are NOT. Auto-sync is aggressive enough to fix a transient backoff; a true defect stays as `Missing` after a `--refresh hard` annotation.

**32. The workstation orchestrates; the VPS runs everything.** Every `kubectl apply`, `helm install`, `argocd app sync`, and `terraform apply` on the workstation is an HTTPS request through the SSH tunnel to the K3s API server ON THE VPS. The K3s API then schedules pods ON THE VPS, allocates PVCs from the VPS's NVMe, touches no resource on the workstation. The workstation holds only: the git checkout, the kubeconfig, the Vault unseal-key file, the GHCR PATs, the Cloudflare tunnel token, the Cloudflare Origin Certs, the operator credential safety net (`~/etradie-<env>-creds.txt`), the mesh CA bundle, and the foreground `ssh -N -L` tunnel + `kubectl port-forward` processes. Everything else — every pod, every PVC, every Vault KV entry, every container image, every log — lives on the VPS. Implications: laptop death mid-deploy does not affect the cluster (just reopen the tunnel from a fresh workstation); BUDGET.md capacity numbers are VPS resources, the workstation is irrelevant to the ledger; the security boundary is the SSH key + the small set of 0600 files on the workstation, not the workstation itself. See README "Architecture — where everything actually runs" for the full topology + request-flow walkthrough.

### Vault state at end of this session

All 14 KV paths exist at TWO locations: doubled (legacy, kept for safety) and single-prefix (canonical, what ESO + every chart reads). A future cleanup commit removes the doubled-prefix entries via `vault kv metadata delete -mount=etradie etradie/<rest>` once all charts have rolled out without incident.

### Session-resume recovery — read this if the session ended

1. **Tunnel** (dedicated terminal, leave open):
   ```bash
   ssh-add ~/.ssh/id_ed25519  # once per WSL boot
   ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173
   ```
2. **ArgoCD port-forward** (separate dedicated terminal, leave open):
   ```bash
   export KUBECONFIG=~/.kube/etradie-contabo.yaml
   kubectl -n argocd port-forward svc/argocd-server 8080:443
   ```
3. **Working terminal env**:
   ```bash
   export KUBECONFIG=~/.kube/etradie-contabo.yaml
   ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
   ```
4. **Argocd CLI login**:
   ```bash
   ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
     -o jsonpath='{.data.password}' | base64 -d)
   argocd login 127.0.0.1:8080 --username admin \
     --password "$ADMIN_ARGO_PWD" --insecure
   unset ADMIN_ARGO_PWD
   ```
5. **Sanity** — all of these should be true:
   - `kubectl -n linkerd get pods` → 3 control-plane pods all Running (2/2 or 4/4)
   - `kubectl -n linkerd get secret linkerd-identity-issuer` → exists, type `kubernetes.io/tls`, DATA 2
   - `kubectl -n argocd get appproject linkerd -o jsonpath='{.spec.namespaceResourceWhitelist}' | jq` → contains `{ group: batch, kind: CronJob }`
   - `kubectl exec -n vault vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" vault kv get -mount=etradie services/engine/staging` → returns secret data (single-prefix path)
   - `argocd app list --grpc-web | grep linkerd` → 3 apps, all `Healthy` (mix of Synced and OutOfSync, both expected)
   - `argocd app list --grpc-web | grep staging` → 10 apps, all `OutOfSync/Missing` (except `mt-node-staging` → `OutOfSync/Healthy`)
6. **First action**: run the diagnostic block from "What is NOT yet diagnosed" above — `argocd app get data-layer-staging` to surface the real reason staging children are not rendering. Then apply the right fix once for all 10.

### Phase 10 closeout TODOs (do these BEFORE flipping the status board to ✅)

1. Diagnose + fix the 10 staging children `OutOfSync/Missing` state.
2. Mint a non-expiring legacy Secret-bound token for `vault-auth` SA and replace the 24h TTL `token_reviewer_jwt` on Vault's `kubernetes/config`.
3. Disable the Vault audit log at `/tmp/vault-audit.log`.
4. PROGRESS.md gotcha #9 (Phase 8 entry) correction commit ("the doubled-prefix was NOT intentional; here is the actual ESO `buildPath` behavior").
5. Once all staging Applications report `Synced/Healthy`, delete the 14 doubled-prefix Vault entries (`vault kv metadata delete -mount=etradie etradie/<rest>` × 14).
6. Optional cosmetic: drop the leading `etradie/` prefix from chart `vaultPath` values across the helm/ tree. No functional effect; pure clarity.

### Correction 2026-06-15 — actual root cause of the 10 staging children `OutOfSync/Missing` state

The "Most likely causes" list above (backoff, AppProject whitelist gap, Helm render error) was written BEFORE the codebase audit and was wrong on all three counts. Audit of `deployments/argocd/appproject.yaml`, `deployments/argocd/children/*-staging.yaml`, every `helm/*/templates/servicemonitor.yaml`, every `helm/*/templates/prometheusrule.yaml`, every `helm/*/values-staging.yaml`, and `BUDGET.md` Table 2B established the verified root cause below. The speculation above is left in place (NOT deleted) so the PROGRESS.md audit trail of "what we believed at the time" stays intact, but it is SUPERSEDED by this section.

#### What is verified now

1. **The `etradie` AppProject whitelist is complete.** `deployments/argocd/appproject.yaml::spec.namespaceResourceWhitelist` already includes `monitoring.coreos.com/{ServiceMonitor,PodMonitor,PrometheusRule}`, `batch/{CronJob,Job}`, `autoscaling/HorizontalPodAutoscaler`, `policy/PodDisruptionBudget`, `networking.k8s.io/NetworkPolicy`, `snapshot.storage.k8s.io/VolumeSnapshot`, `policy.linkerd.io/*`, `external-secrets.io/{ExternalSecret,SecretStore}`, `rbac.authorization.k8s.io/{Role,RoleBinding}`, `apps/{Deployment,StatefulSet,DaemonSet}`, and every other namespace-scoped kind any staging chart ships. **There is no whitelist gap.** Hypothesis #2 above is wrong.
2. **Helm render succeeds; the failure is at server-side-apply dry-run on the cluster.** ArgoCD's repo-server pod renders every chart cleanly (the chart's template-render guards do not fire); the controller then submits the rendered objects to the API server with `ServerSideApply=true` + `ApplyOutOfSyncOnly=true`, and the API server rejects with `the server could not find the requested resource` for `monitoring.coreos.com/ServiceMonitor` and `monitoring.coreos.com/PrometheusRule` because those CRDs do not exist on the cluster. Hypothesis #3 (Helm render error) is wrong.
3. **`--refresh hard` would not have fixed it.** Hard-refresh clears the backoff timer but the underlying dry-run error returns immediately on the next reconcile; the staging children would have flipped back to `OutOfSync/Missing` within seconds. Hypothesis #1 is wrong.
4. **The actual cause: kube-prometheus-stack was never installed, and every staging chart ships `ServiceMonitor`/`PrometheusRule` objects unconditionally.** Verified per chart:
   - `helm/data-layer/values.yaml` defaults `serviceMonitor.enabled: true` and `prometheusRule.enabled: true`. `helm/data-layer/values-staging.yaml` does NOT override either. Templates `helm/data-layer/templates/servicemonitor.yaml` (postgres + redis) and `helm/data-layer/templates/prometheusrule.yaml` (data-layer rule group) therefore render on staging.
   - `helm/engine/values-staging.yaml::serviceMonitor.enabled: true` (explicit). `helm/engine/templates/servicemonitor.yaml` + `helm/engine/templates/prometheusrule.yaml` render.
   - `helm/gateway/values-staging.yaml::serviceMonitor.enabled: true` (explicit). Renders.
   - `helm/execution/values-staging.yaml::serviceMonitor.enabled: true`, `helm/management/values-staging.yaml::serviceMonitor.enabled: true`, `helm/billing/values-staging.yaml::serviceMonitor.enabled: true` (explicit on all three). Render.
   - `helm/edge-ingress/values-staging.yaml::serviceMonitor.{interval,scrapeTimeout,labels}` set (no `enabled` override; base defaults to enabled). Renders.
   - `helm/envoy/values-staging.yaml::serviceMonitor.{interval,scrapeTimeout,labels}` set (no `enabled` override). Renders.
   - `helm/observability-logs/templates/servicemonitor.yaml` + `otel-collector-servicemonitor.yaml` + `tracing-prometheusrule.yaml` render.
   - `helm/mt-node/` ships NO `servicemonitor.yaml` / `prometheusrule.yaml` templates — confirmed by the templates listing. This is independent confirmation that the diagnosis is correct: `mt-node-staging` is the ONLY staging child reporting `Healthy` in the previous PROGRESS entry because (a) `mtConnection.enabled=false` in staging means the chart renders nothing AND (b) it ships no Prometheus Operator objects anyway, so it would not have hit the CRD-not-found wall even if it had rendered.
5. **The cluster has no `monitoring.coreos.com` CRDs.** No `kube-prometheus-stack` Application exists under `deployments/argocd/children/`. No prometheus-operator install has been done out-of-band. The CRDs the staging charts assume (the `ServiceMonitor` / `PrometheusRule` schemas) therefore do not exist, and every staging child fails ArgoCD's `ServerSideApply` dry-run on those objects before the namespace / Services / StatefulSets / ConfigMaps can be applied.
6. **The classification mismatch between README.md Phase 15 and BUDGET.md Table 2B is what hid this during Phase 10.** README.md Phase 15 bullet 4 reads *"Monitoring (optional): install kube-prometheus-stack into `monitoring`..."* — framed as an optional post-deploy operational note. BUDGET.md Table 2B (which the runbook explicitly states it implements) carries five kube-prometheus-stack rows (`Prometheus 200m/768Mi`, `Grafana 100m/128Mi`, `kube-state-metrics 50m/64Mi`, `node-exporter 50m/64Mi`, `prometheus-operator 50m/96Mi`) all marked `ON` in the staging floor (total ~0.45 CPU / ~1.1Gi requests, already counted in the Table 2B staging floor of ≈ 4.1 CPU / ≈ 7.3Gi). It is not optional in the implementation; it is part of the staging floor. The README's "optional" framing made the previous session skip past it during Phase 10. A sibling README commit moves the install into a new Phase 10.6 sub-step (REQUIRED before staging-children sync per Table 2B).

#### Updated TODO order for Phase 10 closeout

Replaces the TODO list in the previous subsection. Items 1–6 below are the canonical Phase 10 closeout sequence; do them in order.

1. Install kube-prometheus-stack per the new README Phase 10.6 — sized to BUDGET.md Table 2B's staging row (`Prometheus 200m/768Mi`, `Grafana 100m/128Mi`, `kube-state-metrics 50m/64Mi`, `node-exporter 50m/64Mi`, `prometheus-operator 50m/96Mi`, 20Gi PVC, 7d retention). Delivered GitOps-style as a new ArgoCD Application under `deployments/argocd/children/` at an early sync wave (before -2) so its CRDs land before any staging child reaches dry-run.
2. After CRDs are present, the existing staging children should auto-sync on their next reconcile (default 3 minutes) because their `automated.{prune:true, selfHeal:true}` config keeps trying. To force the reconcile sooner: `argocd app sync data-layer-staging` (wave -2) then watch the rest of the wave fire in order.
3. Confirm: `argocd app list --grpc-web | grep staging` reports `Synced/Healthy` (or `Synced/Progressing` while pods come up). `kubectl -n etradie-system get pods` shows the data-layer StatefulSets Running 2/2 (postgres + Linkerd proxy sidecar) etc.
4. Mint a non-expiring legacy Secret-bound token for `vault-auth` SA and replace the 24h TTL `token_reviewer_jwt` on Vault's `kubernetes/config` (was item 2 in the previous TODO list).
5. Disable the Vault audit log at `/tmp/vault-audit.log` (was item 3).
6. PROGRESS.md gotcha #9 (Phase 8 entry) correction commit — "the doubled-prefix was NOT intentional; here is the actual ESO `buildPath` behavior" (was item 4).
7. Once all staging Applications report `Synced/Healthy`, delete the 14 doubled-prefix Vault entries (was item 5).
8. Optional cosmetic: drop the leading `etradie/` prefix from chart `vaultPath` values across the `helm/` tree (was item 6).

#### Phase 10 (continuation) operator gotchas — addition

**31. README.md Phase 15 and BUDGET.md Table 2B disagree about whether kube-prometheus-stack is optional, and BUDGET.md wins.** README Phase 15 bullet 4 calls it *"Monitoring (optional)"*; BUDGET.md Table 2B has all five kube-prometheus-stack rows (`Prometheus 200m/768Mi`, `Grafana 100m/128Mi`, `kube-state-metrics 50m/64Mi`, `node-exporter 50m/64Mi`, `prometheus-operator 50m/96Mi`) marked `ON` in the staging floor (~0.45 CPU / ~1.1Gi requests counted in the ≈ 4.1 CPU / ≈ 7.3Gi staging floor), and every staging chart ships `ServiceMonitor`/`PrometheusRule` objects unconditionally. The implementation is BUDGET.md Table 2B; the README's "optional" framing is a misclassification that hid the prerequisite during Phase 10. A sibling README commit moves the kube-prometheus-stack install into a new Phase 10.6 sub-step (REQUIRED before staging-children sync) and rewrites the Phase 15 bullet to talk about post-install operational notes rather than the install itself. Future operators: trust BUDGET.md Table 2B over README.md Phase 15 if they ever disagree again.

### Phase 10.6 — staging children chart fixes (post-monitoring-stack-staging deploy)

After the monitoring stack came up `Synced/Healthy` and the
staging children's CRD-not-found blocker cleared, the 10 staging
Applications synced but **7 of them entered `Synced/Degraded`**.
Diagnosing the failures via pod status + Deployment conditions +
namespace events established three independent chart defects, all
pre-existing and unrelated to the monitoring-stack work. Each fix
landed as its own commit so any regression is independently
bisectable.

#### Fix 1 — init container resources below the etradie-system LimitRange floor

**Symptom.** The `execution`, `management`, `billing` Deployments
reported `ReplicaFailure` with:

```
pods "etradie-execution-..." is forbidden:
  [minimum cpu usage per Container is 50m, but request is 10m,
   minimum memory usage per Container is 64Mi, but request is 16Mi]
```

0 replicas ever created. `etradie-envoy` had the same shape but
rejected on the `linkerd-init` container (Linkerd injection adds
it at admission time).

**Root cause.** Every chart's `wait-for-deps` init container had
`resources.requests: { cpu: 10m, memory: 16Mi }` — below the
`etradie-system` namespace LimitRange minimum (`cpu: 50m, memory:
64Mi`, owned by `helm/data-layer/values.yaml::limitRange.container.
min`). The LimitRange admission plugin rejected every pod creation.

Why engine + gateway pods existed despite the same defect: they
were created during the earlier `data-layer` reconcile BEFORE the
LimitRange was being enforced at admission. They are running on
borrowed time — the next pod recreate (rollout, node drain, image
bump, HPA scale) would have failed admission too. The fix unblocks
execution/management/billing AND closes the latent failure window
for engine/gateway.

**Fix.** Raise `initContainer.resources.requests` to `50m / 64Mi`
and limits to `100m / 128Mi` in all 5 chart `values.yaml` files
(engine, gateway, execution, management, billing). The init
container runs to completion in seconds; the requests are released
back to the namespace quota and the steady-state main-container
sizing per BUDGET.md Table 2B is unaffected.

#### Fix 2 — chromadb crash loop on read-only root filesystem

**Symptom.** `chromadb-0` was in `1/2 CrashLoopBackOff` (the
linkerd-proxy sidecar up, the chromadb container itself crashing).
Log showed:

```
OSError: [Errno 30] Read-only file system: '/chroma/chroma.log'
ValueError: Unable to configure handler 'file'
```

Engine's `wait-for-deps` init container blocked indefinitely
waiting for `chromadb.etradie-system.svc:8000` to come up; gateway
blocked on engine in turn; the whole etradie-system app tier
stuck behind chromadb.

**Root cause.** ChromaDB 0.5.20's image bakes a uvicorn
`log_config.yml` that opens `/chroma/chroma.log` via FileHandler
at startup. The chart correctly set `readOnlyRootFilesystem: true`
(Tier 11 hardening) and mounted the data PVC at `/chroma/chroma`
(subdirectory). The `/chroma` parent stayed on the read-only root
filesystem, so the log-file open failed.

**Fix.** Move the PVC mount point UP one level: mount the data PVC
at `/chroma` (parent) and store persistent data in `/chroma/index`
(subdir). The chromadb log file at `/chroma/chroma.log` then lands
on the writable PVC. `readOnlyRootFilesystem: true` posture is
unchanged.

Data migration: not needed on staging (chromadb never reached
Ready, the existing PVC is empty). Not needed on production
either because the chart change lands BEFORE production ever sees
chromadb data. A future-self-deploy that already has chromadb data
under `/chroma/chroma/` from a pre-fix install needs a one-time
migration (documented in commit body).

#### Fix 3 — envoy namespace PSS enforce=restricted blocks Linkerd proxy-init

**Symptom.** `envoy-system` namespace had 0 pods. Events showed
repeated rejections:

```
pods "etradie-envoy-..." is forbidden: violates PodSecurity
  "restricted:latest": unrestricted capabilities (container
  "linkerd-init" must not include "NET_ADMIN", "NET_RAW" in
  securityContext.capabilities.add)
```

**Root cause.** The envoy chart's `namespace.yaml` template applied
`pod-security.kubernetes.io/enforce=restricted` unconditionally.
Linkerd's injector mutates every meshed pod at admission to add a
`proxy-init` init container that needs NET_ADMIN + NET_RAW to
install iptables rules. Restricted PSS forbids those capabilities;
admission rejected every envoy pod.

**Fix.** Drop the `enforce` label from the envoy namespace; keep
`warn` + `audit` only. Same posture as
`helm/data-layer/templates/namespace.yaml`. Audit-log trail still
flags restricted-tier violations; nothing is silently allowed; the
Linkerd-incompatible enforce-side rejection no longer fires. The
trade-off (Linkerd in restricted-tier namespaces requires relaxing
enforce) is documented and identical to every other meshed
namespace on this platform.

#### Phase 10.6 (continuation) operator gotchas

**33. Init container resources MUST meet the namespace LimitRange floor.** The `etradie-system` namespace LimitRange (owned by `helm/data-layer/values.yaml::limitRange.container.min`) sets a minimum of `cpu: 50m, memory: 64Mi` per container. Init containers running in this namespace MUST request at least that. The pre-fix value of `cpu: 10m / memory: 16Mi` shipped in every service chart's `initContainer.resources.requests` was rejected by LimitRange admission at pod creation time — BUT pods created before the LimitRange was actively enforced continued running on borrowed time (engine, gateway), masking the defect until a later chart (execution, management, billing) triggered a fresh admission. Lesson: every container request — init included — must meet the floor of every namespace it can possibly run in. CI render-check should grep init container requests vs the LimitRange in lockstep.

**34. ChromaDB 0.5.20 hardcoded log file vs readOnlyRootFilesystem.** ChromaDB's image bakes a uvicorn FileHandler pointing at `/chroma/chroma.log` and the path is NOT env-templated. With `readOnlyRootFilesystem: true` and the data PVC mounted at `/chroma/chroma` (a subdirectory), `/chroma` itself is read-only and the log open fails. Fix is to mount the PVC at `/chroma` (parent) and move PERSIST_DIRECTORY to `/chroma/index` so the log file and the data live on the same writable PVC. Watch for similar patterns in other charts that pin `readOnlyRootFilesystem: true` against an image whose log/cache path is not env-configurable. Future ChromaDB upgrades may expose a log-path env knob; if so, prefer that over the subdirectory remount.

**35. Linkerd-injected pods cannot run under PSS `enforce=restricted`.** Linkerd's injector adds a `proxy-init` init container that needs NET_ADMIN + NET_RAW capabilities; PSS restricted-tier forbids those. The compatible posture is PSS `warn` + `audit` only (no `enforce` label) — the audit trail still surfaces any restricted-tier violation but admission does not reject the pod. Every meshed namespace on this platform follows this pattern: `data-layer/namespace.yaml`, `envoy/namespace.yaml` (after this fix), and any future meshed namespace. The PodSecurity admission plugin remains enabled cluster-wide (K3s apiserver flag at Phase 2.1); only individual namespaces opt out of enforce. If a future Linkerd release supports running entirely without an init container (native sidecar without iptables injection), this gotcha could be revisited.

### Outstanding non-blocking items surfaced during Phase 10.6

**CI test failure on `tests/api/endpoints.py`.** Four tests fail with the same shape:

```
assert '/internal/ta/analyze' in {'', '/docs', '/docs/oauth2-redirect',
                                   '/metrics', '/openapi.json'}
```

The test fixture builds a FastAPI app where the registered-paths set has only 5 entries — none of the application routers (`/internal/ta/analyze`, `/internal/broker/account_info`, `/health`, `/api/analysis/latest`) are present. This is a test-fixture defect, not application code; the live engine pod registers all routes correctly. Failure does NOT block this Phase 10.6 deploy because ArgoCD reads chart manifests + images directly from the repo + GHCR; CI gate state is not consulted. Add to a separate engineering ticket; do NOT block Phase 10 closeout on it. Likely cause: a missing router `include_router(...)` in the test fixture's `create_app()` factory, or a config-loading exception silently swallowed during test setup.

---

## Phase 10.6 in-flight checkpoint — 2026-06-15 (session-resume entry point)

**Read this section first if you are picking up Phase 10 mid-flight.** It supersedes every prior "Session-resume recovery" block in the file because the cluster state has moved on materially since each of them was written.

### Status board correction

| Phase | Title | Status at this checkpoint |
|---|---|---|
| 0–9 | (everything up to Phase 9) | ✅ DONE |
| 10 | ArgoCD + AppProjects + root app | 🟡 in progress — monitoring stack Healthy + 9 staging children syncing; 2 chart-level defects under investigation |
| 10.6 | Install kube-prometheus-stack | ✅ DONE — `monitoring-stack-staging` Synced/Healthy; CoreDNS scrape Up; CRDs present |
| 11–15 | (after Phase 10) | ⏸ pending |

Do NOT flip Phase 10 to ✅ in `## Status board` at the top of this file until both open defects (§ below) are resolved AND all 11 staging Applications report `Synced/Healthy`. As of this checkpoint that has NOT happened.

### What landed in this session (in commit order, oldest first)

| Short SHA | Title | What it does |
|---|---|---|
| `f93bdf4f` | PROGRESS.md — Phase 10 continuation 2026-06-15 | Records the Vault path defect + migration + Linkerd mesh up arc |
| `f632ec41` | PROGRESS.md — correct Phase 10 staging-children root cause | Supersedes the wrong hypotheses with the real cause (kube-prometheus-stack missing) |
| `024bada1` | README.md — move kube-prometheus-stack into Phase 10.6 | Reclassifies monitoring from "optional Phase 15" to "REQUIRED Phase 10.6" per BUDGET.md Table 2B |
| `a71020af` | Add dedicated `monitoring` AppProject | New AppProject scoped to kube-prometheus-stack |
| `8b949bc8` | Clean inline comments in monitoring AppProject | Strip doc cross-refs from the YAML |
| `c7483f7f` | Add staging kube-prometheus-stack values overlay + Application | `helm/monitoring-stack/values-staging.yaml` + `deployments/argocd/children/monitoring-stack-staging.yaml` |
| `b049d371` | Add production overlay + Application | `helm/monitoring-stack/values-production.yaml` + `deployments/argocd/children/monitoring-stack-production.yaml` |
| `95bd9c86` | Fix AppProject whitelist + tighten ignoreDifferences | Add `batch/Job`+`batch/CronJob` to monitoring AppProject; remove over-broad `ignoreDifferences` |
| `3ee834e7` | Disable chart's CoreDNS rendering | `coreDns.enabled: false` (the chart's facade Service in `kube-system` was blocked by AppProject scope) |
| `e213fa9d` | Restore CoreDNS scraping via additionalServiceMonitors | Custom ServiceMonitor in `monitoring` ns targeting K3s `kube-dns:9153` directly |
| `ba25de8d` | README.md — document workstation-vs-VPS topology | New "Architecture" subsection + PROGRESS gotcha #32 |
| `73be1e2a` | Raise init container requests across 5 service charts | `cpu: 10m → 50m`, `memory: 16Mi → 64Mi` to clear etradie-system LimitRange floor |
| `f81a646a` | chromadb writable parent dir for `/chroma/chroma.log` | PVC mount moves from `/chroma/chroma` to `/chroma`; `PERSIST_DIRECTORY` to `/chroma/index` |
| `3bc20fa7` | envoy namespace PSS warn+audit (drop enforce) | Same posture as data-layer namespace so Linkerd proxy-init can run |
| `4022660c` | PROGRESS.md — chart fixes + CI test failure TODO + gotchas #33–35 | Documents the 3 chart fixes above + the CI test failure non-blocker |

GitLab `main` and GitHub `origin/main` are both at `4022660c` at the time of this checkpoint.

### Cluster state at this checkpoint

**Healthy and Ready:**

- `monitoring-stack-staging` — `Synced/Healthy`. 5 chart components Running:
  - `kube-prometheus-stack-operator` 1/1
  - `prometheus-kube-prometheus-stack-prometheus-0` 3/3
  - `kube-prometheus-stack-grafana` 3/3
  - `kube-prometheus-stack-kube-state-metrics` 1/1
  - `kube-prometheus-stack-prometheus-node-exporter` (DaemonSet, 1/1 on the single node)
- 10 `monitoring.coreos.com` CRDs present cluster-wide.
- Prometheus scrape targets all `up`: `apiserver`, `cloudflared-metrics`, `kube-dns` (the additionalServiceMonitor for CoreDNS), `kube-prometheus-stack-operator`, `kube-prometheus-stack-prometheus` (×2), `kubelet` (×3). 8 targets total, all healthy.
- `mt-node-staging` — `OutOfSync/Healthy` (chart renders nothing because `mtConnection.enabled=false` in staging; by-design).
- `linkerd-*` Applications — all 3 Healthy; 3 control-plane pods 2/2-or-4/4 in `linkerd` namespace.
- `monitoring-stack-production` — created, `OutOfSync` (manual sync only; expected, do NOT sync on a staging-only box).

**Progressing (good — chart fixes are rolling out):**

- 6 staging children showing `OutOfSync/Progressing`: `data-layer-staging`, `engine-staging`, `gateway-staging`, `execution-staging`, `management-staging`, `billing-staging`, `observability-logs-staging`. New pods spawning under the new pod-template hashes; old pods being drained as the new ones come Ready.
- Pod state at the moment of this checkpoint:
  - `postgres-0` 3/3 Running ✅
  - `redis-0` 3/3 Running ✅
  - `chromadb-0` **1/2 CrashLoopBackOff** (DEFECT A — see below)
  - `etradie-engine-d7bd6444d-2lwp8` 0/2 Init:0/3 (new pod, waiting on chromadb)
  - `etradie-engine-5cd9b9d777-tq8cq` 0/2 Init:0/3 (old pod, will be reaped once new is Ready)
  - `etradie-gateway-bfbc5fcf8-k2lm9` 0/2 Init:0/2 (new pod, waiting on engine)
  - `etradie-gateway-7bd667b5d7-wbkcj` 0/1 Init:CrashLoopBackOff (old pod, will be reaped)
  - `etradie-execution-8576bf499-cchxl` 0/2 Init:0/2 (waiting on engine)
  - `etradie-management-5b697754d6-jngsh` 0/2 Init:0/2 (waiting on engine)
  - `etradie-billing-6bd67b7b55-qpks8` 0/1 Init:0/1 (waiting on engine)
  - In `edge-ingress-system`: `cloudflared-fb8f66bf8-mwp7z` 1/1 Running ✅ (the tunnel itself is up).

**Degraded (the 2 still-open defects):**

- `edge-ingress-staging` — `OutOfSync/Degraded`. The `edge-ingress` Deployment is degraded because `etradie-gateway` is not Ready upstream. This is a cascade of Defect A; expected to clear once chromadb is fixed. NOT a separate defect.
- `envoy-staging` — `OutOfSync/Degraded`. **Zero pods in `envoy-system`** — DEFECT B (see below).

### Open defects at this checkpoint

#### Defect A — chromadb StatefulSet pod not replaced after template change

**Symptom.** Chart commit `f81a646a` changed the chromadb StatefulSet to mount the PVC at `/chroma` (parent) instead of `/chroma/chroma` (subdir). ArgoCD synced the StatefulSet object — BUT `chromadb-0` is still the original pod, age 33 min, restart count 11+, **NOT replaced**.

**Hypothesised root cause.** Classic StatefulSet `RollingUpdate` deadlock:

1. StatefulSet `updateStrategy.type: RollingUpdate` (verified in `helm/data-layer/templates/chromadb-statefulset.yaml`).
2. Rolling update gates each pod-replace on the previous pod being Ready.
3. `chromadb-0` is in CrashLoopBackOff (NOT Ready) under the old broken spec.
4. Controller refuses to delete pod-0 because it's not Ready (would violate the rolling-update guarantee).
5. Pod stays stuck on the old spec; new mount path never applied; loop forever.

**Pre-action verification — confirm hypothesis before fixing:**

```bash
# Compare StatefulSet template vs live pod
kubectl -n etradie-system get statefulset chromadb \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="chromadb")].volumeMounts}' | jq
kubectl -n etradie-system get pod chromadb-0 \
  -o jsonpath='{.spec.containers[?(@.name=="chromadb")].volumeMounts}' | jq
kubectl -n etradie-system get pod chromadb-0 \
  -o jsonpath='{.spec.containers[?(@.name=="chromadb")].env[?(@.name=="PERSIST_DIRECTORY")]}' | jq
```

If the StatefulSet shows `mountPath: /chroma` and the pod shows `mountPath: /chroma/chroma`, hypothesis confirmed.

**Fix (verified-correct path, NOT yet executed):**

```bash
# Delete the stuck pod. StatefulSet controller will immediately
# recreate it under the NEW pod template (the one with /chroma mount).
kubectl -n etradie-system delete pod chromadb-0

# Watch the new pod come up
kubectl -n etradie-system get pod chromadb-0 -w
```

Do NOT run this without first verifying via the three `kubectl get` commands above that the StatefulSet's template actually has the new spec. If the StatefulSet itself still shows the OLD spec, then ArgoCD hasn't synced the change yet — force a sync first: `argocd app sync data-layer-staging --timeout 600`.

**Why ArgoCD didn't auto-handle this.** ArgoCD does NOT issue `kubectl delete pod` to break a StatefulSet rolling-update deadlock. That's a deliberate K8s controller behaviour, not an ArgoCD bug. The operator action is part of the StatefulSet contract.

#### Defect B — envoy-system namespace's pre-existing PSS enforce label not updated by chart re-sync

**Symptom.** Chart commit `3bc20fa7` removed the `pod-security.kubernetes.io/enforce` label from the envoy namespace template. ArgoCD shows `envoy-staging` Synced — BUT `envoy-system` namespace still has zero pods and the live namespace object likely still carries the old `enforce: restricted` label (admission still rejects Linkerd-injected pods).

**Hypothesised root cause.** ArgoCD with `ServerSideApply=true` does NOT remove labels it doesn't own. The `pod-security.kubernetes.io/enforce` label was originally applied by ArgoCD's earlier sync (with the old chart spec), so ArgoCD DOES own that label. But once the new chart template no longer renders the label, ArgoCD should patch it out… if `Prune=true` semantics apply to label keys, which they generally do NOT in server-side-apply mode.

**Pre-action verification — confirm hypothesis before fixing:**

```bash
# Is the enforce label still on the live namespace?
kubectl get namespace envoy-system -o jsonpath='{.metadata.labels}' | jq | grep -E 'pod-security'

# What's the most recent admission rejection (if any)?
kubectl -n envoy-system get events --sort-by='.lastTimestamp' | tail -10
```

If the label is still there, hypothesis confirmed.

**Fix (manual label-removal):**

```bash
# Remove the enforce label directly. Same effect as the chart template
# change (which is now applied to the chart but couldn't reach the
# live label).
kubectl label namespace envoy-system pod-security.kubernetes.io/enforce-
kubectl label namespace envoy-system pod-security.kubernetes.io/enforce-version-

# Force ArgoCD to re-sync the Deployment now that the namespace is permissive
argocd app terminate-op envoy-staging 2>/dev/null
argocd app sync envoy-staging --timeout 600
argocd app wait envoy-staging --health --timeout 600
```

If this works once, the chart template `3bc20fa7` will prevent the label from ever being re-added on a fresh namespace creation. For long-term hardening, consider adding `kubectl.kubernetes.io/last-applied-configuration` annotations that include the absence of the label, or use `argocd app sync --force` once to make ArgoCD reapply the namespace from scratch.

### Diagnostic commands to run at session start

If you are resuming this session, run these in order to determine the exact next action:

```bash
# Sanity: tunnel + argocd + login (see PROGRESS gotcha #32 for context)
kubectl get nodes
curl -sk https://127.0.0.1:8080/healthz
argocd account list 2>&1 | head -3

# Defect A verification (chromadb)
kubectl -n etradie-system get statefulset chromadb \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="chromadb")].volumeMounts}' | jq
kubectl -n etradie-system get pod chromadb-0 \
  -o jsonpath='{.spec.containers[?(@.name=="chromadb")].volumeMounts}' | jq

# Defect B verification (envoy ns PSS)
kubectl get namespace envoy-system -o jsonpath='{.metadata.labels}' | jq | grep -E 'pod-security'

# Overall pod state
kubectl get pods -A --field-selector=status.phase!=Running 2>/dev/null | grep -vE '(Completed|^NAMESPACE)' || echo "  all pods Running"

# Application state
argocd app list --grpc-web | grep -E '(staging|monitoring-stack-staging)'
```

### Phase 10.6 closeout TODOs (updated order)

Do these in sequence; each item resolves a specific blocker before the next.

1. **Defect A:** verify chromadb StatefulSet template-vs-pod drift, delete pod-0 if confirmed, watch new pod come up Healthy. After this, the cascade resolves: engine waits clear, then gateway, then execution/management/billing pods reach Ready (the new pod-template-hash pods you see Init:0/N at this checkpoint).
2. **Defect B:** verify envoy-system PSS label drift, remove enforce label manually if confirmed, force envoy-staging re-sync. Pod should come up Ready.
3. After both defects resolved, run a full `argocd app list --grpc-web | grep staging` and verify all 11 staging Applications report `Synced/Healthy`. The 3 `linkerd-*` Applications will stay `OutOfSync/Healthy` (by-design ESO drift + operator-mutated webhook caBundle drift; documented at the top of the Phase 10 continuation section).
4. **vault-auth token_reviewer_jwt** — mint a non-expiring legacy Secret-bound token and replace the 24h TTL token on Vault's `kubernetes/config`. Was item 4 in the previous closeout list, still required.
5. **Vault audit log** — disable at `/tmp/vault-audit.log` (gotcha #29). Was item 5; still required.
6. **PROGRESS gotcha #9 correction commit** — "the doubled-prefix was NOT intentional; here is the actual ESO `buildPath` behavior" (gotcha #23). Cosmetic but improves the historical accuracy of the file.
7. **Delete the 14 doubled-prefix Vault entries** once all staging Applications are `Synced/Healthy`. `vault kv metadata delete -mount=etradie etradie/<rest>` × 14.
8. **CI test failure** — fix the test-fixture defect in `tests/api/endpoints.py` (the registered-paths set has only 5 entries because the test fixture's `create_app()` factory doesn't `include_router(...)` the application routers). Separate engineering ticket; does NOT block Phase 10 closeout but blocks future CI green status. See "Outstanding non-blocking items" above for context.
9. **README + PROGRESS update** flipping the status board: Phase 10 → ✅ DONE after items 1–3 pass; Phase 11 takes over.

### Files you might want to read first if you have never deployed this platform

- `BUDGET.md` Table 2B — the capacity ledger this deploy implements.
- `docs/runbooks/README.md` "Architecture — where everything actually runs" (PROGRESS gotcha #32 cross-reference) — the workstation-vs-VPS topology.
- `docs/runbooks/README.md` Phase 10 + Phase 10.6 — the canonical procedure for everything we've been doing.
- This PROGRESS.md from Phase 10 continuation onward — the audit trail of what actually happened vs what was planned.

---

## Phase 10.6 in-flight checkpoint — 2026-06-15 (engine RAG bootstrap defect; debugging in progress)

**SUPERSEDES every prior "Phase 10.6 closeout TODO" block above for this in-flight defect.** Once this defect is resolved and engine reaches `2/2 Running` stable, the prior closeout TODOs (vault-auth token_reviewer_jwt, audit log disable, etc.) apply again.

### The exact symptom

`etradie-engine` pods enter `CrashLoopBackOff` on every restart. Engine container reaches the FastAPI lifespan startup, gets past every config and dependency-injection step, and dies at `engine.rag.services.bootstrap.bootstrap()` line 93 with:

```
asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation

The above exception was the direct cause of the following exception:

  File ".../engine/rag/services/bootstrap.py", line 58, in bootstrap
    await seed_knowledge_assets(
  File ".../engine/rag/knowledge/bootstrap/seed.py", line 19, in seed_knowledge_assets
    existing = await document_repo.get_by_doc_type(asset.doc_type)
  ...
  File ".../sqlalchemy/pool/base.py", line 896, in __connect
    self.dbapi_connection = connection = pool._invoke_creator(self)
  ...
  File ".../asyncpg/connect_utils.py", line 934, in __connect_addr
    await connected
engine.shared.exceptions.RAGBootstrapError:
    Failed to bootstrap knowledge assets: connection was closed in the middle of operation
ERROR:    Application startup failed. Exiting.
```

The error is on the very FIRST postgres connection asyncpg tries to open in the engine's outbound pool. It fires immediately (within 1 second after the engine process starts the lifespan), so it is NOT a slow query / not a long-running operation drop. Earlier in the same startup, there are also 3 attempts at `cache_connection_error errno 104 'Connection reset by peer'` against `redis.etradie-system.svc.cluster.local:6379` that all fail before the postgres attempt.

### The headline question being debugged

**Why does the engine pod's outbound Linkerd proxy fail to complete TCP+mTLS to the postgres ClusterIP (and redis ClusterIP), but the same proxy successfully reaches the chromadb ClusterIP using the same path?**

### Cluster state at this checkpoint

- ArgoCD `linkerd-control-plane-production`: Synced revision `64036054`, Healthy. The `OutOfSync` items on it (Deployment linkerd-destination, linkerd-proxy-injector; Secret linkerd-*-validator-k8s-tls; CronJob linkerd-heartbeat) are by-design Linkerd runtime drift (caBundle rotation, ESO field-manager, kube-state-metrics status fields). Documented in earlier PROGRESS gotchas (#23 / #26).
- ArgoCD `data-layer-staging`: Synced revision `64036054`, Healthy. The `OutOfSync` items (StatefulSet postgres/redis/chromadb; ExternalSecret *-credentials; ServiceMonitor postgres/redis) are by-design (Linkerd webhook-injected sidecar drift on the StatefulSet specs, ESO field-manager on ExternalSecret, kube-prometheus-stack runtime fields on ServiceMonitor).
- `linkerd-config` ConfigMap on the cluster: confirmed `outboundConnectTimeout: 10000ms` (the 1s → 10s commit landed and is live).
- postgres-0 pod: 3/3 Running 0 restarts. Annotation `config.linkerd.io/opaque-ports: "5432"` present. Pod IP at last check: `10.42.0.227`.
- redis-0 pod: 3/3 Running 0 restarts. Annotation `config.linkerd.io/opaque-ports: "6379"` present. Pod IP at last check: `10.42.0.228`.
- chromadb-0 pod: 2/2 Running 0 restarts. No opaque-ports annotation. Pod IP at last check: `10.42.0.229`.
- etradie-engine pods: CrashLoopBackOff, restart-count incrementing.
- etradie-gateway / execution / management / billing pods: also restarted; will Init-block waiting on engine.

### Proven facts (from observed evidence, NOT hypotheses)

1. **Engine pod's outbound proxy IS receiving the connection attempts.** `tcp_open_total` for `peer="src"` (the engine app → proxy hop on loopback) shows 24+ connection attempts on postgres ClusterIP 10.43.151.84:5432 and redis ClusterIP 10.43.156.25:6379.

2. **The proxy IS performing the DNAT-aware destination resolution.** `tcp_open_total` for `peer="dst"` has metric rows for postgres (target_addr=`10.42.0.227:5432`, dst_pod=`postgres-0`, tls=`true`, server_id=`default.etradie-system.serviceaccount.identity.linkerd.cluster.local`) and redis (target_addr=`10.42.0.228:6379`, same identity). So the proxy CAN identify the destination pod and IS marking the destination for mTLS.

3. **The proxy NEVER successfully completes the outbound mTLS to postgres or redis.** `tcp_open_total peer="dst"` value is `0` for both postgres and redis. After the 10s timeout fix, the value remains `0`. Chromadb same metric shows `5` (handful of successful opens).

4. **iptables NAT counter on the host kernel proves DNAT IS happening.** `KUBE-SEP-DAHTEJ5G56IQEXKC` (postgres SEP rule) pkts counter incremented to 5,643+; redis SEP rule pkts to 5+; chromadb SEP rule pkts to 12. So the engine pod's SYNs ARE being rewritten by kube-proxy from ClusterIP to pod IP.

5. **The host node CAN reach postgres pod IP directly.** From the VPS netns: `</dev/tcp/10.42.0.54/5432` returned OPEN (before the latest pod restart cycle); same for redis and chromadb. Network plumbing on the cluster level is healthy.

6. **Postgres-0's INBOUND proxy log is EMPTY** after `Certified identity`. No proxy-init errors, no policy-controller errors that affect inbound :5432. The proxy IS up and listening on `:4143` inside the netns. From inside postgres-0's network namespace, `</dev/tcp/127.0.0.1/4143` returns OK.

7. **Postgres-0's iptables (iptables-legacy backend) PROXY_INIT chains are present and correct.** `linkerd-init` container exited 0 with the full chain install in its log:
   ```
   PROXY_INIT_REDIRECT redirects all TCP to :4143
   PROXY_INIT_OUTPUT redirects all TCP from non-proxy users to :4140
   PREROUTING -> PROXY_INIT_REDIRECT
   OUTPUT -> PROXY_INIT_OUTPUT
   ```
8. **Chromadb works through the same proxy.** Engine outbound has 30+ successful HTTP 200 responses to chromadb at `chromadb.etradie-system.svc.cluster.local:8000`. mTLS is established (`tls=true`, server_id=correct). So mesh fundamentals are working for the chromadb destination but not postgres/redis.

9. **The ONLY structural difference between chromadb (works) and postgres/redis (broken) is the opaque-ports annotation.** Chromadb has no `config.linkerd.io/opaque-ports`. Postgres has `5432`. Redis has `6379`. Every other Linkerd setting is identical (native sidecar, mesh injection enabled, same control plane, same identity scheme).

10. **NetworkPolicies allow engine → postgres + redis.** Confirmed via full spec read: `postgres-network-policy` ingress allows `podSelector: app.kubernetes.io/name=etradie-engine` on port 5432; `redis-network-policy` same for 6379. `etradie-engine-network-policy` egress allows port 5432 → `app.kubernetes.io/name=postgres`, 6379 → `app.kubernetes.io/name=redis`, 8000 → `app.kubernetes.io/name=chromadb`. All three should be permitted.

11. **Linkerd control plane is healthy and stable.** 3 control-plane pods Running 53+ minutes uptime: `linkerd-destination` 4/4, `linkerd-identity` 2/2, `linkerd-proxy-injector` 2/2 (restarted to refresh ConfigMap template).

12. **The Linkerd proxy is reading the new `outboundConnectTimeout: 10000ms`.** Confirmed via `kubectl get pod postgres-0 -o jsonpath='...env...'`: `LINKERD2_PROXY_OUTBOUND_CONNECT_TIMEOUT` = `10000ms`. So the timeout change IS propagating to new pod proxies.

13. **Bumping the timeout to 10s did NOT fix the symptom.** With 10s budget the proxy log no longer shows explicit `connect timed out after 1s` warnings, but `tcp_open_total peer="dst"` for postgres+redis still stays at 0 and the engine still crashes with the same `connection was closed in the middle of operation`. So the bottleneck is NOT the 1s connect deadline — that timing fix only suppressed a symptom log; the connection is failing for a different reason.

### Hypotheses tried in this session — chronological

| # | Hypothesis | Tested by | Outcome | Disposition |
|---|---|---|---|---|
| H1 | Linkerd control-plane subscriptions are stale after multiple control-plane restarts | restart linkerd-destination/identity/proxy-injector, verify uptime | control plane stable 53m+ but engine still crashes | rejected — not a stale subscription issue |
| H2 | Postgres / redis pods need a fresh restart so their proxies re-subscribe from a clean state | `kubectl delete pod postgres-0 redis-0` and watch them come back | both came back 3/3 Running cleanly in ~11 sec each; engine still crashes after | rejected — pod restarts alone do not resolve |
| H3 | NetworkPolicies are blocking the engine → postgres/redis traffic | full ingress + egress yaml inspection + label cross-check | NetworkPolicies admit the traffic correctly | rejected — not a NetworkPolicy block |
| H4 | flannel/CNI bridge has stale ARP / FDB entries for the recreated pod IPs | check ARP cache, bridge FDB, host-to-pod-IP connect | ARP REACHABLE, FDB clean, host → pod IPs OPEN | rejected — CNI plumbing is healthy |
| H5 | Linkerd proxy-init iptables rules are missing or broken in postgres-0 netns | `nsenter` + iptables-legacy/nft chain dump | rules are present and correct in iptables-legacy backend | rejected — proxy-init succeeded |
| H6 | Postgres-0's INBOUND proxy never receives the SYN (silent drop) | nsenter ss -tln + connect to loopback 4143 from inside netns | proxy listening on 4143, accepts from loopback | inconclusive — the proxy LISTENS but its inbound metrics show 0 inbound TCP opens from engine |
| H7 | The Linkerd 2.14 default 1s outbound TCP-connect timeout is too tight for opaque-port mTLS on a cold-start single-node | bumped to 10s via `proxy.outboundConnectTimeout: 10000ms` in `deployments/linkerd/control-plane-values.yaml`; verified env var on new pod proxies = 10000ms | engine STILL crashes; chromadb still works; postgres/redis `tcp_open_total peer="dst"` still 0 | **REJECTED — the 10s commit is live and proven inert. The bottleneck is not connect-timeout-related.** |
| H8 (open) | Linkerd 2.14 has a known issue with outbound mTLS to opaque-ports on native-sidecar + single-node where the proxy resolves the destination but cannot complete the TLS handshake for some specific TLS-layer reason | not yet tested | — | **OPEN — next investigation surface** |
| H9 (open) | A field-manager / server-side-apply drift on the engine's outbound proxy environment is silently overriding the opaque-port handling, OR the engine's pod-level service-account-to-service-account TLS resolution is failing for opaque ports | not yet tested | — | **OPEN — next investigation surface** |

### Commits made in this debug session

| Short SHA | What it does | Status |
|---|---|---|
| (reverted via squash) staging-only opaque-ports drop on postgres/redis in `helm/data-layer/values-staging.yaml` | a workaround that silently disabled Tier 9 G9-1 hardening — operator (correctly) called this out as bad practice; reverted in `64036054` | not in current main |
| `64036054` | **PROPER fix attempt**: bump `proxy.outboundConnectTimeout: 1000ms → 10000ms` cluster-wide in `deployments/linkerd/control-plane-values.yaml`; revert the staging opaque-ports drop. Preserves Tier 9 G9-1 hardening. | live on cluster; **demonstrably did NOT fix the symptom** |

### What we have NOT yet tried but should

These are open investigation paths if the next operator picks up:

1. **`linkerd diagnostics` from the operator's local install.** A locally-installed `linkerd` CLI (separate from the cluster) can run `linkerd viz tap` and `linkerd diagnostics endpoints` against the proxy to see live request flow + destination resolution from outside the cluster. The platform's runbook Phase 15 documents installing `linkerd-viz` on demand.

2. **Inspect linkerd-destination's published Server policy for postgres/redis from outside the proxy.** Run from inside the linkerd-destination pod:
   ```bash
   kubectl -n linkerd exec deploy/linkerd-destination -c destination -- \
     /linkerd-destination dump-endpoint postgres.etradie-system.svc.cluster.local:5432
   ```
   Compare to what it returns for chromadb. If postgres has different/missing policy metadata, that's the cause.

3. **TLS handshake debug logs.** Enable proxy log level `trace,linkerd=trace` temporarily on the engine pod (`config.linkerd.io/proxy-log-level` annotation override). The trace logs WILL show the TLS ClientHello + ServerHello (or the lack thereof) on postgres connections.

4. **Upgrade Linkerd 2.14.10 → latest 2.14.x or to 2.16.** Multiple GitHub issues against `linkerd2-proxy` 2.210.x (the proxy version we run) reference outbound opaque-port handling issues on native-sidecar configurations. A targeted minor upgrade may resolve this without further investigation.

5. **Switch from `proxy.proxyEnableNativeSidecar: true` → false on engine pod.** Native sidecar is a 1.29+ feature; the side-effect-free alternative is the legacy init-container-style sidecar (proxy injects as init container before app). This proves whether the issue is in the native-sidecar codepath.

6. **Test engine → postgres connection FROM A SEPARATE meshed pod** to determine if the problem is engine-specific or universal. Create a temporary meshed test pod:
   ```bash
   kubectl -n etradie-system run mesh-probe \
     --image=postgres:16-alpine \
     --annotations='linkerd.io/inject=enabled,config.linkerd.io/proxy-enable-native-sidecar=true' \
     --command -- sleep 3600
   # then exec in and try psql -h postgres.etradie-system.svc.cluster.local
   ```
   If `psql` succeeds from a separate meshed pod, the issue is engine-specific. If it ALSO fails, the issue is universal opaque-ports.

7. **Run the engine pod WITHOUT mesh injection at all** (temporary, staging-only). Add `linkerd.io/inject: disabled` to engine pod template. If the engine then boots cleanly, the mesh is unambiguously the issue and we have a clean baseline.

### Diagnostic commands at session resume

If you are resuming this debug session, run these first to confirm the cluster state matches this checkpoint:

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml

# 1. Tunnel + auth
kubectl get nodes        # vmi3362776 Ready ...
argocd account list --grpc-web 2>&1 | head -3

# 2. linkerd-config has the 10000ms (the H7 fix that is live but inert)
kubectl -n linkerd get cm linkerd-config -o yaml | grep -E 'outboundConnect|inboundConnect'
# expect: outboundConnectTimeout: 10000ms / inboundConnectTimeout: 100ms

# 3. Confirm postgres + redis still have opaque-ports annotation
kubectl -n etradie-system get pod postgres-0 -o jsonpath='{.metadata.annotations}' | jq | grep opaque
kubectl -n etradie-system get pod redis-0 -o jsonpath='{.metadata.annotations}' | jq | grep opaque
# expect: "5432" and "6379" respectively

# 4. Confirm engine pod's NEW proxy has the 10000ms env var
NEWPOD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o jsonpath='{.items[0].metadata.name}')
kubectl -n etradie-system get pod "$NEWPOD" \
  -o jsonpath='{.spec.containers[?(@.name=="linkerd-proxy")].env}' \
  | jq '.[] | select(.name | test("CONNECT_TIMEOUT"))'
# expect: LINKERD2_PROXY_OUTBOUND_CONNECT_TIMEOUT value 10000ms

# 5. Confirm the engine STILL crashes with the same RAGBootstrapError
kubectl -n etradie-system logs "$NEWPOD" -c engine --previous --tail=30 2>&1 | tail -10
# expect: "connection was closed in the middle of operation" + "Application startup failed. Exiting."

# 6. Confirm engine outbound proxy tcp_open_total peer="dst" for postgres/redis = 0
kubectl -n etradie-system port-forward "$NEWPOD" 14191:4191 >/tmp/pf.log 2>&1 &
PF=$!
sleep 3
curl -sf http://127.0.0.1:14191/metrics 2>&1 | grep 'tcp_open_total.*peer="dst"' | grep -E 'postgres|redis|chromadb'
kill $PF 2>/dev/null
```

If those 6 checks match this checkpoint, you are at the same state. Pick up at "What we have NOT yet tried but should" above. Recommended next step: option **6** (the meshed test pod) because it cleanly bisects engine-specific vs universal opaque-ports, and **does not require any chart change or pod template modification on the production-tracking helm charts**.

### Operator gotcha #36 — SUPERSEDED (hypothesis was WRONG)

**The earlier "Linkerd 2.14.10 opaque-port outbound silently fails"
hypothesis recorded here has been DISPROVEN.** Do NOT act on it. The
engine RAG-bootstrap blocker was four separate layered defects, not an
unfixable Linkerd opaque-ports bug:

1. NetworkPolicy missing the Linkerd proxy inbound port **4143** on
   every meshed service — **FIXED** (commits 57e73bf6 → 74574c4c).
2. chromadb doing L7/HTTP through the proxy (`appProtocol: http`) so it
   depended on the linkerd-policy controller — **FIXED** by marking it
   `opaque-ports: 8000` (commit c52ea2fc).
3. The 9 RAG knowledge docs were never copied into the engine image
   (Dockerfile + `.dockerignore` `*.md` exclusion) — **FIXED** (commit
   c52ea2fc + the `.dockerignore` re-include commit). Verified: all 9
   `.md` present in the new image.
4. `linkerd-policy` Service Endpoints went stale after repeated
   `linkerd-destination` rolls, so chromadb's proxy dialed a dead
   policy-controller IP → 504/fail-fast on the chromadb hop — **OPEN /
   PARTIALLY FIXED** (endpoint reconciled to the live pod; the engine +
   chromadb proxies still need a clean restart in that window).

**Canonical resume document:**
[`docs/runbooks/CHROMADB-RAG-CHECKPOINT.md`](CHROMADB-RAG-CHECKPOINT.md)
contains the full session state, what is PROVEN vs RULED OUT (so the
dead ends are not re-tried), every fix commit, the single open blocker,
and copy-paste EXACT resume steps. Start there next session.

---

## Phase 10.6 — RESOLVED 2026-06-16 evening (engine READY 2/2 — read this first)

> **This section supersedes every earlier Phase 10.6 / chromadb-RAG /
> engine-bootstrap entry above.** Those entries are kept as an audit
> trail of dead-ends and partial hypotheses; this section records what
> actually fixed it.

### Headline state

- ✅ **etradie-engine: READY=true** within ~20s of pod start, restart
  count 0, `/readiness` returns the JSON below, `/health` returns
  `{"status":"ok"}` HTTP 200.
  ```json
  {"status":"ready","db":true,"cache":true,
   "rag":{"enabled":true,"vectorstore_connected":true,
          "database_connected":true,"embedding_ready":true}}
  ```
- ✅ Engine image digest currently running:
  `ghcr.io/flamegreat-1/etradie/engine@sha256:b30ee6733b2c9bac8d7e97db10f9ef39061d4ddb83b9d0ba832aa3f801092964`
  (CI commit on GitHub main; rebuild succeeded with the OpenTelemetry
  bump + the pre-baked HF model + the tzlocal pin).
- 🟡 **Downstream cascade — UNBLOCKED past wait-for-deps but main
  containers still failing.** gateway/execution/management pods are
  now `1/2 CrashLoopBackOff` (proxy up, main container crashes) and
  billing/edge-ingress are still `Init:CrashLoopBackOff` (likely
  reusing OLD pods that have a stale wait-for-deps state — a fresh
  force-delete is needed to surface their real main-container errors).
  This is the next operator task.

### The six fixes that landed this session (in commit order)

Every one of these is now on `main` AND has been verified live in the
running engine image.

| # | Short SHA | Fix | What it does |
|---|---|---|---|
| 1 | `27ae1a37` | engine lifespan reorder | Health-checks DB + cache (with their own 3× exponential backoff) BEFORE spawning the active-connections refresher. Warms the cold pool inside lifespan ordering rather than racing it. |
| 2 | `a626042f` | (insufficient) bump opentelemetry 0.51b0/1.30.0 → 0.55b1/1.34.1 | Attempted to pick up the `_IncludedRouter` getattr-guard. Was incorrect — 0.55b1 still had `route = starlette_route.path` bare access at line 453+456 of `opentelemetry/instrumentation/fastapi/__init__.py`. SUPERSEDED by commit 7 below. |
| 3 | `d505cad4` | revert engine mesh-disabled + OTel-disabled workarounds | Tried to re-enable mesh + tracing after fixes 1+2; required fix 6 to actually work. |
| 4 | `f033386b` | `image.pullPolicy: Always` on staging engine | Kubelet re-pulls `:0.1.0` on every pod create so an in-place CI rebuild of the tag is picked up. |
| 5 | `aff0e645` | pre-bake sentence-transformers model + fix egress | Dockerfile pre-bakes `all-MiniLM-L6-v2` into the image. NetworkPolicy egress was rewritten from broken `namespaceSelector: {}` (matches only in-cluster pods) to working `ipBlock: 0.0.0.0/0` minus K3s pod/svc CIDRs on ports 80/443. |
| 6 | `13ec57e4` | pin python:3.12-slim by digest + bust GHA cache | The CI GHA BuildKit cache had been resolving `FROM python:3.12-slim` to a poisoned manifest pointing at `python:3.14-slim` (no prebuilt wheels for the C-extension pins). Digest pin + cache-scope bump fixed CI. |
| 7 | `206b13da` | bump opentelemetry to 1.42.1 / 0.63b1 (FINAL) | The ACTUAL `_IncludedRouter` getattr guard is from instrumentation 0.57b0 onward; 1.42.1/0.63b1 is the pip-resolvable matched line. |
| 8 | `(this commit)` | docs update | Records the resolved state. |

Plus two helper commits the cluster needed at runtime:
- `cc97e632` + `f255c797`: disable mesh injection on the engine pod
  (staging overlay) — **TEMPORARY**, see "CRITICAL TEMPORARY POSTURE"
  below.
- Live action (not committed; idempotent): `kubectl delete pod` on
  postgres-0 / redis-0 / chromadb-0 to force their inbound proxies to
  re-resolve `linkerd-policy` to the live destination pod IP
  (`10.42.0.6`). The OLD inbound proxies were chasing dead policy-
  controller IPs from earlier linkerd-destination rolls; the restart
  cleared the staleness. **If linkerd-destination rolls again, the
  data-layer pods need to be restarted again** until a permanent fix
  is in place upstream.

### 🚨 CRITICAL TEMPORARY POSTURE — REVERT BEFORE PRODUCTION

**Mesh injection is DISABLED on the engine pod only.** Every other
workload on the cluster is fully meshed (postgres, redis, chromadb,
gateway, execution, management, billing, edge-ingress, envoy, mt-node,
monitoring stack, ArgoCD itself).

- **Where:** `helm/engine/values-staging.yaml::podAnnotations`,
  the line `linkerd.io/inject: "disabled"` (with the inline comment
  block explaining why).
- **Why it had to go off:** With mesh ON, postgres + redis + chromadb
  proxies reset every inbound connection from the engine during the
  first ~30ms of FastAPI lifespan startup. The lifespan-reorder fix
  (commit 1) PLUS the data-layer proxy restart (live action) PLUS
  `proxy-await: enabled` (already in base values) together were
  insufficient — the data-layer proxies' policy-controller dependency
  chain stays fragile across `linkerd-destination` rolls. Disabling
  mesh on the engine sidesteps the whole class of failure for staging
  and lets us validate everything else.
- **Trade-off accepted for staging only:** engine →
  postgres/redis/chromadb hops are plaintext TCP inside the cluster
  (not mTLS). The data-layer pods still mTLS each other and every
  other east-west hop in the cluster is still mTLS. ufw blocks every
  non-SSH inbound publicly. On a single-node K3s VPS with the data
  layer co-located, the plaintext hop never leaves loopback / cluster
  network namespace.
- **Revert path (do this before production cutover):**
  1. Land an upstream code fix in the engine that wraps the first DB
     / redis / chromadb call in a retry-with-backoff loop tolerant of
     `Connection reset by peer` for the first ~5s (defense-in-depth
     against any cold-start handshake jitter).
  2. Validate against a freshly-rolled `linkerd-destination` that the
     engine pod can come up with mesh ON.
  3. Delete the `linkerd.io/inject: "disabled"` line +
     accompanying comment block from
     `helm/engine/values-staging.yaml::podAnnotations`.
  4. Commit, push to both remotes, force ArgoCD sync, delete the
     engine pod, verify `inject=enabled` + `containers=linkerd-proxy
     engine` on the new pod, verify it reaches READY=true.

### What is currently TURNED OFF / DEGRADED that needs reverting later

| What | Where it is | Why it is off | When to turn back on |
|---|---|---|---|
| Engine Linkerd mesh injection | `helm/engine/values-staging.yaml::podAnnotations::linkerd.io/inject: "disabled"` | cold-start handshake race (see above) | After upstream retry-with-backoff fix in engine lifespan; before production |
| OTel tracing — was OFF temporarily | re-enabled in commit `d505cad4` after fixes 1+2 landed; current `helm/engine/values-staging.yaml::config.observability.otelEndpoint = otel-collector.etradie-observability.svc.cluster.local:4317` | (was) `_IncludedRouter` instrumentor crash; now fixed by commit 7 | already re-enabled — no action |
| Engine `image.pullPolicy: Always` (staging only) | `helm/engine/values-staging.yaml::image.pullPolicy: Always` | staging needs in-place tag updates during deploys | After we cut a real `0.1.1` chart-pin bump, flip back to `IfNotPresent` (chart base default) |

Production overlay (`helm/engine/values-production.yaml`) is UNTOUCHED
by this session. Production uses `IfNotPresent` + mesh-on by default;
those defaults are correct for production and must remain so.

### Mesh / data-layer / runtime invariants verified working this session

1. The data-layer (postgres-0 / redis-0 / chromadb-0) IS fully meshed,
   3/3 and 2/2 Ready, proxies show only `Certified identity` —
   confirmed clean immediately after the live-restart action.
2. ESO ClusterSecretStore `vault-backend` Valid; every chart
   ExternalSecret materialises correctly.
3. Linkerd identity + destination + proxy-injector all Healthy in the
   `linkerd` namespace (`linkerd-destination-7bb76fd76-c8gfm` at
   `10.42.0.6`; `linkerd-policy` + `linkerd-dst` endpoints both point
   at that IP).
4. ArgoCD `engine-staging` Application Synced/Healthy.
5. Engine RAG bootstrap completes end-to-end:
   `rag_bootstrap_starting → bootstrap_seeding_started → 9× seed_skipped_exists
    → bootstrap_seeding_completed → rag_bootstrap_completed → application_started
    → Uvicorn running on http://0.0.0.0:8000`.
6. Pre-baked HF model loads from disk (`/home/etradie/.cache/...`) at
   pod start — no HuggingFace egress at boot.

### Open work for the next operator (resume point)

1. **Surface the downstream cascade errors.** With the engine now Ready,
   the etradie Service Endpoints populate and wait-for-deps clears for
   gateway/execution/management/billing. They MOVED past Init to main
   container, where they now crash with their OWN errors (not
   engine-blocked anymore). Force-delete all stuck pods to surface the
   real errors:
   ```bash
   for svc in etradie-gateway etradie-execution etradie-management etradie-billing; do
     kubectl -n etradie-system delete pod -l app.kubernetes.io/name=$svc --grace-period=0 --force
   done
   kubectl -n edge-ingress-system delete pod -l app.kubernetes.io/name=edge-ingress --grace-period=0 --force
   sleep 25
   for svc in etradie-gateway etradie-execution etradie-management etradie-billing; do
     POD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=$svc \
       --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
     echo "=== $svc ($POD) ==="
     kubectl -n etradie-system logs "$POD" --all-containers=true --tail=40 2>&1 | tail -40
   done
   ```
2. Fix each downstream service's main-container error in turn.
3. Once all five staging children are `Synced/Healthy` AND pods are
   `Ready`, run the Phase 14 end-to-end verification block from the
   README.
4. Implement the engine retry-with-backoff lifespan fix; flip
   `linkerd.io/inject` back to enabled; verify mesh-on works; commit.
5. Complete the Phase 10.6 closeout TODOs that were carried over from
   earlier checkpoints (non-expiring `vault-auth` token, disable
   `/tmp/vault-audit.log`, delete the 14 doubled-prefix Vault entries,
   flip Phase 10 status board to ✅).

### Session-resume checklist if the operator session ended here

```bash
# 1. Tunnel + KUBECONFIG (always once per WSL boot)
ssh-add ~/.ssh/id_ed25519
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173        # dedicated terminal, leave open
export KUBECONFIG=~/.kube/etradie-contabo.yaml

# 2. ArgoCD port-forward (separate dedicated terminal)
kubectl -n argocd port-forward svc/argocd-server 8080:443

# 3. ArgoCD CLI login (working terminal)
ADMIN=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d)
argocd login 127.0.0.1:8080 --username admin --password "$ADMIN" --insecure
unset ADMIN

# 4. Sanity — these must all hold true
kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine
# expect: 1/1 Running 0 restarts (no linkerd-proxy sidecar, by-design temporary)

kubectl -n etradie-system port-forward \
  $(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
    -o jsonpath='{.items[0].metadata.name}') 18000:8000 >/tmp/pf.log 2>&1 &
sleep 3
curl -sS http://127.0.0.1:18000/readiness
# expect: {"status":"ready","db":true,"cache":true,"rag":{...,"embedding_ready":true}}
kill %1

kubectl -n linkerd get pods
# expect: linkerd-destination + linkerd-identity + linkerd-proxy-injector all Running

kubectl -n etradie-system get pod postgres-0 redis-0 chromadb-0
# expect: postgres 3/3, redis 3/3, chromadb 2/2 — all Running
```

If any of those 4 sanity checks fail, RE-READ this section before
touching anything. If the engine has flipped to CrashLoopBackOff again
after being Ready, the most likely cause is
linkerd-destination got restarted again and the data-layer pods'
proxies are stale — restart postgres-0 / redis-0 / chromadb-0 in that
order, wait for them to come back Ready, then restart the engine pod.
Documented in detail in CHROMADB-RAG-CHECKPOINT.md.

---

## Phase 10.6 — postgres TLS server-side + engine native-TLS revert 2026-06-16 (the real fix)

> **This section supersedes the previous-session `ENGINE_DB_NATIVE_TLS=false`
> + `linkerd.io/inject: "disabled"` engine workarounds.** Those were
> debug-arc dead-ends; root cause was that postgres did not serve TLS
> while every application config enforces `sslmode=require`. With this
> series of three commits, the chart now matches the application
> contract and both workarounds are reverted.

### How the staging cascade surfaced this

After Vault path mount mismatch + execution/management missing
`auth_admin_password` were fixed earlier in this session, the
`execution` and `management` pods reached the main container and
crashed at first DB ping with:

```
fatal: failed to connect to `user=etradie database=etradie`:
       10.43.151.84:5432 (postgres.etradie-system.svc.cluster.local):
       tls error: read tcp 10.42.0.239:45900->10.43.151.84:5432:
       read: connection reset by peer
```

Meshed-pod psql probes from a temporary `pgprobe-meshed` pod proved:

| sslmode | result |
|---|---|
| disable | OK (returns `1`) |
| prefer  | OK (returns `1`) |
| require | FAIL `server does not support SSL, but SSL was required` |

And `SHOW ssl;` on postgres-0 returned `off`. Postgres was plaintext.

### The 4-validator contract that hard-enforces sslmode=require

Reading every config validator in the codebase (not just the engine's,
as earlier sessions had):

| Service | File | What it enforces in prod/staging |
|---|---|---|
| auth (gateway/execution/management share `src/auth`) | `src/auth/config.go::validate()` | `AUTH_DATABASE_URL` non-empty (string-level audit invariant) |
| billing | `src/billing/config/config.go::requireTLSDatabaseURL` | sslmode in {require, verify-ca, verify-full}; rejects disable/allow/prefer with explicit error message *"refusing to start in a production-like environment"* |
| execution | `src/execution/internal/config/config.go::validate()` | Identical to billing's check, same allowed set |
| engine | `src/engine/config.py::_validate_production_secrets` | Identical string-level check on `DATABASE_URL` query string |

The billing config carries the load-bearing comment:
*"Default to require so the connection is encrypted **even when the
service mesh is off**"*. The intent across the codebase is
unambiguous: TLS is a wire-level invariant, independent of Linkerd.

### The previous-session engine workaround was a debug-arc dead-end

The history:

| Date | Commit | What happened |
|---|---|---|
| 2026-05-04 | `ae1ed53e` | Postgres StatefulSet added. No SSL config from day one. |
| 2026-06-09 | `f935b42c` | postgres-exporter sidecar added with `sslmode=disable` (loopback). Inline comment claims *"meshed peers are mTLS'd by Linkerd, not libpq TLS"* — true for the EXPORTER hop, but conflates loopback semantics with remote-client semantics. |
| 2026-06-15 09:29Z | `23e3f674` | Engine `migrate` init crashed: `TypeError: connect() got an unexpected keyword argument 'sslmode'`. asyncpg has its own protocol impl and doesn't accept libpq's `sslmode` kwarg name. Fix #1: translate libpq sslmode → asyncpg `ssl=`. |
| 2026-06-15 09:59Z | `8843f074` | 30 minutes later, fix #1 produced a new failure: `ConnectionError: PostgreSQL server ... rejected SSL upgrade`. Author traced it to plaintext postgres, added `ENGINE_DB_NATIVE_TLS` env var defaulting to `false` (MESH mode → asyncpg ssl=False regardless of DSN sslmode). The commit message itself framed it as a forward-compatible escape hatch for managed-postgres deploys, NOT the intended steady state. |

The workaround masked the underlying inconsistency: the chart was the
component out of step with the application contract, not the engine.

### The fix (3 commits in this series)

**Commit 1: helm/data-layer — enable postgres TLS server-side.**

  - New `tls-cert-init` initContainer in `postgres-statefulset.yaml`.
    Reuses the `postgres:16-alpine` image (already cached on the node,
    uid 70 native, `/usr/bin/openssl` present as a runtime dep of
    `openssl-dev` pulled by the official Dockerfile). Generates a
    10-year self-signed RSA-4096 cert+key into an emptyDir mounted
    at `/var/lib/postgresql/certs/`. Owner uid 70, mode 0600 on key,
    0644 on cert (postgres refuses to start otherwise: `FATAL:
    private key file has group or world access`).
  - Idempotent: skips regeneration if the cert exists with >30 days
    to expiry. Rolling restart on the same node reuses the cert; pod
    recreate generates fresh.
  - SAN list in `postgres-cert-init-configmap.yaml` (new): the
    canonical postgres FQDN + headless + short forms + localhost +
    127.0.0.1. Centralised so a future operator-driven rotation
    regenerates with the same SANs.
  - Postgres args appended: `-c ssl=on -c ssl_cert_file=... -c
    ssl_key_file=...`. Composed with the existing audit-logging `-c`
    args block; the readOnlyRootFilesystem + non-root posture is
    preserved (no config-file mount added).
  - Backup + restore-drill CronJobs: `PGSSLMODE=require` added
    explicitly. libpq defaults to `prefer` (which still works against
    a TLS-on server), but explicit > implicit; matches every other
    postgres consumer's posture exactly.

  Stock `pg_hba.conf` is `host all all all scram-sha-256` (accepts
  both TLS and non-TLS). The postgres-exporter sidecar's loopback
  connection (sslmode=disable) keeps working without change. Remote
  clients enforce sslmode=require at their end and always negotiate TLS.

**Commit 2: helm/engine — flip ENGINE_DB_NATIVE_TLS=true + re-enable mesh.**

  - New `config.database.nativeTls` value in `helm/engine/values.yaml`
    (default `"false"` in base for forward-compat with managed-postgres
    deploys that don't run our data-layer chart).
  - `ENGINE_DB_NATIVE_TLS` rendered from this value in the engine
    ConfigMap. The ConfigMap is mounted via envFrom on both the
    engine main container AND the migrate init container, so the
    single key feeds both code paths (engine.shared.db.connection +
    engine.shared.db.migrations.env).
  - `values-staging.yaml` and `values-production.yaml` both set this
    to `"true"`. Engine asyncpg now uses native TLS
    (`ssl='require'`), same wire semantics as the Go services'
    `sslmode=require`.
  - `values-staging.yaml` also REMOVES the temporary
    `linkerd.io/inject: "disabled"` annotation block. The mesh was
    disabled on engine only as a temporary unblock during the data-
    layer plaintext-postgres workaround arc; with postgres now
    serving TLS, the original cold-start handshake race no longer
    applies. Engine joins the mesh end-to-end like every other
    service. Base values.yaml's mesh annotations (native sidecar,
    proxy-await, opaque-ports for mt-node :5555 + chromadb :8000,
    skip-outbound for OTel :4317) apply unchanged.

**Commit 3: docs (this commit).** README troubleshooting row +
this PROGRESS section.

### What this does NOT change

- **Zero application source code changed.** The Go validators continue
  to enforce `sslmode=require` — they will now succeed because postgres
  serves TLS. The engine's MESH-mode flag (`ENGINE_DB_NATIVE_TLS=false`
  default in `src/engine/shared/db/connection.py`) stays in code as a
  forward-compatible escape hatch for managed-postgres deployments;
  the chart's prod/staging overlays opt out of that default by setting
  the env var to `"true"`.
- **Vault DSN format unchanged.** Every Vault path keeps
  `sslmode=require`. Audit-trail invariant intact.
- **Linkerd opaque-ports unchanged.** `opaque-ports: "5432"` on
  postgres still tells the proxy to raw-TCP-tunnel the connection.
  The bytes inside the tunnel are now TLS-encrypted instead of
  plaintext postgres wire — defense in depth, not conflict.
- **NetworkPolicies unchanged.** Port 5432 is still 5432;
  `appProtocol: postgresql` on the Service is still accurate.

### Defense in depth on every in-cluster postgres hop

1. **ufw at the host** (Tier 11; postgres :5432 not exposed publicly).
2. **Linkerd mTLS** (Tier 9 mesh identity; opaque-ports raw-TCP tunnel).
3. **Application TLS** (libpq sslmode=require; pgx + asyncpg both honour).

### Operator rollout sequence after merging this commit

The three commits go to `main` in order; ArgoCD reconciles in dependency
order. Operator does NOT need to live-patch the cluster — just push +
monitor + run one cleanup at the end.

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml

# 1. Verify the data-layer change reconciled — postgres MUST roll with TLS on.
argocd app sync data-layer-staging --grpc-web --timeout 300
argocd app wait data-layer-staging --health --timeout 300
for i in $(seq 1 30); do
  R=$(kubectl -n etradie-system get pod postgres-0 \
      -o jsonpath='{.status.containerStatuses[*].ready}' 2>/dev/null \
      | tr ' ' '\n' | grep -c true)
  echo "T+$((i*5))s postgres-0 ready=$R/3"
  [ "$R" = "3" ] && break
  sleep 5
done

# 2. Sanity: postgres now serves TLS.
kubectl -n etradie-system exec postgres-0 -c postgres -- \
  psql -U etradie -d etradie -c "SHOW ssl;"
# expect: ssl on (was 'off' before this fix)

# 3. Sanity: cert file exists with the correct SAN list.
kubectl -n etradie-system exec postgres-0 -c postgres -- \
  openssl x509 -in /var/lib/postgresql/certs/server.crt -noout -subject -dates -ext subjectAltName
# expect: CN=postgres.etradie-system.svc.cluster.local + SAN with the
# 5 hostnames listed in postgres-cert-init-configmap.yaml + IP:127.0.0.1

# 4. Sync the engine. It rolls with ENGINE_DB_NATIVE_TLS=true and
#    mesh sidecar injected (the previous-session inject:"disabled"
#    override is removed).
argocd app sync engine-staging --grpc-web --timeout 600
argocd app wait engine-staging --health --timeout 600

# 5. Engine pod sanity: 2/2 (engine + linkerd-proxy), ENGINE_DB_NATIVE_TLS=true.
ENG=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
      --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl -n etradie-system get pod "$ENG" -o wide
kubectl -n etradie-system get pod "$ENG" -o jsonpath='{.spec.containers[*].name}{"\n"}'
# expect: linkerd-proxy engine (or engine linkerd-proxy)
kubectl -n etradie-system exec "$ENG" -c engine -- env | grep ENGINE_DB_NATIVE_TLS
# expect: ENGINE_DB_NATIVE_TLS=true

# 6. Force-restart the Go service pods so they handshake against
#    the now-TLS-serving postgres in a clean state.
for svc in etradie-gateway etradie-execution etradie-management etradie-billing; do
  kubectl -n etradie-system delete pod -l app.kubernetes.io/name=$svc --grace-period=0 --force
done
kubectl -n edge-ingress-system delete pod -l app.kubernetes.io/name=edge-ingress --grace-period=0 --force
sleep 60
kubectl -n etradie-system get pods

# 7. Final state: every staging child Synced/Healthy.
argocd app list --grpc-web | grep staging
# expect: 11 apps; 10 Synced/Healthy + linkerd-* OutOfSync/Healthy
# (the latter is by-design ESO + webhook caBundle drift; documented
# in earlier PROGRESS sections).
```

### Phase 10.6 closeout TODOs after this fix lands cleanly

The engine mesh-disabled override was the only remaining production-
blocking debt; it is reverted by this series. The remaining
close-out items are operational hygiene, NOT production-blockers:

1. Mint a non-expiring legacy Secret-bound token for the `vault-auth`
   ServiceAccount and replace the 24h TTL `token_reviewer_jwt` on
   Vault's `kubernetes/config` (PROGRESS gotcha #28).
2. Disable the Vault audit log at `/tmp/vault-audit.log` (PROGRESS
   gotcha #29).
3. PROGRESS gotcha #9 correction commit ("the doubled-prefix was NOT
   intentional; here is the actual ESO `buildPath` behavior" —
   PROGRESS gotcha #23).
4. Delete the 14 doubled-prefix Vault entries (post-stability cleanup).
5. Flip the Phase 10 status board to ✅ once all 11 staging children
   report Synced/Healthy under the rollout sequence above.

### Phase 10.6 operator gotchas added by this fix

**37. Chart-vs-application TLS contract drift is silent until first
connect.** The data-layer chart shipped postgres with SSL off from
commit `ae1ed53e` (2026-05-04). Every config validator in the Go and
Python source enforced `sslmode=require` from day one. The mismatch
produced no error at chart-render time, no error at Vault-write time,
no error at pod-schedule time, no error at namespace-admission time —
it surfaced ONLY when the first application client opened a TCP
connection and asked for SSL. Earlier sessions diagnosed the engine
case wrongly (added ENGINE_DB_NATIVE_TLS workaround instead of fixing
the chart). Lesson: when adding a fail-closed wire-level validator in
any service, audit the chart that provisions the server-side endpoint
in the same MR — drift between server posture and client posture is
invisible until a real connection is attempted.

**38. Postgres `ssl_key_file` permissions are strict.** Postgres
refuses to start unless `ssl_key_file` is either (i) owner = postgres
user + mode 0600, or (ii) owner = root + group = postgres-group +
mode 0640. The `tls-cert-init` initContainer runs as uid 70 (postgres
user inside `postgres:16-alpine`) with `fsGroup: 70` on the pod, so
files are owner-correct by default; the script also `chmod 0600` /
`chmod 0644` explicitly as a defense against future fsGroup changes.
Skipping the explicit chmod or running the init container as root
(without setting `runAsUser: 70`) breaks the strict-mode contract
and postgres logs `FATAL: private key file has group or world access`.

**39. asyncpg `ssl='require'` against a self-signed cert succeeds.**
asyncpg's `ssl='require'` is the documented analog of libpq's
`sslmode=require`: it encrypts the channel but does NOT chain-verify
or hostname-verify. The chart's self-signed cert is therefore
accepted by both pgx (libpq) and asyncpg without any client-side CA
distribution. A future hardening to `verify-ca` / `verify-full`
would require distributing the CA bundle to every consumer pod,
which is out of scope for in-cluster TLS where Linkerd already
provides identity. See `src/engine/shared/db/connection.py::
_translate_sslmode_for_asyncpg` for the full asyncpg ssl-kwarg
mapping documentation.
