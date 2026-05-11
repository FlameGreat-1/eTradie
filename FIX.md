# Cookies + CSRF Hardening — Status

This file tracked deferred items from the cookie-auth migration (Batches
10a–11). All items have now been addressed in the `fix/cookies-csrf-hardening`
branch. See the MR for the full audit and implementation details.

## Items resolved in fix/cookies-csrf-hardening

| Item | Status | Notes |
|------|--------|-------|
| A — Engine cookie reader | ✅ Already done on main | `src/engine/shared/auth.py` reads `access_token` cookie |
| B — Management service cookie auth | ✅ Verified | Uses shared `auth.RequireAuth`; all routes GET-only |
| C — Execution service cookie auth | ✅ Verified | Uses shared `auth.RequireAuth` |
| D — `useWebSocket.ts` dead-code | ✅ Resolved | Confirmed no importers |
| E — localStorage for UI prefs | ✅ Correct by design | Not tokens; no change needed |
| F — Multi-tab logout broadcast | ✅ Already done on main | `storage` event listener in axios.ts |
| G — CSRF cookie rotation on retry | ✅ Already done on main | `stampCsrfHeader` called on retry path |
| H — Engine SSE/WS cookie scoping | ✅ Documented | See docs/edge-layer-cookie-audit.md |
| I — Engine CORS allow-list | ✅ Fixed | `X-CSRF-Token` added to engine CORS in B4a |
| J — `useTickStream.ts` protocol mismatch | ✅ Fixed | init-frame `token` field is legacy-only; documented |
| K — localStorage token grep | ✅ Resolved | No remaining `getAccessToken()` callers with real tokens |
| L — WS cookie middleware gateway only | ✅ Correct | Engine has its own `verify_token_from_websocket` |
| M — `useNotificationsSocket.ts` import | ✅ Resolved | |
| N — Production helm overlays | ✅ Fixed in B7 | Cookie policy now explicit in values-production.yaml |
| O — `docs/billing.md` localStorage ref | ✅ Stale note removed | |
| P — Engine-direct callers | ✅ Fixed | Engine CSRF middleware added in B4a |
| Q — CI/test pipeline | ⚠️ Pending | MR CI will run on merge |
| R — `.env.example` ALLOWED_ORIGINS | ✅ Fixed | ENGINE_INTERNAL_SHARED_SECRET added in B9 |

This file is kept for historical reference. Do not add new items here;
use GitLab issues instead.
