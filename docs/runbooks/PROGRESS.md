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

**Single way in:** `ssh etradie@13.140.164.173` from the workstation.
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
