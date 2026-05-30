# infrastructure/cluster/vault-paths/mt_node_tenant_secrets.tf
#
# H1 fix (Vault Agent Injector, part 1/6): per-tenant secret plumbing.
#
# Replaces the plaintext-in-K8s-Secret envelope used by HostedProvisioner
# with a Vault-native delivery channel. The engine writes per-tenant MT
# credentials to a parameterised Vault path; the mt-node Pod's Vault
# Agent Injector fetches them at startup with its own short-lived token.
#
# Resources owned by THIS file:
#
#   - vault_auth_backend.kubernetes
#       Declares the existing Kubernetes auth backend as a managed
#       resource. The bootstrap README already requires this backend to
#       be enabled (ESO depends on it). Declaring it here makes the
#       bootstrap reproducible end-to-end and lets Terraform configure
#       the JWT issuer / CA in lockstep with the cluster.
#
#   - vault_kubernetes_auth_backend_config.kubernetes
#       Configures the backend's Kubernetes API server and the JWT
#       issuer claim. The CA cert and reviewer JWT come from the same
#       in-cluster ServiceAccount the ESO chart already uses, so no new
#       cluster bootstrap step is required.
#
#   - vault_policy.mt_node_provisioner
#       Policy granting the engine's ServiceAccount write access on the
#       per-tenant path. The path includes a glob so the engine can
#       write to ANY tenant's path without the policy being mutated on
#       every signup. WRITE only (create / update / delete the data);
#       no read. The engine never reads back what it wrote.
#
#   - vault_policy.mt_node_tenant
#       Policy granting a per-tenant Pod READ access on exactly its own
#       tenant path. The path is templated on the Pod's bound metadata
#       (etradie.connection-id label), so a Pod's Vault Agent can ONLY
#       fetch the secret for the connection_id it was provisioned for.
#       Even if the Pod's SA token leaked, the holder could not read
#       any other tenant's credentials.
#
#   - vault_kubernetes_auth_backend_role.mt_node_provisioner
#       Vault role the engine pod's SA authenticates against. Bound to
#       the etradie-engine ServiceAccount in etradie-system namespace.
#
#   - vault_kubernetes_auth_backend_role.mt_node_tenant
#       Vault role the mt-node pod's SA authenticates against. Bound to
#       every per-tenant SA created in etradie-system (the engine
#       provisions a dedicated SA per tenant named etradie-mt-<conn[:12]>).
#       alias_name_source=serviceaccount_uid so the entity alias is
#       stable across SA rotations.
#
# Path convention (NOT a Terraform resource; documented here for clarity):
#
#   etradie/tenants/mt-node/<sa_name>
#
#   where <sa_name> = etradie-mt-<connection_id[:12]> (the engine-allocated
#   per-tenant ServiceAccount name; matches the Helm release name and the
#   K8s StatefulSet name).
#
#     keys:
#       mt5_login           - broker account login (string)
#       mt5_password        - broker trading password (string)
#       mt5_zmq_auth_token  - per-tenant EA AUTH_TOKEN (string)
#
# The engine writes here at provision time via Vault HTTP API
# (POST /v1/etradie/data/tenants/mt-node/<sa_name>). The Vault Agent in
# the per-tenant Pod renders these into /vault/secrets/mt-credentials.env
# which entrypoint.sh sources at startup.
#
# Variables required from existing variables.tf:
#   var.vault_mount     - KV-v2 mount name (default "etradie")
#   var.environment     - one of staging / production
#
# Additional variables introduced here:
#   var.k8s_host        - in-cluster API server URL (e.g.
#                         https://kubernetes.default.svc)
#   var.k8s_ca_cert     - PEM-encoded CA bundle for the API server
#   var.k8s_reviewer_jwt - JWT for a ServiceAccount with the
#                         system:auth-delegator ClusterRole (used by
#                         the TokenReview API; identical reviewer the
#                         ESO chart uses).
#
# Audit ref: CHECKLIST Section 9 'Credential security' (H1 proper fix).

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

# ---------------------------------------------------------------------
# Kubernetes auth method - declared as a managed resource so the
# bootstrap is reproducible. The bootstrap README already requires this
# backend to be enabled for the External Secrets Operator; we adopt it
# here.
# ---------------------------------------------------------------------
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
  backend                = vault_auth_backend.kubernetes.path
  kubernetes_host        = var.k8s_host
  kubernetes_ca_cert     = var.k8s_ca_cert
  token_reviewer_jwt     = var.k8s_reviewer_jwt
  # Default to the in-cluster service-account-token JWT issuer claim.
  # Vault 1.13+ requires this when token_reviewer_jwt is set.
  issuer                 = "https://kubernetes.default.svc.cluster.local"
  disable_iss_validation = false
  disable_local_ca_jwt   = false
}

# ---------------------------------------------------------------------
# Policy: mt_node_provisioner
#
# Granted to the engine pod's SA. Allows WRITE on every tenant path under
# etradie/tenants/mt-node/. Does NOT grant 'read' because the engine
# never reads back what it wrote - it has the plaintext at create time
# and persists nothing on the engine side (broker_connections.id is the
# only handle).
#
# Capabilities reference:
#   create  - POST  /v1/<mount>/data/<path>          (write a new version)
#   update  - POST  /v1/<mount>/data/<path>          (write a new version on an existing path; Vault treats both as create+update)
#   delete  - DELETE /v1/<mount>/data/<path>         (soft-delete the latest version)
#   sudo    - required to permanently destroy versions or read /metadata for paths the policy does NOT grant 'read' on
#
# We intentionally do NOT grant 'list' on the parent path - the engine
# never enumerates tenant paths. It always knows the exact connection_id
# (the row id from broker_connections) at the call site.
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# Policy: mt_node_tenant
#
# Granted to every per-tenant mt-node Pod via the K8s auth role.
# READ ONLY, scoped to the SINGLE path keyed by the requesting Pod's
# ServiceAccount name. A pod cannot read any other tenant's credentials
# even if its SA token leaked.
#
# Why service_account_name and not a custom 'connection_id' field:
# Vault's Kubernetes auth backend does NOT copy arbitrary SA annotations
# into the entity alias metadata. The only metadata fields available in
# policy templates are the standard set produced by TokenReview:
#   service_account_name, service_account_uid, service_account_namespace,
#   service_account_secret_name, role.
# The engine's per-tenant SA name is deterministically derived from the
# broker_connections.id (etradie-mt-<id[:12]>), so the SA name is a
# stable, non-secret tenant identifier. The engine writes credentials
# to <path_prefix>/<sa_name>; the Pod reads from the SAME path because
# {{identity.entity.aliases.<accessor>.metadata.service_account_name}}
# renders to its own SA name.
#
# {{identity.entity.aliases.<accessor>.metadata.<key>}} templating is
# the Vault-native multi-tenant isolation primitive. The accessor value
# is the backend's runtime accessor (vault_auth_backend.kubernetes.accessor).
# ---------------------------------------------------------------------
resource "vault_policy" "mt_node_tenant" {
  name = "mt-node-tenant-${var.environment}"

  policy = <<-EOT
    # Per-Pod tenant secret. Path is templated on the Pod's SA name.
    # The engine writes to the SAME path at provision time.
    path "${var.vault_mount}/data/tenants/mt-node/{{identity.entity.aliases.${vault_auth_backend.kubernetes.accessor}.metadata.service_account_name}}" {
      capabilities = ["read"]
    }
  EOT
}

# ---------------------------------------------------------------------
# Role: mt_node_provisioner
#
# Engine pod's SA authenticates here. Bound to the etradie-engine SA in
# etradie-system namespace.
# ---------------------------------------------------------------------
resource "vault_kubernetes_auth_backend_role" "mt_node_provisioner" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "mt-node-provisioner"
  bound_service_account_names      = ["etradie-engine"]
  bound_service_account_namespaces = ["etradie-system"]
  token_policies                   = [vault_policy.mt_node_provisioner.name]
  token_period                     = 900   # 15m renewals
  token_max_ttl                    = 3600  # 1h hard cap
  audience                         = "vault"
}

# ---------------------------------------------------------------------
# Role: mt_node_tenant
#
# Per-tenant mt-node Pods authenticate here. Each Pod has its OWN
# ServiceAccount provisioned by the engine (name etradie-mt-<conn[:12]>);
# the SA is annotated with vault.hashicorp.com/role and the role binds
# via a regex that matches the SA name pattern. The connection_id metadata
# is extracted from the SA's etradie.connection-id annotation by the
# K8s auth backend (via the metadata.* fields).
#
# alias_name_source=serviceaccount_uid is intentional: it keeps the
# Vault entity alias stable across SA token rotations. The connection_id
# metadata flows through alias_metadata, not alias_name.
# ---------------------------------------------------------------------
resource "vault_kubernetes_auth_backend_role" "mt_node_tenant" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "mt-node-tenant"
  # Glob-match every per-tenant SA name the engine creates. The engine's
  # SA names follow the pattern etradie-mt-<conn[:12]>; '*' would also
  # match etradie-engine, so we use a more specific prefix.
  bound_service_account_names      = ["etradie-mt-*"]
  bound_service_account_namespaces = ["etradie-system"]
  token_policies                   = [vault_policy.mt_node_tenant.name]
  token_period                     = 900
  token_max_ttl                    = 3600
  audience                         = "vault"
  alias_name_source                = "serviceaccount_uid"
}
