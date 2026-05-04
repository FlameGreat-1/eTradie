# Deploying eTradie on OCI OKE (Oracle Kubernetes Engine)

End-to-end production deployment of the full eTradie platform onto
Oracle Cloud Infrastructure (OCI) using OKE (Oracle Container
Engine for Kubernetes). After completing this runbook you will
have a publicly reachable, Cloudflare-Tunnel-fronted eTradie
deployment running on OCI managed Kubernetes.

Most of this runbook is **identical** to the Contabo K3s guide
(`contabo-k3s.md`). The only OCI-specific sections are:

* Section 0–3 (cluster + storage provisioning).
* Section 9.x (OCI-native backup + DR).

From section 4 (Vault) onwards, every command works on any
Kubernetes cluster. That is by design: the chart code is cluster-
agnostic.

---

## Architecture

```text
Internet
   |
   v
Cloudflare edge        (TLS, DDoS, anycast)
   |
   v  outbound tunnel  (cloudflared inside the OKE cluster)
+--------------------------------------------------------------+
| OCI tenancy / compartment                                     |
|                                                               |
|  VCN (10.0.0.0/16)                                            |
|    +- public subnet  (10.0.1.0/24)   <-- node pool / NAT      |
|    +- private subnet (10.0.2.0/24)   <-- OKE control plane    |
|                                                               |
|  OKE cluster (3 worker nodes across 3 ADs)                    |
|    edge-ingress-system: cloudflared + edge-ingress            |
|    envoy-system:        etradie-envoy                         |
|    etradie-system:      gateway, engine, execution,           |
|                         management, postgres, redis, chromadb |
|    vault, external-secrets, argocd: platform infra            |
|                                                               |
|  Block Volumes (oci-bv) for postgres / redis / chromadb PVCs  |
|  Object Storage bucket for Postgres pg_dump off-cluster sync  |
+--------------------------------------------------------------+
```

No public LoadBalancer is provisioned. Cloudflare Tunnel is
outbound-only.

---

## 0. Prerequisites

* OCI tenancy + a dedicated compartment (e.g. `etradie-prod`).
* An OCI user with API key and a group / policy granting:
  ```
  Allow group <etradie-admins> to manage all-resources in compartment etradie-prod
  ```
* OCI CLI installed locally and configured (`~/.oci/config`).
  Verify: `oci iam region list`.
* The same workstation tools as Contabo: `kubectl`, `helm`,
  `terraform`, `vault` CLI, `cloudflared`.
* A Cloudflare zone (Free plan suffices).

---

## 1. VCN + subnets

Use the OCI Networking quick-start to create a VCN with internet +
NAT gateways, or apply the snippet below directly via terraform.

```hcl
resource "oci_core_vcn" "etradie" {
  compartment_id = var.compartment_id
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "etradie-${var.environment}"
  dns_label      = "etradie"
}

resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.etradie.id
  display_name   = "etradie-igw"
}

resource "oci_core_nat_gateway" "nat" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.etradie.id
  display_name   = "etradie-nat"
}

resource "oci_core_subnet" "public" {
  compartment_id    = var.compartment_id
  vcn_id            = oci_core_vcn.etradie.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "etradie-public"
  dns_label         = "public"
  prohibit_internet_ingress = false
}

resource "oci_core_subnet" "private" {
  compartment_id    = var.compartment_id
  vcn_id            = oci_core_vcn.etradie.id
  cidr_block        = "10.0.2.0/24"
  display_name      = "etradie-private"
  dns_label         = "private"
  prohibit_internet_ingress = true
}
```

Apply via terraform; capture the subnet OCIDs as outputs.

---

## 2. OKE cluster

### 2.1 Provision via Terraform (recommended)

The repo ships an OCI skeleton at `infrastructure/cluster/oci/` with
the variable surface. Fill in `main.tf` with one of:

```hcl
# Option A: community module (oracle-quickstart/oke-quickstart)
module "oke" {
  source  = "oracle-quickstart/oke-quickstart/oci"
  version = "~> 5.1"

  compartment_ocid = var.compartment_id
  region           = var.region
  vcn_id           = oci_core_vcn.etradie.id
  k8s_version      = var.kubernetes_version

  worker_pools = {
    platform = {
      shape         = var.node_pool_shape   # VM.Standard.E5.Flex
      ocpus         = 4
      memory        = 32
      size          = var.node_pool_size    # 3
      boot_volume_size = 100
    }
  }

  freeform_tags = var.tags
}
```

```hcl
# Option B: native resources (more control)
resource "oci_containerengine_cluster" "etradie" {
  compartment_id     = var.compartment_id
  kubernetes_version = var.kubernetes_version
  name               = local.cluster_name
  vcn_id             = oci_core_vcn.etradie.id

  options {
    service_lb_subnet_ids = [oci_core_subnet.public.id]
    add_ons {
      is_kubernetes_dashboard_enabled = false
      is_tiller_enabled               = false
    }
  }
}

resource "oci_containerengine_node_pool" "platform" {
  cluster_id         = oci_containerengine_cluster.etradie.id
  compartment_id     = var.compartment_id
  kubernetes_version = var.kubernetes_version
  name               = "platform"
  node_shape         = var.node_pool_shape

  node_shape_config {
    ocpus         = 4
    memory_in_gbs = 32
  }

  node_config_details {
    placement_configs {
      availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
      subnet_id           = oci_core_subnet.public.id
    }
    placement_configs {
      availability_domain = data.oci_identity_availability_domains.ads.availability_domains[1].name
      subnet_id           = oci_core_subnet.public.id
    }
    placement_configs {
      availability_domain = data.oci_identity_availability_domains.ads.availability_domains[2].name
      subnet_id           = oci_core_subnet.public.id
    }
    size = var.node_pool_size
  }

  node_source_details {
    image_id    = data.oci_core_images.oke_image.images[0].id
    source_type = "IMAGE"
  }
}
```

Apply:

```bash
cd infrastructure/cluster/oci
terraform init
terraform apply -var environment=production -var compartment_id=<...>
```

### 2.2 Provision via OCI CLI (manual fallback)

```bash
oci ce cluster create \
  --compartment-id <compartment-ocid> \
  --vcn-id <vcn-ocid> \
  --kubernetes-version v1.30.1 \
  --name etradie-production \
  --service-lb-subnet-ids '["<public-subnet-ocid>"]' \
  --wait-for-state SUCCEEDED

oci ce node-pool create \
  --cluster-id <cluster-ocid> \
  --compartment-id <compartment-ocid> \
  --kubernetes-version v1.30.1 \
  --name platform \
  --node-shape VM.Standard.E5.Flex \
  --node-shape-config '{"ocpus": 4, "memoryInGBs": 32}' \
  --size 3 \
  --placement-configs '[{...},{...},{...}]'
```

---

## 3. Authenticate kubectl + verify storage

```bash
oci ce cluster create-kubeconfig \
  --cluster-id <cluster-ocid> \
  --file ~/.kube/etradie-oci.yaml \
  --region <region> \
  --token-version 2.0.0

export KUBECONFIG=~/.kube/etradie-oci.yaml
kubectl get nodes
# 3 nodes Ready, one per AD

kubectl get storageclass
# Expected: oci-bv (default), oci-bv-encrypted
```

If `oci-bv` is not the default StorageClass:

```bash
kubectl patch storageclass oci-bv \
  -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

The data-layer chart's PVCs use the cluster default; this works
out-of-the-box on OKE.

---

## 4. Install Vault (HA mode, 3 replicas)

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

kubectl create namespace vault

helm install vault hashicorp/vault \
  --namespace vault \
  --version 0.28.1 \
  --set 'server.ha.enabled=true' \
  --set 'server.ha.replicas=3' \
  --set 'server.ha.raft.enabled=true' \
  --set 'server.dataStorage.size=10Gi' \
  --set 'server.dataStorage.storageClass=oci-bv' \
  --set 'ui.enabled=true'
```

### 4.1 Initialise + unseal

```bash
kubectl -n vault wait --for=condition=Ready pod/vault-0 --timeout=120s
kubectl -n vault exec -ti vault-0 -- vault operator init \
  -key-shares=5 -key-threshold=3 > vault-init.txt

for i in 1 2 3; do
  KEY=$(grep "Unseal Key $i:" vault-init.txt | awk '{print $4}')
  kubectl -n vault exec -ti vault-0 -- vault operator unseal "$KEY"
done

# Join + unseal vault-1 and vault-2 against the leader (vault-0):
for pod in vault-1 vault-2; do
  kubectl -n vault exec -ti $pod -- vault operator raft join http://vault-0.vault-internal:8200
  for i in 1 2 3; do
    KEY=$(grep "Unseal Key $i:" vault-init.txt | awk '{print $4}')
    kubectl -n vault exec -ti $pod -- vault operator unseal "$KEY"
  done
done

kubectl -n vault exec -ti vault-0 -- vault status
# All 3 nodes "active" or "standby"; not "sealed".
```

### 4.2 Configure auth + KV + ESO policy

*Identical to the Contabo guide section 3.3.*

```bash
ROOT_TOKEN=$(grep 'Initial Root Token:' vault-init.txt | awk '{print $4}')
kubectl -n vault port-forward svc/vault 8200:8200 &
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=$ROOT_TOKEN

vault secrets enable -version=2 -path=secret kv
vault auth enable kubernetes
vault write auth/kubernetes/config \
  kubernetes_host=https://kubernetes.default.svc.cluster.local

vault policy write etradie-eso - <<'EOF'
path "secret/data/etradie/*" { capabilities = ["read", "list"] }
path "secret/metadata/etradie/*" { capabilities = ["read", "list"] }
EOF

vault write auth/kubernetes/role/etradie-eso \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=etradie-eso ttl=1h
```

---

## 5. External Secrets Operator

*Identical to Contabo guide section 4.* No OCI-specific changes.

```bash
helm repo add external-secrets https://charts.external-secrets.io
kubectl create namespace external-secrets
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --version 0.10.4 --set installCRDs=true

cat <<'EOF' | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata: { name: vault-backend }
spec:
  provider:
    vault:
      server: "http://vault.vault.svc.cluster.local:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "etradie-eso"
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
EOF
```

---

## 6. Cloudflare Tunnel

*Identical to Contabo guide section 5.* The tunnel runs as a pod
in OKE; OCI does not need any inbound LB or public IP.

Follow `docs/deployment/contabo-k3s.md` section 5 verbatim, then
proceed.

---

## 7. Vault path bootstrap + populate secrets

*Identical to Contabo guide section 6.* Run
`infrastructure/cluster/vault-paths/` against the OKE cluster's
Vault, then `vault kv put` every secret from the same command list.

---

## 8. ArgoCD

*Identical to Contabo guide section 7.* Sync waves apply unchanged.

---

## 9. End-to-end verification

*Identical to Contabo guide section 8.* All curl commands target
`https://api.etradie.com/...` regardless of which cluster is
backing the Tunnel.

---

## 10. OCI-specific day-2 operations

### 10.1 Block Volume snapshots for Postgres PVC

OKE's `oci-bv` provisioner creates OCI Block Volumes. Snapshot the
Postgres PVC nightly via OCI Volume Backup Policy:

```bash
PVC_BV_OCID=$(kubectl -n etradie-system get pvc data-postgres-0 \
  -o jsonpath='{.spec.volumeName}' | xargs -I {} kubectl get pv {} \
  -o jsonpath='{.spec.csi.volumeHandle}')

oci bv volume-backup-policy-assignment create \
  --asset-id $PVC_BV_OCID \
  --policy-id <bronze-or-silver-policy-ocid>
```

Use the OCI-managed Bronze (weekly), Silver (daily), or Gold (hourly)
policy depending on RPO requirements.

### 10.2 Off-cluster Postgres dumps to OCI Object Storage

The data-layer chart's CronJob writes `pg_dump` to a `/backups`
PVC. To sync those files to OCI Object Storage, add a sidecar
step to the CronJob (or a separate CronJob) using `oci os object
put`:

```yaml
# values-production.yaml addition:
postgres:
  backup:
    extraSyncCommand: |
      oci os object put --bucket-name etradie-prod-backups \
        --file "${TARGET}" --name "$(basename ${TARGET})" --force
```

(Requires mounting an OCI CLI config Secret into the CronJob pod;
not covered in detail here.)

### 10.3 OKE upgrade

OKE supports rolling upgrades:

```bash
oci ce cluster update --cluster-id <ocid> --kubernetes-version v1.31.1
oci ce node-pool update --node-pool-id <ocid> --kubernetes-version v1.31.1
```

The node pool replaces nodes one at a time; PDBs ensure no service
outage.

### 10.4 Node pool autoscaling

Enable the OKE Cluster Autoscaler add-on:

```bash
oci ce cluster install-addon \
  --cluster-id <ocid> \
  --addon-name ClusterAutoscaler
```

Configure min/max via the addon configuration CRD; the chart HPAs
then drive node-level scaling automatically.

### 10.5 Monitoring stack

*Identical to Contabo guide section 9.4.* Use
`kube-prometheus-stack` against OCI's default storage class.

---

## 11. Disaster recovery on OCI

### Single AD loss

The node pool is spread across 3 ADs (section 2.1). Loss of one AD
removes ~33% of nodes; HPA + topology spread constraints keep
service running. No operator action needed.

### Region loss

RTO ~ 90 minutes. RPO ~ 24 hours (last nightly dump synced to
Object Storage).

1. Provision OKE in a paired region (`oci-ashburn-1` <->
   `oci-phoenix-1`, etc.) using sections 1–3 of this guide.
2. Restore Vault from the most recent Raft snapshot stored in the
   paired region's Object Storage bucket.
3. Repeat sections 5 (ESO), 8 (ArgoCD).
4. Restore the most recent Postgres `pg_dump` from Object Storage.
5. Update Cloudflare Tunnel to point at the new cluster (re-issue
   token in Cloudflare Zero Trust UI; update Vault; restart
   cloudflared).
6. DNS is unaffected (CNAME still points to the same
   `<tunnel-id>.cfargotunnel.com`).

---

## What is identical to Contabo / kubeadm / GKE / AKS / kind

| Component | OCI-specific? |
|---|---|
| Cloudflare Tunnel + cloudflared chart template | No |
| Edge-ingress, envoy, gateway, engine, execution, management charts | No |
| Vault install command (only the storage class differs) | Mostly no |
| ESO ClusterSecretStore | No |
| ArgoCD install + AppProject + root-app | No |
| Vault path bootstrap (`infrastructure/cluster/vault-paths/`) | No |
| Cloudflare zone Terraform (`infrastructure/cloudflare/`) | No |
| Public hostnames, DNS records, TLS posture | No |

The **only** OCI-specific code lives under
`infrastructure/cluster/oci/`. Everything else is reused verbatim
from the Contabo guide. That is the proof that the platform is
truly write-once-deploy-anywhere.

---

## Reference

* Cluster skeleton:        `infrastructure/cluster/oci/`
* Cloud-agnostic Vault paths: `infrastructure/cluster/vault-paths/`
* Cloudflare zone:         `infrastructure/cloudflare/`
* Edge defence chain:      `docs/architecture/edge-cloudflare-envoy.md`
* Contabo guide (companion): `docs/deployment/contabo-k3s.md`
