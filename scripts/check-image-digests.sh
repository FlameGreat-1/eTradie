#!/usr/bin/env bash
# ============================================================================
# check-image-digests.sh
#
# Fail if any `FROM` line in a tracked Dockerfile references a base
# image by tag without an immutable @sha256 digest. Build-stage alias
# references (FROM <stage>) and `FROM scratch` are exempt.
#
# Used by CI as the digest-pinning enforcement gate. Run directly to
# audit locally:
#   bash scripts/check-image-digests.sh
# ============================================================================
set -euo pipefail

DOCKERFILES=(
  "Dockerfile"
  "src/gateway/Dockerfile"
  "src/execution/Dockerfile"
  "src/management/Dockerfile"
  "src/billing/Dockerfile"
  "docker/mt-node/Dockerfile"
  "deployments/edge-ingress/docker/Dockerfile.edge-ingress"
)

unpinned=0

for file in "${DOCKERFILES[@]}"; do
  if [[ ! -f "${file}" ]]; then
    echo "WARN: ${file} not found; skipping" >&2
    continue
  fi
  # Collect known build-stage aliases declared by 'AS <name>' so a
  # later 'FROM <name>' (stage reference) is not flagged as unpinned.
  mapfile -t stages < <(grep -iEo '[[:space:]]+as[[:space:]]+[^[:space:]]+[[:space:]]*$' "${file}" \
    | sed -E 's/[[:space:]]+[Aa][Ss][[:space:]]+//; s/[[:space:]]*$//' || true)
  while IFS= read -r line; do
    # Strip the leading 'FROM ' and any trailing ' AS stage'.
    ref="$(echo "${line}" | sed -E 's/^[[:space:]]*FROM[[:space:]]+//; s/[[:space:]]+[Aa][Ss][[:space:]]+.*$//; s/[[:space:]]*$//')"
    # Exempt: scratch, a build-stage alias, or an already-pinned digest.
    if [[ "${ref}" == "scratch" ]]; then continue; fi
    is_stage=0
    for s in "${stages[@]:-}"; do
      if [[ "${ref}" == "${s}" ]]; then is_stage=1; break; fi
    done
    if [[ "${is_stage}" -eq 1 ]]; then continue; fi
    if [[ "${ref}" == *@sha256:* ]]; then continue; fi
    echo "UNPINNED: ${file}: FROM ${ref}" >&2
    unpinned=$((unpinned + 1))
  done < <(grep -iE '^[[:space:]]*FROM[[:space:]]+' "${file}")
done

if [[ "${unpinned}" -gt 0 ]]; then
  echo "" >&2
  echo "${unpinned} unpinned base image(s). Run 'make pin-image-digests' to pin them." >&2
  exit 1
fi

echo "all tracked Dockerfile base images are digest-pinned"
