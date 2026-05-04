# eTradie deployment runbooks

This directory is the **single authoritative source** for deploying
the eTradie platform onto a Kubernetes cluster.

## Pick your target

| Target | Guide | When to choose |
|---|---|---|
| Contabo VPS (K3s, single or multi-node) | [`contabo-k3s.md`](./contabo-k3s.md) | Cheapest, self-managed. Best for staging or a single-region production. |
| OCI OKE (Oracle managed Kubernetes) | [`oci-oke.md`](./oci-oke.md) | Managed control plane, AD-spread for HA, native Block Volume snapshots. Best for multi-AZ production. |
| Anything else (kubeadm, GKE, AKS, kind, k3d) | Follow `contabo-k3s.md` from section 2 onwards | Same chart code, same Vault paths, same ArgoCD wiring. Only the cluster provisioning step changes. |

## What is the same on every target

Everything from section 4 onwards in either runbook (Vault, ESO,
Cloudflare Tunnel, Vault path bootstrap, ArgoCD, AppProject,
verification, day-2 ops) is **identical**. That is by design: the
chart code is cluster-agnostic.

The only target-specific details are:

* Cluster provisioning (`k3s install ...` vs `oci ce cluster create`).
* Storage class name (`local-path` on K3s, `oci-bv` on OKE).
* Backup destination (off-VPS rsync vs OCI Object Storage).
* Vault HA topology (single-node fine for K3s on one VPS; HA Raft
  recommended on OKE multi-AD).

The edge layer is identical because Cloudflare Tunnel does not care
which cluster is on the other end of the outbound connection.

## Cluster topology summary

```text
Internet -> Cloudflare edge -> Cloudflare Tunnel
                                     |
                                     v
                           cloudflared pod (in cluster)
                                     |
                                     v
                           edge-ingress (TLS termination, geo-routing)
                                     |
                                     v
                           etradie-envoy (WASM filters, rate limit)
                                     |
                                     v
                           gateway (auth, orchestration)
                                     |
              +----------------------+----------------------+
              v                      v                      v
           engine                execution               management
           (Python)                (Go)                    (Go)
              \                      |                      /
               \                     v                     /
                +--> postgres / redis / chromadb (data layer) <--+
```

All pods run inside the cluster. No port is exposed from any node
to the public internet.

## Prerequisites common to every target

* A registered domain on Cloudflare with the zone in **Active** state.
* Cloudflare Zero Trust (Free) for the Tunnel.
* A Vault instance the cluster can reach (the runbooks install Vault
  in-cluster by default).
* Workstation tools: `kubectl >= 1.28`, `helm >= 3.14`,
  `terraform >= 1.6`, `vault >= 1.15`.

## What this directory does NOT cover

* **Broker / MT5 EA deployment** — that is a separate concern
  documented at [`../vps/deployment_guide.md`](../vps/deployment_guide.md)
  (Windows VPS for MT5 + ZeroMQ Expert Advisor).
* **Local development** — see the root `docker-compose.yml` and
  `Makefile` targets (`make dev-up`, `make dev-down`).
* **Code-level architecture** — see
  [`../architecture/edge-cloudflare-envoy.md`](../architecture/edge-cloudflare-envoy.md)
  for the four-layer defence chain rationale (note: the apply
  commands in that file are historical; use the runbooks here).
