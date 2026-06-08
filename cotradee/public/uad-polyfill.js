// navigator.userAgentData polyfill.
//
// MUST run before any ES module is parsed. lightweight-charts 4.2.x
// calls navigator.userAgentData.brands.some(...) at module top-level
// inside its isChromiumBased() probe. On Firefox, Safari, iOS WebViews
// and many privacy-hardened mobile browsers navigator.userAgentData is
// undefined, so .brands is undefined and the .some() call throws
// synchronously - long before our React error boundary or chart
// try/catch can react.
//
// Loaded from index.html as a CLASSIC (non-module) <script src> in
// <head>. A classic head script executes synchronously during head
// parsing, which is guaranteed to be BEFORE any type="module" script
// (ES modules are always deferred per the HTML spec). This preserves
// the "runs before any module" guarantee the inline version relied on,
// while keeping index.html free of inline scripts so the page CSP can
// be `script-src 'self'` with no hash. The typed reference
// implementation lives at cotradee/src/lib/userAgentDataPolyfill.ts.
//
// ES5-compatible and self-contained so it cannot itself fail in older
// runtimes.
(function () {
  try {
    if (typeof navigator === 'undefined') return;

    function makeStub() {
      return { brands: [], mobile: false, platform: '' };
    }

    function brandsIsArray() {
      try {
        var uad = navigator.userAgentData;
        return !!uad && Object.prototype.toString.call(uad.brands) === '[object Array]';
      } catch (e) {
        return false;
      }
    }

    function tryDefine(target, key, value) {
      try {
        Object.defineProperty(target, key, {
          configurable: true,
          writable: true,
          enumerable: true,
          value: value
        });
        return true;
      } catch (e) {
        return false;
      }
    }

    function tryDeleteThenAssign(target, key, value) {
      try { delete target[key]; } catch (e) { /* ignore */ }
      try { target[key] = value; return true; } catch (e) { return false; }
    }

    function tryAssign(target, key, value) {
      try { target[key] = value; return true; } catch (e) { return false; }
    }

    // Already correct? Nothing to do.
    if (brandsIsArray()) return;

    // Strategy 1: patch the existing userAgentData.brands.
    var current;
    try { current = navigator.userAgentData; } catch (e) { current = undefined; }
    if (current) {
      if (tryDefine(current, 'brands', []) && brandsIsArray()) return;
      if (tryDeleteThenAssign(current, 'brands', []) && brandsIsArray()) return;
      if (tryAssign(current, 'brands', []) && brandsIsArray()) return;
    }

    // Strategy 2: replace userAgentData on the navigator instance.
    var stub = makeStub();
    if (tryDefine(navigator, 'userAgentData', stub) && brandsIsArray()) return;
    if (tryDeleteThenAssign(navigator, 'userAgentData', stub) && brandsIsArray()) return;
    if (tryAssign(navigator, 'userAgentData', stub) && brandsIsArray()) return;

    // Strategy 3: replace userAgentData on Navigator.prototype.
    var proto;
    try { proto = Object.getPrototypeOf(navigator); } catch (e) { proto = null; }
    if (proto) {
      var stub2 = makeStub();
      if (tryDefine(proto, 'userAgentData', stub2) && brandsIsArray()) return;
      if (tryDeleteThenAssign(proto, 'userAgentData', stub2) && brandsIsArray()) return;
      if (tryAssign(proto, 'userAgentData', stub2) && brandsIsArray()) return;
    }
  } catch (e) {
    /* never let the polyfill itself crash the page */
  }
})();
