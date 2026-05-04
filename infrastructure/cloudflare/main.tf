# infrastructure/cloudflare/main.tf
#
# Owns:
# - Cloudflare zone-level settings (TLS minimum, AOP enablement,
#   always-use-https).
# - DNS records pointing the public hostnames at the EKS NLB.
# - AWS Security Group rules that restrict TCP/443 ingress to the
#   Cloudflare published ranges (defence-in-depth pair with AOP).
#
# Does NOT own:
# - The AOP CA bytes (those live in Vault, written by the operator
#   after the cluster module bootstraps the path).
# - Any Kubernetes manifest.

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
resource "cloudflare_authenticated_origin_pulls" "this" {
  zone_id = var.zone_id
  enabled = var.enable_authenticated_origin_pulls
}

#
# 3. DNS records for every hostname the platform serves.
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

#
# 4. Origin firewall: TCP/443 ingress is allowed ONLY from Cloudflare's
#    published ranges. Belt-and-braces with AOP: AOP makes spoofing
#    impossible at the application layer; this drops the packets at the
#    network layer before TLS handshake even starts.
#
resource "aws_security_group_rule" "cloudflare_ipv4" {
  for_each = toset(var.cloudflare_ipv4_ranges)

  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [each.value]
  security_group_id = var.origin_security_group_id
  description       = "Cloudflare IPv4 (${each.value})"
}

resource "aws_security_group_rule" "cloudflare_ipv6" {
  for_each = toset(var.cloudflare_ipv6_ranges)

  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  ipv6_cidr_blocks  = [each.value]
  security_group_id = var.origin_security_group_id
  description       = "Cloudflare IPv6 (${each.value})"
}
