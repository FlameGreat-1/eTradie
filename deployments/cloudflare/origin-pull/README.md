# Cloudflare AOP - origin-pull/

This directory holds the CA bundle that edge-ingress requires on every
TLS handshake (mTLS is mandatory; there is no skip path).

## Files

| File | Purpose | Where it comes from |
|------|---------|---------------------|
| `origin-pull-ca.pem` | The active CA whose certificates edge-ingress trusts. | **In dev**: identical bytes to `dev-aop-ca.pem`. **In staging / production**: the Cloudflare-published AOP CA, resolved from Vault via the `cloudflare-aop-ca` ExternalSecret. |
| `dev-aop-ca.pem` | Self-signed dev CA used by the local docker-compose `edge` profile. **Trusts nothing outside local containers.** | Generated once via the openssl recipe below; committed for reproducibility. |
| `dev-client.crt` + `dev-client.key` | Client cert signed by `dev-aop-ca.pem`. Used by `curl --cert ...` to authenticate to the local edge-ingress. | Generated alongside the CA. |

## Local docker-compose flow

```bash
docker compose --profile edge up --build

# Authenticated request (succeeds, gets to gateway):
curl --cacert deployments/edge-ingress/docker/certs/localhost.crt \
     --cert  deployments/cloudflare/origin-pull/dev-client.crt \
     --key   deployments/cloudflare/origin-pull/dev-client.key \
     https://localhost:8443/auth/healthz

# Unauthenticated request (must fail at TLS handshake):
curl -k https://localhost:8443/auth/healthz
```

If the second invocation does NOT fail, the mTLS code path is broken.
This is the local equivalent of the production validation step in
`docs/architecture/edge-cloudflare-envoy.md` ("direct origin hit fails
at TLS").

## Production / staging

- The bytes of `origin-pull-ca.pem` are NEVER committed for non-dev.
- The Vault path `etradie/services/edge-ingress/cloudflare/aop_ca` is
  the source of truth.
- The `cloudflare-aop-ca` ExternalSecret synthesises the Kubernetes
  Secret of the same name in `edge-ingress-system`.
- The edge-ingress Deployment mounts that Secret at
  `/etc/edge-ingress/cloudflare/origin-pull-ca.pem` - the same path
  the local docker-compose uses, so there is one code path across all
  environments.

## Regenerating the dev CA

The committed dev CA is valid for 10 years. To regenerate (e.g. on
rotation policy):

```bash
set -eu
cd deployments/cloudflare/origin-pull

# 1. New CA key + self-signed CA cert (10 years).
openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout dev-aop-ca.key \
  -out    dev-aop-ca.pem \
  -days 3650 \
  -subj "/CN=etradie-dev-aop-ca/O=eTradie Dev/C=US"

# 2. New client key + CSR.
openssl req -nodes -newkey rsa:2048 \
  -keyout dev-client.key \
  -out    dev-client.csr \
  -subj "/CN=etradie-dev-client/O=eTradie Dev/C=US"

# 3. Sign the client cert with the new CA (5 years).
openssl x509 -req -in dev-client.csr \
  -CA dev-aop-ca.pem -CAkey dev-aop-ca.key -CAcreateserial \
  -out dev-client.crt -days 1825 -sha256

# 4. Make origin-pull-ca.pem identical to dev-aop-ca.pem for local.
cp dev-aop-ca.pem origin-pull-ca.pem

# 5. Tidy.
rm dev-aop-ca.key dev-client.csr dev-aop-ca.srl
```

Commit only `dev-aop-ca.pem`, `dev-client.crt`, `dev-client.key`, and
`origin-pull-ca.pem`. **Never commit the CA private key**
(`dev-aop-ca.key`).

## Threat surface

The dev CA private key is destroyed at generation time (step 5 above).
The committed `dev-aop-ca.pem` is a public certificate; possessing it
grants nothing more than the ability to verify other dev certs.
`dev-client.key` IS a private key, but the cert it pairs with is
trusted ONLY by the local dev CA, which is trusted ONLY by the local
edge-ingress container running on the dev workstation. Stealing
`dev-client.key` lets an attacker authenticate to a local container
on a developer's laptop - nothing more. No production system trusts
any of these files.
