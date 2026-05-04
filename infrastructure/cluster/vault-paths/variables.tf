variable "environment" {
  description = "Target environment. Drives the Vault path scheme."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be one of: staging, production."
  }
}

variable "vault_address" {
  description = "Vault HTTPS endpoint."
  type        = string
}

variable "vault_namespace" {
  description = "Optional Vault namespace (HCP / Enterprise). Empty for OSS."
  type        = string
  default     = ""
}

variable "vault_mount" {
  description = "KV-v2 mount name. Default 'secret' matches Vault dev defaults; production deployments often use a dedicated mount per app."
  type        = string
  default     = "secret"
}
