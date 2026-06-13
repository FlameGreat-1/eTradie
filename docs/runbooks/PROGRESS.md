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
