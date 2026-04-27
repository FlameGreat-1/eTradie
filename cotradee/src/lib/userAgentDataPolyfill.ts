/**
 * Defensive polyfill for `navigator.userAgentData.brands`.
 *
 * Background:
 *   lightweight-charts 4.2.0 calls
 *     navigator.userAgentData.brands.some(...)
 *   inside an internal `isChromiumBased()` probe without guarding
 *   against either `userAgentData` being undefined, `brands` being
 *   a non-array, or the access itself throwing on privacy-hardened
 *   mobile browsers. The crash propagates out of createChart and
 *   tears the dashboard down via React's error boundary.
 *
 *   This function makes a best-effort to ensure that
 *     navigator.userAgentData       is an object, and
 *     navigator.userAgentData.brands is an array,
 *   so the chart library's probe runs without throwing.
 *
 *   Every step is wrapped in try/catch so a hostile environment can
 *   never bring the polyfill itself down. As a last resort, if we
 *   cannot patch `navigator` at all (some iOS WebViews mark the
 *   property non-configurable AND non-writable), the chart still has
 *   a try/catch around createChart and degrades gracefully.
 */
export function installUserAgentDataPolyfill(): void {
  try {
    if (typeof navigator === 'undefined') return;

    const nav = navigator as Navigator & {
      userAgentData?: { brands?: unknown };
    };

    let current: { brands?: unknown } | undefined;
    try {
      current = nav.userAgentData;
    } catch {
      // Some hardened browsers throw on read.
      current = undefined;
    }

    let needsBrandsPatch = false;
    if (current) {
      try {
        needsBrandsPatch = !Array.isArray(current.brands);
      } catch {
        needsBrandsPatch = true;
      }
    }

    // Case 1: the field is missing entirely. Try multiple strategies
    // because mobile WebViews differ in what they allow.
    if (!current) {
      if (tryDefineProperty(nav, 'userAgentData', { brands: [] })) return;
      if (tryDeleteThenAssign(nav, 'userAgentData', { brands: [] })) return;
      if (tryPlainAssign(nav, 'userAgentData', { brands: [] })) return;
      return;
    }

    // Case 2: the field exists but `brands` is missing or not an array.
    if (needsBrandsPatch) {
      if (tryDefineProperty(current as Record<string, unknown>, 'brands', [])) return;
      if (tryDeleteThenAssign(current as Record<string, unknown>, 'brands', [])) return;
      if (tryPlainAssign(current as Record<string, unknown>, 'brands', [])) return;
    }
  } catch {
    /* never let the polyfill itself crash the app */
  }
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
