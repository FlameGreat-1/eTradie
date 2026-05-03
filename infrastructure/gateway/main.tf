# Render the kustomize overlay for the requested environment with the
# image tag and per-env values injected as a final patch. The render is
# done in a null_resource so the image-pin step is reproducible from a
# clean checkout (`kustomize edit set image` mutates kustomization.yaml
# in place; we run it in a copy under .terraform to keep the repo tree
# clean).

locals {
  overlay_path = "${var.repo_root}/${var.kustomize_path}/overlays/${var.environment}"
  image_ref    = "${var.image_repository}:${var.image_tag}"
  workdir      = "${path.module}/.terraform/build"
}

resource "null_resource" "build_manifest" {
  triggers = {
    overlay_path        = local.overlay_path
    image_ref           = local.image_ref
    replicas_min        = var.replicas_min
    replicas_max        = var.replicas_max
    vault_path          = var.vault_path
    log_level           = var.log_level
    trusted_proxy_cidrs = var.trusted_proxy_cidrs
    trust_cloudflare    = tostring(var.trust_cloudflare)
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu
      mkdir -p ${local.workdir}
      rm -rf ${local.workdir}/${var.environment}
      cp -r ${local.overlay_path} ${local.workdir}/${var.environment}

      # Pin the image tag in the copied overlay (does not touch the
      # repo tree).
      cd ${local.workdir}/${var.environment}
      kustomize edit set image \
        ${var.image_repository}=${local.image_ref}

      # Render to a flat manifest the kubectl provider applies.
      kustomize build . > ${local.workdir}/${var.environment}-manifest.yaml
    EOT
  }
}

data "local_file" "rendered_manifest" {
  filename   = "${local.workdir}/${var.environment}-manifest.yaml"
  depends_on = [null_resource.build_manifest]
}

data "kubectl_file_documents" "manifest" {
  content = data.local_file.rendered_manifest.content
}

resource "kubectl_manifest" "gateway" {
  for_each  = data.kubectl_file_documents.manifest.manifests
  yaml_body = each.value

  # Ordering: namespaces and CRDs first; gateway resources rely on
  # ExternalSecrets being present in the namespace, which the platform
  # module guarantees before this module runs.
  server_side_apply = true
  force_conflicts   = true
}
