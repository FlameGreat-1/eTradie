# cotradee — eTradie trading dashboard (SPA)

React + TypeScript + Vite single-page app. Deployed to **Vercel**.

## Build & deploy

Vercel runs `npm run build`. The `prebuild` hook regenerates
`vercel.json` from the generator so the deployed response-header policy
is always in lock-step with the source:

```bash
npm install
npm run build      # prebuild -> generate:headers, then tsc -b && vite build
```

`npm run lint` includes `lint:headers`, a drift gate that fails if the
committed `vercel.json` does not match `scripts/generate-vercel-headers.mjs`.

## Security headers (TIER 5)

The browser renders the SPA's `index.html` from Vercel, so the
page-level security headers live in **`vercel.json`** (the only place
that governs the document the browser actually loads). They are:

| Header | Value |
|--------|-------|
| `Content-Security-Policy` | `script-src 'self'` (no inline script, no hash), Google Fonts allowed for style/font, `connect-src` derived from the build's `VITE_*` backend origins, `frame-ancestors 'none'`, `object-src 'none'`, `upgrade-insecure-requests` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | all sensitive features denied |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |

The `navigator.userAgentData` polyfill that must run before any ES
module (for lightweight-charts) is the external classic script
`public/uad-polyfill.js`, loaded synchronously in `<head>` before the
module script. Keeping it external (not inline) is what lets the CSP be
`script-src 'self'` with no hash.

> The API origin (`api.*`) sets its OWN, stricter headers at Envoy
> (`helm/envoy` `securityHeaders`). These `vercel.json` headers protect
> the SPA document; the Envoy headers protect the JSON API. Both are
> required — a CSP only governs the response it is attached to.

### `connect-src` is derived from `VITE_*` — nothing extra to set

The browser calls FOUR backends directly (traced from `src/lib/axios.ts`
+ `src/config/env.ts`): the gateway does NOT proxy the engine /
execution / management browser routes, so the SPA reaches each on its
own origin:

| `VITE_*` var | service the browser calls |
|--------------|---------------------------|
| `VITE_GATEWAY_HTTP_URL` | `/auth/*`, `/api/v1/cycle/run`, `/api/v1/symbols*`, `/api/v1/config*`, `/api/v1/health`, billing, `/events/*` |
| `VITE_GATEWAY_WS_URL` | `/ws/notifications` |
| `VITE_ENGINE_URL` | `/api/broker/*`, `/api/analysis/*`, `/api/llm/*`, `/api/usage/me` |
| `VITE_EXECUTION_URL` | `/api/v1/state`, `/api/v1/account`, `/api/v1/orders/cancel`, `/api/v1/settings` |
| `VITE_MANAGEMENT_URL` | management surface |

`generate-vercel-headers.mjs` reads these same five vars from
`process.env` and emits a `connect-src` containing exactly those origins
(each `http(s)` origin also contributes its `ws(s)` companion). Because
`prebuild` runs in the SAME environment Vite builds in, the CSP can
never disagree with what the bundle actually connects to.

**Operator action: none beyond the normal `VITE_*` Vercel project env
vars.** Set `VITE_GATEWAY_HTTP_URL`, `VITE_GATEWAY_WS_URL`,
`VITE_ENGINE_URL`, `VITE_EXECUTION_URL`, `VITE_MANAGEMENT_URL` for the
environment (as you must anyway for the app to function), and the build
bakes the matching `connect-src`. The committed `vercel.json` uses the
`.env.example` localhost origins as the in-repo baseline.

## Environment variables

See `.env.example`. Only `VITE_`-prefixed values reach the browser
bundle; never put secrets there.
