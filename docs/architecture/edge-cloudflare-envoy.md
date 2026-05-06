# eTradie Edge Defence Chain - Cloudflare → edge-ingress → envoy → gateway

This document is the canonical reference for the four-layer defence
chain that fronts the eTradie gateway in staging and production. It
describes WHY each layer exists and WHAT it protects against. For
HOW to deploy the platform, see [`../deployment/README.md`](../deployment/README.md).

#### High-level chain

```text
Internet
   ↓
Cloudflare Free   ← absorbs L3/L4 DDoS, hides origin IP, rate-limits at edge
   ↓
edge-ingress      ← TLS re-termination, Cloudflare AOP mTLS, geo-routing,
                    global + per-IP connection limits, cert hot-reload
   ↓
envoy             ← per-request WASM filters: rate limit, header /
                    method / size validation, circuit breaker,
                    request validation, traceparent injection
   ↓
gateway           ← JWT auth, CORS, business-level rate limits,
                    trust-aware client-IP resolution, cycle scheduling
```

Each layer addresses a different attack class. Removing any one of them
creates a real exploitation path.

#### Why four layers

| Layer | Protects against | Cannot protect against |
|-------|------------------|------------------------|
| Cloudflare | L3/L4 DDoS, origin IP exposure, known-bad IPs, basic WAF, TLS 1.0 downgrades | Per-user rate limits on encrypted /api endpoints |
| edge-ingress | TLS re-termination behind Cloudflare, per-region routing, global / per-IP connection limits, cert hot-reload, **origin spoofing via AOP mTLS** | Application-level rate limits |
| envoy + WASM | Per-request rate limits, header injection, path traversal, oversized payloads, malformed methods, circuit breaker on backend failures | JWT validation (envoy does not know the secret) |
| gateway | JWT validation, CORS, business-level rate limits, role-based authorisation, trust-aware client-IP for per-IP / per-user limits | Network-layer attacks |

#### Trust chain for client-IP

This is the single most important correctness property of the chain. If it
is wrong, per-IP rate limits collapse silently and login brute-force becomes
trivial.

The gateway's `auth.ClientIPResolver` (src/auth/clientip.go) is the only
component that resolves the real client IP. It accepts a list of trusted
proxy CIDRs (`AUTH_TRUSTED_PROXY_CIDRS`) plus an optional Cloudflare flag
(`AUTH_TRUST_CLOUDFLARE`).

##### Decision tree

```text
immediate peer (r.RemoteAddr) in trusted set?
  no  → ignore all forwarding headers, return peer.
  yes → prefer CF-Connecting-IP (set by Cloudflare; not
         user-controllable through Cloudflare's edge),
         else right-most non-trusted entry of X-Forwarded-For,
         else X-Real-IP,
         else fall back to peer.
```

##### Required env values

| Environment | AUTH_TRUSTED_PROXY_CIDRS | AUTH_TRUST_CLOUDFLARE |
|-------------|--------------------------|------------------------|
| local | `172.28.0.0/16` (the docker-compose subnet) | `false` |
| staging | `10.42.0.0/16` | `false` |
| production | `10.100.0.0/16` | `true` |

Local dev sets the trusted CIDR to the docker-compose `etradie-network`
subnet so the trust-aware code path is exercised on every developer
workstation. There is no "empty trust" shape anywhere.

If `AUTH_TRUST_CLOUDFLARE=true`, the resolver additionally trusts the
Cloudflare-published IPv4 + IPv6 ranges shipped under
`deployments/cloudflare/ip-ranges/`. Refresh those weekly via
`deployments/cloudflare/scripts/refresh-cloudflare-ips.sh` (CI handles this).

##### Spoofing scenarios this defeats

- **Direct origin hit** - attacker discovers origin IP, hits
  `edge-ingress:443` directly, sets `X-Forwarded-For: 1.2.3.4`. AOP mTLS
  fails the TLS handshake before any HTTP byte is read. Even if AOP is
  bypassed somehow, the gateway sees the immediate peer outside the trusted
  set and ignores XFF entirely.
- **Cloudflare-bypass with valid TLS** - same as above but somehow with a
  valid Cloudflare AOP cert (would require Cloudflare CA compromise).
  Gateway still applies trust-chain logic and rejects spoofing because the
  immediate peer is the attacker, not Cloudflare.
- **Header injection from a user behind Cloudflare** - attacker sets
  `CF-Connecting-IP: 4.3.2.1` from their browser. Cloudflare strips and
  rewrites this header before forwarding. Edge-ingress sees Cloudflare's
  injected `CF-Connecting-IP` (the real attacker IP). Gateway honours that.
  Spoof attempt is invisibly rewritten to truth.

#### Health-check chain

A sick downstream must propagate up the chain so traffic is shed before it
arrives at a service that will 503.

```text
Cloudflare    → health-checks edge-ingress 9902/healthz (default off on
                Free; relies on edge-ingress LB health)
edge-ingress  → health-checks envoy via TCP probe to envoy:8080
envoy         → active HTTP probe to gateway /readiness
gateway       → /readiness probes Redis + Python engine
```

This means: when the engine is sick, gateway /readiness returns 503,
envoy ejects the gateway endpoint, edge-ingress sees envoy report unready,
Cloudflare sees edge-ingress unready (in production with Cloudflare
Load Balancing). Traffic is shed before it reaches a 5xx.

Critical: envoy probes `/readiness` not `/health`. `/health` is a static 200
that says nothing about downstream state. This was fixed in commits
`7ad8697b` (source configs) and `809a0d74` (k8s configmap).

#### Local development

Fast inner loop (no edge):

```bash
docker compose up
# gateway is reachable on http://localhost:8080
```

Full chain locally (with mTLS enforced):

```bash
# One-time: set MAXMIND_LICENSE_KEY in .env (free key from MaxMind).
echo "MAXMIND_LICENSE_KEY=<your-key>" >> .env

# Brings up the entire chain. Generates a self-signed dev AOP CA + a
# client cert if they do not already exist (idempotent), then starts
# the docker-compose `edge` profile. mTLS is enforced in dev exactly
# as in production.
make edge-up
```

After the chain is up:

```bash
# Direct gateway (bypasses edge - dev only)
curl -fsS http://localhost:8080/health

# Through envoy (bypasses edge-ingress)
curl -fsS http://localhost:18080/livez

# Unauthenticated request through the full chain MUST fail at TLS:
curl -k https://localhost:8443/auth/healthz   # → handshake failure

# Authenticated request through the full chain (mTLS):
curl --cacert deployments/edge-ingress/docker/certs/localhost.crt \
     --cert  deployments/cloudflare/origin-pull/dev-client.crt \
     --key   deployments/cloudflare/origin-pull/dev-client.key \
     https://localhost:8443/auth/healthz   # → 200

# CI-friendly assertion of both:
make edge-test
```

The second curl failing locally is the proof that the mTLS code path
is live in dev exactly as in production. There is no `enabled: false`
dev-shortcut anywhere in the codebase.

#### Production validation checklist

After deployment, all of the following must be observable. Any failure means
the chain is broken and traffic should be rolled back to the previous
canary.

- `curl -fsS https://api.exoper.com/auth/healthz` returns 200 via
  Cloudflare.
- Direct origin hit fails at TLS:
  ```bash
  curl -v --resolve api.exoper.com:443:<origin-ip> \
    https://api.exoper.com/auth/healthz
  # Expected: TLS handshake failure (no client cert).
  ```
- Cloudflare dashboard → Analytics → Traffic shows non-zero requests
  hitting the AOP-protected origin.
- Gateway logs show `client_ip_resolution.method=cf_connecting_ip` for
  Cloudflare-originated requests.
- Gateway logs show `client_ip_resolution.method=peer` for any
  not-from-Cloudflare requests (intra-cluster traffic, Kubernetes probes).
- Envoy stats: `cluster.gateway_cluster.upstream_rq_2xx` > 0 and
  `cluster.gateway_cluster.health_check.success` > 0.
- Edge-ingress metrics: `edge_ingress_handshake_total{result="success"}` > 0
  AND `edge_ingress_handshake_total{result="client_cert_required"}` > 0
  (the second from probe traffic that legitimately gets rejected).

#### Rate-limit ladder

| Layer | Scope | Default for trading platform |
|-------|-------|-------------------------------|
| Cloudflare Free | Global per-zone | Off by default (Free tier has 10k req/month rate-limiting budget; useful for /auth/* only) |
| edge-ingress | Per-IP connection cap | 1000 conn/IP, 100k global |
| envoy WASM | Per-IP request rate | 100 req/sec/IP, 10 000 req/sec global |
| gateway (auth) | Per-IP for sensitive ops | 10 logins/min, 5 registrations/min, 20 refreshes/min |
| gateway (business) | Per-user JWT-bound | 10 orders/sec/user (configure per env) |

The ladder is intentionally redundant: an attacker who spoofs an IP at
layer N still hits layer N+1's per-user limit because that one is bound to
the authenticated user, not the IP.

#### Failure-mode table

| Symptom | Most likely layer | Grep |
|---------|-------------------|------|
| Whole API unreachable (TCP refused) | Cloudflare or LB | Cloudflare dashboard → Health |
| TLS handshake fails for everyone | edge-ingress AOP CA mismatch | `kubectl logs -n edge-ingress-system -l app.kubernetes.io/name=edge-ingress \| grep client_auth` |
| All requests 5xx | envoy upstream eject | `kubectl exec ... -- curl localhost:9901/clusters \| grep gateway_cluster` |
| Per-IP rate limit hits the wrong people | gateway trust chain misconfig | `kubectl logs -n etradie-system -l app.kubernetes.io/name=etradie-gateway \| grep client_ip_resolution` |
| /readiness flapping | gateway downstream sick | `kubectl logs ... -l app.kubernetes.io/name=etradie-engine` |
| Specific user blocked | gateway business rate limit | gateway logs filtered by user_id |

#### Rotation procedures

##### Cloudflare AOP CA (rare; ~once/decade)

1. Cloudflare publishes the new chain at the canonical URL.
2. CI's weekly run of `refresh-cloudflare-ips.sh` detects the SHA-256
   change and fails loudly.
3. **Append** the new chain to the Vault secret
   `etradie/services/edge-ingress/cloudflare/aop_ca` (do not replace).
   ExternalSecret picks up the change within `refreshInterval=1h`.
4. Edge-ingress accepts client certs signed by EITHER CA during the
   overlap window (rustls' WebPkiClientVerifier handles multi-cert
   bundles natively).
5. After Cloudflare's announced cutover date passes, drop the old CA
   from the Vault secret.

##### Cloudflare published IP ranges (occasional; ~quarterly)

Weekly CI runs `refresh-cloudflare-ips.sh` and opens a PR if the diff is
non-empty. Merge the PR within 7 days. Failure to do so causes legitimate
Cloudflare edge nodes to be classified as untrusted by the gateway resolver,
which silently downgrades per-IP rate limits to peer-IP limits.

##### TLS leaf certificates (90 days, typical)

Cert-manager (or your equivalent) renews into the
`edge-ingress-tls-certs` Secret. Edge-ingress hot-reloads on
`tls.cert_reload_interval` (default 1h in production). No pod restart
required.

#### Out-of-scope (covered elsewhere)

- Cloudflare zone DNS / CNAME setup: `deployments/cloudflare/README.md`.
- Helm chart specifics: `helm/{gateway,envoy,edge-ingress}/`.
- Service-by-service deployment manifests:
  `deployments/{gateway,envoy,edge-ingress}/kubernetes/`.
- Per-service Dockerfile internals: `deployments/*/docker/`.

#### What does NOT exist anymore

For anyone reviewing older designs or stale tickets, the following
shapes were intentionally removed and **do not exist** anywhere in
the codebase:

- No `client_auth.enabled` field. mTLS is always enforced.
- No `client_auth.mode` field with values `required` / `optional` /
  `none`. There is one mode: required.
- No "soft launch" or "AOP rollout" middle state.
- No empty `AUTH_TRUSTED_PROXY_CIDRS` default. Every environment ships
  the actual subnet.
- No `EDGE_PROFILE_ENABLED` env var. The switch is `make edge-up`.
- No `CLOUDFLARE_AOP_MODE` env var. Replaced by mandatory ca_path.
- No committed AOP CA bytes in git. The CA lives in Vault
  (`etradie/services/edge-ingress/cloudflare/aop_ca`); the dev CA is
  generated on demand and gitignored.
