#!/usr/bin/env bash
#
# Refresh the Cloudflare published IPv4/IPv6 origin ranges, and verify
# the Cloudflare AOP CA fingerprint has not changed. The committed
# range files are the source of truth for the gateway's trust-aware
# client-IP resolver and for the origin firewall Terraform module;
# the AOP CA itself lives in Vault, NOT in git, so this script never
# writes the CA bytes back to the repo.
#
# Designed for weekly CI execution.
#
# Writes:
#   deployments/cloudflare/ip-ranges/ipv4.txt
#   deployments/cloudflare/ip-ranges/ipv6.txt
#
# Verifies (does NOT write):
#   SHA-256 fingerprint of
#   https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem
#   matches EXPECTED_AOP_CA_SHA256 below.
#
# Exit codes:
#   0 - success, no diff (ranges unchanged, CA fingerprint matches)
#   1 - script failure (network, validation, CA fingerprint mismatch).
#       CA mismatch is exit 1 not 2 because a CA rotation cannot be
#       fixed by opening a PR: an operator MUST update Vault first.
#   2 - success, IP ranges changed (CI uses this to open a PR with the
#       updated ip-ranges files).
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CF_DIR="${REPO_ROOT}/deployments/cloudflare"
IPV4_FILE="${CF_DIR}/ip-ranges/ipv4.txt"
IPV6_FILE="${CF_DIR}/ip-ranges/ipv6.txt"

# Pinned fingerprint of the current Cloudflare AOP CA. When Cloudflare
# rotates this changes, the script fails with exit 1, and an operator
# must perform the rotation procedure documented in
# docs/architecture/edge-cloudflare-envoy.md before updating this pin.
#
# To find the live fingerprint:
#   curl -fsSL https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem | \
#     openssl x509 -noout -fingerprint -sha256 | awk -F= '{print $2}' | tr -d ':' | tr A-Z a-z
EXPECTED_AOP_CA_SHA256=""

log() {
  printf '[refresh-cloudflare-ips] %s\n' "$*" >&2
}

fetch() {
  local url="$1"
  local out="$2"
  log "fetching ${url}"
  curl --fail --silent --show-error --location --max-time 30 \
    --retry 3 --retry-delay 2 --retry-connrefused \
    --output "${out}" "${url}"
}

validate_cidrs() {
  local file="$1"
  local family="$2"
  local ok=1
  while IFS= read -r line; do
    [[ -z "${line}" || "${line}" =~ ^# ]] && continue
    if [[ "${family}" == "4" ]]; then
      if ! [[ "${line}" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}/[0-9]{1,2}$ ]]; then
        log "invalid IPv4 CIDR in ${file}: ${line}"
        ok=0
      fi
    else
      if ! [[ "${line}" =~ ^[0-9a-fA-F:]+/[0-9]{1,3}$ ]]; then
        log "invalid IPv6 CIDR in ${file}: ${line}"
        ok=0
      fi
    fi
  done < "${file}"
  [[ "${ok}" -eq 1 ]]
}

mkdir -p "${CF_DIR}/ip-ranges"

tmp_ipv4="$(mktemp)"
tmp_ipv6="$(mktemp)"
tmp_ca="$(mktemp)"
trap 'rm -f "${tmp_ipv4}" "${tmp_ipv6}" "${tmp_ca}"' EXIT

fetch "https://www.cloudflare.com/ips-v4" "${tmp_ipv4}"
fetch "https://www.cloudflare.com/ips-v6" "${tmp_ipv6}"
fetch "https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem" "${tmp_ca}"

# Sort deterministically so the diff is stable.
LC_ALL=C sort -u "${tmp_ipv4}" -o "${tmp_ipv4}"
LC_ALL=C sort -u "${tmp_ipv6}" -o "${tmp_ipv6}"

validate_cidrs "${tmp_ipv4}" 4
validate_cidrs "${tmp_ipv6}" 6

actual_ca_sha256="$(openssl x509 -in "${tmp_ca}" -noout -fingerprint -sha256 \
  | awk -F= '{print $2}' | tr -d ':' | tr '[:upper:]' '[:lower:]')"
log "fetched AOP CA SHA-256: ${actual_ca_sha256}"

if [[ -z "${EXPECTED_AOP_CA_SHA256}" ]]; then
  log "FATAL: EXPECTED_AOP_CA_SHA256 is unset."
  log "Pin the current Cloudflare AOP CA fingerprint at the top of"
  log "this script before running it; an empty pin is not a valid"
  log "baseline."
  exit 1
fi

if [[ "${actual_ca_sha256}" != "${EXPECTED_AOP_CA_SHA256}" ]]; then
  log "FATAL: Cloudflare AOP CA fingerprint changed."
  log "  expected: ${EXPECTED_AOP_CA_SHA256}"
  log "  actual:   ${actual_ca_sha256}"
  log "This is a Cloudflare CA rotation. Follow the rotation runbook"
  log "in docs/architecture/edge-cloudflare-envoy.md (\"Rotation"
  log "procedures > Cloudflare AOP CA\") BEFORE updating the pin."
  exit 1
fi

changed=0

if ! cmp -s "${tmp_ipv4}" "${IPV4_FILE}"; then
  log "ipv4 ranges changed; writing ${IPV4_FILE}"
  cp "${tmp_ipv4}" "${IPV4_FILE}"
  changed=1
fi

if ! cmp -s "${tmp_ipv6}" "${IPV6_FILE}"; then
  log "ipv6 ranges changed; writing ${IPV6_FILE}"
  cp "${tmp_ipv6}" "${IPV6_FILE}"
  changed=1
fi

if [[ "${changed}" -eq 1 ]]; then
  log "Cloudflare IP ranges changed. CI should open a PR."
  exit 2
fi

log "no changes"
exit 0
