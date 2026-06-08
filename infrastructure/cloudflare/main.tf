# infrastructure/cloudflare/main.tf
#
# Owns:
# - Cloudflare zone-level settings (TLS minimum, AOP enablement,
#   always-use-https).
# - DNS records pointing the public hostnames at the Cloudflare
#   Tunnel UUID (`<tunnel-id>.cfargotunnel.com`) created in the
#   Cloudflare Zero Trust UI / via cloudflare_zero_trust_tunnel.
# - TIER4 A2c abuse-prevention edge controls: WAF managed ruleset,
#   per-IP rate limits on /api/* and /auth/*, and Super Bot Fight Mode.
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
  # ttl = 1 means 'auto'; Cloudflare REQUIRES ttl=1 for proxied=true
  # records. Audit ref: IC-H2.
  ttl     = 1
  comment = "Managed by infrastructure/cloudflare (env=${var.environment})"

  # Refuse `terraform destroy` on production DNS. Audit ref: IC-H1.
  lifecycle {
    prevent_destroy = true
  }
}

#
# 4. WAF — Cloudflare Managed Ruleset (TIER4 A2c).
#
#    This is the FIRST layer of abuse prevention (anonymous / volumetric
#    / known-bad-signature). The Envoy local_ratelimit + max_request_bytes
#    and the gateway per-user limiter are the always-on origin BACKSTOP
#    (see docs/security/TIER4_ABUSE_PREVENTION_PLAN.md section 0).
#
#    Deploys Cloudflare's Managed Ruleset in the
#    http_request_firewall_managed phase via an `execute` action, which
#    is the v4-provider-correct way to enable a managed WAF ruleset.
#
resource "cloudflare_ruleset" "waf_managed" {
  count = var.enable_waf ? 1 : 0

  zone_id     = var.zone_id
  name        = "etradie-waf-managed"
  description = "TIER4 A2c: enable Cloudflare Managed Ruleset (WAF). Managed by infrastructure/cloudflare."
  kind        = "zone"
  phase       = "http_request_firewall_managed"

  rules {
    ref         = "exec_cloudflare_managed"
    description = "Execute the Cloudflare Managed Ruleset"
    expression  = "true"
    action      = "execute"
    action_parameters {
      id = "efb7b8c949ac4650a09736fc376e9aee" # Cloudflare Managed Ruleset (stable well-known id)
    }
  }
}

#
# 5. Rate limiting (TIER4 A2c).
#
#    Coarse per-IP limit on /api/* and a TIGHTER per-IP limit on /auth/*
#    (login / register / refresh / password-reset) to blunt credential
#    stuffing at the edge before it reaches the origin. Both return 429.
#    The origin still enforces its own per-user limits regardless.
#
resource "cloudflare_ruleset" "rate_limit" {
  count = var.enable_rate_limiting ? 1 : 0

  zone_id     = var.zone_id
  name        = "etradie-rate-limit"
  description = "TIER4 A2c: per-IP edge rate limits on /api/* and /auth/*. Managed by infrastructure/cloudflare."
  kind        = "zone"
  phase       = "http_ratelimit"

  # TIGHTER /auth/* rule listed FIRST so it matches before the broad
  # /api/* rule (rules evaluate top-down; /auth/* is not under /api/* in
  # this platform, but ordering tightest-first is the safe convention).
  rules {
    ref         = "auth_credential_stuffing"
    description = "Tight per-IP limit on auth endpoints (credential stuffing)"
    expression  = "(http.request.uri.path matches \"^/auth/\")"
    action      = "block"
    ratelimit {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = var.auth_rate_limit_period
      requests_per_period = var.auth_rate_limit_requests
      mitigation_timeout  = var.auth_rate_limit_period
    }
  }

  rules {
    ref         = "api_coarse"
    description = "Coarse per-IP limit on /api/*"
    expression  = "(http.request.uri.path matches \"^/api/\")"
    action      = "block"
    ratelimit {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = var.api_rate_limit_period
      requests_per_period = var.api_rate_limit_requests
      mitigation_timeout  = var.api_rate_limit_period
    }
  }
}

#
# 6. Bot protection (TIER4 A2c).
#
#    Two mutually-exclusive paths, chosen by the zone's Cloudflare plan.
#    Both default OFF so the default config applies cleanly on ANY plan;
#    the operator enables exactly ONE after confirming the entitlement
#    (see docs/runbooks/tier4-abuse-prevention.md).
#
#      6a. Super Bot Fight Mode  -> Pro / Business plans.
#          Toggled via the zone-level bot-fight-mode setting.
#      6b. Bot Management (ML)    -> Enterprise add-on only.
#          The dedicated cloudflare_bot_management resource.
#
#    Guard: enabling both at once is a misconfiguration (they conflict),
#    so a precondition fails fast with a clear message.
#
resource "cloudflare_zone_settings_override" "bot" {
  count = var.enable_super_bot_fight_mode ? 1 : 0

  zone_id = var.zone_id

  settings {
    # "bic" = Browser Integrity Check; combined with the dashboard's
    # Super Bot Fight Mode this is the Pro/Business-tier bot defence.
    bic = "on"
  }

  lifecycle {
    precondition {
      condition     = !(var.enable_super_bot_fight_mode && var.enable_bot_management)
      error_message = "enable_super_bot_fight_mode (Pro/Business) and enable_bot_management (Enterprise) are mutually exclusive; enable exactly one based on the zone's Cloudflare plan."
    }
  }
}

resource "cloudflare_bot_management" "this" {
  count = var.enable_bot_management ? 1 : 0

  zone_id            = var.zone_id
  enable_js          = true
  fight_mode         = true
  optimize_wordpress = false

  lifecycle {
    precondition {
      condition     = !(var.enable_super_bot_fight_mode && var.enable_bot_management)
      error_message = "enable_super_bot_fight_mode (Pro/Business) and enable_bot_management (Enterprise) are mutually exclusive; enable exactly one based on the zone's Cloudflare plan."
    }
  }
}

#
# 7. HSTS (Strict-Transport-Security) at the TLS-terminating edge.
#
#    Emitted as a response-header transform rule. HSTS is set HERE (not
#    at Envoy) so it is only ever asserted over the Cloudflare-terminated
#    TLS connection. The other browser security headers
#    (Content-Security-Policy, X-Frame-Options, X-Content-Type-Options,
#    Referrer-Policy) are emitted at Envoy via
#    helm/envoy/values.yaml::securityHeaders -> the HCM
#    response_headers_to_add block in helm/envoy/templates/configmap.yaml.
#    The HSTS value is composed from the hsts_* variables.
#
resource "cloudflare_ruleset" "hsts" {
  count = var.enable_hsts ? 1 : 0

  zone_id     = var.zone_id
  name        = "etradie-hsts"
  description = "TIER5: emit Strict-Transport-Security on every edge response. Managed by infrastructure/cloudflare."
  kind        = "zone"
  phase       = "http_response_headers_transform"

  rules {
    ref         = "set_hsts"
    description = "Set Strict-Transport-Security on all responses"
    expression  = "true"
    action      = "rewrite"
    action_parameters {
      headers {
        name      = "Strict-Transport-Security"
        operation = "set"
        value     = "max-age=${var.hsts_max_age}${var.hsts_include_subdomains ? "; includeSubDomains" : ""}${var.hsts_preload ? "; preload" : ""}"
      }
    }
  }
}
