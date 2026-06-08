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
| `Content-Security-Policy` | `script-src 'self'` (no inline script, no hash), Google Fonts allowed for style/font, `connect-src` scoped to the API + WS origins, `frame-ancestors 'none'`, `object-src 'none'`, `upgrade-insecure-requests` |
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

### Scoping `connect-src` per environment

`connect-src` defaults to the production gateway origin
(`https://api.exoper.com` + `wss://api.exoper.com`). It MUST list every
origin the browser calls — i.e. the `VITE_*` URLs in
`src/config/env.ts` for that build (gateway HTTP + WS, and engine /
execution / management if the SPA calls them directly). Override at
build time and regenerate:

```bash
VERCEL_CONNECT_SRC="https://api.exoper.com wss://api.exoper.com" \
  npm run generate:headers
```

Set `VERCEL_CONNECT_SRC` as a Vercel Project Environment Variable so the
`prebuild` step bakes the correct origins into `vercel.json` for each
environment (production / preview). If it is unset the production
default above is used.

## Environment variables

See `.env.example`. Only `VITE_`-prefixed values reach the browser
bundle; never put secrets there.
