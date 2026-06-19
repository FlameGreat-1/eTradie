# WebSocket `/ws/notifications` investigation — handover

**Status:** in progress, NOT resolved.
**Last updated:** 2026-06-19.
**Affected environment:** staging (`staging-api.exoper.com`). Production not yet exercised because production rolls on RELEASE_TAG bumps, not main merges.

## TL;DR for the next operator

WebSocket upgrades to `wss://staging-api.exoper.com/ws/notifications` (and to `/api/broker/stream-ticks`, `/api/broker/stream-positions`) **do not complete the 101 Switching Protocols handshake**. The SPA at `https://app.exoper.com` shows `WebSocket connection failed` in the console and the dashboard notifications panel never attaches.

Four merged fixes targeting envoy v1.28 and the gateway upgrader did NOT fully resolve it. The current failure mode is **gorilla `CheckOrigin` returning false on the gateway** even though the env var is correctly set. Final diagnostic step (curl the gateway directly from inside the cluster with the same Origin header) was hanging when this document was written, so the bisect between "envoy mangles the Origin header" vs "gateway allowlist genuinely doesn't contain the origin" is incomplete.

Do NOT commit another speculative envoy fix. Read this document, then run the verification block in [Step 6](#step-6-the-decisive-test-still-to-run) before changing anything.

---

## Reproduce the failure

From the operator workstation, after logging into the SPA so the access token cookie exists, OR by minting one with the admin credentials:

```bash
# Mint a fresh token (the body returns no access_token because
# AUTH_RETURN_TOKENS_IN_BODY=false in staging; read it from the cookie
# jar instead).
curl -sS -c /tmp/cookies.txt -X POST \
  -H 'Content-Type: application/json' \
  --data '{"username":"admin","password":"<ADMIN_PASSWORD>"}' \
  https://staging-api.exoper.com/auth/login >/dev/null
ACCESS_TOKEN=$(awk '/__Secure-access_token/{print $7}' /tmp/cookies.txt)
echo "ACCESS_TOKEN length: ${#ACCESS_TOKEN}"   # expect a long JWT (>300 chars)

# Reproduce.
WS_KEY=$(openssl rand -base64 16)
curl -i -N --http1.1 --max-time 8 \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: ${WS_KEY}" \
  -H "Origin: https://app.exoper.com" \
  -H "Cookie: __Secure-access_token=${ACCESS_TOKEN}" \
  "https://staging-api.exoper.com/ws/notifications"
```

**Current observed result** (as of the last test before this document was written):

```
HTTP/1.1 403 Forbidden
Content-Length: 10
Sec-Websocket-Version: 13
Upgrade: websocket
Access-Control-Allow-Origin: https://app.exoper.com
Access-Control-Allow-Credentials: true

Forbidden
```

This response shape (plain-text body `Forbidden` + `Sec-Websocket-Version: 13` + CORS headers) is the gorilla/websocket upgrader's default `CheckOrigin` rejection. The corresponding gateway log line:

```
{"level":"error","service":"alert","component":"ws_handler",
 "error":"websocket: request origin not allowed by Upgrader.CheckOrigin",
 "remote":"10.42.0.220:57064","event":"ws_upgrade_failed"}
```

## Why this is unexpected

The gateway env var IS set correctly. Confirmed live:

```bash
$ kubectl -n etradie-system exec etradie-gateway-... -c gateway -- \
    sh -c 'echo "$GATEWAY_ALLOWED_ORIGINS"'
https://staging.exoper.com,https://app.exoper.com
```

The HTTP CORS allowlist works correctly. An OPTIONS preflight for the same path with the same Origin header returns:

```
HTTP/2 204
access-control-allow-origin: https://app.exoper.com
access-control-allow-credentials: true
```

So `corsMiddleware` (HTTP CORS) and `newUpgrader` (WS CheckOrigin) — both reading the same `allowedOrigins` map built in [`src/gateway/internal/server/http_server.go`](../../src/gateway/internal/server/http_server.go) — give opposite answers for the same Origin string. That's the contradiction the next operator must resolve.

## What has been tried, in order, and what each change actually did

| # | Commit | Change | Effect |
|---|---|---|---|
| 1 | [`fadaed2a`](https://gitlab.com/exoper2/exoper/-/commit/fadaed2afd58607ff28030bc537c593ff869d5e6) | `src/alert/handler.go`: `CheckOrigin` consults the gateway's `allowedOrigins` map (the same map `corsMiddleware` uses). Wires the map through `WebSocketHandler(hub, allowedOrigins)`. | Made the WS upgrader and the HTTP CORS layer use a single source of truth. Did NOT unblock the SPA — at that point Cloudflare was blocking before reaching the gateway anyway. |
| 2 | [`6ddaeda0`](https://gitlab.com/exoper2/exoper/-/commit/6ddaeda02499a8b84e8059662b1a32e98777999e) | `src/execution/...`: pass `nil` allowlist at the execution-side WS call site (CI build fix). | Build-only fix for !148's signature change. No runtime behavior change for staging. |
| 3 | [Cloudflare dashboard, manual] | Zone-level WebSockets toggle: OFF → ON. | Stopped Cloudflare returning its own 403 lock-down page for WS upgrades. WS requests now traverse Cloudflare → cloudflared → edge-ingress → envoy. |
| 4 | [`!149` — `5ea5e08e`](https://gitlab.com/exoper2/exoper/-/merge_requests/149) | `helm/envoy/templates/configmap.yaml`: add HCM-level + per-route `upgrade_configs: [{upgrade_type: "websocket"}]`. Add `websocketUpgrade.enabled` toggle to `helm/envoy/values.yaml` (default `true`). | Removed envoy's HCM-level 403 upgrade-gate rejection. WS now reaches the WASM filter. Did NOT unblock — request hung 60s with `response_flags: "SI"` and `upstream_host: null`. |
| 5 | [`!150` — `7460753e`](https://gitlab.com/exoper2/exoper/-/merge_requests/150) | `helm/envoy/templates/configmap.yaml`: replace per-route `BufferPerRoute` on `/` with `envoy.config.route.v3.FilterConfig { disabled: true }`. | Was supposed to skip the buffer filter for upgrade requests. In envoy v1.28 it did NOT take effect for upgrades; WS still hung with the identical `SI` / `upstream_host: null` signature. |
| 6 | [`!151` — `67d03130`](https://gitlab.com/exoper2/exoper/-/merge_requests/151) | `helm/envoy/templates/configmap.yaml`: REMOVE the chain-level `envoy.filters.http.buffer` filter entirely. Remove `maxRequestBytesChainCeiling` from values.yaml. | **This finally unblocked envoy.** WS request now reaches the gateway in milliseconds. New failure mode: gateway gorilla upgrader returns 403 with `request origin not allowed by Upgrader.CheckOrigin`. |

The sequence is important: each fix exposed the next layer of the problem. After `!151`, envoy is no longer the failing component. The current failure is at the gateway WS handler.

## What works right now

- Login / register / `/auth/me` / all non-upgrade REST traffic to the gateway works end-to-end via Cloudflare → cloudflared → edge-ingress → envoy → gateway.
- HTTP CORS preflight (`OPTIONS`) correctly admits `https://app.exoper.com` for `/ws/notifications`.
- Envoy access log for the WS attempt now records the request reaching it and being forwarded — no more `SI` / `upstream_host: null`.
- Gateway pod log records each WS attempt with the `websocket: request origin not allowed` error.

## What is broken

- gorilla WS upgrader's `CheckOrigin` callback returns `false` for `https://app.exoper.com`.
- This happens despite:
  - `GATEWAY_ALLOWED_ORIGINS` env var being set correctly in the pod.
  - The same `allowedOrigins` map being used by `corsMiddleware`, which admits the same origin.
  - The exact-match key in the map being `"https://app.exoper.com"` (verified by reading `auth.BuildCORSAllowlist` in [`src/auth/cors.go`](../../src/auth/cors.go) — the map key is `u.Scheme + "://" + u.Host`).

## The single decisive bisect that is still missing

Is the gateway's `r.Header.Get("Origin")` somehow different from the literal `"https://app.exoper.com"` we send? Possibilities to verify in priority order:

1. **envoy/cloudflared/edge-ingress is mangling the Origin header** — adding a port, a path, normalizing case, appending whitespace.
2. **The gateway's allowlist map genuinely doesn't contain `"https://app.exoper.com"`** — maybe a parsing edge case in `envconfig`'s comma-split, leading whitespace, BOM character, etc.
3. **The `allowedOrigins` map in the WS handler closure is a different instance from the one in `corsMiddleware`** — would require a code bug in [`src/gateway/internal/server/http_server.go`](../../src/gateway/internal/server/http_server.go).

### Step 6: the decisive test, still to run

From inside the cluster, bypassing Cloudflare/cloudflared/edge-ingress/envoy entirely:

```bash
kubectl -n etradie-system run wsdebug2 --rm -i --restart=Never \
  --image=nicolaka/netshoot \
  --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":65532,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"wsdebug2","image":"nicolaka/netshoot","stdin":true,"resources":{"requests":{"cpu":"50m","memory":"64Mi"},"limits":{"cpu":"200m","memory":"128Mi"}},"securityContext":{"allowPrivilegeEscalation":false,"runAsNonRoot":true,"runAsUser":65532,"seccompProfile":{"type":"RuntimeDefault"},"capabilities":{"drop":["ALL"]}}}]}}' \
  --command -- sh -c "
    WS_KEY=\$(openssl rand -base64 16)
    curl -sS -i --max-time 5 --http1.1 -N \
      -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
      -H 'Sec-WebSocket-Version: 13' \
      -H \"Sec-WebSocket-Key: \$WS_KEY\" \
      -H 'Origin: https://app.exoper.com' \
      -H 'Host: staging-api.exoper.com' \
      -H 'Cookie: __Secure-access_token=${ACCESS_TOKEN}' \
      http://gateway.etradie-system.svc.cluster.local:8080/ws/notifications
  "
```

**If this returns `101 Switching Protocols`** → envoy or cloudflared is mangling the Origin header in transit. Next step is to add tcpdump or an envoy access log Origin field to capture exactly what the gateway sees.

**If this ALSO returns 403 with the gorilla error** → the gateway's allowlist genuinely doesn't contain `https://app.exoper.com`. Next step is to add a temporary debug log in [`src/alert/handler.go`](../../src/alert/handler.go) `newUpgrader.CheckOrigin` dumping both the received `origin` and the map keys, redeploy gateway, reproduce, capture, then revert the debug commit.

## Tools the cluster does NOT have (avoid these wastes of time)

- The envoy v1.28 official image has no `wget`, `curl`, or `nc`. Use `kubectl port-forward` + workstation curl to query the admin interface, or `cat /proc/net/tcp` for socket state.
- The gateway-go image has no `wget`. `kubectl exec ... sh -c 'echo "$VAR"'` and reading `/proc/<pid>/environ` work.
- PodSecurity admission in `envoy-system` and `etradie-system` namespaces requires the security context block shown in the `overrides` example above. A bare `kubectl run --image=nicolaka/netshoot` will be rejected.
- `envoy-system` resource quota is tight (`limits.cpu=4` total). Spawning a debug pod there can be rejected; spawn in `etradie-system` with `--limits cpu=200m,memory=128Mi`.

## Files involved (read these before changing anything)

| File | Why it matters |
|---|---|
| [`src/alert/handler.go`](../../src/alert/handler.go) | The gorilla upgrader and `CheckOrigin` callback are here. |
| [`src/auth/cors.go`](../../src/auth/cors.go) | `BuildCORSAllowlist`. Map key construction. |
| [`src/gateway/internal/server/http_server.go`](../../src/gateway/internal/server/http_server.go) | Constructs `allowedOrigins` once, hands the same map to `alert.WebSocketHandler` AND `corsMiddleware`. |
| [`src/gateway/internal/config/config.go`](../../src/gateway/internal/config/config.go) | `AllowedOrigins []string \`envconfig:"ALLOWED_ORIGINS"\`` field. |
| [`helm/gateway/values-staging.yaml`](../../helm/gateway/values-staging.yaml) | `config.gateway.allowedOrigins` value (the literal string `"https://staging.exoper.com,https://app.exoper.com"`). |
| [`helm/envoy/templates/configmap.yaml`](../../helm/envoy/templates/configmap.yaml) | The envoy filter chain. After `!151`, the chain-level Buffer is gone; the chain is `wasm → local_ratelimit → router`. |
| [`helm/envoy/values.yaml`](../../helm/envoy/values.yaml) | `config.envoy.websocketUpgrade.enabled` toggle (default `true`). |

## Cloudflare zone state

WebSockets toggle: **ON** (operator flipped manually in the dashboard after the initial diagnosis). This is NOT yet captured in Terraform. The Terraform change to add `websockets = "on"` to `cloudflare_zone_settings_override` was prepared as [`!148`](https://gitlab.com/exoper2/exoper/-/merge_requests/148) and then CLOSED without merging — the operator flipped it via dashboard instead. The dashboard state is the live truth right now; when the WS investigation is fully resolved, the next operator should reopen and merge the Terraform change so the next `terraform apply` does not drift the toggle back off and so production inherits the same default.

## Mesh state at the time of investigation

Linkerd mesh is OFF for the 5 services involved in this path (engine, gateway, execution, management, billing) per [`PHASE10.6-MESH-DISABLED-CHECKPOINT.md`](PHASE10.6-MESH-DISABLED-CHECKPOINT.md). This means envoy → gateway is plain HTTP, not mTLS. Linkerd is not in the failing path for this investigation.

Mesh is ON for: postgres, redis, chromadb, edge-ingress, envoy. The envoy → upstream hop sees a linkerd-proxy sidecar in `envoy-system` (envoy is meshed); the gateway side does not (gateway is not meshed in staging right now).

## Verification matrix after the next fix

When the gateway WS handler problem is resolved:

```bash
# 1. Direct curl from workstation through Cloudflare.
WS_KEY=$(openssl rand -base64 16)
curl -i -N --http1.1 --max-time 5 \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: ${WS_KEY}" \
  -H "Origin: https://app.exoper.com" \
  -H "Cookie: __Secure-access_token=${ACCESS_TOKEN}" \
  "https://staging-api.exoper.com/ws/notifications"
# Expect: HTTP/1.1 101 Switching Protocols + Sec-WebSocket-Accept: <hash>

# 2. Gateway log shows the connection landing.
kubectl -n etradie-system logs -l app.kubernetes.io/name=etradie-gateway -c gateway --since=30s \
  | grep ws_client_connected
# Expect: an entry with subscriber_id, user_id, min_severity

# 3. Envoy access log shows 101 (not 408).
kubectl -n envoy-system logs -l app.kubernetes.io/name=etradie-envoy -c envoy --since=30s \
  | grep '"path":"/ws/notifications"' | tail -3
# Expect: "response_code":101, "upstream_host":"10.42.0.<gateway>:8080"

# 4. Browser at https://app.exoper.com. Hard-refresh (Ctrl-Shift-R).
#    The console "WebSocket connection failed" reconnect loop stops;
#    the notifications panel attaches; /api/broker/stream-ticks and
#    /api/broker/stream-positions WS connections also complete.
```

## Lessons logged for the next operator

- **Do not chase envoy fixes any further.** Envoy is no longer the failing component after `!151`. The next investigation is purely in the gateway WS handler / CheckOrigin path.
- **Verify before committing.** Three of the four envoy fixes (`!149` `!150` `!151`) were committed before being verified end-to-end. Two of them did not actually unblock the symptom. Always run [Step 6](#step-6-the-decisive-test-still-to-run) before opening a fix MR.
- **The mirror IS automatic.** GitLab → GitHub push happens within seconds of a merge. ArgoCD picks up the diff on its 3-minute poll cycle.
- **CI deploy-bump rolls 6 services together** (gateway/engine/execution/management/billing/edge-ingress). During the rollout, the SPA will see transient 502s as envoy's STRICT_DNS resolver briefly points at terminating pods. The 502s clear within 1-2 minutes of the rollout completing.
- **`AUTH_RETURN_TOKENS_IN_BODY=false` in staging** means the `/auth/login` JSON body does NOT contain `access_token`. Read it from the cookie jar (`awk '/__Secure-access_token/{print $7}' /tmp/cookies.txt`).
