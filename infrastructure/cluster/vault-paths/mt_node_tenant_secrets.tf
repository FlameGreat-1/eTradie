# Per-tenant mt-node credential infrastructure.
#
# The engine writes per-tenant MT broker credentials to
# etradie/tenants/mt-node/<sa_name> at provision time; the per-tenant
# Pod's Vault Agent Injector renders them into
# /vault/secrets/mt-credentials.env at startup, which entrypoint.sh
# sources. The plaintext credentials never appear in a K8s Secret.
#
# <sa_name> equals etradie-mt-<connection_id[:12]> (the engine-allocated
# per-tenant ServiceAccount name; identical to the Helm release name
# and the K8s StatefulSet name).
#
# Stored keys: mt5_login, mt5_password, mt5_zmq_auth_token.
#
# Resources defined here:
#   - vault_auth_backend.kubernetes               - declared as managed.
#   - vault_kubernetes_auth_backend_config        - issuer + reviewer JWT.
#   - vault_policy.mt_node_provisioner            - engine SA: WRITE only.
#   - vault_policy.mt_node_tenant                 - Pod SA: READ on its
#                                                   own path (templated
#                                                   on the Pod's SA name).
#   - vault_kubernetes_auth_backend_role.mt_node_provisioner
#   - vault_kubernetes_auth_backend_role.mt_node_tenant

variable "k8s_host" {
  description = "In-cluster Kubernetes API server URL Vault should reach for TokenReview. Typically https://kubernetes.default.svc on in-cluster Vault deployments, or the cluster's external endpoint for HCP Vault / external Vault."
  type        = string
}

variable "k8s_ca_cert" {
  description = "PEM-encoded CA bundle for the Kubernetes API server. On in-cluster Vault this is /var/run/secrets/kubernetes.io/serviceaccount/ca.crt; on external Vault the operator supplies it explicitly."
  type        = string
  sensitive   = true
}

variable "k8s_reviewer_jwt" {
  description = "JWT for a ServiceAccount that holds the system:auth-delegator ClusterRole. Vault uses this to call the TokenReview API to validate Pod SA tokens. Same reviewer the External Secrets Operator already uses."
  type        = string
  sensitive   = true
  default     = ""
}

# Kubernetes auth method. Declared as a managed resource so Terraform
# owns the backend's tune block and the bootstrap is reproducible.
resource "vault_auth_backend" "kubernetes" {
  type        = "kubernetes"
  path        = "kubernetes"
  description = "Kubernetes auth backend for in-cluster pods (ESO + mt-node Agent Injector)."
  tune {
    default_lease_ttl  = "15m"
    max_lease_ttl      = "1h"
    listing_visibility = "unauth"
  }
}

resource "vault_kubernetes_auth_backend_config" "kubernetes" {
  backend            = vault_auth_backend.kubernetes.path
  kubernetes_host    = var.k8s_host
  kubernetes_ca_cert = var.k8s_ca_cert
  token_reviewer_jwt = var.k8s_reviewer_jwt
  # Default to the in-cluster service-account-token JWT issuer claim.
  # Vault 1.13+ requires this when token_reviewer_jwt is set.
  issuer                 = "https://kubernetes.default.svc.cluster.local"
  disable_iss_validation = false
  disable_local_ca_jwt   = false
}

# Engine ServiceAccount policy. WRITE on every tenant path; no read,
# no list. The engine has the plaintext at provision time and never
# needs to read it back.
resource "vault_policy" "mt_node_provisioner" {
  name = "mt-node-provisioner-${var.environment}"

  policy = <<-EOT
    # Engine writes per-tenant credentials. WRITE only - no read, no list.
    path "${var.vault_mount}/data/tenants/mt-node/*" {
      capabilities = ["create", "update", "delete"]
    }

    # Engine performs hard-delete of all versions on connection-delete to
    # purge the credentials from Vault entirely. Requires 'delete' on the
    # metadata endpoint (Vault treats this differently from data delete).
    path "${var.vault_mount}/metadata/tenants/mt-node/*" {
      capabilities = ["delete"]
    }
  EOT
}

# Per-tenant Pod policy. READ only, scoped to the single path keyed
# by the requesting Pod's ServiceAccount name. The K8s auth backend
# exposes service_account_name in the entity alias metadata; templating
# the path against it gives each Pod access to its own credentials and
# nothing else, even if the SA token leaks.
resource "vault_policy" "mt_node_tenant" {
  name = "mt-node-tenant-${var.environment}"

  policy = <<-EOT
    path "${var.vault_mount}/data/tenants/mt-node/{{identity.entity.aliases.${vault_auth_backend.kubernetes.accessor}.metadata.service_account_name}}" {
      capabilities = ["read"]
    }
  EOT
}

# Engine SA authenticates here. Bound to the etradie-engine SA in the
# etradie-system namespace; 15-minute renewals with a 1-hour hard cap.
resource "vault_kubernetes_auth_backend_role" "mt_node_provisioner" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "mt-node-provisioner"
  bound_service_account_names      = ["etradie-engine"]
  bound_service_account_namespaces = ["etradie-system"]
  token_policies                   = [vault_policy.mt_node_provisioner.name]
  token_period                     = 900
  token_max_ttl                    = 3600
  audience                         = "vault"
}

# Per-tenant Pods authenticate here. The glob matches the engine's
# per-tenant SA naming convention (etradie-mt-<conn[:12]>) without
# accidentally matching etradie-engine. alias_name_source=serviceaccount_uid
# keeps the entity alias stable across SA token rotations.
resource "vault_kubernetes_auth_backend_role" "mt_node_tenant" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "mt-node-tenant"
  bound_service_account_names      = ["etradie-mt-*"]
  bound_service_account_namespaces = ["etradie-system"]
  token_policies                   = [vault_policy.mt_node_tenant.name]
  token_period                     = 900
  token_max_ttl                    = 3600
  audience                         = "vault"
  alias_name_source                = "serviceaccount_uid"
}
