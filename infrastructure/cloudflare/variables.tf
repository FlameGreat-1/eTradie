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
  validation {
    condition     = length(var.hostnames) > 0
    error_message = "hostnames must contain at least one entry. Audit ref: IC-M3."
  }
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
  validation {
    condition     = contains(["1.0", "1.1", "1.2", "1.3"], var.min_tls_version)
    error_message = "min_tls_version must be one of 1.0, 1.1, 1.2, 1.3. Audit ref: IC-M2."
  }
}

variable "always_use_https" {
  description = "Force redirects from http -> https at the Cloudflare edge."
  type        = bool
  default     = true
}

# ---------------------------------------------------------------------------
# TIER4 A2c: abuse-prevention edge controls (WAF / rate limiting / bot).
# ---------------------------------------------------------------------------

variable "enable_waf" {
  description = "Deploy the Cloudflare Managed Ruleset (WAF) in the http_request_firewall_managed phase. Default ON."
  type        = bool
  default     = true
}

variable "enable_rate_limiting" {
  description = "Deploy per-IP edge rate-limit rules on /api/* and /auth/*. Default ON."
  type        = bool
  default     = true
}

variable "enable_bot_management" {
  description = "Enable the ENTERPRISE Cloudflare Bot Management resource (cloudflare_bot_management, ML bot scoring). Default OFF: requires the Enterprise Bot Management add-on; enabling on a non-Enterprise zone fails apply. Use enable_super_bot_fight_mode instead on Pro/Business. The two are mutually exclusive."
  type        = bool
  default     = false
}

variable "enable_super_bot_fight_mode" {
  description = "Enable Super Bot Fight Mode (Pro/Business plans) via the zone bot-fight-mode setting. Default OFF: requires a Pro or Business plan. Mutually exclusive with enable_bot_management (Enterprise)."
  type        = bool
  default     = false
}

variable "api_rate_limit_requests" {
  description = "Coarse per-IP request budget on /api/* within api_rate_limit_period. Sized generously so it only trips on volumetric abuse; the origin enforces per-user limits."
  type        = number
  default     = 600
  validation {
    condition     = var.api_rate_limit_requests >= 1 && var.api_rate_limit_requests <= 1000000
    error_message = "api_rate_limit_requests must be 1..1000000."
  }
}

variable "api_rate_limit_period" {
  description = "Window (seconds) for the /api/* per-IP rate limit. Cloudflare allows 10, 60, 120, 300, 600, 3600."
  type        = number
  default     = 60
  validation {
    condition     = contains([10, 60, 120, 300, 600, 3600], var.api_rate_limit_period)
    error_message = "api_rate_limit_period must be one of 10, 60, 120, 300, 600, 3600 (Cloudflare-allowed periods)."
  }
}

variable "auth_rate_limit_requests" {
  description = "TIGHTER per-IP request budget on /auth/* within auth_rate_limit_period to blunt credential stuffing."
  type        = number
  default     = 20
  validation {
    condition     = var.auth_rate_limit_requests >= 1 && var.auth_rate_limit_requests <= 100000
    error_message = "auth_rate_limit_requests must be 1..100000."
  }
}

variable "auth_rate_limit_period" {
  description = "Window (seconds) for the /auth/* per-IP rate limit. Cloudflare allows 10, 60, 120, 300, 600, 3600."
  type        = number
  default     = 60
  validation {
    condition     = contains([10, 60, 120, 300, 600, 3600], var.auth_rate_limit_period)
    error_message = "auth_rate_limit_period must be one of 10, 60, 120, 300, 600, 3600 (Cloudflare-allowed periods)."
  }
}
