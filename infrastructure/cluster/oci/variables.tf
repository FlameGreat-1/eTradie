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

variable "kubernetes_endpoint_is_public" {
  description = "Expose the Kubernetes API on a public endpoint. Production deployments typically front this with Cloudflare Tunnel or an OCI Bastion, NOT a public endpoint."
  type        = bool
  default     = false
}

variable "kubernetes_api_subnet_id" {
  description = "OCID of the subnet hosting the K8s API endpoint."
  type        = string
}

variable "kubernetes_api_nsg_ids" {
  description = "Optional NSGs to attach to the K8s API endpoint."
  type        = list(string)
  default     = []
}

variable "kubernetes_worker_subnet_id" {
  description = "OCID of the subnet hosting node pool workers."
  type        = string
}

variable "kubernetes_lb_subnet_ids" {
  description = "OCIDs of subnets where LoadBalancer Services land. Empty list when using Cloudflare Tunnel (default platform mode)."
  type        = list(string)
  default     = []
}

variable "pods_cidr" {
  description = "Pod CIDR for the OCI VCN-Native CNI."
  type        = string
  default     = "10.244.0.0/16"
}

variable "services_cidr" {
  description = "Service CIDR."
  type        = string
  default     = "10.96.0.0/16"
}

variable "node_pool_shape" {
  description = "OCI compute shape for the platform node pool. Use a flex shape so OCPU + memory are tunable per environment."
  type        = string
  default     = "VM.Standard.E5.Flex"
}

variable "node_pool_ocpus" {
  description = "OCPUs per node (flex shape)."
  type        = number
  default     = 4
}

variable "node_pool_memory_gbs" {
  description = "Memory in GiB per node (flex shape). With 32 GiB and ~1.5 GiB per mt-node Pod, a 4-OCPU node fits ~18 mt-node Pods before bin-packing pressure."
  type        = number
  default     = 32
}

variable "node_pool_size" {
  description = "Initial node count. Cluster Autoscaler manages it from there."
  type        = number
  default     = 3
}

variable "node_pool_min_size" {
  description = "Cluster Autoscaler floor. Production: keep >= 3 for zone spread."
  type        = number
  default     = 3
}

variable "node_pool_max_size" {
  description = "Cluster Autoscaler ceiling. 12 nodes at 4 OCPU / 32 GiB = room for ~150 mt-node Pods at 1.5 GiB ceiling."
  type        = number
  default     = 12
}

variable "node_pool_boot_volume_size_gbs" {
  description = "Boot volume size per worker node (GiB)."
  type        = number
  default     = 100
}

variable "node_pool_image_id" {
  description = "Image OCID for the worker nodes. Use the latest OKE-published Oracle Linux 8 image for the target K8s version."
  type        = string
}

variable "node_pool_availability_domains" {
  description = "List of OCI availability domain names the node pool spans. Use all ADs in the region for HA."
  type        = list(string)
}

variable "node_pool_kms_key_id" {
  description = "Optional KMS key OCID for in-transit + at-rest volume encryption. When null, OCI uses the default Oracle-managed key."
  type        = string
  default     = null
}

variable "tags" {
  description = "Freeform tags applied to OCI resources."
  type        = map(string)
  default     = {}
}
