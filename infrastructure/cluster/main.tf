# infrastructure/cluster/main.tf
#
# Owns the EKS cluster, the default node group, OIDC provider, IAM
# roles needed by add-ons, and the Vault path schema bootstrap. Does
# NOT install any Kubernetes resources - that is ArgoCD's job once the
# cluster is reachable.

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

  eks_managed_node_groups = {
    default = {
      instance_types = var.node_group_instance_types
      min_size       = var.node_group_min_size
      max_size       = var.node_group_max_size
      desired_size   = var.node_group_desired_size

      labels = {
        "workload" = "etradie-system"
      }

      taints = []

      # Force IMDSv2 (security baseline).
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
