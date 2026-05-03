# Cloudflare AOP - origin-pull/

This directory holds the CA bundle that edge-ingress requires on every
TLS handshake (mTLS is mandatory; there is no skip path).

## Files

| File | Purpose | Where it comes from |
|------|---------|---------------------|
| `generate-dev-certs.sh` | Generator script that produces the four PEMs below. **The only file in this directory that is committed.** | Hand-written, idempotent. |
| `origin-pull-ca.pem` | The active CA whose certificates edge-ingress trusts. | **In dev**: identical bytes to `dev-aop-ca.pem` (produced by the generator). **In staging / production**: the Cloudflare-published AOP CA, resolved from Vault via the `cloudflare-aop-ca` ExternalSecret. |
| `dev-aop-ca.pem` | Self-signed dev CA. **Trusts nothing outside local containers.** | Produced by `generate-dev-certs.sh`; gitignored. |
| `dev-client.crt` + `dev-client.key` | Client cert + key signed by the dev CA. | Produced by `generate-dev-certs.sh`; gitignored. |

## First-time setup

```bash
make dev-certs   # or: ./deployments/cloudflare/origin-pull/generate-dev-certs.sh
```

Run once per workstation. Idempotent: skips work if the bundle is
already present. Pass `--force` to regenerate.

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

## Regenerating

```bash
./generate-dev-certs.sh --force
```

Reads its own working directory, so safe to run from anywhere on the
contributor's machine.

## Threat surface

The dev CA private key is destroyed at the end of every generator
run. `dev-aop-ca.pem` is a public certificate; possessing it grants
nothing more than the ability to verify other dev certs.
`dev-client.key` IS a private key, but the cert it pairs with is
trusted ONLY by the local dev CA, which is trusted ONLY by the local
edge-ingress container running on the dev workstation. Stealing
`dev-client.key` lets an attacker authenticate to a local container
on a developer's laptop - nothing more. No production system trusts
any of these files. None of them are committed; the entire directory
except the generator and README is gitignored.
