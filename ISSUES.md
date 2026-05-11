# Known Issues — Resolved

All issues identified in the cookies+CSRF audit have been addressed in
the `fix/cookies-csrf-hardening` branch. This file is kept for historical
reference.

## Summary of resolved issues (17 total)

| # | Severity | Issue | Batch |
|---|----------|-------|-------|
| 1 | CRITICAL | Helm production missing cookie cross-subdomain config | B7 |
| 2 | CRITICAL | Engine has zero CSRF enforcement on mutating endpoints | B4 |
| 3 | CRITICAL | Execution service has zero CSRF enforcement | B3 |
| 4 | HIGH | Management service no CSRF middleware | B3 |
| 5 | HIGH | CORS Allow-Headers hardcoded, decoupled from AUTH_CSRF_HEADER | B2/B3/B4 |
| 6 | HIGH | Naive double-submit CSRF (not HMAC-signed) | B1 |
| 7 | HIGH | Refresh-token rotation race across tabs | B6 |
| 8 | HIGH | /auth/logout unreachable if access cookie expired | B2 |
| 9 | HIGH | Login/refresh return tokens in JSON body | B2 |
| 10 | MEDIUM | Engine /internal/* reachable with user cookie | B4/B5 |
| 11 | MEDIUM | .env.example unsafe defaults, no prod-mode guard | B1/B9 |
| 12 | MEDIUM | Engine APP_ENV missing = dev path silently | B4 |
| 13 | MEDIUM | Engine WS init-frame token channel undocumented | B4 |
| 14 | MEDIUM | No __Secure- cookie name prefixes | B1/B6 |
| 15 | MEDIUM | CORS allowlist not validated at startup | B2 |
| 16 | LOW | Edge layer cookie+CSRF forwarding unverified | B8 |
| 17 | LOW | FIX.md and ISSUES.md stale | B9 |

See the MR `fix/cookies-csrf-hardening` for full implementation details.
