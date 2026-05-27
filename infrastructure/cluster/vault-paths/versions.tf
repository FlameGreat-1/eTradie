terraform {
  required_version = ">= 1.6.0"
  required_providers {
    vault = {
      source = "hashicorp/vault"
      # Locked to the 4.x major. Audit ref: IV-H3.
      version = "~> 4.0"
    }
  }
  # See infrastructure/cloudflare/versions.tf for the backend
  # convention. Audit ref: IV-H3, XI-1.
}
