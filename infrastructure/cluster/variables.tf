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

variable "node_group_instance_types" {
  description = "EC2 instance types for the default node group."
  type        = list(string)
  default     = ["c6i.2xlarge"]
}

variable "node_group_min_size" {
  description = "Minimum node count."
  type        = number
  default     = 3
}

variable "node_group_max_size" {
  description = "Maximum node count."
  type        = number
  default     = 12
}

variable "node_group_desired_size" {
  description = "Initial node count."
  type        = number
  default     = 3
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
