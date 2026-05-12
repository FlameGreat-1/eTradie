#!/usr/bin/env node
/* eslint-disable no-console */

/**
 * Static check that every active cookie-consent category has a
 * runtime consumer in the SPA, and that every dormant category has
 * NONE.
 *
 * Run via `npm run lint:consent` or implicitly via `npm run lint`.
 * The script exits 0 on success and 1 on any inconsistency, with a
 * human-readable diagnostic on stderr describing exactly which
 * category is drifting and where to look.
 *
 * Design notes:
 *
 *   - Plain Node, zero npm deps. The build pipeline must stay fast
 *     and the guard must stay debuggable by anyone who can read JS.
 *   - Source-of-truth for the active Category union is read by
 *     regex against the types.ts file rather than via tsc, again to
 *     keep the script standalone. The regex is anchored on the
 *     exact `export type Category = ...;` declaration so a refactor
 *     into a different form will fail the script loudly rather than
 *     silently bypass it.
 *   - Source-of-truth for the dormant set is dormantCategories.ts.
 *     We read it as text and parse the array literal, again to
 *     avoid a tsc step.
 *   - Consumer patterns scanned across cotradee/src (excluding the
 *     consent feature directory so the dormant export itself doesn't
 *     count as a consumer):
 *         useHasConsent('<name>')   useHasConsent("<name>")
 *         <ConsentGate category='<name>'>   ...category="<name>"
 *     Templated forms (variable-keyed) are NOT counted; if a future
 *     consumer wants dynamic keying it must declare its intent
 *     explicitly so this script can be updated to whitelist it.
 */

import { promises as fs } from 'node:fs';
import path from 'node:path';
import url from 'node:url';

const __filename = url.fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// scripts/ lives directly under cotradee/, so the SPA root is one up.
const SPA_ROOT = path.resolve(__dirname, '..');
const SRC_ROOT = path.join(SPA_ROOT, 'src');
const CONSENT_FEATURE_DIR = path.join(SRC_ROOT, 'features', 'consent');
const TYPES_FILE = path.join(CONSENT_FEATURE_DIR, 'types.ts');
const DORMANT_FILE = path.join(CONSENT_FEATURE_DIR, 'dormantCategories.ts');

// ---------------------------------------------------------------------------
// Source-of-truth extraction
// ---------------------------------------------------------------------------

async function readActiveCategories() {
  const src = await fs.readFile(TYPES_FILE, 'utf8');
  // Match: export type Category = 'a' | 'b' | 'c';
  // Tolerant of whitespace and newlines between members. Anchored
  // on the literal `export type Category` so a rename surfaces as
  // a parse failure rather than a silent miss.
  const re = /export\s+type\s+Category\s*=\s*([^;]+);/m;
  const m = src.match(re);
  if (!m) {
    throw new Error(
      `Could not locate 'export type Category = ...;' in ${path.relative(SPA_ROOT, TYPES_FILE)}. ` +
        `Refactor the union into a single declaration and re-run the guard.`,
    );
  }
  const body = m[1];
  // Each member is a quoted string literal; extract them all.
  const members = [...body.matchAll(/'([^']+)'|"([^"]+)"/g)].map((mm) => mm[1] || mm[2]);
  if (members.length === 0) {
    throw new Error(
      `Parsed an empty Category union from ${path.relative(SPA_ROOT, TYPES_FILE)}. ` +
        `Did the union become unparseable? Check for non-string-literal members.`,
    );
  }
  return members;
}

async function readDormantCategories() {
  const src = await fs.readFile(DORMANT_FILE, 'utf8');
  // Match: export const DORMANT_CATEGORIES: readonly Category[] = [ ... ] as const;
  const re = /DORMANT_CATEGORIES\s*:\s*readonly\s+Category\[\]\s*=\s*\[([^\]]*)\]/m;
  const m = src.match(re);
  if (!m) {
    throw new Error(
      `Could not locate DORMANT_CATEGORIES array in ${path.relative(SPA_ROOT, DORMANT_FILE)}.`,
    );
  }
  const body = m[1];
  return [...body.matchAll(/'([^']+)'|"([^"]+)"/g)].map((mm) => mm[1] || mm[2]);
}

// ---------------------------------------------------------------------------
// Consumer scan
// ---------------------------------------------------------------------------

async function walk(dir, out) {
  let entries;
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name.startsWith('.')) continue;
      await walk(full, out);
    } else if (e.isFile() && /\.(ts|tsx)$/.test(e.name)) {
      out.push(full);
    }
  }
  return out;
}

function makeConsumerPatterns(category) {
  // useHasConsent('analytics')  or  useHasConsent("analytics")
  // <ConsentGate category='analytics'>  or  ...category="analytics"
  const esc = category.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [
    new RegExp(`useHasConsent\\(\\s*['"]${esc}['"]\\s*\\)`),
    new RegExp(`category\\s*=\\s*['"]${esc}['"]`),
  ];
}

async function countConsumers(category, files) {
  const patterns = makeConsumerPatterns(category);
  const hits = [];
  for (const f of files) {
    const src = await fs.readFile(f, 'utf8');
    for (const re of patterns) {
      if (re.test(src)) {
        hits.push(path.relative(SPA_ROOT, f));
        break;
      }
    }
  }
  return hits;
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

async function main() {
  const [active, dormant] = await Promise.all([
    readActiveCategories(),
    readDormantCategories(),
  ]);

  // Sanity: every dormant entry must also exist in the active union.
  for (const d of dormant) {
    if (!active.includes(d)) {
      console.error(
        `[consent-guard] FAIL: '${d}' is listed in DORMANT_CATEGORIES but is not a member of the Category union. ` +
          `Either add it to the union or remove it from the dormant list.`,
      );
      process.exit(1);
    }
  }

  // Collect every .ts/.tsx file under src/, EXCLUDING the consent
  // feature directory itself. The dormant exports there must not
  // count as runtime consumers.
  const allFiles = await walk(SRC_ROOT, []);
  const consumerFiles = allFiles.filter((f) => !f.startsWith(CONSENT_FEATURE_DIR + path.sep));

  let failed = false;

  for (const cat of active) {
    const hits = await countConsumers(cat, consumerFiles);
    const isDormant = dormant.includes(cat);

    if (isDormant) {
      if (hits.length > 0) {
        console.error(
          `[consent-guard] FAIL: category '${cat}' is marked DORMANT but has ${hits.length} consumer(s):\n` +
            hits.map((h) => `  - ${h}`).join('\n') +
            `\n  -> Either remove the consumer(s) or promote '${cat}' out of DORMANT_CATEGORIES ` +
            `and update the Cookie Policy to describe the live processing.`,
        );
        failed = true;
      } else {
        console.log(`[consent-guard] ok: '${cat}' is dormant with 0 consumers (expected).`);
      }
      continue;
    }

    if (hits.length === 0) {
      console.error(
        `[consent-guard] FAIL: category '${cat}' is ACTIVE but has zero consumers. ` +
          `Either wire it through (useHasConsent('${cat}') / <ConsentGate category="${cat}">) ` +
          `or add it to DORMANT_CATEGORIES in cotradee/src/features/consent/dormantCategories.ts ` +
          `and update the Cookie Policy text to describe it as not currently in use.`,
      );
      failed = true;
    } else {
      console.log(
        `[consent-guard] ok: '${cat}' is active with ${hits.length} consumer(s): ${hits.join(', ')}`,
      );
    }
  }

  if (failed) {
    process.exit(1);
  }
  console.log('[consent-guard] all category invariants hold.');
}

main().catch((err) => {
  console.error('[consent-guard] script failed:', err.message);
  process.exit(1);
});
