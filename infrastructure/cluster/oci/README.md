# infrastructure/cluster/oci/

Provisions an Oracle OKE Enhanced cluster + autoscaled platform node
pool. Wires up the `workload=etradie-system:NoSchedule` taint that
every `values-production.yaml` toleration is configured to match.

## What it owns

- `oci_containerengine_cluster.etradie` (Enhanced cluster).
- `oci_containerengine_node_pool.platform` (autoscaled).
- `kubeconfig` output (sensitive).

## What it does NOT own

- The VCN, subnets, NAT gateways, route tables. Operator brings these.
- The Cluster Autoscaler in-cluster Deployment. Installed via Helm
  after `terraform apply` (see `cluster/bootstrap/` step 9).
- The platform node image OCID. Operator passes the latest
  OKE-published Oracle Linux 8 image OCID for the target K8s version.

## Variables of note

| Var | Default | Notes |
|---|---|---|
| `kubernetes_version` | `v1.32.1` | bump explicitly per OCI patch line |
| `node_pool_shape` | `VM.Standard.E5.Flex` | tunable OCPU + memory |
| `node_pool_ocpus` | `4` | per-node OCPU |
| `node_pool_memory_gbs` | `32` | ~18 mt-node Pods per node at 1.5 GiB ceiling |
| `node_pool_min_size` | `3` | autoscaler floor; keep >= 3 for AD spread |
| `node_pool_max_size` | `12` | autoscaler ceiling; ~150 mt-node Pods total |
| `node_pool_availability_domains` | required | spread across all in-region ADs |
| `kubernetes_endpoint_is_public` | `false` | Cloudflare Tunnel default; flip only if you NEED a public endpoint |

## Apply order

```bash
terraform init
terraform apply -var-file=production.tfvars
terraform output -raw kubeconfig > ~/.kube/etradie-production.yaml
KUBECONFIG=~/.kube/etradie-production.yaml kubectl get nodes
```

Then follow `../bootstrap/README.md` from step 1 (cert-manager) onward.

## Taint

The `workload=etradie-system:NoSchedule` taint is applied via the
kubelet `--register-with-taints` flag through the node metadata
`user_data` (OCI does not expose pool taints via the API directly).
Every `values-production.yaml` in this repo already tolerates this
taint, so no chart change is required to land Pods.

## Audit refs

- CHECKLIST Section 5 - 'Predictable resource usage per new user'
- CHECKLIST Section 6 - 'Auto-healing system for crashed containers'
  (the autoscaler heals node failures; the Deployment heals Pod failures;
  the entrypoint.sh + watchdog heal terminal failures).
- IO-H2 - explicit kubernetes_version, no implicit minor bump.
