terraform {
  required_version = ">= 1.6.0"
  required_providers {
    oci = {
      source = "oracle/oci"
      # Locked to the 5.x major. Audit ref: IO-H1.
      version = "~> 5.0"
    }
  }
  # See infrastructure/cloudflare/versions.tf for the backend
  # convention. Audit ref: IV-H3, XI-1.
}
