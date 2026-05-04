# infrastructure/cluster/vault-paths/

Cloud-agnostic Vault KV-v2 path bootstrap. Creates the empty paths
the platform charts' ExternalSecrets reference, with no AWS / OCI /
GCP provider dependency.

## When to apply

After Vault is reachable from the operator's machine. Vault itself
can be:

- HCP Vault (managed),
- Vault chart on the same K8s cluster the platform will run on,
- Vault VM external to the cluster.

The ESO (External Secrets Operator) ClusterSecretStore separately
authenticates pods to Vault; this module only creates the **paths**.

## Apply

```bash
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=...   # token with secret/data/etradie/* write

terraform init
terraform apply \
  -var environment=production \
  -var vault_address=$VAULT_ADDR
```

## What it creates

| Path | Used by |
|---|---|
| `etradie/services/edge-ingress/<env>/tls` | edge-ingress per-host TLS certs |
| `etradie/services/edge-ingress/<env>/cloudflare/aop_ca` | Cloudflare AOP CA bundle |
| `etradie/services/edge-ingress/<env>/cloudflare/tunnel` | Cloudflare Tunnel token |
| `etradie/services/edge-ingress/<env>/maxmind` | MaxMind GeoLite credentials |
| `etradie/services/gateway/<env>` | gateway DB / JWT / encryption keys |
| `etradie/services/engine/<env>` | engine LLM / data-provider keys |
| `etradie/services/execution/<env>` | execution DB + broker creds |
| `etradie/services/management/<env>` | management DB + broker creds |

All paths are seeded with a `bootstrap: placeholder` value that the
operator overwrites with real bytes; subsequent terraform applies
leave operator-written values intact (`lifecycle.ignore_changes`).
