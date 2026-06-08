// localStorage keys. NOTE: there are deliberately NO access/refresh
// token keys here. Since the cookie-auth migration (Batch 11) the
// access and refresh tokens live in HttpOnly cookies that JavaScript
// cannot read or write; the only JS-readable auth value is the CSRF
// token cookie (read directly in lib/axios.ts, not stored here). Do
// NOT add token keys back — doing so re-opens the XSS token-exfil
// vector the cookie migration closed.
export const STORAGE_KEYS = {
  THEME: 'etradie_theme',
} as const;

export const SIDEBAR_WIDTH = 48;
export const HEADER_HEIGHT = 50;
