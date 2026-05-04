# infrastructure/cluster/main.tf
#
# Owns the EKS cluster, the default node group, OIDC provider, IAM
# roles needed by add-ons, and the Vault path schema bootstrap. Does
# NOT install any Kubernetes resources - that is ArgoCD's job once the
# cluster is reachable.

# Vault provider configuration. Required so the vault_kv_secret_v2
# resources below can actually reach Vault. Authentication is via
# the operator's `VAULT_TOKEN` environment variable (or any other
# auth method honoured by the Vault provider's default chain), so
# this module does not embed credentials.
provider "vault" {
  address = var.vault_address
  # Optional Vault Enterprise / HCP namespace. Empty for OSS Vault,
  # validated as such by variables.tf default.
  namespace = var.vault_namespace
}

locals {
  cluster_name = coalesce(var.cluster_name, "etradie-${var.environment}")
  common_tags = merge(
    {
      "app.kubernetes.io/part-of"   = "etradie"
      "app.kubernetes.io/managed-by" = "terraform"
      "etradie.com/environment"      = var.environment
    },
    var.tags,
  )
}

#
# 1. EKS cluster.
#
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.20"

  cluster_name    = local.cluster_name
  cluster_version = var.kubernetes_version

  vpc_id                   = var.vpc_id
  subnet_ids               = var.private_subnet_ids
  control_plane_subnet_ids = var.private_subnet_ids

  cluster_endpoint_public_access  = false
  cluster_endpoint_private_access = true

  # Encrypt secrets at rest with a customer-managed KMS key. The module
  # creates the key when one is not supplied, with appropriate IAM
  # policies for the EKS control plane.
  cluster_encryption_config = {
    resources = ["secrets"]
  }

  # OpenID Connect provider is required for IAM Roles for Service
  # Accounts (IRSA). External Secrets Operator, cluster-autoscaler,
  # and the AWS Load Balancer Controller all use IRSA roles below.
  enable_irsa = true

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # Three purpose-tainted node groups so production scheduling
  # actually segregates workloads. The taints here MUST match the
  # tolerations declared in helm/edge-ingress/values-production.yaml
  # and helm/gateway/values-production.yaml.
  eks_managed_node_groups = {
    # Dedicated edge group: only edge-ingress pods (which carry the
    # matching toleration) can schedule here. Hosts the public NLB
    # backends; isolated from internal traffic.
    edge = {
      instance_types = var.edge_node_group.instance_types
      min_size       = var.edge_node_group.min_size
      max_size       = var.edge_node_group.max_size
      desired_size   = var.edge_node_group.desired_size

      labels = {
        "workload" = "edge"
      }

      taints = [
        {
          key    = "workload"
          value  = "edge"
          effect = "NO_SCHEDULE"
        },
      ]

      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"
        http_put_response_hop_limit = 1
      }
    }

    # Dedicated etradie-system group: gateway / engine / execution /
    # management pods (which carry the matching toleration). Isolated
    # from edge ingress and from cluster add-ons.
    etradie_system = {
      instance_types = var.etradie_system_node_group.instance_types
      min_size       = var.etradie_system_node_group.min_size
      max_size       = var.etradie_system_node_group.max_size
      desired_size   = var.etradie_system_node_group.desired_size

      labels = {
        "workload" = "etradie-system"
      }

      taints = [
        {
          key    = "workload"
          value  = "etradie-system"
          effect = "NO_SCHEDULE"
        },
      ]

      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"
        http_put_response_hop_limit = 1
      }
    }

    # Untainted group for cluster add-ons (cluster-autoscaler,
    # metrics-server, prometheus-adapter, ESO, ALB controller, ArgoCD
    # itself). Add-ons must schedule somewhere even when both
    # workload-tainted groups are at capacity.
    system = {
      instance_types = var.system_node_group.instance_types
      min_size       = var.system_node_group.min_size
      max_size       = var.system_node_group.max_size
      desired_size   = var.system_node_group.desired_size

      labels = {
        "workload" = "system"
      }

      taints = []

      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"
        http_put_response_hop_limit = 1
      }
    }
  }

  tags = local.common_tags
}

#
# 2. IAM roles for cluster add-ons (IRSA pattern).
#
#    These roles are referenced by the Helm charts at
#    helm/edge-ingress, helm/envoy, helm/gateway via service-account
#    annotations. The role ARNs are exposed as outputs.
#

# External Secrets Operator: Vault-backed reads only.
module "irsa_eso" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.39"

  role_name = "${local.cluster_name}-eso"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = [
        "external-secrets:external-secrets",
      ]
    }
  }

  tags = local.common_tags
}

# cluster-autoscaler.
module "irsa_autoscaler" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.39"

  role_name                        = "${local.cluster_name}-autoscaler"
  attach_cluster_autoscaler_policy = true
  cluster_autoscaler_cluster_names = [module.eks.cluster_name]

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:cluster-autoscaler"]
    }
  }

  tags = local.common_tags
}

# AWS Load Balancer Controller (provisions the NLB the edge-ingress
# Service annotation requests).
module "irsa_alb" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.39"

  role_name                              = "${local.cluster_name}-alb-controller"
  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }

  tags = local.common_tags
}

#
# 3. Vault path schema bootstrap.
#
#    These resources create the empty KV-v2 paths the helm charts'
#    ExternalSecrets reference. They do NOT write secret bytes;
#    operators populate the paths after this module applies.
#
resource "vault_kv_secret_v2" "edge_ingress_tls" {
  mount               = "secret"
  name                = "etradie/services/edge-ingress/${var.environment}/tls"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; operator must populate before edge-ingress can roll out"
  })
  lifecycle {
    ignore_changes = [data_json] # operator-managed once bootstrapped
  }
}

resource "vault_kv_secret_v2" "edge_ingress_aop_ca" {
  mount               = "secret"
  name                = "etradie/services/edge-ingress/${var.environment}/cloudflare/aop_ca"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with the Cloudflare AOP CA PEM after the cloudflare module applies"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "edge_ingress_maxmind" {
  mount               = "secret"
  name                = "etradie/services/edge-ingress/${var.environment}/maxmind"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with MaxMind license_key + account_id"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "gateway" {
  mount               = "secret"
  name                = "etradie/services/gateway/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with auth_database_url, auth_jwt_secret, broker_encryption_key, llm_encryption_key, ..."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}
