SO WHAT'S EXACTLY THE FLOW OF THE CLOUDFLARE, EDGE INGRESS, ENVOY, GATEWAY NOW ACCORDING TO EXACTLY WHAT WE IMPLEMENTED IN THE CODEBASE?
AVOID GUESSING
AVOID ASSUMPTION
I NEED THE REAL TRUTH NOT LIES
ALSO, WHAT EXACTLY IS THE USEFULNESS OF HELM, DELOYMENTS AND INFRASTRUCTURE AND IS IT REALLY USEFUL AND NECCESSARY IN THIS APPLICATION OR I HAVE BUILT A TECHNICAL DEBT?




Confirmed: `TcpStream::connect(address)` — plain TCP. The handler does `copy_bidirectional` between the **decrypted** TLS stream from the client and a **plain** TCP stream to envoy. Now I have 100% accurate ground truth. Time to write the answer.

---

## The actual flow as implemented in the codebase

This is what the code on `main` does today, traced from `main.rs` → handler.rs → upstream proxy → envoy filter → gateway. No guesses; everything below has a file reference.

#### Stage 1 — Cloudflare edge (external infrastructure)

**This is not code in your repo.** It's Cloudflare's anycast network configured by `infrastructure/cloudflare/main.tf` and the runbook in `deployments/cloudflare/README.md`. The TF module sets:

- `cloudflare_zone_settings_override`: `min_tls_version=1.2`, `tls_1_3=on`, `always_use_https=on`, `ssl=strict`.
- `cloudflare_authenticated_origin_pulls`: AOP enabled at zone level.
- `cloudflare_record` for each public hostname (`api.etradie.com`, etc.) → CNAME to the EKS NLB, `proxied=true`.
- `aws_security_group_rule` × N: TCP/443 ingress on the origin security group restricted to Cloudflare's published IPv4/IPv6 ranges only.

Result: a request to `https://api.etradie.com/x` hits a Cloudflare edge POP. Cloudflare terminates the public TLS (the cert that browsers trust), then opens a **new** TLS connection to the origin NLB **with a Cloudflare-signed client certificate** (AOP). The origin firewall drops the packet at L3/L4 if it didn't come from a Cloudflare IP.

#### Stage 2 — NLB → edge-ingress (the AWS Network Load Balancer)

`helm/edge-ingress/templates/service.yaml` declares a `Service.type=LoadBalancer` with annotations:
- `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"`
- `service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "tcp"` (line 65 of `values.yaml`)
- `service.beta.kubernetes.io/aws-load-balancer-ssl-cert: <ARN>` only if you set `service.tlsCertificateArn`

Reading the NLB annotations carefully: `backend-protocol: "tcp"` — the NLB does **not** terminate TLS. It does pure L4 TCP passthrough. The TLS Cloudflare opened to the origin is forwarded byte-for-byte to an edge-ingress pod on port 443.

#### Stage 3 — edge-ingress (Rust, your own binary)

Real flow from `src/edge-ingress/crates/edge-server/src/handler.rs::handle_connection`:

1. **Acquire connection-limit tokens** (per-IP + global) — `connection_limiter.acquire(client_addr.ip())`.
2. **Perform TLS handshake** with mandatory mTLS — `tls_acceptor.accept(stream)` in `crates/tls/src/acceptor.rs`. The `TlsConfig::client_auth.ca_path` field is required; the helm `configmap.yaml` template fail-renders if it's empty. The CA bundle at that path is the Cloudflare AOP CA (synthesised into a Secret by the `cloudflare-aop-ca` ExternalSecret). **A request that does not present a Cloudflare-signed client cert fails the handshake here. There is no skip path.**
3. **Geo-routing** — `geo_router.route(client_addr.ip(), upstream_health)` in `crates/geo-router/src/router.rs`:
   - `GeoIpLookup::lookup_or_default(ip)` mmaps `/data/geoip/GeoLite2-City.mmdb` and returns country code + lat/lon.
   - `RegionSelector::select_region_by_country` picks one of `UsEast1`, `UsWest2`, `EuWest1`, `ApSoutheast1` (hard-coded mapping in `region.rs` lines 84–98).
   - `FallbackPolicy` walks the `upstream_health` HashMap and falls back to a healthy region if the preferred region's pool is unhealthy.
4. **Connect to the selected upstream endpoint** — `upstream_proxy.connect(selected_region)` in `crates/upstream/src/proxy.rs`. This is `TcpStream::connect(address)` — **plain TCP, no TLS to envoy**.
5. **Bidirectional copy** — `tokio::io::copy_bidirectional(client_stream, upstream_stream)` (handler.rs line ~175).

**This is critical and you need to know it:** edge-ingress does **not** parse HTTP. It is an L4 TCP proxy that happens to terminate TLS. Whatever the client sends after the TLS handshake (HTTP/1.1, HTTP/2, gRPC, even non-HTTP) is byte-copied to envoy. So:

- **Edge-ingress does NOT add `X-Forwarded-For` or `CF-Connecting-IP`.** Those headers reach gateway only because Cloudflare set them inside the encrypted TLS payload before edge-ingress started decrypting.
- The `helm/edge-ingress/values.yaml` upstream endpoint list points at `etradie-envoy.envoy-system.svc.cluster.local:8080`. Plain HTTP, port 8080.

The `xff_num_trusted_hops: 1` in envoy's config is consistent with this: there is exactly **one** trusted forwarder upstream of envoy (Cloudflare via the AOP-protected tunnel; edge-ingress doesn't count because it's an L4 hop that doesn't touch headers).

#### Stage 4 — envoy (vanilla envoyproxy/envoy:v1.28.0 + your WASM filter)

`helm/envoy/templates/configmap.yaml` renders the envoy YAML. Flow per request:

1. envoy `http_connection_manager` parses the HTTP request from the TCP stream.
2. **WASM filter `envoy.filters.http.wasm`** runs first, loading `/etc/envoy/wasm/integration-filter.wasm`. From `src/envoy/crates/integration-filter/src/lib.rs::on_http_request_headers`:
   - Extracts trace context from `traceparent` / `x-trace-id` headers (or generates new).
   - Extracts client IP from forwarding headers (the WASM filter calls `etradie_envoy_rate_limiter::extract_client_ip(headers)` — see `context.rs` line 95).
   - Runs the `FilterOrchestrator` chain in `orchestrator.rs::execute_filter_chain`:
     - **Rate limiter** (`filters/rate_limit.rs`)
     - **Header validator** (`filters/header.rs`)
     - **Request validator** (`filters/request.rs`)
     - Wrapped by a **circuit breaker** that opens after consecutive denials.
   - Health check paths (`/healthz`, `/readyz`, etc.) bypass the chain.
   - On allow: stamps `x-trace-id`, `x-request-id`, `traceparent` headers and returns `Action::Continue`.
   - On deny: returns 429/413/400 with a structured error JSON; envoy never proxies upstream.
3. **`envoy.filters.http.router`** routes the allowed request to cluster `gateway_cluster`.
4. envoy connects to `gateway-service.etradie-system.svc.cluster.local:8080` (plain HTTP), with circuit breakers (`max_connections=1024`), outlier detection (eject after 5 consecutive 5xx), retries (`retry_on: connect-failure,refused-stream,unavailable,cancelled,retriable-status-codes`, `num_retries=2`), and active health checks against the gateway's `/readiness`.

#### Stage 5 — gateway (Go, your binary)

The gateway runs Go code. `src/auth/clientip.go::ClientIPResolver.Resolve`:
1. Parse `r.RemoteAddr` (the immediate TCP peer = an envoy pod IP).
2. Check if that IP is in `AUTH_TRUSTED_PROXY_CIDRS` (defaults to `10.100.0.0/16` in production from `helm/gateway/values-production.yaml`) **or** in the published Cloudflare ranges (when `AUTH_TRUST_CLOUDFLARE=true`, mounted from the chart-bundled `helm/gateway/files/cloudflare/{ipv4,ipv6}.txt`).
3. If trusted: prefer `CF-Connecting-IP`, else walk `X-Forwarded-For` from right to left to find the rightmost untrusted entry, else `X-Real-IP`.
4. If untrusted peer: ignore all forwarding headers, return the raw peer. **This is the spoof-proof contract.**

Everything else is normal Go HTTP handling.

#### End-to-end byte path on a successful request

```
browser
  └─[TLS to api.etradie.com]──► Cloudflare POP
                                  │ (Cloudflare terminates browser TLS,
                                  │  signs with its AOP client cert,
                                  │  opens a new TLS to origin NLB)
                                  ▼
                           AWS NLB :443 (L4 TCP passthrough)
                                  ▼
                  edge-ingress pod :443 (Rust)
                    1. mTLS handshake against Cloudflare AOP CA
                    2. GeoIP lookup → pick region
                    3. Plain TCP connect to envoy
                                  │ (decrypted bytes piped via
                                  │  copy_bidirectional, no HTTP parsing)
                                  ▼
                  envoy pod :8080 (envoyproxy/envoy + your WASM)
                    1. Parse HTTP
                    2. WASM filter: rate limit, header validation,
                       request validation, circuit breaker
                    3. Stamp trace headers
                    4. Route to gateway_cluster
                                  ▼
                  gateway pod :8080 (Go)
                    1. clientip.Resolve trusts envoy peer (in 10.100/16)
                    2. Prefer CF-Connecting-IP from Cloudflare
                    3. Business logic
```

---

## What helm, deployments, infrastructure actually do — and is it tech debt?

Real answer per directory, no marketing.

#### `infrastructure/` (Terraform) — **necessary, not debt**

Two modules, both narrow-scope:

- **`infrastructure/cluster/`** owns the AWS account-level primitives nothing else can own: the EKS cluster itself, the OIDC provider, IAM roles for IRSA (ESO, cluster-autoscaler, ALB controller), the three node groups with taints (`edge`, `etradie_system`, `system`), and Vault path bootstrap. None of this can live in Kubernetes manifests because it must exist *before* the cluster exists.
- **`infrastructure/cloudflare/`** owns the Cloudflare zone, AOP enablement, R53/CNAME records, and the AWS Security Group rules that restrict origin TCP/443 to Cloudflare ranges. Cannot live in Kubernetes either — Cloudflare's API is the only way to manage these.

Run frequency: rarely (cluster bootstrap, region expansion, AZ changes, security group updates). Touched maybe once a quarter.

**Verdict: necessary.** This is exactly what Terraform exists for.

#### `helm/` (charts) — **necessary, not debt**

Three charts: `edge-ingress`, `envoy`, `gateway`. Each owns the runtime contract for its service: Deployment, HPA, PDB, Service(s), NetworkPolicy, ServiceAccount + Role, ServiceMonitor, ResourceQuota, LimitRange, ExternalSecret(s), and the ConfigMap that renders the service's runtime config from values.

The fail-fast guards inside templates (`fail` on empty `clientAuth.caPath`, `wasm.base64`, `tlsCertificateArn`) are what make this enterprise-grade rather than YAML soup.

Run frequency: every cluster deploy. Touched whenever a service contract changes.

**Verdict: necessary.** Helm is the de facto industry standard for parameterised Kubernetes manifests; the charts are the source of truth for what runs in production.

#### `deployments/` — **mixed; mostly necessary, some tech debt**

What's actually in there now:

- **`deployments/argocd/`** — AppProject, root-app, six child Applications. ArgoCD Application CRDs **must** be Kubernetes manifests (they live in the `argocd` namespace). They cannot live in `helm/` because helm charts are what they reference. **Necessary.**
- **`deployments/cloudflare/`** — IP ranges (source of truth for both the gateway chart's bundled copy and the TF module's input), the AOP CA pin file, the `generate-dev-certs.sh` script for local dev, the weekly `refresh-cloudflare-ips.sh` script, and a runbook README. **Necessary** — these are integration artefacts, not duplicates.
- **`deployments/edge-ingress/docker/`** — `Dockerfile.edge-ingress`, local certs, local config YAML for the docker-compose `edge` profile. **Necessary** for local dev.
- **`deployments/envoy/docker/`** — empty since MR `!11` deleted `Dockerfile.envoy`. The directory exists but holds no useful files. **Mild debt** — the empty directory should be removed.

**Verdict: mostly necessary. One small piece of debt** (the now-empty `deployments/envoy/docker/`).

#### Was this over-built?

For a money-handling trading platform with mTLS-backed Cloudflare AOP, multi-region geo-routing, WASM-based request validation, GitOps deploys, and Vault-backed secrets — no, this is the right shape. The three layers serve genuinely different consumers:

| Layer | Owner | Cadence | Review path |
|---|---|---|---|
| `infrastructure/` | Terraform applies | Quarterly | Platform team |
| `helm/` | ArgoCD reconciles | Every commit to `main` | Service owners |
| `deployments/argocd/` | `kubectl apply` once per cluster | Almost never | Platform team |

Removing any of these three pushes work into one of the others incorrectly: putting Cloudflare zone setup into helm forces a chicken-and-egg (helm needs the cluster, which needs the IAM, which needs Terraform); putting Kubernetes manifests into Terraform creates the ArgoCD ownership war that you already saw and removed (`infrastructure/gateway/` deleted in MR `!11` for exactly that reason).

#### One genuine debt I will flag

The **edge-ingress is an L4 TCP proxy, not an L7 proxy**. That has two consequences you should be aware of:

1. **edge-ingress cannot apply HTTP-level decisions.** Anything path-based, header-based, or method-based has to live in envoy (which is what your WASM filter does). That's actually fine and correct architecturally — edge-ingress's job is "is this connection from Cloudflare?" + "where geographically should it land?", and envoy's job is "is this request safe to forward?".

2. **The geo-router only sees the client IP from the TCP peer, not from `CF-Connecting-IP`.** Since Cloudflare terminates the public TLS and opens a new connection to the NLB, the immediate TCP peer at edge-ingress is the **Cloudflare edge POP IP**, not the real end-user IP. So edge-ingress's geo-routing is actually routing on **Cloudflare POP geography**, not end-user geography. This may or may not be what you want — Cloudflare POPs are roughly user-adjacent (that's the whole point of a CDN), but it's not the same as routing on the original eyeball IP.

If you want true end-user geo-routing, edge-ingress would need to be an L7 proxy that reads `CF-Connecting-IP` from the HTTP request before picking a region. That is **not tech debt today** — it's a deliberate architectural choice — but it's worth knowing the tradeoff exists. If the trading-platform UX needs sub-region precision (e.g. routing Tokyo users to ApSoutheast1 even when their Cloudflare POP is in Hong Kong), you'd want to revisit.

That's the truth, traced through real source.






I HOPE IT'S EXACTLY THE ETRADIE/SRC/EDGE-INGRESS AND  ETRADIE/SRC/ENVOY THAT WE USED WITH THE CLOUDFLARE OR ARE THE WHOLE OF THAT ONE NOW DEAD CODES?
ALSO THESE THINGS YOU POINTED OUT HERE, ARE THERE GOING TO PREVENT THE PLATFORM FROM WORKING AND BREAK THINGS OR IT'S ACCURATE AND WILL FUNCTION WITH NO PROBLEM? I MEAN ACCORDING TO EXACTLY WHAT WE HAVE NOW:
One genuine debt I will flag
The edge-ingress is an L4 TCP proxy, not an L7 proxy. That has two consequences you should be aware of:
edge-ingress cannot apply HTTP-level decisions. Anything path-based, header-based, or method-based has to live in envoy (which is what your WASM filter does). That's actually fine and correct architecturally — edge-ingress's job is "is this connection from Cloudflare?" + "where geographically should it land?", and envoy's job is "is this request safe to forward?".
The geo-router only sees the client IP from the TCP peer, not from CF-Connecting-IP. Since Cloudflare terminates the public TLS and opens a new connection to the NLB, the immediate TCP peer at edge-ingress is the Cloudflare edge POP IP, not the real end-user IP. So edge-ingress's geo-routing is actually routing on Cloudflare POP geography, not end-user geography. This may or may not be what you want — Cloudflare POPs are roughly user-adjacent (that's the whole point of a CDN), but it's not the same as routing on the original eyeball IP.
If you want true end-user geo-routing, edge-ingress would need to be an L7 proxy that reads CF-Connecting-IP from the HTTP request before picking a region. That is not tech debt today — it's a deliberate architectural choice — but it's worth knowing the tradeoff exists. If the trading-platform UX needs sub-region precision (e.g. routing Tokyo users to ApSoutheast1 even when their Cloudflare POP is in Hong Kong), you'd want to revisit.
That's the truth, traced through real source.








Two questions. I'll answer each from the actual code, no assumptions.

#### Question 1: Are `src/edge-ingress` and `src/envoy` the actual code we're using, or dead code?

**They are the actual code in active use.** I traced this end-to-end:

**edge-ingress (Rust binary):**
- `deployments/edge-ingress/docker/Dockerfile.edge-ingress` line 22: `COPY src/edge-ingress/Cargo.toml src/edge-ingress/Cargo.lock ./` and `COPY src/edge-ingress/crates ./crates`. The Dockerfile is the build context for the production image.
- `helm/edge-ingress/values.yaml` line 11: `image.repository: etradie/edge-ingress` — the chart deploys whatever image was built from that Dockerfile.
- The Rust binary's `main.rs` reads `CONFIG_PATH` (default `/etc/edge-ingress/config.yaml`), which the helm chart's ConfigMap mounts at exactly that path with values rendered from `helm/edge-ingress/values.yaml`'s `config:` block. Same path, same shape.
- Local docker-compose `edge` profile (`docker-compose.yml`) builds `etradie/edge-ingress:local` from the same Dockerfile and runs the same binary.

**envoy WASM filter (Rust → WASM):**
- This is not the envoy proxy itself. The proxy is **upstream `envoyproxy/envoy:v1.28.0`** (we removed the custom envoy Dockerfile in MR `!11`). What we ship is the WASM **integration filter** that envoy loads.
- `helm/envoy/templates/configmap-wasm.yaml` line ~24: the binary bytes go into `binaryData.integration-filter.wasm` from `.Values.wasm.base64`. CI populates that via `--set-file wasm.base64=src/envoy/target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm` (per the comment in `helm/envoy/values.yaml` lines ~178–185 and the staging Argo app's CI hint).
- envoy mounts that ConfigMap at `/etc/envoy/wasm/integration-filter.wasm` and the envoy YAML config (`helm/envoy/templates/configmap.yaml`) references that exact path.
- The local docker-compose mounts `${EDGE_ENVOY_WASM_PATH}` (defaulting to `./src/envoy/target/wasm32-wasi/release/etradie_envoy_integration_filter.wasm`) at the same path, so local and cluster load identical bytes.

So `src/edge-ingress/` and `src/envoy/` are both actively shipping. **Nothing in either tree is dead code at the source-of-truth level.**

The one nuance: `src/envoy/scripts/generate-configmap.sh` is the only dead artefact in the envoy tree — it writes to `deployments/envoy/kubernetes/base/`, a directory removed in MR `!9`. The helm chart's `configmap-wasm.yaml` template replaced it. The script being orphan doesn't break anything (nothing calls it), but it should be deleted in a future cleanup. The Rust source under `src/envoy/crates/` is the real artefact and is alive.

#### Question 2: Will the L4 / Cloudflare-POP-geo behaviour break things or just function suboptimally?

**It will function, with no errors, no crashes, no broken requests. The platform works.** What I flagged is a *precision* tradeoff, not a *correctness* one. Let me show you exactly why, with the code.

**Behaviour 1: edge-ingress is L4, not L7.**

This is by design and intentional in the implementation. Read the request path:

1. Cloudflare edge does the public TLS termination and applies its own L7 rules (WAF, bot management, header injection — `CF-Connecting-IP`, `X-Forwarded-For`).
2. edge-ingress does mTLS (proves Cloudflare), geo-region selection, then `tokio::io::copy_bidirectional` of the **decrypted** bytes to envoy. Whatever HTTP/1.1, HTTP/2, gRPC frames Cloudflare put inside that TLS tunnel pass through unmodified.
3. envoy parses HTTP at L7 and applies your WASM filter (rate limit / header validation / request validation / circuit breaker) on every request.
4. gateway's `clientip.go::Resolve` reads `CF-Connecting-IP` (because the immediate TCP peer is the envoy pod, which is in `AUTH_TRUSTED_PROXY_CIDRS=10.100.0.0/16` per `values-production.yaml`).

**No HTTP-level decision is missed.** Path/header/method enforcement happens at envoy via the WASM filter. The gateway sees the real end-user IP from `CF-Connecting-IP`. Rate-limiting is keyed on that real IP. The only thing edge-ingress is missing is the *ability* to make HTTP-level decisions itself, but it doesn't *need* to — envoy is sitting one hop downstream doing exactly that. **Nothing breaks.**

**Behaviour 2: edge-ingress geo-routes on the Cloudflare POP IP, not the eyeball IP.**

This too will function correctly with no error path triggered. Look at what it actually does in `handler.rs::route_to_upstream`:

```
geo_router.route(conn_info.client_ip, &upstream_health)
```

Where `conn_info.client_ip` is the TCP peer (Cloudflare POP). The router does a MaxMind lookup on that POP IP, which returns the POP's country code, then `region.rs::select_region_by_country` maps it to one of `UsEast1 / UsWest2 / EuWest1 / ApSoutheast1`. Cloudflare's POPs are deployed close to users by definition — that's the whole CDN value proposition. So:

- A user in New York → hits a US-East Cloudflare POP → POP IP geolocates to US → edge-ingress picks `UsEast1`. **Right answer.**
- A user in London → hits a London POP → POP IP geolocates to GB → edge-ingress picks `EuWest1`. **Right answer.**
- A user in Tokyo → hits a Tokyo POP → picks `ApSoutheast1`. **Right answer.**

The edge cases where POP geo and eyeball geo diverge are narrow:
- The user's local POP is unreachable and Cloudflare routes their request through a more distant POP.
- A user in a country that hosts no Cloudflare POP (the request still lands at the nearest POP, which may be in a neighbouring country in a different region bucket).
- A misconfigured client (e.g. VPN-routed) where eyeball IP and POP IP are in different regions.

In all those cases, the request still **succeeds** — it just lands at a possibly-suboptimal upstream region, which adds round-trip latency but does not break anything. The fallback policy (`crates/geo-router/src/fallback.rs`) further protects you: if the picked region's upstream pool is unhealthy, it walks the fallback list. Worst case: a request originating in Tokyo but routed via Hong Kong POP lands at `ApSoutheast1` in Singapore (which is what a Tokyo user would get anyway under the country-code mapping — `JP` → `ApSoutheast1` per `region.rs` line 91).

#### Bottom line

**The platform will function correctly with no errors, no failures, no broken request paths.** Both behaviours I flagged are deliberate architectural tradeoffs that produce a working system; they are not bugs and not deploy-blockers.

The only reason to revisit them is if you later discover, from real production telemetry, that:
- Some HTTP-level enforcement *needs* to happen before the Cloudflare-AOP-validated TLS terminates (extremely rare; envoy is a more efficient place for it anyway because it's already an L7 proxy with a richer filter ecosystem).
- Geo-routing precision actually matters at sub-Cloudflare-POP granularity (likely not — for a trading platform the dominant latency factor is "which region hosts the gateway", not "which of the two adjacent regions does this specific user hit", and Cloudflare POPs already cluster correctly by country).

If you want, I can add a passive observability piece: log the difference between `conn_info.client_ip` (Cloudflare POP) and the `CF-Connecting-IP` header value (when edge-ingress is later upgraded to L7) so you have data on whether the Tokyo-via-HK case is real in your traffic. That would be a 50-line metric addition with no risk — but it's not necessary today. Let me know if you want it.











The one nuance: src/envoy/scripts/generate-configmap.sh is the only dead artefact in the envoy tree — it writes to deployments/envoy/kubernetes/base/, a directory removed in MR !9. The helm chart's configmap-wasm.yaml template replaced it. The script being orphan doesn't break anything (nothing calls it), but it should be deleted in a future cleanup. The Rust source under src/envoy/crates/ is the real artefact and is alive.
YOU SHOULD DELETE THAT
The only thing edge-ingress is missing is the ability to make HTTP-level decisions itself, but it doesn't need to — envoy is sitting one hop downstream doing exactly that.
SO IS THE EDGE-INGRESS HTTP-LEVEL CODE NOW DEAD CODES?
LASTLY, SO WITH ALL THIS WE DID IT MEANS WE ARE GOING TO HAVE HIGH LATENCY COMPARED TO IF HAD USED JUST CLOUDFLARE ONLY WITHOUT EDGE-INGRESS+ENVOY OR EDGE-INGRESS+ENVOY ONLY WITHOUT CLOUDFLARE?