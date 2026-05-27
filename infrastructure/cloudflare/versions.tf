terraform {
  required_version = ">= 1.6.0"

  required_providers {
    cloudflare = {
      source = "cloudflare/cloudflare"
      # Locked to the 4.x major. v5 has breaking changes to
      # cloudflare_zone_settings_override and
      # cloudflare_authenticated_origin_pulls; upgrade behind a
      # deliberate version-bump PR. Audit ref: IC-C1.
      version = "~> 4.40"
    }
  }

  # Backend is operator-owned. Recommended choice for this repo's
  # GitLab.com hosting is the gitlab http backend:
  #   terraform {
  #     backend "http" {
  #       # set via `terraform init -backend-config=...` or env
  #     }
  #   }
  # Documented here so the next operator does not run terraform with
  # a local-file state by accident. Audit ref: IV-H3, XI-1.
}
