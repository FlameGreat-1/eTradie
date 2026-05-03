variable "namespace" {
  description = "Kubernetes namespace the gateway runs in. Must exist before apply (created by cluster-bootstrap)."
  type        = string
  default     = "etradie-system"
}

variable "environment" {
  description = "Target environment. Selects the kustomize overlay under deployments/gateway/kubernetes/overlays/."
  type        = string
  default     = "production"
  validation {
    condition     = contains(["local", "staging", "production"], var.environment)
    error_message = "environment must be one of: local, staging, production."
  }
}

variable "image_repository" {
  description = "Container image repository for the gateway."
  type        = string
  default     = "registry.gitlab.com/cotradee3/cotradeecode/gateway"
}

variable "image_tag" {
  description = "Image tag (typically a SHA injected by CI)."
  type        = string
  default     = "0.1.0"
}

variable "replicas_min" {
  description = "HPA minimum replica count."
  type        = number
  default     = 2
  validation {
    condition     = var.replicas_min >= 1
    error_message = "replicas_min must be at least 1."
  }
}

variable "replicas_max" {
  description = "HPA maximum replica count. Must be >= replicas_min."
  type        = number
  default     = 6
}

variable "vault_path" {
  description = "Vault path resolved by the ExternalSecret for the gateway."
  type        = string
  default     = "etradie/services/gateway"
}

variable "log_level" {
  description = "GATEWAY_LOG_LEVEL value."
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARN", "ERROR"], var.log_level)
    error_message = "log_level must be one of: DEBUG, INFO, WARN, ERROR."
  }
}

variable "trusted_proxy_cidrs" {
  description = "Comma-separated CIDRs trusted by the auth client-IP resolver."
  type        = string
  default     = "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
}

variable "trust_cloudflare" {
  description = "Whether AUTH_TRUST_CLOUDFLARE is set to true."
  type        = bool
  default     = false
}

variable "kustomize_path" {
  description = "Path to the kustomize tree (relative to repo root). Override only for vendored tests."
  type        = string
  default     = "deployments/gateway/kubernetes"
}

variable "repo_root" {
  description = "Absolute or workspace-relative path to the repo root. Defaults to the standard CI checkout layout."
  type        = string
  default     = "${path.root}/../.."
}
