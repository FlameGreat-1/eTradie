#!/usr/bin/env node
/* eslint-disable no-console */

/**
 * Generate cotradee/vercel.json (the SPA's response-header policy).
 *
 * WHY THIS EXISTS
 * ---------------
 * The SPA is deployed to Vercel. Vercel applies the headers in
 * vercel.json's `headers` array to the static assets it serves —
 * including the index.html document the browser renders. That document
 * is where XSS and clickjacking happen, so the page-level
 * Content-Security-Policy + framing/MIME/referrer/permissions headers
 * MUST live here. (The API-origin headers set at Envoy protect api.*
 * only; a CSP protects the document it is attached to, nothing else.)
 *
 * NO INLINE SCRIPT, NO HASH
 * -------------------------
 * index.html carries no inline <script>: the navigator.userAgentData
 * polyfill is an external classic script (public/uad-polyfill.js) that
 * still runs before any ES module. So the CSP is `script-src 'self'`
 * with no 'sha256-' hash and no 'unsafe-inline' — nothing to drift.
 *
 * connect-src IS DERIVED FROM THE BUILD'S SINGLE API ORIGIN
 * --------------------------------------------------------
 * Single public entry point (Option B). lib/axios.ts now builds ONE
 * axios client against VITE_API_URL (src/config/env.ts), and the
 * gateway reverse-proxies the dashboard's engine/execution/management
 * calls to the internal services by path prefix. The browser therefore
 * connects to exactly ONE HTTP origin and ONE WebSocket origin:
 *
 *   VITE_API_URL     gateway HTTP origin: /auth/*, /api/v1/*,
 *                    /api/analysis|broker|llm|usage|processor/* (proxied
 *                    to engine), /api/execution/* (proxied to execution),
 *                    /api/management/* (proxied to management), billing,
 *                    /events/*
 *   VITE_API_WS_URL  gateway WS origin: /ws/notifications and the
 *                    proxied engine streams /api/broker/stream-ticks,
 *                    /api/broker/stream-positions
 *
 * connect-src is therefore DERIVED from exactly these two vars so it
 * always matches what the bundle calls. The generator reads the SAME
 * process.env Vite reads at build time, so prebuild bakes the
 * production origin (https://api.exoper.com + wss://api.exoper.com) in
 * on every Vercel deploy.
 *
 * USAGE
 *   node scripts/generate-vercel-headers.mjs           # writes vercel.json
 *   node scripts/generate-vercel-headers.mjs --check    # verify, no write
 *
 * --check is the CI drift gate (npm run lint:headers). It compares
 * against the SAME VITE_* env it sees, so CI runs it with the env that
 * produced the committed file (the repo baseline uses the .env.example
 * localhost origins). The authoritative production file is produced by
 * prebuild on Vercel with the project's env vars.
 *
 * Zero npm deps, Node ESM — same constraints as
 * scripts/check-consent-consumers.mjs.
 */

import { promises as fs } from 'node:fs';
import path from 'node:path';
import url from 'node:url';

const __filename = url.fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// scripts/ lives directly under cotradee/, so the SPA root is one up.
const SPA_ROOT = path.resolve(__dirname, '..');
const VERCEL_JSON = path.join(SPA_ROOT, 'vercel.json');

// The single API-origin vars the SPA's axios/WS clients use. These are
// the SINGLE source of truth for what the browser connects to;
// connect-src is derived from them. Mirrors src/config/env.ts exactly.
// Defaults match cotradee/.env.example so a bare repo checkout produces
// a deterministic baseline vercel.json. Production overrides these via
// the Vercel project env (VITE_API_URL=https://api.exoper.com,
// VITE_API_WS_URL=wss://api.exoper.com) and prebuild bakes them in.
const VITE_ORIGIN_VARS = {
  VITE_API_URL: 'http://localhost:8080',
  VITE_API_WS_URL: 'ws://localhost:8080',
};

// ---------------------------------------------------------------------------
// connect-src derivation
// ---------------------------------------------------------------------------

/**
 * Collapse a full URL to its CSP source origin: scheme://host[:port],
 * no path/query/fragment. Returns null for an unparseable/empty value.
 */
function toOrigin(raw) {
  if (!raw || !raw.trim()) return null;
  let u;
  try {
    u = new URL(raw.trim());
  } catch {
    return null;
  }
  // u.origin is scheme://host[:port] for http/https/ws/wss.
  if (u.origin && u.origin !== 'null') return u.origin;
  return null;
}

/**
 * For an http(s) origin, return its ws(s) companion (same host), because
 * the WS client connects to the same host over ws/wss. For a ws(s)
 * origin, return its http(s) companion for symmetry. Returns null when
 * no mapping applies.
 */
function companionOrigin(origin) {
  if (origin.startsWith('https://')) return 'wss://' + origin.slice('https://'.length);
  if (origin.startsWith('http://')) return 'ws://' + origin.slice('http://'.length);
  if (origin.startsWith('wss://')) return 'https://' + origin.slice('wss://'.length);
  if (origin.startsWith('ws://')) return 'http://' + origin.slice('ws://'.length);
  return null;
}

/**
 * Build the de-duplicated, sorted connect-src origin list from the
 * two VITE_* API-origin vars (VITE_API_URL/VITE_API_WS_URL; env
 * override -> .env.example default). Each origin also contributes its
 * ws(s)/http(s) companion so the single host is allowed for both XHR
 * and WebSocket. 'self' is added by the CSP builder, never here.
 */
function deriveConnectSrc(envLookup) {
  const set = new Set();
  for (const [name, fallback] of Object.entries(VITE_ORIGIN_VARS)) {
    const origin = toOrigin(envLookup(name) || fallback);
    if (!origin) continue;
    set.add(origin);
    const companion = companionOrigin(origin);
    if (companion) set.add(companion);
  }
  return [...set].sort();
}

// ---------------------------------------------------------------------------
// CSP + header assembly
// ---------------------------------------------------------------------------

function buildCsp(connectSrc) {
  const connect = ["'self'", ...connectSrc].join(' ');
  // No 'unsafe-inline' for scripts: index.html has no inline script
  // (the polyfill is /uad-polyfill.js, covered by 'self'). style-src
  // allows 'unsafe-inline' because Vite/Tailwind inject inline <style>
  // and style injection is not script execution; font/style from
  // Google Fonts; img from self + data: URIs (local SVG/PNG icons).
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    `connect-src ${connect}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    'upgrade-insecure-requests',
  ].join('; ');
}

function buildVercelConfig(csp) {
  return {
    $schema: 'https://openapi.vercel.sh/vercel.json',
    headers: [
      {
        source: '/(.*)',
        headers: [
          { key: 'Content-Security-Policy', value: csp },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          {
            key: 'Permissions-Policy',
            value: 'accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains',
          },
        ],
      },
    ],
  };
}

function serialize(config) {
  // 2-space indent + trailing newline: stable, diff-friendly, Prettier-
  // compatible so the committed file is byte-reproducible.
  return JSON.stringify(config, null, 2) + '\n';
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

async function main() {
  const checkOnly = process.argv.includes('--check');

  const connectSrc = deriveConnectSrc((name) => process.env[name]);
  const csp = buildCsp(connectSrc);
  const expected = serialize(buildVercelConfig(csp));

  if (checkOnly) {
    let actual;
    try {
      actual = await fs.readFile(VERCEL_JSON, 'utf8');
    } catch {
      console.error(
        '[vercel-headers] FAIL: cotradee/vercel.json is missing. ' +
          'Run: npm run generate:headers and commit the result.',
      );
      process.exit(1);
    }
    if (actual !== expected) {
      console.error(
        '[vercel-headers] FAIL: cotradee/vercel.json is out of sync with the generator.\n' +
          '  Either the header policy changed or the VITE_* origins differ from the\n' +
          '  committed baseline. Regenerate with the intended env and commit:\n' +
          '    npm run generate:headers\n' +
          `  Derived connect-src: ${connectSrc.join(' ') || '(none)'}`,
      );
      process.exit(1);
    }
    console.log('[vercel-headers] ok: vercel.json matches the generator.');
    return;
  }

  await fs.writeFile(VERCEL_JSON, expected, 'utf8');
  console.log(
    '[vercel-headers] wrote cotradee/vercel.json (connect-src: ' +
      (connectSrc.join(' ') || '(none)') + ').',
  );
}

main().catch((err) => {
  console.error('[vercel-headers] script failed:', err.message);
  process.exit(1);
});
