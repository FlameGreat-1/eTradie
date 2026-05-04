# infrastructure/cluster/oci/main.tf
#
# OCI OKE cluster bootstrap. SKELETON ONLY — see README.md.
#
# An operator targeting OCI fills this in against either:
#   - oracle/oci/containerengine_cluster + containerengine_node_pool,
#     OR
#   - the community oci-oke Terraform module.
#
# The variable surface in variables.tf is final; main.tf is
# intentionally empty so the module compiles to a no-op until the
# operator fills it in. This avoids shipping unverified OCI code
# that pretends to work.

locals {
  cluster_name = coalesce(var.cluster_name, "etradie-${var.environment}")
}

# Placeholder so `terraform init` succeeds without errors. Replace
# with the actual OKE cluster + node pool resources before applying.
resource "null_resource" "placeholder" {
  triggers = {
    cluster_name = local.cluster_name
  }
}
