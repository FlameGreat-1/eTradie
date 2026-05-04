# infrastructure/cluster/variables.tf

variable "environment" {
  description = "Target environment. Drives naming and the Vault path scheme."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be one of: staging, production."
  }
}

variable "region" {
  description = "AWS region to deploy the cluster in."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name. Defaults to etradie-<environment>."
  type        = string
  default     = null
}

variable "kubernetes_version" {
  description = "EKS Kubernetes minor version."
  type        = string
  default     = "1.30"
}

variable "vpc_id" {
  description = "ID of an existing VPC to deploy into."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs (one per AZ) used for node groups and the EKS control-plane ENIs."
  type        = list(string)
  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "At least two private subnets are required for HA."
  }
}

variable "public_subnet_ids" {
  description = "Public subnet IDs used for the edge-ingress NLB."
  type        = list(string)
  validation {
    condition     = length(var.public_subnet_ids) >= 2
    error_message = "At least two public subnets are required for HA NLB."
  }
}

# Per-group node sizing. Each group is independently tunable so
# operators can scale edge vs internal vs system pools without
# changing the others. The defaults reflect the production posture
# documented in helm/<svc>/values-production.yaml (edge-ingress
# HPA maxReplicas=10, gateway HPA maxReplicas=10).

variable "edge_node_group" {
  description = "Sizing for the dedicated edge node group (taint workload=edge:NoSchedule). Hosts edge-ingress only."
  type = object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
  })
  default = {
    instance_types = ["c6i.2xlarge"]
    min_size       = 2
    max_size       = 10
    desired_size   = 3
  }
}

variable "etradie_system_node_group" {
  description = "Sizing for the dedicated etradie-system node group (taint workload=etradie-system:NoSchedule). Hosts gateway, engine, execution, management."
  type = object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
  })
  default = {
    instance_types = ["c6i.2xlarge"]
    min_size       = 3
    max_size       = 20
    desired_size   = 3
  }
}

variable "system_node_group" {
  description = "Sizing for the untainted add-ons node group. Hosts cluster-autoscaler, metrics-server, prometheus-adapter, ESO, ALB controller, ArgoCD."
  type = object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
  })
  default = {
    instance_types = ["c5.large"]
    min_size       = 2
    max_size       = 4
    desired_size   = 2
  }
}

variable "vault_address" {
  description = "Vault HTTPS endpoint reachable from the EKS cluster (used by ESO)."
  type        = string
}

variable "vault_namespace" {
  description = "Optional Vault namespace (HCP / enterprise). Empty for OSS."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags applied to every AWS resource."
  type        = map(string)
  default     = {}
}
