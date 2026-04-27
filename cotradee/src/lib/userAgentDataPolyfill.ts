/**
 * Defensive polyfill for `navigator.userAgentData.brands`.
 *
 * Background:
 *   lightweight-charts 4.2.0 calls `navigator.userAgentData.brands.some(...)`
 *   inside an internal `isChromiumBased()` probe without guarding
 *   against either `userAgentData` being undefined (Firefox / Safari)
 *   or `brands` being a non-array (older Chromium / non-secure context
 *   / partial UA-Client-Hints implementations). The result is a
 *   `Cannot read properties of undefined (reading 'some')` crash that
 *   takes down the entire dashboard via React's error boundary.
 *
 * Strategy:
 *   At module load (called from main.tsx before any chart code runs)
 *   ensure that:
 *     • `navigator.userAgentData`         exists as an object
 *     • `navigator.userAgentData.brands`  exists as an array
 *   We never overwrite a value that's already correct, so browsers
 *   that expose a real implementation are unaffected.
 */
export function installUserAgentDataPolyfill(): void {
  if (typeof navigator === 'undefined') return;

  const nav = navigator as Navigator & {
    userAgentData?: { brands?: unknown };
  };

  if (!nav.userAgentData) {
    try {
      Object.defineProperty(nav, 'userAgentData', {
        configurable: true,
        value: { brands: [] },
      });
    } catch {
      /* property may be non-configurable on some platforms */
    }
    return;
  }

  if (!Array.isArray(nav.userAgentData.brands)) {
    try {
      Object.defineProperty(nav.userAgentData, 'brands', {
        configurable: true,
        value: [],
      });
    } catch {
      /* leave it alone if we can't patch */
    }
  }
}
