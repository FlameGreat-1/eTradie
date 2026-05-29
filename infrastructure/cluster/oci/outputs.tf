output "cluster_id" {
  description = "OCID of the OKE cluster."
  value       = oci_containerengine_cluster.etradie.id
}

output "cluster_name" {
  description = "Display name of the OKE cluster."
  value       = oci_containerengine_cluster.etradie.name
}

output "cluster_endpoint" {
  description = "K8s API endpoint(s)."
  value       = oci_containerengine_cluster.etradie.endpoints
  sensitive   = false
}

output "node_pool_id" {
  description = "OCID of the platform node pool."
  value       = oci_containerengine_node_pool.platform.id
}

output "kubeconfig" {
  description = "kubeconfig YAML for the cluster (30-day token). Pipe to ~/.kube/etradie-<env>.yaml."
  value       = data.oci_containerengine_cluster_kube_config.etradie.content
  sensitive   = true
}
