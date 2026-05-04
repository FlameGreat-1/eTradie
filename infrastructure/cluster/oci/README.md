# infrastructure/cluster/oci/

OCI OKE cluster bootstrap module. **Skeleton only — not
production-ready.** Provides the variable surface and provider
versions so an OCI operator can extend `main.tf` with the actual
OKE module reference (`oracle/oci/oke`) without rewriting the rest
of the platform.

## Why a skeleton

The AWS module under `../aws/` is the working production reference.
Building an equivalent OKE module is substantial work that:

- requires a real OCI tenancy + compartment to validate against,
- pins instance shapes that should match the operator's reserved
  capacity (not the chart-default `c6i.2xlarge`),
- chooses a CNI (flannel / native pod networking) that affects
  NetworkPolicy enforcement.

Rather than commit untested code, this directory documents the
shape of what needs to exist; an operator with an OCI account fills
in `main.tf` against `oracle/oci/containerengine_cluster` and
`oracle/oci/containerengine_node_pool` (or the community OKE module).

## Vault paths

This module does NOT manage Vault paths. Apply `../vault-paths/`
separately after Vault is reachable. That separation lets the same
Vault path bootstrap work on AWS, OCI, or Contabo without
duplication.
