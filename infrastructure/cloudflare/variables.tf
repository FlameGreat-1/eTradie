variable "environment" {
  description = "Target environment."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be one of: staging, production."
  }
}

variable "zone_id" {
  description = "Cloudflare zone ID for etradie.com (or staging.etradie.com)."
  type        = string
}

variable "hostnames" {
  description = "Map of hostname -> NLB hostname (CNAME target). Example: { \"api.etradie.com\" = \"k8s-eks-...elb.amazonaws.com\" }"
  type        = map(string)
}

variable "enable_authenticated_origin_pulls" {
  description = "Whether to enable Authenticated Origin Pulls at the zone level. Production = true; staging = optional."
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

variable "origin_security_group_id" {
  description = "AWS security group ID that fronts the NLB. Cloudflare published ranges will be the only ingress allowed on TCP/443 once the rules are applied."
  type        = string
}

variable "cloudflare_ipv4_ranges" {
  description = "Cloudflare published IPv4 origin ranges (one CIDR per element). Sourced from deployments/cloudflare/ip-ranges/ipv4.txt."
  type        = list(string)
}

variable "cloudflare_ipv6_ranges" {
  description = "Cloudflare published IPv6 origin ranges (one CIDR per element)."
  type        = list(string)
}

variable "tags" {
  description = "Tags for AWS resources created by this module."
  type        = map(string)
  default     = {}
}
