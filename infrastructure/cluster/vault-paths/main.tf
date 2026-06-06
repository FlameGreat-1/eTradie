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

# edge-ingress TLS. Audit ref: IV-M1.
resource "vault_kv_secret_v2" "edge_ingress_tls" {
  mount               = var.vault_mount
  name                = "etradie/services/edge-ingress/${var.environment}/tls"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate keys api_cert + api_key + wildcard_cert + wildcard_key (production) or staging_api_cert + staging_api_key + staging_wildcard_cert + staging_wildcard_key (staging). Values are PEM-encoded certificate / key strings."
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

# MaxMind GeoLite credentials. Audit ref: IV-M1.
resource "vault_kv_secret_v2" "edge_ingress_maxmind" {
  mount               = var.vault_mount
  name                = "etradie/services/edge-ingress/${var.environment}/maxmind"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate keys license_key + account_id with a free GeoLite2 sign-up at https://www.maxmind.com/en/geolite2/signup. Both required."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

# Gateway secrets. Single source of truth for every key the gateway's
# ExternalSecret reads, including billing_internal_shared_secret
# (which the gateway sends to billing-service in X-Internal-Auth
# and MUST equal etradie/services/billing/<env>:internal_shared_secret).
# Audit ref: IV-C1, IV-M3.
resource "vault_kv_secret_v2" "gateway" {
  mount               = var.vault_mount
  name                = "etradie/services/gateway/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate keys: auth_database_url, postgres_user, postgres_password, postgres_host, postgres_port, postgres_db, gateway_redis_url, auth_jwt_secret, auth_admin_password, engine_internal_shared_secret (must equal etradie/services/engine/${var.environment}:engine_internal_shared_secret if you also store it there), billing_internal_shared_secret (MUST EQUAL etradie/services/billing/${var.environment}:internal_shared_secret)."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

# Engine secrets. Every key below is read by helm/engine/templates/externalsecret.yaml.
# rag_chroma_auth_token is INTENTIONALLY NOT in this path; the canonical
# Vault location is etradie/data-layer/chromadb/<env>:auth_token so that
# the chromadb server and the engine read the SAME source. Audit ref:
# IV-C2, X-6, D-C3.
resource "vault_kv_secret_v2" "engine" {
  mount               = var.vault_mount
  name                = "etradie/services/engine/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate keys: database_url, postgres_user, postgres_password, redis_url, redis_password, broker_encryption_key, auth_jwt_secret, cftc_app_token, fred_api_key, twelvedata_api_key, processor_anthropic_api_key, processor_openai_api_key, processor_gemini_api_key, mt5_metaapi_token. broker_encryption_key is the ONLY credential KEK in the platform (the engine is the sole consumer; gateway/execution/management do NOT hold it) and is KEK version 1 for credential-at-rest envelope encryption. To ROTATE the credential KEK, add broker_encryption_key_v<n> (n>=2, e.g. broker_encryption_key_v2 = openssl rand -hex 32) and declare it in helm/engine values externalSecrets.engine.rotationKeyVersions; the engine activates the highest version, the re-wrap routine migrates rows, then remove the old version to revoke it. Note: rag_chroma_auth_token is NOT in this path; populate etradie/data-layer/chromadb/${var.environment}:auth_token instead (single source of truth shared with the ChromaDB server)."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

# Execution service secrets. Audit ref: IV-M1.
resource "vault_kv_secret_v2" "execution" {
  mount               = var.vault_mount
  name                = "etradie/services/execution/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate keys: execution_database_url, execution_redis_url, auth_jwt_secret, engine_internal_shared_secret. auth_jwt_secret MUST equal etradie/services/gateway/${var.environment}:auth_jwt_secret. engine_internal_shared_secret MUST equal etradie/services/gateway/${var.environment}:engine_internal_shared_secret AND the engine's value -- execution sends it in X-Internal-Auth on every /internal/broker/* call and the pod fails fast at startup without it when BROKER_MODE=mt5 in production/staging. NOTE: no broker/credential encryption KEK here -- execution does not encrypt credentials; it reaches the broker via the engine /internal/broker/* bridge."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

# Management service secrets. Audit ref: IV-M1.
resource "vault_kv_secret_v2" "management" {
  mount               = var.vault_mount
  name                = "etradie/services/management/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate keys: management_database_url, management_redis_url, auth_jwt_secret, engine_internal_shared_secret. auth_jwt_secret MUST equal etradie/services/gateway/${var.environment}:auth_jwt_secret. engine_internal_shared_secret MUST equal etradie/services/gateway/${var.environment}:engine_internal_shared_secret AND the engine's value -- management sends it in X-Internal-Auth on every /internal/broker/* call and the pod fails fast at startup without it when BROKER_MODE=mt5 in production/staging. NOTE: no broker/credential encryption KEK here -- management does not encrypt credentials; it reaches the broker via the engine /internal/broker/* bridge."
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

# NOTE: the previous separate vault_kv_secret_v2.gateway_billing_secret
# resource was REMOVED. It managed the SAME Vault path as the
# vault_kv_secret_v2.gateway resource above, producing perpetual
# Terraform drift. Vault KV-v2 stores ONE document per path; two
# Terraform resources cannot co-own it. The gateway resource above
# already enumerates billing_internal_shared_secret in its bootstrap
# payload. Audit ref: IV-C1.

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

# ChromaDB auth token. THIS IS THE CANONICAL LOCATION. Both the
# chromadb StatefulSet (reads CHROMA_SERVER_AUTHN_CREDENTIALS) AND
# the engine pod (reads RAG_CHROMA_AUTH_TOKEN) MUST read this single
# Vault document so they cannot get out of sync. Key name is the
# simpler 'auth_token' (was previously 'chroma_auth_token' on the
# server side and 'rag_chroma_auth_token' on the engine side - two
# separate keys in two separate paths held by convention only).
# Audit ref: IV-C2, X-6, D-C3, SC-C2.
resource "vault_kv_secret_v2" "data_layer_chromadb" {
  mount               = var.vault_mount
  name                = "etradie/data-layer/chromadb/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate the single key 'auth_token' with the ChromaDB token. Both the ChromaDB server (CHROMA_SERVER_AUTHN_CREDENTIALS) and the engine (RAG_CHROMA_AUTH_TOKEN) read from this exact Vault path. Generate with: openssl rand -hex 32."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

# MT-node platform secrets.
#
# Holds the platform-level encryption key the engine uses to seal
# per-user MT broker credentials (login / password / server) before
# writing them to a per-tenant Kubernetes Secret in etradie-system.
# The mt-node Deployment (created at runtime by HostedProvisioner)
# mounts that Secret as envFrom so credentials NEVER appear as a
# V1EnvVar value field, never in `kubectl describe`, never in audit
# logs that dump env. The encryption key NEVER leaves the engine pod;
# only the sealed bytes are stored in the per-tenant Secret.
#
# Keys (all required):
#   mt_node_credential_encryption_key - 32-byte hex string used by the
#                                       engine to AES-GCM seal user MT
#                                       creds. Generate once per env
#                                       with: openssl rand -hex 32 .
#                                       Rotation invalidates all
#                                       in-flight per-tenant Secrets;
#                                       follow the rotation runbook.
#   default_zmq_auth_token           - Platform-level default token
#                                       the EA's AUTH_TOKEN inside the
#                                       container is configured with.
#                                       Per-user override is supported
#                                       by the engine via the EA
#                                       connection path; this default
#                                       is consumed only by the hosted
#                                       (in-cluster) container path.
#                                       Generate with:
#                                         openssl rand -hex 32 .
# Audit ref: CHECKLIST Section 1 (credential security pre-requisite
# for the mt-node Deployment), and refactor of HostedProvisioner in
# Step 4 of this MR series.
# Linkerd service-mesh identity (CHECKLIST Tier 9). Holds the mTLS
# issuer cert/key + trust anchor the linkerd identity ExternalSecret
# (deployments/linkerd/templates/identity-externalsecret.yaml) reads.
# The platform runs NO cert-manager; the mesh CA lifecycle lives here.
#
# Keys (all required before the linkerd-control-plane Application syncs):
#   trust_anchor_pem - PEM root CA (PUBLIC). Generate with:
#       step certificate create root.linkerd.cluster.local ca.crt ca.key \
#         --profile root-ca --no-password --insecure
#     trust_anchor_pem = contents of ca.crt
#   issuer_tls_crt   - PEM intermediate issuer cert, signed by the root.
#       step certificate create identity.linkerd.cluster.local \
#         issuer.crt issuer.key --profile intermediate-ca \
#         --not-after 8760h --no-password --insecure \
#         --ca ca.crt --ca-key ca.key
#     issuer_tls_crt = contents of issuer.crt
#   issuer_tls_key   - PEM intermediate issuer private key (issuer.key).
#
# Rotation: re-issue the intermediate from the same root, update
# issuer_tls_crt/issuer_tls_key, let ESO refresh; the trust anchor only
# changes on a full CA rotation (rare, documented in the runbook).
resource "vault_kv_secret_v2" "linkerd_identity" {
  mount               = var.vault_mount
  name                = "etradie/platform/linkerd/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate keys trust_anchor_pem (PEM root CA, public), issuer_tls_crt (PEM intermediate issuer cert signed by the root), issuer_tls_key (PEM intermediate issuer key) BEFORE the linkerd-control-plane ArgoCD Application is synced. Generate with smallstep `step` CLI per the runbook in docs/runbooks/tier9-linkerd-mesh-rollout.md (section 0)."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}

resource "vault_kv_secret_v2" "mt_node" {
  mount               = var.vault_mount
  name                = "etradie/services/mt-node/${var.environment}"
  delete_all_versions = false
  data_json = jsonencode({
    bootstrap = "placeholder; populate default_zmq_auth_token (openssl rand -hex 32) before any user can pick connection_type=hosted. Per-tenant MT credentials are stored in etradie/tenants/mt-node/<sa_name> via the Vault Agent Injector path - see mt_node_tenant_secrets.tf."
  })
  lifecycle {
    ignore_changes = [data_json]
  }
}
