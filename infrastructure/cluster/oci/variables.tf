variable "environment" {
  description = "Target environment. Drives naming."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be one of: staging, production."
  }
}

variable "region" {
  description = "OCI region (e.g. us-ashburn-1, uk-london-1)."
  type        = string
}

variable "compartment_id" {
  description = "OCI compartment OCID the cluster lives in."
  type        = string
}

variable "vcn_id" {
  description = "VCN OCID for the OKE cluster."
  type        = string
}

variable "kubernetes_version" {
  description = "OKE Kubernetes minor version. Bump explicitly when OCI publishes a new patch line. Audit ref: IO-H2."
  type        = string
  default     = "v1.32.1"
}

variable "cluster_name" {
  description = "OKE cluster display name. Defaults to etradie-<environment>."
  type        = string
  default     = null
}

variable "node_pool_shape" {
  description = "OCI compute shape for the platform node pool. Use a flex shape so OCPU + memory are tunable per environment."
  type        = string
  default     = "VM.Standard.E5.Flex"
}

variable "node_pool_size" {
  description = "Number of worker nodes in the platform pool."
  type        = number
  default     = 3
}

variable "tags" {
  description = "Freeform tags applied to OCI resources."
  type        = map(string)
  default     = {}
}
