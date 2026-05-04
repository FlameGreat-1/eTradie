#!/usr/bin/env bash
#
# Refresh the Cloudflare published IPv4/IPv6 origin ranges, and verify
# the Cloudflare AOP CA fingerprint has not changed against the pin
# committed at deployments/cloudflare/origin-pull/aop-ca.sha256.
#
# Designed for weekly CI execution.
#
# Two modes:
#
#   normal:    Default. Reads the pin from aop-ca.sha256, fetches the
#              live CA, exits 1 on mismatch. Updates ip-ranges/*.txt
#              if Cloudflare published new ranges; exits 2 in that
#              case so CI can open a PR.
#
#   --bootstrap: First-run mode. Run once on a fresh repo to capture
#              the current live AOP CA fingerprint into
#              aop-ca.sha256 AND the PEM bytes into
#              origin-pull/origin-pull-ca.pem. Both files are then
#              committed by the operator. Subsequent runs treat them
#              as the immutable pinned baseline.
#
# Writes:
#   deployments/cloudflare/ip-ranges/ipv4.txt
#   deployments/cloudflare/ip-ranges/ipv6.txt
#   (--bootstrap only) deployments/cloudflare/origin-pull/aop-ca.sha256
#   (--bootstrap only) deployments/cloudflare/origin-pull/origin-pull-ca.pem
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
AOP_CA_PIN_FILE="${CF_DIR}/origin-pull/aop-ca.sha256"
AOP_CA_PEM_FILE="${CF_DIR}/origin-pull/origin-pull-ca.pem"

MODE="normal"
if [[ "${1:-}" == "--bootstrap" ]]; then
  MODE="bootstrap"
fi

log() {
  printf '[refresh-cloudflare-ips] %s\n' "$*" >&2
}

# Read the pinned fingerprint from the committed pin file. Strips
# comments (lines starting with #) and blank lines, takes the first
# non-empty result.
read_pin() {
  if [[ ! -f "${AOP_CA_PIN_FILE}" ]]; then
    log "FATAL: pin file not found: ${AOP_CA_PIN_FILE}"
    log "Run this script with --bootstrap once to capture the current"
    log "Cloudflare AOP CA fingerprint, then commit the result."
    exit 1
  fi
  local pin
  pin="$(grep -v -E '^[[:space:]]*(#|$)' "${AOP_CA_PIN_FILE}" | head -n1 | tr -d '[:space:]')"
  if [[ -z "${pin}" ]]; then
    log "FATAL: pin file is empty: ${AOP_CA_PIN_FILE}"
    log "Run this script with --bootstrap once to capture the current"
    log "Cloudflare AOP CA fingerprint, then commit the result."
    exit 1
  fi
  printf '%s' "${pin}"
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

if [[ "${MODE}" == "bootstrap" ]]; then
  log "--bootstrap mode: writing pin file and PEM"
  mkdir -p "$(dirname "${AOP_CA_PIN_FILE}")"
  cat > "${AOP_CA_PIN_FILE}" <<EOF
# Cloudflare Authenticated Origin Pulls (AOP) CA pinned fingerprint.
#
# Source of truth for the AOP CA bytes that edge-ingress trusts at
# /etc/edge-ingress/cloudflare/origin-pull-ca.pem. Captured once via
# \`refresh-cloudflare-ips.sh --bootstrap\` and committed; thereafter
# every weekly CI run verifies the live Cloudflare-published bytes
# still hash to this value. A mismatch means Cloudflare rotated the
# CA and an operator must follow the rotation runbook in
# docs/architecture/edge-cloudflare-envoy.md.
#
# Format: single line, lowercase hex SHA-256, no colons.
${actual_ca_sha256}
EOF
  cp "${tmp_ca}" "${AOP_CA_PEM_FILE}"
  log "wrote ${AOP_CA_PIN_FILE}"
  log "wrote ${AOP_CA_PEM_FILE}"
  log "Commit BOTH files. Subsequent runs will verify against this baseline."
  # Fall through to the IP-range refresh logic below; bootstrap is
  # additive, not exclusive.
else
  expected_pin="$(read_pin)"
  if [[ "${actual_ca_sha256}" != "${expected_pin}" ]]; then
    log "FATAL: Cloudflare AOP CA fingerprint changed."
    log "  expected (pin file): ${expected_pin}"
    log "  actual   (live):     ${actual_ca_sha256}"
    log "This is a Cloudflare CA rotation. Follow the rotation runbook"
    log "in docs/architecture/edge-cloudflare-envoy.md (\"Rotation"
    log "procedures > Cloudflare AOP CA\") BEFORE updating the pin."
    exit 1
  fi
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
