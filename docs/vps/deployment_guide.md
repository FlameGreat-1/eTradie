# MetaTrader Hosting Deployment Guide

> Production deployment guide for eTradie's MetaTrader integration paths.
>
> The eTradie platform supports two connection types for MetaTrader 4 and 5
> in production: `hosted` (our K8s cluster runs MT under Wine+Xvfb) and
> `metaapi` (MetaApi.cloud managed SaaS). Pick the one that matches your
> hosting model.

---

## 1. Connection types at a glance

| Type | Where MT runs | Provisioning | Auto-recovery | Production-ready |
|------|---------------|--------------|---------------|------------------|
| `hosted` | Linux container inside your K8s cluster (helm/mt-node chart) | Engine API at runtime | K8s controllers + watchdog sidecar | YES (this guide, section 2) |
| `metaapi` | MetaApi.cloud (managed) | MetaApiProvisioner | MetaApi.cloud SLA | YES (no infra to manage; see MetaApi docs) |

> A third enum value, `connection_type='ea'`, exists in the codebase
> as a local-development escape hatch only. It reads single-tenant
> `MT5_ZMQ_*` env vars from the engine's own environment and is
> disabled in production by `ENGINE_DISALLOW_EA_CONNECTION_TYPE=true`
> in `values-production.yaml`. It is NOT a user-facing connection
> type and is not documented here for user consumption.

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
└──────────────────────────────────────────────────────────┘
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

## 4. Choosing between paths

| Need | Use |
|------|-----|
| Lowest operational overhead | `metaapi` |
| Full control + no third-party SaaS | `hosted` |

The `hosted` path is what the rest of this CHECKLIST section refers
to when it says 'self-hosted MetaTrader'. The previous version of
this document claimed `hosted` was production-ready while the engine
lacked the RBAC + NetworkPolicy + chart needed to make it work; that
is now resolved by the mt-node hardening series.
