## Edge Layer (edge-ingress + envoy) — Cookie and CSRF Header Pass-Through

**Verified: 2026-05-11 as part of the cookies+CSRF hardening audit.**

### edge-ingress (Rust, `src/edge-ingress/`)

`src/edge-ingress/crates/edge-server/src/handler.rs::proxy_traffic` uses
`tokio::io::copy_bidirectional` — it is a **raw TCP tunnel**. After TLS
termination, it pipes raw bytes bidirectionally between the client and the
upstream (envoy). It does not parse HTTP at all. `Cookie:`, `Set-Cookie:`,
`X-CSRF-Token`, `X-Internal-Auth`, `Authorization` — all pass through
untouched. No header stripping or injection occurs at this layer.

### envoy (WASM filter, `src/envoy/`)

`src/envoy/config/envoy.yaml` routes all traffic to `gateway_cluster` with
no `request_headers_to_add`, `request_headers_to_remove`,
`response_headers_to_add`, or `response_headers_to_remove` directives.

The WASM integration filter (`src/envoy/crates/integration-filter/`) only
reads `x-trace-id`, `x-request-id`, `traceparent`, and `x-forwarded-for`
for observability purposes. It does not modify, strip, or block any other
header.

**Result:** Both edge layers are transparent pass-throughs for:
- `Cookie:` request header (browser sends access_token + csrf_token)
- `Set-Cookie:` response header (gateway sets all three auth cookies)
- `X-CSRF-Token:` request header (SPA echoes the CSRF cookie)
- `X-Internal-Auth:` request header (gateway-to-engine shared secret)
- `Authorization:` request header (Bearer token for non-browser clients)

No code changes are required in either layer.
