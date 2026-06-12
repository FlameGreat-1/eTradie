# eTradie — Deployment Progress CHECKLIST

> **Purpose:** live, resumable tracker for the single-node Contabo VPS
> deployment. Follow `docs/runbooks/README.md` (the AUTHORITATIVE runbook;
> `docs/deployment/contabo-k3s.md` has stale image tags + omits the Linkerd
> mesh). Tick each box as it is verified. If we stop, resume at the first
> unticked item.
>
> **Box:** Contabo VPS 30 NVMe (8 vCPU / 24 GB / 200 GB) — BUDGET.md Table 2B.
> **Host:** `13.140.164.173` (Ubuntu, root access).
> **Environment:** `__________` (staging OR production — ONE per box).
> **Started:** `__________`   **Last updated:** `__________`

---

## How to use

- `[ ]` = not started/verified, `[x]` = done AND verified by its check.
- Do NOT mark a box until its **Verify** step passed.
- Record generated values OUT-OF-BAND (never in git). See Phase 8.11.

---

## Phase 0 — Prerequisites

- [ ] 0.1 Workstation tools installed (`ssh`, `kubectl>=1.29`, `helm>=3.14`, `terraform>=1.7`, `vault>=1.15`, `git`, `jq`, `openssl`, `base64`, `curl`, `rustup`, `step`, `argocd`)
- [ ] 0.2 Accounts/assets ready (Cloudflare zone `exoper.com` Active; MaxMind GeoLite2 acct + license; engine LLM/data keys; billing keys)
- [ ] 0.3 Repo cloned on workstation
- [ ] 0.4 CI-built app images present in GHCR (engine/gateway/execution/management/billing `0.1.0` + edge-ingress `0.2.0`) — mt-node NOT expected yet

## Phase 1 — VPS host hardening (`docs/runbooks/vps-host-hardening.md`)

- [ ] 1.1 Non-root sudo user created, SSH key copied, reconnected as it
- [ ] 1.2 SSH hardened (`PasswordAuthentication no`, `PermitRootLogin prohibit-password`, drop-in), `sshd -t` ok, ssh reloaded
- [ ] 1.2a Verified from a SECOND session: password auth refused, key auth works (keep first session open)
- [ ] 1.3 `apt update && upgrade`; base packages installed (`ca-certificates curl gnupg git make jq unzip ufw chrony`)
- [ ] 1.4 Time sync: `chronyc tracking` stratum <= 3
- [ ] 1.5 Kernel/ulimit tuning applied (`/etc/sysctl.d/99-etradie.conf` + limits), `sysctl --system`
- [ ] 1.6 fail2ban sshd jail active
- [ ] 1.7 Firewall: default-deny inbound, only 22/tcp open; `ufw status verbose` (or `nft list ruleset`) confirms
- [ ] 1.8 K8s API stays private (6443 NOT on 0.0.0.0); `ss -tlnp | grep :6443` confirms
- [ ] 1.9 *** System restart required *** handled (reboot if pending, reconnect)

## Phase 2 — Install K3s (>= 1.29 REQUIRED for Linkerd native sidecars)

- [ ] 2.1 K3s installed `v1.30.4+k3s1` with the exact `INSTALL_K3S_EXEC` (disable traefik + servicelb, NodeRestriction+PodSecurity, eviction-hard)
- [ ] 2.2 Verified: `kubectl get nodes` Ready; `kube-system` pods Running
- [ ] 2.3 kubeconfig exported to workstation `~/.kube/etradie-contabo.yaml` (127.0.0.1 -> VPS IP), `kubectl get nodes` Ready from workstation

## Phase 2.5 — Build + push mt-node Wine image (do BEFORE relying on 0.4)

- [ ] 2.5.1 WineHQ apt candidate version discovered -> `WINEHQ_VERSION`
- [ ] 2.5.2 EA binary SHAs computed (`make mt-node-ea-sha`)
- [ ] 2.5.3 MT5 + MT4 installer SHA256s obtained
- [ ] 2.5.4 `make push-mt-node` built + pushed with all build args + `MT_NODE_TAG=0.1.0`
- [ ] 2.5.5 Verified `ghcr.io/flamegreat-1/etradie-mt-node:0.1.0` present (`docker manifest inspect`)

## Phase 3 — Vault + Vault Agent Injector

- [ ] 3.1 Vault installed (chart 0.28.1, standalone, dataStorage 10Gi local-path, injector + ui enabled)
- [ ] 3.2 Init + unseal done; `vault-init.txt` STORED OFFLINE; `vault status` Sealed:false
- [ ] 3.3 Injector pod Running 1/1
- [ ] 3.4 kubernetes auth + KV-v2 `secret` mount + `etradie-eso` policy/role created
- [ ] 3.5 Token-review SA `vault-auth` + clusterrolebinding created

## Phase 4 — External Secrets Operator + ClusterSecretStore

- [ ] 4.1 ESO installed (chart 0.10.4, CRDs), deployment Available
- [ ] 4.2 `ClusterSecretStore vault-backend` applied; status reason `Valid`

## Phase 5 — Stakater Reloader

- [ ] 5.1 Reloader installed; `deployment/reloader-reloader` rolled out

## Phase 6 — Cloudflare Tunnel

- [ ] 6.1 Tunnel `etradie-<env>` created; token copied (unrecoverable)
- [ ] 6.2 Public hostnames added (`api.exoper.com` -> edge-ingress svc:443, etc.); CNAMEs auto-created
- [ ] 6.3 Tunnel UUID + token noted

## Phase 7 — Generate Linkerd mesh CA

- [ ] 7.1 Root CA (`ca.crt`/`ca.key`) created with `step`
- [ ] 7.2 Intermediate issuer (`issuer.crt`/`issuer.key`) created; `ca.crt` retained for Phase 10.4

## Phase 8 — Bootstrap Vault paths + populate every secret

- [ ] 8.1 `terraform apply` created empty KV paths (`-var environment=<env>`)
- [ ] 8.2 Shared secrets generated ONCE (DB/REDIS/JWT/BROKER/CHROMA/ADMIN/ENGINE_SHARED/BILLING_SHARED/MT_DEFAULT_ZMQ + DB/REDIS URLs)
- [ ] 8.3 Data layer secrets written (postgres, redis, chromadb auth_token)
- [ ] 8.4 Linkerd identity written (trust_anchor/issuer crt+key)
- [ ] 8.5 Edge-ingress written (cloudflare tunnel token, aop_ca, maxmind, empty tls)
- [ ] 8.6 Gateway written (JWT, admin pwd, BOTH shared secrets, DB URL)
- [ ] 8.7 Engine written (broker_encryption_key, provider keys, DB/redis)
- [ ] 8.8 Execution + Management written (matching JWT + engine shared secret)
- [ ] 8.9 Billing written (internal_shared_secret == gateway billing secret; provider keys)
- [ ] 8.10 mt-node platform fallback ZMQ token written
- [ ] 8.11 Generated values saved out-of-band (mode 0600, never committed)

## Phase 9 — Build + inject the envoy WASM filter

- [ ] 9.1 WASM built (`cargo build --release --target wasm32-wasi`)
- [ ] 9.2 `helm/envoy/values-<env>-wasm.yaml` generated (base64 + sha256 + builtAt)
- [ ] 9.3 envoy ArgoCD child references the wasm overlay; committed + pushed to `main`

## Phase 10 — ArgoCD + AppProjects + root app

- [ ] 10.1 ArgoCD installed (v2.13.3); `argocd-server` Available
- [ ] 10.2 Admin password retrieved; UI port-forward up
- [ ] 10.2.1 `argocd login` succeeded (`argocd account list` works)
- [ ] 10.3 Both AppProjects + root app-of-apps applied
- [ ] 10.4 Linkerd trust anchor passed to control-plane app (`--helm-set-file identityTrustAnchorsPEM=ca.crt`)

## Phase 11 — Provision mt-node tenant Vault infrastructure

- [ ] 11.1 `terraform apply` (with k8s_host/ca/reviewer_jwt) created per-tenant Vault roles/policies

## Phase 12 — Sync the platform in dependency order (wait Synced+Healthy each)

- [ ] 12.1 `linkerd-identity-<env>` (wave -6)
- [ ] 12.2 `linkerd-crds-<env>` (-5)
- [ ] 12.3 `linkerd-control-plane-<env>` (-4)
- [ ] 12.4 `observability-logs-<env>` (-2)
- [ ] 12.5 `data-layer-<env>` (-2)
- [ ] 12.6 `engine-<env>` + `mt-node-<env>` (-1)
- [ ] 12.7 `billing-<env>` (1)
- [ ] 12.8 `gateway-<env>`, `execution-<env>`, `management-<env>` (0)
- [ ] 12.9 `envoy-<env>` (5)
- [ ] 12.10 `edge-ingress-<env>` (10)
- [ ] 12.11 Confirmed ONLY `*-<env>` + three `linkerd-*` synced (no cross-env apps)

## Phase 13 — Database migrations

- [ ] 13.1 `\dt` shows expected tables (engine migrate init container ran)

## Phase 14 — End-to-end verification

- [ ] 14.1 All pods Ready (`kubectl get pods -A | grep -vE '(Running|Completed)'` empty)
- [ ] 14.2 Mesh healthy + `linkerd-proxy` injected
- [ ] 14.3 ESO synced every Secret (`kubectl get externalsecret -A`)
- [ ] 14.4 Cloudflare Tunnel HEALTHY; cloudflared logs show 'Registered tunnel connection'
- [ ] 14.5 Public reachability + auth round-trip (healthz, auth/health, login -> token -> state/account 200)
- [ ] 14.6 Frontend (Vercel) reaches `https://api.exoper.com`; CORS origin matches

## Phase 14.5 — Hosted-MT (Wine) provisioning readiness

- [ ] 14.5.1 Pre-flight: engine SA can create statefulsets/services; platform ExternalSecret materialised; `MT_NODE_IMAGE` + `VAULT_ADDR` correct in engine config
- [ ] 14.5.3 (when a test/real hosted connection exists) tenant pod verified (Ready, tmpfs creds, /healthz 200, PVC bound, ZMQ reachable)

## Phase 15 — Post-deploy operational notes

- [ ] 15.1 Disabled toggles left OFF per BUDGET.md Table 2B (HPA/PDB/Linkerd HA/viz/policy/snapshotter)
- [ ] 15.2 (production) Postgres backup CronJob + B2 offsite path populated BEFORE first 02:00 UTC run
- [ ] 15.3 Vault Raft snapshots backed up out-of-band
- [ ] 15.4 (optional) kube-prometheus-stack installed into `monitoring`

---

## Session log (append as we go)

| Date/time (UTC) | Phase reached | Notes / blockers |
|---|---|---|
|  |  |  |
