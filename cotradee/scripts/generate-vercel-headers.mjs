#!/usr/bin/env node
/* eslint-disable no-console */

/**
 * Generate cotradee/vercel.json from index.html.
 *
 * WHY THIS EXISTS
 * ---------------
 * The SPA is deployed to Vercel. Vercel applies response headers from
 * the `headers` array in vercel.json to the static assets it serves —
 * including the index.html document the browser actually renders. That
 * document is where XSS and clickjacking happen, so the page-level
 * Content-Security-Policy + framing/MIME/referrer headers MUST live
 * here (the API-origin headers set at Envoy protect api.* only; CSP
 * protects the document it is attached to, nothing else).
 *
 * THE INLINE-SCRIPT PROBLEM
 * -------------------------
 * index.html carries ONE inline <script>: the navigator.userAgentData
 * polyfill that MUST run before any ES module is parsed (see
 * cotradee/vite.config.ts and cotradee/src/main.tsx), otherwise
 * lightweight-charts 4.2.x crashes at module-eval on Firefox / Safari /
 * iOS WebViews. It cannot be moved to an external module. Under a
 * strict CSP an inline script is blocked unless allowed by a nonce or a
 * 'sha256-<hash>' source. A nonce cannot be injected into a statically
 * hosted file, so the correct mechanism is the hash — computed here
 * from the EXACT bytes of the inline script so it can never drift.
 *
 * USAGE
 *   node scripts/generate-vercel-headers.mjs           # writes vercel.json
 *   node scripts/generate-vercel-headers.mjs --check    # verify, no write
 *
 * The --check mode is the CI drift gate: it regenerates in memory and
 * exits 1 if the committed vercel.json differs, so a change to the
 * inline script (which changes the hash) without regenerating fails the
 * build LOUDLY instead of silently shipping a CSP that blocks the
 * bootstrap script and crashes the chart.
 *
 * connect-src ORIGINS
 * -------------------
 * The browser calls the gateway (HTTP + WS), and may call the engine /
 * execution / management origins directly via the VITE_* build vars
 * (see cotradee/src/config/env.ts). connect-src is therefore composed
 * from env vars so it matches the VITE_* values of the SAME build, with
 * the production gateway origin as the documented default. Pass extra
 * origins as a space- or comma-separated list in VERCEL_CONNECT_SRC.
 *
 * Zero npm deps, Node ESM — same constraints as
 * scripts/check-consent-consumers.mjs.
 */

import { createHash } from 'node:crypto';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import url from 'node:url';

const __filename = url.fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// scripts/ lives directly under cotradee/, so the SPA root is one up.
const SPA_ROOT = path.resolve(__dirname, '..');
const INDEX_HTML = path.join(SPA_ROOT, 'index.html');
const VERCEL_JSON = path.join(SPA_ROOT, 'vercel.json');

// ---------------------------------------------------------------------------
// connect-src origins
// ---------------------------------------------------------------------------
//
// Default to the production gateway origin (HTTP + WS) that the whole
// edge stack is built around (api.exoper.com). Operators / CI override
// per environment via VERCEL_CONNECT_SRC so the policy tracks the
// VITE_* build vars exactly. 'self' is always included by the CSP
// builder below; do NOT repeat it here.
const DEFAULT_CONNECT_SRC = [
  'https://api.exoper.com',
  'wss://api.exoper.com',
];

function parseConnectSrc(raw) {
  if (!raw || !raw.trim()) return DEFAULT_CONNECT_SRC;
  // Accept space- or comma-separated origins.
  const parts = raw
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return parts.length > 0 ? parts : DEFAULT_CONNECT_SRC;
}

// ---------------------------------------------------------------------------
// Inline-script extraction + hashing
// ---------------------------------------------------------------------------

/**
 * Extract the body of the FIRST inline <script> (no src=, no
 * type=module) from index.html. The CSP hash is computed over the
 * exact characters between the opening <script ...> tag and the
 * closing </script>, with NO trimming — the browser hashes the
 * literal text node, so any change here changes the hash.
 */
function extractInlineScript(html) {
  // Match <script> ... </script> where the opening tag has no `src`
  // attribute and no `type="module"`. The polyfill is the only such
  // script in index.html.
  const re = /<script(?![^>]*\bsrc=)(?![^>]*type=["']module["'])[^>]*>([\s\S]*?)<\/script>/i;
  const m = html.match(re);
  if (!m) {
    throw new Error(
      'generate-vercel-headers: could not find the inline bootstrap <script> in index.html. ' +
        'If the polyfill script was moved or removed, update this generator and the CSP design.',
    );
  }
  return m[1];
}

function sha256Base64(text) {
  return createHash('sha256').update(text, 'utf8').digest('base64');
}

// ---------------------------------------------------------------------------
// CSP + header assembly
// ---------------------------------------------------------------------------

function buildCsp(scriptHashB64, connectSrc) {
  const connect = ["'self'", ...connectSrc].join(' ');
  // Ordered, explicit directives. No 'unsafe-inline' for scripts (the
  // single inline script is allowed by its hash). style-src allows
  // 'unsafe-inline' because Vite/Tailwind inject inline <style> and
  // style injection is not script execution; font/style from Google
  // Fonts; img from self + data: URIs (local SVG/PNG icons).
  return [
    "default-src 'self'",
    `script-src 'self' 'sha256-${scriptHashB64}'`,
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
  // Headers apply to every route the SPA serves. Vercel evaluates
  // `headers` against the request path; `/(.*)` matches all.
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
  // 2-space indent + trailing newline so the committed file is stable
  // and diff-friendly, matching Prettier defaults used across the repo.
  return JSON.stringify(config, null, 2) + '\n';
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

async function main() {
  const checkOnly = process.argv.includes('--check');

  const html = await fs.readFile(INDEX_HTML, 'utf8');
  const inlineScript = extractInlineScript(html);
  const hash = sha256Base64(inlineScript);
  const connectSrc = parseConnectSrc(process.env.VERCEL_CONNECT_SRC);
  const csp = buildCsp(hash, connectSrc);
  const expected = serialize(buildVercelConfig(csp));

  if (checkOnly) {
    let actual;
    try {
      actual = await fs.readFile(VERCEL_JSON, 'utf8');
    } catch {
      console.error(
        '[vercel-headers] FAIL: cotradee/vercel.json is missing. ' +
          'Run: node scripts/generate-vercel-headers.mjs and commit the result.',
      );
      process.exit(1);
    }
    if (actual !== expected) {
      console.error(
        '[vercel-headers] FAIL: cotradee/vercel.json is out of sync with index.html.\n' +
          '  The inline bootstrap <script> changed (so its CSP sha256 changed) or the\n' +
          '  header policy/connect-src drifted. Regenerate and commit:\n' +
          '    node scripts/generate-vercel-headers.mjs\n' +
          `  Expected script hash: sha256-${hash}`,
      );
      process.exit(1);
    }
    console.log('[vercel-headers] ok: vercel.json matches index.html (script hash sha256-' + hash + ').');
    return;
  }

  await fs.writeFile(VERCEL_JSON, expected, 'utf8');
  console.log('[vercel-headers] wrote cotradee/vercel.json (inline-script hash sha256-' + hash + ').');
}

main().catch((err) => {
  console.error('[vercel-headers] script failed:', err.message);
  process.exit(1);
});
