# Cloudflare integration

This directory holds every artefact required to put **Cloudflare Free** in
front of `edge-ingress` -> `envoy` -> `gateway` so that:

1. **Layer-3/4 DDoS** is absorbed by Cloudflare before any byte reaches the
   eTradie origin.
2. **The origin IP is never exposed** in DNS. All public hostnames
   (`api.etradie.com`, `*.etradie.com`, `staging-api.etradie.com`) resolve to
   Cloudflare's anycast IPs.
3. **Origin-spoofing** is impossible: even if an attacker discovers the
   origin IP, they cannot terminate TLS on `edge-ingress:443` because
   `edge-ingress` requires a client certificate signed by Cloudflare's
   public Authenticated Origin Pulls (AOP) CA on every connection.
4. **Trust-aware client-IP resolution** in `src/auth/clientip.go`
   honours `CF-Connecting-IP` and `X-Forwarded-For` only when the
   immediate peer is in Cloudflare's published IP ranges OR in the
   operator-configured `AUTH_TRUSTED_PROXY_CIDRS`. Anywhere else, the
   raw peer wins. This makes per-IP rate limiting genuinely per-IP
   even when the path is bypassed.

## Files

| Path | Purpose |
|------|---------|
| `origin-pull/origin-pull-ca.pem` | Cloudflare's canonical AOP CA chain. **Not committed**: `edge-ingress` reads it at runtime from a Vault-backed Secret synthesised by the `cloudflare-aop-ca` ExternalSecret in `helm/edge-ingress/templates/externalsecret-aop-ca.yaml`. |
| `origin-pull/generate-dev-certs.sh` | Generates a self-signed dev CA + client cert for the local docker-compose `edge` profile. |
| `ip-ranges/ipv4.txt` | Cloudflare's published IPv4 origin ranges. **Source of truth**. |
| `ip-ranges/ipv6.txt` | Cloudflare's published IPv6 origin ranges. **Source of truth**. |
| `scripts/refresh-cloudflare-ips.sh` | Re-pulls the canonical ranges from Cloudflare and writes them to BOTH `ip-ranges/` AND `helm/gateway/files/cloudflare/`. Designed for weekly CI execution. |

## Helm consumption

* `helm/edge-ingress/templates/externalsecret-aop-ca.yaml` synthesises
  the AOP CA Secret from Vault path
  `etradie/services/edge-ingress/cloudflare/aop_ca` and mounts it into
  edge-ingress at `/etc/edge-ingress/cloudflare/origin-pull-ca.pem`.
* `helm/gateway/templates/configmap-cf-ranges.yaml` renders a ConfigMap
  from the chart-local copy at `helm/gateway/files/cloudflare/`,
  gated on `trustChain.trustCloudflare="true"`. Mounted into gateway
  at `/etc/etradie/cloudflare/{ipv4,ipv6}.txt`.

## Operator runbook

### 1. Enable AOP in the Cloudflare dashboard

1. Cloudflare dashboard -> **SSL/TLS** -> **Origin Server** -> **Authenticated Origin Pulls**.
2. Set **Authenticated Origin Pulls** to **On (zone-level)**.
3. Verify the cert at
    https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem
    matches the bytes of `origin-pull/origin-pull-ca.pem` shipped here:
    ```
    openssl x509 -in deployments/cloudflare/origin-pull/origin-pull-ca.pem -noout -fingerprint -sha256
    ```
    The expected fingerprint is documented in Cloudflare's docs and is
    pinned by the Rust TLS layer (`src/edge-ingress/crates/tls/src/`).
4. Cloudflare dashboard -> **SSL/TLS** -> **Edge Certificates** -> **Always Use HTTPS** = **On**, **Minimum TLS Version** = **1.2**, **TLS 1.3** = **On**.

### 2. Origin firewall (defence-in-depth pair with AOP)

AOP alone makes spoofing impossible at the application layer. Adding an
origin-firewall rule that drops TCP/443 from anything **outside**
Cloudflare's published ranges gives you a second layer that does not
rely on TLS handshake reaching the application. Configure your cloud
provider's firewall (AWS Security Group, GCP firewall, etc.) to allow
port 443 only from the union of `ip-ranges/ipv4.txt` and
`ip-ranges/ipv6.txt`.

A reference Terraform module is provided under `infrastructure/cloudflare/`
in a sibling commit.

### 3. Refresh schedule

Cloudflare adds new ranges occasionally. The CI pipeline runs
`scripts/refresh-cloudflare-ips.sh` every Sunday and opens a PR if the
diff is non-empty. The PR must be merged within 7 days to avoid
legitimate Cloudflare edge nodes being treated as untrusted by
`src/auth/clientip.go` (which would silently downgrade per-IP rate
limits).

### 4. Rotation of the origin-pull CA

Cloudflare has rotated the AOP CA exactly once historically. When they
rotate again:

1. Cloudflare publishes the new chain at the same URL.
2. `scripts/refresh-cloudflare-ips.sh` validates the chain in addition
    to ranges, and a CI alert fires if the SHA-256 fingerprint changes.
3. Update `origin-pull/origin-pull-ca.pem` with the new chain (do NOT
    overwrite; **append** until the cutover window closes, then drop
    the old). edge-ingress accepts any cert signed by **either** CA in
    the bundle during the overlap window.
4. Once Cloudflare's announced cutover date passes, drop the old CA
    from the bundle and redeploy.

### 5. Validating end-to-end

After all four layers are deployed (Cloudflare -> edge-ingress -> envoy ->
gateway), the following must all be true:

- `curl -v https://api.etradie.com/auth/healthz` returns 200 via
   Cloudflare.
- Direct origin hit (`curl -v --resolve api.etradie.com:443:<origin-ip>
   https://api.etradie.com/auth/healthz`) **fails** with a TLS handshake
   error (no client cert).
- Gateway logs show `client_ip_resolution.method=cf_connecting_ip` for
   Cloudflare-originated requests when `AUTH_TRUST_CLOUDFLARE=true`.
