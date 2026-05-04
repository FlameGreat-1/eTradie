# infrastructure/cluster/vault-paths/main.tf
#
# Cloud-agnostic Vault KV-v2 path bootstrap. Creates the empty paths
# the helm charts' ExternalSecrets reference. Does NOT write the
# secret bytes themselves — operators populate them post-bootstrap.
#
# Usable on any environment that has a reachable Vault. No AWS
# provider, no cloud SDK; only the Vault provider.
#
# Apply order (any cluster):
#   1. cluster bootstrap (cluster/aws or cluster/oci or bootstrap/)
#   2. install Vault (chart from hashicorp/vault, or external HCP)
#   3. install ESO (chart from external-secrets/external-secrets)
#   4. apply this module to create the KV paths
#   5. operator populates path values
#   6. ArgoCD reconciles platform charts

provider "vault" {
  address   = var.vault_address
  namespace = var.vault_namespace
}

resource "vault_kv_secret_v2" "edge_ingress_tls" {
  mount               = var.vault_mount
  name                = "etradie/services/edge-ingress/${var.environment}/tls"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; operator must populate before edge-ingress can roll out"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "edge_ingress_aop_ca" {
  mount               = var.vault_mount
  name                = "etradie/services/edge-ingress/${var.environment}/cloudflare/aop_ca"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with the Cloudflare AOP CA PEM after the cloudflare module applies"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "edge_ingress_tunnel" {
  mount               = var.vault_mount
  name                = "etradie/services/edge-ingress/${var.environment}/cloudflare/tunnel"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with the Cloudflare Tunnel token (key: tunnel_token) after creating the Tunnel in Cloudflare Zero Trust"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "edge_ingress_maxmind" {
  mount               = var.vault_mount
  name                = "etradie/services/edge-ingress/${var.environment}/maxmind"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with MaxMind license_key + account_id"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "gateway" {
  mount               = var.vault_mount
  name                = "etradie/services/gateway/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with auth_database_url, auth_jwt_secret, broker_encryption_key, llm_encryption_key, ..."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "engine" {
  mount               = var.vault_mount
  name                = "etradie/services/engine/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with anthropic_api_key, openai_api_key, twelvedata_api_key, fred_api_key, ..."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "execution" {
  mount               = var.vault_mount
  name                = "etradie/services/execution/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with execution_database_url, broker credentials"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "management" {
  mount               = var.vault_mount
  name                = "etradie/services/management/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with management_database_url, broker credentials"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}
