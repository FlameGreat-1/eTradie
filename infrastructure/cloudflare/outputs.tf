output "hostnames" {
  description = "Hostnames managed by this module and their CNAME targets (Cloudflare Tunnel UUIDs)."
  value       = var.hostnames
}

output "authenticated_origin_pulls_enabled" {
  description = "Whether AOP is enabled at the zone level."
  value       = var.enable_authenticated_origin_pulls
}

output "min_tls_version" {
  description = "Configured Cloudflare minimum TLS version."
  value       = var.min_tls_version
}

output "waf_enabled" {
  description = "Whether the Cloudflare Managed Ruleset (WAF) is deployed."
  value       = var.enable_waf
}

output "rate_limiting_enabled" {
  description = "Whether per-IP edge rate-limit rules on /api/* and /auth/* are deployed (TIER4 A2c)."
  value       = var.enable_rate_limiting
}

output "bot_management_enabled" {
  description = "Whether Super Bot Fight Mode is enabled (requires plan entitlement)."
  value       = var.enable_bot_management
}

output "hsts_enabled" {
  description = "Whether the HSTS response-header transform rule is deployed at the edge."
  value       = var.enable_hsts
 }
