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
