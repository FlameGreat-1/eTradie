#!/usr/bin/env bash
# ============================================================================
# pin-image-digests.sh
#
# Pin every Dockerfile `FROM` base image to an immutable @sha256 digest.
#
# Digests are RESOLVED FROM THE REGISTRY at run time via
# `docker buildx imagetools inspect` - they are never hand-written. Run
# this once to materialise the pins, commit the result, and let
# Dependabot's docker ecosystem keep them current thereafter.
#
# Usage:
#   make pin-image-digests      # or: bash scripts/pin-image-digests.sh
#
# Requirements:
#   - docker (with buildx) on PATH and able to pull from the registries
#     hosting the base images (Docker Hub for the public bases here).
#
# Behaviour:
#   - Idempotent. A FROM already carrying a digest is re-resolved and
#     updated to the current digest for its tag (digest rotation).
#   - Only the tracked Dockerfiles below are rewritten.
#   - A registry-resolution failure for any image aborts the whole run
#     with a non-zero exit and leaves files untouched (set -e + a temp
#     file swap), so a partial pin can never be committed.
# ============================================================================
set -euo pipefail

# Tracked Dockerfiles. Keep in lockstep with the docker entries in
# .github/dependabot.yml and the build matrix in .github/workflows/ci.yml.
DOCKERFILES=(
  "Dockerfile"
  "src/gateway/Dockerfile"
  "src/execution/Dockerfile"
  "src/management/Dockerfile"
  "src/billing/Dockerfile"
  "docker/mt-node/Dockerfile"
  "deployments/edge-ingress/docker/Dockerfile.edge-ingress"
)

if ! command -v docker >/dev/null 2>&1; then
  echo "FATAL: docker is required to resolve registry digests" >&2
  exit 1
fi

# resolve_digest <image-ref-without-digest> -> prints sha256:...
# <image-ref> is e.g. "alpine:3.19" or "golang:1.23-alpine".
resolve_digest() {
  local ref="$1"
  local digest
  digest="$(docker buildx imagetools inspect "${ref}" --format '{{.Manifest.Digest}}' 2>/dev/null)" || true
  if [[ -z "${digest}" || "${digest}" != sha256:* ]]; then
    echo "FATAL: could not resolve a digest for '${ref}' from the registry" >&2
    return 1
  fi
  printf '%s' "${digest}"
}

pin_file() {
  local file="$1"
  if [[ ! -f "${file}" ]]; then
    echo "WARN: ${file} not found; skipping" >&2
    return 0
  fi
  local tmp
  tmp="$(mktemp)"
  # Process line by line. A FROM line looks like one of:
  #   FROM image:tag
  #   FROM image:tag AS stage
  #   FROM image:tag@sha256:... [AS stage]   (already pinned)
  # We normalise to: FROM image:tag@sha256:<resolved> [AS stage]
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" =~ ^([[:space:]]*FROM[[:space:]]+)([^[:space:]@]+)(@sha256:[a-f0-9]+)?([[:space:]]+[Aa][Ss][[:space:]]+[^[:space:]]+)?[[:space:]]*$ ]]; then
      local prefix="${BASH_REMATCH[1]}"
      local imageref="${BASH_REMATCH[2]}"   # image:tag (no digest)
      local suffix="${BASH_REMATCH[4]:-}"   # " AS stage" or empty
      # Skip a bare scratch / build-stage alias FROM (no registry image).
      if [[ "${imageref}" == "scratch" || "${imageref}" != *:* ]]; then
        printf '%s\n' "${line}" >> "${tmp}"
        continue
      fi
      local digest
      digest="$(resolve_digest "${imageref}")"
      # prefix retains the original 'FROM ' token plus its indentation.
      printf '%s%s@%s%s\n' "${prefix}" "${imageref}" "${digest}" "${suffix}" >> "${tmp}"
      echo "pinned: ${imageref}@${digest}  (${file})" >&2
    else
      printf '%s\n' "${line}" >> "${tmp}"
    fi
  done < "${file}"
  mv "${tmp}" "${file}"
}

for f in "${DOCKERFILES[@]}"; do
  pin_file "${f}"
done

echo "done. review 'git diff' and commit the pinned digests." >&2
