# infrastructure/cluster/oci/main.tf
#
# OCI OKE cluster + autoscaled node pool for the eTradie platform.
#
# Owns:
#   - The OKE cluster control plane.
#   - The platform node pool, tainted workload=etradie-system:NoSchedule
#     so only eTradie workloads with the matching toleration land here.
#   - The kubeconfig output (sensitive).
#
# Does NOT own:
#   - The VCN, subnets, NAT gateways. Operator passes them as variables.
#   - The Cluster Autoscaler. Installed via Helm (bootstrap README).
#   - Any Kubernetes manifest (those land via ArgoCD).
#
# Apply order:
#   1. terraform init
#   2. terraform apply -var-file=<env>.tfvars
#   3. terraform output -raw kubeconfig > ~/.kube/etradie-<env>.yaml
#   4. KUBECONFIG=~/.kube/etradie-<env>.yaml kubectl get nodes
#   5. Follow cluster/bootstrap/ steps 1-9 (ESO, Vault paths, ArgoCD).

locals {
  cluster_name = coalesce(var.cluster_name, "etradie-${var.environment}")
  default_tags = merge(
    {
      environment = var.environment
      app         = "etradie"
      managed-by  = "terraform"
    },
    var.tags,
  )
}

# ---------------------------------------------------------------------
# OKE Cluster (Enhanced)
# Enhanced gives us cluster add-on management, virtual node pools,
# and the K8s API features the platform charts rely on (ServerSide
# Apply, native sidecar containers).
# ---------------------------------------------------------------------
resource "oci_containerengine_cluster" "etradie" {
  compartment_id     = var.compartment_id
  kubernetes_version = var.kubernetes_version
  name               = local.cluster_name
  vcn_id             = var.vcn_id
  type               = "ENHANCED_CLUSTER"

  endpoint_config {
    is_public_ip_enabled = var.kubernetes_endpoint_is_public
    subnet_id            = var.kubernetes_api_subnet_id
    nsg_ids              = var.kubernetes_api_nsg_ids
  }

  options {
    service_lb_subnet_ids = var.kubernetes_lb_subnet_ids

    kubernetes_network_config {
      pods_cidr     = var.pods_cidr
      services_cidr = var.services_cidr
    }

    add_ons {
      is_kubernetes_dashboard_enabled = false
      is_tiller_enabled               = false
    }

    admission_controller_options {
      is_pod_security_policy_enabled = false # PSP removed in 1.25+; we use PSA via namespace labels
    }
  }

  cluster_pod_network_options {
    cni_type = "OCI_VCN_IP_NATIVE"
  }

  image_policy_config {
    is_policy_enabled = false # Sigstore/AdmissionReview not in scope for v0.1.0
  }

  freeform_tags = local.default_tags
}

# ---------------------------------------------------------------------
# Platform node pool
# ---------------------------------------------------------------------
resource "oci_containerengine_node_pool" "platform" {
  cluster_id         = oci_containerengine_cluster.etradie.id
  compartment_id     = var.compartment_id
  kubernetes_version = var.kubernetes_version
  name               = "${local.cluster_name}-platform"
  node_shape         = var.node_pool_shape

  node_shape_config {
    ocpus         = var.node_pool_ocpus
    memory_in_gbs = var.node_pool_memory_gbs
  }

  node_source_details {
    source_type             = "IMAGE"
    image_id                = var.node_pool_image_id
    boot_volume_size_in_gbs = var.node_pool_boot_volume_size_gbs
  }

  node_config_details {
    size = var.node_pool_size

    dynamic "placement_configs" {
      for_each = var.node_pool_availability_domains
      content {
        availability_domain = placement_configs.value
        subnet_id           = var.kubernetes_worker_subnet_id
      }
    }

    kms_key_id = var.node_pool_kms_key_id

    # Cluster-autoscaler relies on these annotations to size up/down
    # the pool. Each tag is consumed by the helm chart at bootstrap.
    freeform_tags = merge(
      local.default_tags,
      {
        "k8s.io_cluster-autoscaler_enabled"                = "true"
        "k8s.io_cluster-autoscaler_${local.cluster_name}"  = "owned"
        "k8s.io_cluster-autoscaler_node-template_min-size" = tostring(var.node_pool_min_size)
        "k8s.io_cluster-autoscaler_node-template_max-size" = tostring(var.node_pool_max_size)
      },
    )

    is_pv_encryption_in_transit_enabled = true
  }

  # Apply the etradie-system taint so only Pods with the matching
  # toleration (set in every values-production.yaml) schedule here.
  initial_node_labels {
    key   = "workload"
    value = "etradie-system"
  }

  # NOTE: OCI's API exposes node taints via initial_node_labels +
  # node_eviction_node_pool_settings is for upgrades. Actual NoSchedule
  # taint application happens via the kubelet config below; OCI does
  # not expose taints directly on the node pool API, so we use the
  # documented workaround of a kubelet --register-with-taints arg in
  # the node metadata.
  node_metadata = {
    user_data = base64encode(<<-EOT
      #!/bin/bash
      curl --fail -H "Authorization: Bearer Oracle" -L0 \
        http://169.254.169.254/opc/v2/instance/metadata/oke_init_script \
        | base64 --decode > /var/run/oke-init.sh
      bash /var/run/oke-init.sh \
        --kubelet-extra-args "--register-with-taints=workload=etradie-system:NoSchedule"
    EOT
    )
  }

  freeform_tags = local.default_tags

  lifecycle {
    ignore_changes = [
      # autoscaler mutates this at runtime; do not fight it.
      node_config_details[0].size,
      kubernetes_version,
    ]
  }
}

# ---------------------------------------------------------------------
# Kubeconfig (sensitive output)
# ---------------------------------------------------------------------
data "oci_containerengine_cluster_kube_config" "etradie" {
  cluster_id    = oci_containerengine_cluster.etradie.id
  expiration    = 2592000
  token_version = "2.0.0"
}
