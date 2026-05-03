output "namespace" {
  description = "Namespace the gateway runs in."
  value       = var.namespace
}

output "deployment_name" {
  description = "Name of the gateway Deployment."
  value       = "etradie-gateway"
}

output "service_name" {
  description = "Name of the ClusterIP Service."
  value       = "gateway-service"
}

output "headless_service_name" {
  description = "Name of the headless Service used for per-pod gRPC."
  value       = "gateway-headless"
}

output "image_ref" {
  description = "Fully-qualified image reference applied by this module."
  value       = local.image_ref
}

output "environment" {
  description = "Resolved environment."
  value       = var.environment
}
