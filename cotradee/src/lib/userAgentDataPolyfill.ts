/**
 * Defensive polyfill for `navigator.userAgentData.brands`.
 *
 * Background
 * ----------
 * lightweight-charts 4.2.0 calls
 *     navigator.userAgentData.brands.some(...)
 * inside an internal `isChromiumBased()` probe at module-eval time,
 * without guarding against `userAgentData` being undefined or
 * `brands` being a non-array. The crash propagates out of
 * createChart and tears the dashboard down via React's error
 * boundary.
 *
 * Why the previous version was insufficient
 * -----------------------------------------
 * It assumed any of (defineProperty | delete+assign | plain assign)
 * would either succeed or throw. On certain hardened mobile
 * WebViews `navigator.userAgentData` is an accessor returning a
 * fresh object per read, so writes to `brands` silently no-op
 * without raising. The polyfill returned early on a falsely
 * "successful" call and the chart still crashed.
 *
 * Strategy
 * --------
 * For each candidate target / property pair, we perform a write,
 * then *read back* and verify the value is actually an array. Only
 * a verified read-back counts as success.
 *
 * Escalation order:
 *   1. Patch `navigator.userAgentData.brands` directly.
 *   2. Replace `navigator.userAgentData` with a frozen stub on the
 *      navigator instance.
 *   3. Replace `userAgentData` on Navigator.prototype.
 *
 * Every step is individually wrapped in try/catch so a hostile
 * environment can never bring the polyfill itself down.
 * TradingChart.tsx wraps createChart in try/catch as well, so
 * if every strategy fails the chart simply degrades gracefully
 * instead of taking the dashboard with it.
 */

type UADStub = {
  brands: { brand: string; version: string }[];
  mobile: boolean;
  platform: string;
};

function makeStub(): UADStub {
  return Object.freeze({
    brands: Object.freeze([]) as unknown as { brand: string; version: string }[],
    mobile: false,
    platform: '',
  });
}

export function installUserAgentDataPolyfill(): void {
  try {
    if (typeof navigator === 'undefined') return;
    if (isBrandsArray()) return;

    // Strategy 1: patch existing userAgentData.brands.
    if (patchExistingBrands()) return;

    // Strategy 2: replace navigator.userAgentData on the instance.
    if (replaceOnInstance()) return;

    // Strategy 3: replace userAgentData on Navigator.prototype.
    if (replaceOnPrototype()) return;

    // If we reach here, the chart's try/catch will catch the eventual
    // throw and render its "chart unavailable" fallback.
  } catch {
    /* never let the polyfill itself crash the app */
  }
}

function isBrandsArray(): boolean {
  try {
    const nav = navigator as Navigator & {
      userAgentData?: { brands?: unknown };
    };
    return Array.isArray(nav.userAgentData?.brands);
  } catch {
    return false;
  }
}

function patchExistingBrands(): boolean {
  let current: { brands?: unknown } | undefined;
  try {
    current = (navigator as Navigator & { userAgentData?: { brands?: unknown } })
      .userAgentData;
  } catch {
    return false;
  }
  if (!current) return false;

  const target = current as Record<string, unknown>;

  // Try defineProperty first (handles non-writable but configurable
  // properties). Verify by reading back through navigator, NOT the
  // captured `current` reference, because some browsers return a
  // fresh object on each access.
  if (tryDefineProperty(target, 'brands', [])) {
    if (isBrandsArray()) return true;
  }
  if (tryDeleteThenAssign(target, 'brands', [])) {
    if (isBrandsArray()) return true;
  }
  if (tryPlainAssign(target, 'brands', [])) {
    if (isBrandsArray()) return true;
  }
  return false;
}

function replaceOnInstance(): boolean {
  const target = navigator as unknown as Record<string, unknown>;
  const stub = makeStub();

  if (tryDefineProperty(target, 'userAgentData', stub)) {
    if (isBrandsArray()) return true;
  }
  if (tryDeleteThenAssign(target, 'userAgentData', stub)) {
    if (isBrandsArray()) return true;
  }
  if (tryPlainAssign(target, 'userAgentData', stub)) {
    if (isBrandsArray()) return true;
  }
  return false;
}

function replaceOnPrototype(): boolean {
  let proto: object | null;
  try {
    proto = Object.getPrototypeOf(navigator);
  } catch {
    return false;
  }
  if (!proto) return false;

  const target = proto as Record<string, unknown>;
  const stub = makeStub();

  if (tryDefineProperty(target, 'userAgentData', stub)) {
    if (isBrandsArray()) return true;
  }
  if (tryDeleteThenAssign(target, 'userAgentData', stub)) {
    if (isBrandsArray()) return true;
  }
  if (tryPlainAssign(target, 'userAgentData', stub)) {
    if (isBrandsArray()) return true;
  }
  return false;
}

function tryDefineProperty(target: object, key: string, value: unknown): boolean {
  try {
    Object.defineProperty(target, key, {
      configurable: true,
      writable: true,
      enumerable: true,
      value,
    });
    return true;
  } catch {
    return false;
  }
}

function tryDeleteThenAssign(target: object, key: string, value: unknown): boolean {
  try {
    delete (target as Record<string, unknown>)[key];
    (target as Record<string, unknown>)[key] = value;
    return true;
  } catch {
    return false;
  }
}

function tryPlainAssign(target: object, key: string, value: unknown): boolean {
  try {
    (target as Record<string, unknown>)[key] = value;
    return true;
  } catch {
    return false;
  }
}
