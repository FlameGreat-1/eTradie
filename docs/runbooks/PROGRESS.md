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
