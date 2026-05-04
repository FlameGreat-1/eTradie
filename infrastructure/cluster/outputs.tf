output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API endpoint (private)."
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64-encoded EKS cluster CA certificate."
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "OIDC provider ARN (used by IRSA-bound service accounts in helm charts)."
  value       = module.eks.oidc_provider_arn
}

output "oidc_provider_url" {
  description = "OIDC provider URL (without https://)."
  value       = module.eks.cluster_oidc_issuer_url
}

output "irsa_eso_role_arn" {
  description = "IRSA role ARN for External Secrets Operator. Annotate the ESO ServiceAccount with this."
  value       = module.irsa_eso.iam_role_arn
}

output "irsa_autoscaler_role_arn" {
  description = "IRSA role ARN for cluster-autoscaler."
  value       = module.irsa_autoscaler.iam_role_arn
}

output "irsa_alb_controller_role_arn" {
  description = "IRSA role ARN for the AWS Load Balancer Controller."
  value       = module.irsa_alb.iam_role_arn
}

output "vault_paths" {
  description = "Bootstrapped Vault paths (operator must populate before ArgoCD reconciles)."
  value = {
    edge_ingress_tls    = vault_kv_secret_v2.edge_ingress_tls.path
    edge_ingress_aop_ca = vault_kv_secret_v2.edge_ingress_aop_ca.path
    edge_ingress_maxmind = vault_kv_secret_v2.edge_ingress_maxmind.path
    gateway              = vault_kv_secret_v2.gateway.path
  }
}
