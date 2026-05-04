# infrastructure/cloudflare/main.tf
#
# Owns:
# - Cloudflare zone-level settings (TLS minimum, AOP enablement,
#   always-use-https).
# - DNS records pointing the public hostnames at the Cloudflare
#   Tunnel UUID (`<tunnel-id>.cfargotunnel.com`) created in the
#   Cloudflare Zero Trust UI / via cloudflare_zero_trust_tunnel.
#
# Does NOT own:
# - The AOP CA bytes (those live in Vault, written by the operator
#   after the cloudflare module + vault-paths module apply).
# - Any Kubernetes manifest.
# - Any AWS resource. The platform does not deploy on AWS.

#
# 1. Zone-level TLS posture.
#
resource "cloudflare_zone_settings_override" "this" {
  zone_id = var.zone_id

  settings {
    min_tls_version  = var.min_tls_version
    tls_1_3          = "on"
    always_use_https = var.always_use_https ? "on" : "off"
    ssl              = "strict"
  }
}

#
# 2. Authenticated Origin Pulls (zone-level).
#
#    With Cloudflare Tunnel, mTLS between Cloudflare and the origin
#    is automatic via the tunnel; AOP at the zone level is still
#    valuable as a defence-in-depth layer that asserts the origin
#    presents a Cloudflare-issued client cert. Recommended ON for
#    production.
#
resource "cloudflare_authenticated_origin_pulls" "this" {
  zone_id = var.zone_id
  enabled = var.enable_authenticated_origin_pulls
}

#
# 3. DNS records for every hostname the platform serves.
#
#    With Cloudflare Tunnel the CNAME target is the tunnel UUID:
#      <tunnel-id>.cfargotunnel.com
#    The operator passes the tunnel UUID via the `hostnames` map
#    when creating the records (or uses cloudflare_zero_trust_tunnel
#    + cloudflare_record together in a wrapper module).
#
resource "cloudflare_record" "hostname" {
  for_each = var.hostnames

  zone_id = var.zone_id
  name    = each.key
  type    = "CNAME"
  content = each.value
  proxied = true
  ttl     = 1
  comment = "Managed by infrastructure/cloudflare (env=${var.environment})"
}
