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
    data_layer_postgres  = vault_kv_secret_v2.data_layer_postgres.path
    data_layer_redis     = vault_kv_secret_v2.data_layer_redis.path
    data_layer_chromadb  = vault_kv_secret_v2.data_layer_chromadb.path
  }
}
