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

# Billing microservice secrets.
#
# The billing service reads EVERY key below at startup and refuses to
# boot when any required key is missing. Populate this path BEFORE
# the billing ArgoCD Application is reconciled, otherwise the pod
# CrashLoops with `billing config: required key ... missing value`.
#
# Key inventory (all required unless marked optional):
#
#   billing_database_url          - Full postgres DSN for the billing
#                                   tables (may share the same DB as
#                                   auth; billing creates its own
#                                   tables via SchemaSQL() at startup).
#   postgres_user / postgres_password / postgres_host / postgres_port
#   postgres_db / postgres_sslmode - Fallback when billing_database_url
#                                   is empty; mirrors the gateway pattern.
#   internal_shared_secret        - >= 32 hex chars. MUST match the
#                                   value at
#                                   etradie/services/gateway/<env>
#                                   -> billing_internal_shared_secret.
#                                   Generate once:
#                                     openssl rand -hex 32
#                                   then populate BOTH paths.
#   billing_redis_url             - Redis URL for cross-service alert
#                                   publishing (etradie:alerts channel).
#                                   MUST point at the same Redis the
#                                   gateway subscribes to.
#   paddle_webhook_secret         - Paddle dashboard signing secret.
#   paddle_api_key                - Paddle API bearer token.
#   paddle_price_pro_byok         - Paddle price_id for pro_byok tier.
#   paddle_price_pro_managed      - Paddle price_id for pro_managed tier.
#   lemonsqueezy_webhook_secret   - LS dashboard signing secret.
#   lemonsqueezy_api_key          - LS API bearer token.
#   lemonsqueezy_store_id         - LS store numeric ID.
#   lemonsqueezy_variant_pro_byok    - LS variant_id for pro_byok.
#   lemonsqueezy_variant_pro_managed - LS variant_id for pro_managed.
resource "vault_kv_secret_v2" "billing" {
  mount               = var.vault_mount
  name                = "etradie/services/billing/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with billing_database_url, internal_shared_secret, billing_redis_url, paddle_webhook_secret, paddle_api_key, paddle_price_pro_byok, paddle_price_pro_managed, lemonsqueezy_webhook_secret, lemonsqueezy_api_key, lemonsqueezy_store_id, lemonsqueezy_variant_pro_byok, lemonsqueezy_variant_pro_managed BEFORE the billing chart is reconciled"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

# Gateway billing shared secret. The gateway reads this as
# GATEWAY_BILLING_INTERNAL_SHARED_SECRET. It MUST equal the value
# stored at etradie/services/billing/<env>/internal_shared_secret.
# Stored separately so the gateway Vault path does not need read
# access to the billing path (least-privilege).
resource "vault_kv_secret_v2" "gateway_billing_secret" {
  mount               = var.vault_mount
  name                = "etradie/services/gateway/${var.environment}"
  delete_all_versions = false
  # This resource manages only the billing_internal_shared_secret key.
  # All other gateway keys are managed by the operator post-bootstrap.
  # ignore_changes prevents Terraform from overwriting operator-set
  # values on subsequent applies.
  data_json = jsonencode({
    billing_internal_shared_secret = "placeholder; replace with the same 32-byte hex value stored at etradie/services/billing/${var.environment}/internal_shared_secret"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

# Data-layer paths. The data-layer chart's ExternalSecrets
# (helm/data-layer/templates/{postgres,redis,chromadb}-externalsecret.yaml)
# read from these paths. Without them, the StatefulSets are stuck in
# Init: indefinitely waiting for ESO to materialise an empty Secret
# whose Vault source does not exist.

resource "vault_kv_secret_v2" "data_layer_postgres" {
  mount               = var.vault_mount
  name                = "etradie/data-layer/postgres/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with postgres_user, postgres_db, postgres_password BEFORE the data-layer chart is reconciled (postgres pod blocks otherwise)"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "data_layer_redis" {
  mount               = var.vault_mount
  name                = "etradie/data-layer/redis/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with redis_password"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "data_layer_chromadb" {
  mount               = var.vault_mount
  name                = "etradie/data-layer/chromadb/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate with chroma_auth_token (must equal engine's RAG_CHROMA_AUTH_TOKEN value)"
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}
