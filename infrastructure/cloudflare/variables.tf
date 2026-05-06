variable "environment" {
  description = "Target environment."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be one of: staging, production."
  }
}

variable "zone_id" {
  description = "Cloudflare zone ID for exoper.com (or staging.exoper.com)."
  type        = string
}

variable "hostnames" {
  description = "Map of hostname -> CNAME target. With Cloudflare Tunnel the target is `<tunnel-id>.cfargotunnel.com`. Example: { \"api.exoper.com\" = \"abcd1234-....cfargotunnel.com\" }"
  type        = map(string)
}

variable "enable_authenticated_origin_pulls" {
  description = "Whether to enable Authenticated Origin Pulls at the zone level. Recommended ON in all environments as defence-in-depth alongside Cloudflare Tunnel."
  type        = bool
  default     = true
}

variable "min_tls_version" {
  description = "Minimum TLS version Cloudflare will negotiate with clients."
  type        = string
  default     = "1.2"
}

variable "always_use_https" {
  description = "Force redirects from http -> https at the Cloudflare edge."
  type        = bool
  default     = true
}
