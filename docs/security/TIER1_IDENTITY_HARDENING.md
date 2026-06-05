# Tier 1 — Identity & Authentication hardening (MFA excluded)

Source-of-truth tracker for the staged Tier 1 work. MFA (TOTP / backup
codes / enforcement) is deliberately OUT OF SCOPE for this pass per the
product decision; everything else under CHECKLIST.md Tier 1 is in scope,
plus the cross-cutting auth findings the audit surfaced.

Branch: `tier1-identity-hardening`.

## Work items

- [x] 1. Argon2id password hashing (`password.go`): HashPassword,
        VerifyPassword (Argon2id + legacy bcrypt), NeedsRehash,
        ValidatePasswordComplexity, GenerateStrongPassword.
- [x] 2. Wire User.SetPassword -> Argon2id + complexity;
        User.CheckPassword -> scheme-detecting verify; add
        NeedsPasswordRehash. bcrypt import removed from models.go.
- [x] 3. Admin seed uses GenerateStrongPassword (policy-compliant
        fallback) so first boot does not fail the new complexity rule.
- [x] 4. JWT verify hardening (`token.go`): fail CLOSED on missing
        status claim; validate issuer.
- [x] 5. Refresh-token reuse detection (family revocation) +
        transparent Argon2id rehash on login (`handlers.go`).
- [x] 6. Account lockout + shared (Redis-backed) login rate limiting.
        auth.AttemptLimiter interface + policy (5 failures -> exp
        backoff base 1m cap 15m, counter window 15m) + dev in-memory
        impl; handler wiring on login/register/refresh with pre-check
        lockout + RegisterFailure/ResetFailures; gateway
        RedisAttemptLimiter (atomic Lua sliding window + lock key);
        container wiring is FAIL-CLOSED in prod/staging (Redis limiter
        mandatory, NO silent in-memory fallback), dev-only explicit
        in-memory mode with a loud warning. Fail-open on Redis ERROR
        (availability over a login-wide outage), logged at WARN.
- [x] 7. Password breach detection (HIBP k-anonymity). breach.go
        (HIBPBreachChecker + NoopBreachChecker), enforced on
        register/change/reset, fail-open on API error, env-gated wiring
        (on in prod/staging, off in dev unless AUTH_BREACH_CHECK_ENABLED).
- [x] 8. Password history controls. auth_password_history table +
        PasswordHistoryStore (RecordHash with prune, IsReused via
        VerifyPassword); reject last PasswordHistorySize=5 on
        change/reset; seeded on register; fail-open on store error;
        wired from authPool in gateway main.
- [x] 9. Service-token revocation via per-user TOKEN EPOCH.
        auth_users.token_epoch column + User.TokenEpoch +
        Claims.TokenEpoch ('tv') + Claims.TokenType ('token_type').
        IssueTokenPair + IssueServiceToken stamp 'tv'; signature
        change propagated to ALL issuers (execution reconcile_identity
        + main.go restore/coldstart/preload/refresh-loop; management
        main.go restore+renewal; management supervisor). Enforcement:
        TokenService.WithEpochResolver(UserStore) -> VerifyAccessToken
        rejects a SERVICE token whose tv < current epoch, FAIL-CLOSED
        on resolver error or unknown user; access tokens skip the
        lookup (stateless). Resolver wired only in execution+management
        (the service-token consumers); gateway left nil. Revocation
        triggers: BumpTokenEpoch on admin deactivate, change-password,
        and reset redemption.
- [x] 10. Anti-ATO notifications. mails/security_alert_template.go
        (PasswordChanged + NewLogin templates, HTML-escaped, shared
        meta block); SessionStore.HasPriorSessionFromIP for new-device
        detection (checked BEFORE session insert, fail-open);
        Handler.WithSecurityNotifications + nil-safe fire-and-forget
        notifyPasswordChanged / notifyNewLogin; wired into login
        (new IP), change-password, and reset redemption; gateway
        injects the existing *mails.Sender.
- [x] 11. Removed the dead peer-only RateLimitMiddleware + peerOnly
        helper (footgun: collapses to one global bucket behind the
        ingress; zero callers). RateLimiter +
        RateLimitMiddlewareWithResolver retained (auth/consent/support
        all use them). Documented the intentional two-layer design
        (per-pod in-memory burst guard + cluster-wide Redis
        AttemptLimiter) in RegisterRoutes so the dev fallback is not
        mistaken for redundancy.
- [ ] 12. Tests for all of the above + final wiring verification.

## Design decisions / back-compat

- Argon2id params: m=64MiB, t=3, p=2, 16B salt, 32B key (OWASP / RFC
  9106). Encoded in the PHC string so a future bump is auto-upgraded by
  NeedsRehash on next login.
- Zero forced reset: VerifyPassword reads bcrypt hashes; login rehashes
  to Argon2id transparently. Existing rows keep working.
- Complexity: length [8,72] + >=3 of 4 char classes + common-password
  denylist + no username/email substring. Enforced centrally in
  SetPassword so register / admin-create / change / reset / seed all
  inherit it.
- Fail-closed: a JWT missing 'status' or with a wrong 'iss' is rejected
  (status is a security gate; tier defaults to 'free' as least-privilege).
- Reuse detection: a revoked-but-unexpired refresh token presented again
  triggers full session-family revocation + a security log event.

## STATUS: IN PROGRESS (items 1-11 landed; 12 pending)
