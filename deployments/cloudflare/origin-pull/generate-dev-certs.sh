#!/usr/bin/env bash
#
# Generate the local-only Cloudflare AOP dev CA + client cert used by
# the docker-compose `edge` profile.
#
# Output (all in this directory):
#   dev-aop-ca.pem      Self-signed CA (10 years).
#   dev-client.crt      Client cert signed by the CA (5 years).
#   dev-client.key      Client key.
#   origin-pull-ca.pem  Identical bytes to dev-aop-ca.pem - the file
#                       edge-ingress mounts at
#                       /etc/edge-ingress/cloudflare/origin-pull-ca.pem
#                       (same in-pod path as staging / production for
#                       one code path everywhere).
#
# The generated files are .gitignored. Do NOT commit them.
#
# Usage:
#   ./generate-dev-certs.sh           # generate if missing
#   ./generate-dev-certs.sh --force   # regenerate even if present
#
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${DIR}"

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
  FORCE=1
fi

if [[ "${FORCE}" -eq 0 \
   && -s origin-pull-ca.pem \
   && -s dev-client.crt \
   && -s dev-client.key ]]; then
  echo "[generate-dev-certs] PEM bundle already present; skipping (use --force to regenerate)" >&2
  exit 0
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "[generate-dev-certs] openssl not found in PATH" >&2
  exit 1
fi

echo "[generate-dev-certs] generating dev AOP CA + client cert" >&2

# 1. CA key + self-signed CA cert (10 years).
openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout dev-aop-ca.key \
  -out    dev-aop-ca.pem \
  -days 3650 \
  -subj "/CN=etradie-dev-aop-ca/O=eTradie Dev/C=US" \
  >/dev/null 2>&1

# 2. Client key + CSR.
openssl req -nodes -newkey rsa:2048 \
  -keyout dev-client.key \
  -out    dev-client.csr \
  -subj "/CN=etradie-dev-client/O=eTradie Dev/C=US" \
  >/dev/null 2>&1

# 3. Sign the client cert with the CA (5 years).
openssl x509 -req -in dev-client.csr \
  -CA dev-aop-ca.pem -CAkey dev-aop-ca.key -CAcreateserial \
  -out dev-client.crt -days 1825 -sha256 \
  >/dev/null 2>&1

# 4. origin-pull-ca.pem is the file edge-ingress reads. In dev, it's
#    a copy of dev-aop-ca.pem. In staging/production, it's the
#    Cloudflare-published bytes resolved from Vault.
cp dev-aop-ca.pem origin-pull-ca.pem

# 5. Drop the CA private key and intermediate scratch files.
#    Keeping the CA private key on disk in a dev workstation is a
#    real attack surface (someone steals it and signs new client
#    certs that are trusted by the local edge); destroying it now
#    means the only way to mint new dev clients is to rerun this
#    script (which produces a fresh CA the local edge will not
#    trust until restarted).
rm -f dev-aop-ca.key dev-client.csr dev-aop-ca.srl

# 6. Lock down permissions on the client key.
chmod 600 dev-client.key

echo "[generate-dev-certs] generated:" >&2
echo "  $(pwd)/dev-aop-ca.pem" >&2
echo "  $(pwd)/origin-pull-ca.pem" >&2
echo "  $(pwd)/dev-client.crt" >&2
echo "  $(pwd)/dev-client.key" >&2
