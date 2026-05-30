output "vault_paths" {
  description = "Bootstrapped Vault paths the helm charts reference via ExternalSecrets. Audit ref: IV-H4."
  value = {
    edge_ingress_tls     = vault_kv_secret_v2.edge_ingress_tls.path
    edge_ingress_aop_ca  = vault_kv_secret_v2.edge_ingress_aop_ca.path
    edge_ingress_tunnel  = vault_kv_secret_v2.edge_ingress_tunnel.path
    edge_ingress_maxmind = vault_kv_secret_v2.edge_ingress_maxmind.path
    gateway              = vault_kv_secret_v2.gateway.path
    engine               = vault_kv_secret_v2.engine.path
    execution            = vault_kv_secret_v2.execution.path
    management           = vault_kv_secret_v2.management.path
    billing              = vault_kv_secret_v2.billing.path
    mt_node              = vault_kv_secret_v2.mt_node.path
    data_layer_postgres  = vault_kv_secret_v2.data_layer_postgres.path
    data_layer_redis     = vault_kv_secret_v2.data_layer_redis.path
    data_layer_chromadb  = vault_kv_secret_v2.data_layer_chromadb.path
  }
}

# Per-tenant mt-node credential plumbing. The engine writes
# credentials under <path_prefix>/<sa_name> at provision time; the
# per-tenant Pod authenticates via tenant_role and reads from the
# same path. See mt_node_tenant_secrets.tf for the full contract.
output "mt_node_tenant_secrets" {
  description = "Per-tenant mt-node credential infrastructure (Vault Agent Injector). The engine writes plaintext credentials to <path_prefix>/<connection_id> at provision time; the per-tenant Pod fetches them via the tenant role."
  value = {
    path_prefix          = "${var.vault_mount}/tenants/mt-node"
    provisioner_role     = vault_kubernetes_auth_backend_role.mt_node_provisioner.role_name
    tenant_role          = vault_kubernetes_auth_backend_role.mt_node_tenant.role_name
    provisioner_policy   = vault_policy.mt_node_provisioner.name
    tenant_policy        = vault_policy.mt_node_tenant.name
    k8s_auth_backend     = vault_auth_backend.kubernetes.path
  }
}
