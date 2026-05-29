# MetaTrader Hosting Deployment Guide

> Production deployment guide for eTradie's three MetaTrader integration paths.
>
> The eTradie platform supports three connection types for MetaTrader 4 and 5.
> Pick the one that matches your hosting model.

---

## 1. Connection types at a glance

| Type | Where MT runs | Provisioning | Auto-recovery | Production-ready |
|------|---------------|--------------|---------------|------------------|
| `hosted` | Linux container inside your K8s cluster (helm/mt-node chart) | Engine API at runtime | K8s controllers + watchdog sidecar | YES (this guide, sections 2-4) |
| `metaapi` | MetaApi.cloud (managed) | MetaApiProvisioner | MetaApi.cloud SLA | YES (no infra to manage; see MetaApi docs) |
| `ea` | A Windows VPS YOU operate | manual (scripts/vps/*.ps1) | Windows Task Scheduler watchdog | YES, but the engine must be reachable FROM the cluster TO your VPS at TCP/5555. Inside the standard Cloudflare-Tunnel-only topology this requires an opt-in network policy exception. See section 5 below. |

---

## 2. Hosted MetaTrader (recommended)

The eTradie engine spins up a dedicated per-user Kubernetes Deployment
running the custom `etradie-mt-node` Docker image (Wine + Xvfb +
MetaTrader + ZeroMQ EA + a watchdog sidecar).

```text
┌─────────────────────────────────────────────────────────┐
│ Kubernetes Cluster (etradie-system namespace)        │
│                                                      │
│  ┌────────────────┐         ┌─────────────────────┐   │
│  │ etradie-engine │  ZMQ    │ etradie-mt-<conn>   │   │
│  │ (FastAPI)      ├───────►│ (Deployment+Svc)   │   │
│  │                │ :5555   │   - mt-node ctr      │   │
│  │ HostedProv.    │         │   - watchdog sidecar │   │
│  │ +K8s API RBAC  │         │   - PVC (.wine)      │   │
│  └────┬──────────┘         └─────────────────────┘   │
│       │ manages via apps/v1.Deployment             │
│       ▼                                              │
│  ┌────────────────┐                                 │
│  │ K8s API server │                                 │
│  └────────────────┘                                 │
└─────────────────────────────────────────────────────────┘
```

### Production guarantees

- **No Windows server required.** Wine + Xvfb run MT terminals headlessly.
- **No public network exposure.** The ZMQ port 5555 is reachable only
  via the in-cluster ClusterIP Service. The chart's NetworkPolicy
  allows ingress only from `app.kubernetes.io/name=etradie-engine`.
- **Per-tenant credentials sealed via AES-GCM** by the engine before
  writing to the per-tenant Kubernetes Secret. The encryption key
  lives in `etradie/services/mt-node/<env>:mt_node_credential_encryption_key`.
- **Auto-recovery in three layers:**
  1. `entrypoint.sh` supervises MT5 inside the container (up to 5
     in-pod restarts within 5 min before the kubelet restarts the Pod).
  2. The watchdog sidecar polls the EA's HEALTH command every 10s and
     signals MT5 to terminate on `mt5_connected=false`, `authenticated=false`,
     or RSS ≥ 80% of the cgroup limit.
  3. K8s `Deployment` + `restartPolicy=Always` cycles the Pod if the
     watchdog itself wedges (livenessProbe fail).
- **Persistent Wine prefix** via PVC so chart profile, symbol cache,
  and EA settings survive Pod restarts.

### One-time platform setup

Done once per environment by an operator with kubeconfig + vault token.

1. Provision the cluster + node pool (`infrastructure/cluster/oci/`)
   or follow the manual K3s bootstrap (`infrastructure/cluster/bootstrap/`).
2. Apply Vault path schema (`infrastructure/cluster/vault-paths/`).
3. Populate the mt-node platform path:
   ```bash
   vault kv put secret/etradie/services/mt-node/production \
     mt_node_credential_encryption_key="$(openssl rand -hex 32)" \
     default_zmq_auth_token="$(openssl rand -hex 32)"
   ```
4. Apply the ArgoCD `mt-node-production` child Application. ArgoCD
   reconciles the PriorityClass + platform ExternalSecret + watchdog
   ConfigMap. Per-user Deployments are NOT managed by ArgoCD; the
   engine creates them at runtime.

### Per-user provisioning (transparent)

1. User signs in to dashboard, picks 'MetaTrader 5'.
2. User enters MT login + password + broker server, clicks Connect.
3. Engine calls `HostedProvisioner.provision_account()`:
   - Creates per-tenant K8s Secret with sealed creds (`etradie-mt-<id>-creds`).
   - Creates `Deployment` + `ClusterIP Service` + `PVC`.
   - Blocks up to 300s waiting for Deployment Ready + ZMQ PING success.
4. On success, engine writes `broker_connections.hosted_container_id`
   = release name, `broker_connections.ea_auth_token` = per-tenant ZMQ
   token (column-encrypted at rest by `broker_encryption_key`).
5. Dashboard shows the connection as Active.

### Build the mt-node image

CI publishes a digest-pinned image to GHCR. Local builds:

```bash
# Compile EA binaries in MetaEditor first, then drop into docker/mt-node/ea/
make build-mt-node    # uses 'skip' SHA in dev
MT5_INSTALLER_SHA256=<hash> MT4_INSTALLER_SHA256=<hash> make build-mt-node  # prod
```

The Dockerfile's build will FAIL with no `MT*_INSTALLER_SHA256` set,
this is deliberate.

### Verify

```bash
make mt-node-lint              # helm lint (both render paths)
make mt-node-deploy-dry-run    # helm template (both render paths)
make mt-node-chaos             # provisioner contract + soak + OOM + disconnect
```

---

## 3. MetaApi cloud

No additional infra required. The engine reads `MT5_METAAPI_TOKEN`
from Vault path `etradie/services/engine/<env>:mt5_metaapi_token`.
Dashboard 'MetaApi (managed)' option triggers per-user account
provisioning by `MetaApiProvisioner`.

---

## 4. EA on Windows VPS (fallback)

For users who already own a Windows VPS and prefer running MT there
(e.g. broker-pinned IP whitelisting).

```text
 IMPORTANT: In the standard eTradie cluster topology, the engine
 sits behind Cloudflare Tunnel and its NetworkPolicy egress allows
 outbound TCP only on 80/443 (broker REST), DNS, and the in-cluster
 mt-node :5555 selector. Outbound TCP/5555 to an arbitrary public
 VPS is NOT allowed.

 To use the VPS path in production, you have two options:
   (a) Run the engine OUTSIDE the cluster (the docker-compose dev
       deployment). The engine's NetworkPolicy does not apply.
   (b) Add a NetworkPolicy egress exception for the VPS IP/24,
       reviewed and applied as a one-off Vault-CIDR-allowlist diff
       to helm/engine/values-production.yaml. This is operator-
       initiated and out of scope for the dashboard flow.

 Most users should pick the 'hosted' option (section 2) or MetaApi
 (section 3). The VPS path is supported for completeness, not as the
 default.
```

### Windows VPS setup steps

1. Provision a Windows Server 2022 VPS.
2. Install MetaTrader and log in to your broker account.
3. Open MetaEditor, compile `ZeroMQ_EA.mq5` (source in
   `src/engine/ta/broker/mt5/zmq/`).
4. Run the automation scripts as Administrator:
   ```powershell
   .\setup_vps.ps1 `
     -MT5DataFolder "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\ABC123" `
     -LinuxMachineIP "<engine-egress-ip>" `
     -VPSPassword "<strong-password>"
   .\install_monitor_task.ps1 -Action install
   ```
5. In the dashboard, choose 'Custom EA Connection' and provide:
   - VPS public IP
   - ZMQ port (default 5555)
   - Auth token (the one you set in `setup_vps.ps1`)

### Security caveats (READ THIS)

**ZeroMQ traffic to a remote VPS is unencrypted at the wire level.**
A full ZMQ-CURVE encryption fix (libzmq's native key-pair scheme)
is tracked as a follow-up MR; it requires EA-side MQL5 changes
plus a `broker_connections` schema migration to carry the public/
secret key pair per tenant.

**Interim posture you MUST adopt for production EA-on-VPS:**

1. **WireGuard or Tailscale overlay (recommended).** Add the VPS
   and the engine egress IP (or in K8s deployments, every node
   the engine pod may schedule on) to a private WireGuard mesh.
   The ZMQ traffic then traverses the encrypted tunnel and the
   public internet sees no plaintext. Tailscale's `tailscale up`
   + ACLs is the lowest-overhead way to do this; WireGuard works
   equally well with a fixed peer list.

2. **Source-IP whitelist on Windows Firewall.** The
   `setup_vps.ps1` script does this when you pass
   `-LinuxMachineIP <engine-egress-ip>`. This stops a remote
   attacker from connecting to TCP/5555 at all; it does NOT
   stop on-path passive sniffing on the public internet.

3. **Operator-visible warning.** When a tenant opens an `ea`
   connection, the engine emits a structured log line
   `ea_connection_unencrypted_zmq` and bumps the metric
   `etradie_broker_ea_connection_unencrypted_total`. Operators
   should add a PrometheusRule that alerts on a non-zero rate
   so a new exposed tenant is caught at sign-up time.

Credentials live in `startup.ini` on the VPS disk; rotate the
auth token by re-running `setup_vps.ps1` AND updating the
dashboard.

---

## 5. Choosing between paths

| Need | Use |
|------|-----|
| Lowest operational overhead | `metaapi` |
| Full control + no third-party SaaS | `hosted` |
| Already own a Windows VPS for broker reasons | `ea` (with cluster egress exception) |

The `hosted` path is what the rest of this CHECKLIST section refers
to when it says 'self-hosted MetaTrader'. The previous version of
this document claimed `hosted` was production-ready while the engine
lacked the RBAC + NetworkPolicy + chart needed to make it work; that
is now resolved by the mt-node hardening series (this MR).
