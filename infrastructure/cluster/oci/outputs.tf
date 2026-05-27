# Placeholder outputs for the OCI cluster skeleton module. Audit ref: IO-M1.

output "cluster_name" {
  description = "OKE cluster display name. Empty until main.tf is implemented."
  value       = local.cluster_name
}

output "cluster_id" {
  description = "OKE cluster OCID. Empty until main.tf is implemented."
  value       = ""
}

output "kubeconfig_path" {
  description = "Path to a generated kubeconfig file. Empty until main.tf is implemented."
  value       = ""
}
