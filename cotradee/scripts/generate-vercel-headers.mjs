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
 * connect-src ORIGINS
 * -------------------
 * The browser calls the gateway (HTTP + WS) and may call the engine /
 * execution / management origins directly via the VITE_* build vars
 * (see cotradee/src/config/env.ts). connect-src is composed from
 * VERCEL_CONNECT_SRC so it matches the VITE_* values of the SAME build,
 * with the production gateway origin as the documented default. Pass a
 * space- or comma-separated list; 'self' is always added by the CSP
 * builder and must NOT be repeated.
 *
 * USAGE
 *   node scripts/generate-vercel-headers.mjs           # writes vercel.json
 *   node scripts/generate-vercel-headers.mjs --check    # verify, no write
 *
 * --check is the CI drift gate (npm run lint:headers): it regenerates in
 * memory and exits 1 if the committed vercel.json differs, so a policy /
 * connect-src change without regenerating fails the build loudly.
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

// ---------------------------------------------------------------------------
// connect-src origins
// ---------------------------------------------------------------------------
//
// Default to the production gateway origin (HTTP + WS) the whole edge
// stack is built around (api.exoper.com). Operators / CI override per
// environment via VERCEL_CONNECT_SRC so the policy tracks the VITE_*
// build vars exactly. 'self' is always included by the CSP builder
// below; do NOT repeat it here.
const DEFAULT_CONNECT_SRC = ['https://api.exoper.com', 'wss://api.exoper.com'];

function parseConnectSrc(raw) {
  if (!raw || !raw.trim()) return DEFAULT_CONNECT_SRC;
  const parts = raw
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return parts.length > 0 ? parts : DEFAULT_CONNECT_SRC;
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

  const connectSrc = parseConnectSrc(process.env.VERCEL_CONNECT_SRC);
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
          '  The header policy or connect-src drifted. Regenerate and commit:\n' +
          '    npm run generate:headers',
      );
      process.exit(1);
    }
    console.log('[vercel-headers] ok: vercel.json matches the generator.');
    return;
  }

  await fs.writeFile(VERCEL_JSON, expected, 'utf8');
  console.log('[vercel-headers] wrote cotradee/vercel.json.');
}

main().catch((err) => {
  console.error('[vercel-headers] script failed:', err.message);
  process.exit(1);
});
