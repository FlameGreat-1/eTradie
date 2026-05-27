variable "environment" {
  description = "Target environment. Drives the Vault path scheme."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be one of: staging, production."
  }
}

variable "vault_address" {
  description = "Vault HTTPS endpoint. Authentication is performed via VAULT_TOKEN env var (operator must export before terraform apply). Audit ref: IV-H1."
  type        = string
}

variable "vault_namespace" {
  description = "Optional Vault namespace (HCP / Enterprise). Empty for OSS."
  type        = string
  default     = ""
}

variable "vault_mount" {
  description = "KV-v2 mount name. Default 'etradie' uses a dedicated mount per app (production posture). The dev 'secret' mount is intentionally NOT the default to prevent an accidental write to an unprivileged path. Audit ref: IV-M2."
  type        = string
  default     = "etradie"
}
