THESE ARE THE ISSUES YOU IDENTIFIED DURING THE TIER 1 AUDIT:



I found the **first real finding**. Comparing the engine's JWT verification (`auth.py::_verify_token`) against the hardened Go verifier (`token.go::VerifyAccessToken`):

**FINDING A1 — Engine JWT verification does NOT fail-closed on missing `status` (drift from Tier 1 item 4).**

In the Go gateway (item 4), I changed `VerifyAccessToken` to **reject** a token missing the `status` claim (`status` is a security gate). But the engine's Python `_verify_token`:
- `require` list is only `["sub","username","role","exp","iat"]` — **`status` is not required**, and
- `status = payload.get("status", "active")` — **silently defaults a missing/empty `status` to `"active"`**.

This is exactly the fail-open posture I removed on the Go side. It's not a full bypass today (the gateway is the front door and its tokens always carry `status`), but the engine accepts cookie/Bearer tokens **directly** (`get_current_user` is used on public engine routes), so a token minted without `status` would be treated as `active` at the engine even though the gateway would reject it. That's an inconsistency between two verifiers of the same token — a real drift and a latent privilege issue if a suspended user's token ever lacked `status`.

Also note the engine **does not enforce the token-epoch (`tv`) claim at all** — but that's acceptable by design: the engine only consumes **user** access tokens (15-min), not the 30-day service tokens (those go to execution/management over gRPC). Item 9 deliberately scoped epoch enforcement to service-token consumers. So no finding there, but I'll document it.

Let me verify the engine's processor handler trusts `X-User-Id` only behind `verify_internal_auth`, and check the broker/llm connection routers for user-scoping. Then I'll read the admin engine routes and the internal router.





Now I have a **second important finding** plus confirmation of a gap from the Tier 1 work.

**FINDING A2 — The Tier 1 features that are env-gated/SMTP-dependent are NOT surfaced in the gateway Helm chart.** The Go config + handler read these, but the deploy layer never sets them:

1. **`AUTH_BREACH_CHECK_ENABLED`** — item 7's HIBP toggle. `breachCheckEnabled()` defaults ON in prod when `APP_ENV` is production/staging. But the gateway configmap **does not set `APP_ENV`** anywhere I can see, and doesn't set `AUTH_BREACH_CHECK_ENABLED`. So in prod the breach check defaults… based on `APP_ENV`, which must be set somewhere. I need to verify `APP_ENV` is injected (the cookie-secure and Redis-limiter fail-closed guards ALL depend on `isProdLikeEnv()`/`isProdLikeEnvContainer()` reading `APP_ENV`). **If `APP_ENV` is not set in the gateway pod, every prod-only guard silently disables** — that would be a serious finding (cookie-secure not enforced, in-memory rate limiter allowed, breach check off). This is the single most important thing to confirm.

2. **SMTP / mailer config** for the new security notifications (item 10) and password reset — the gateway needs SMTP env vars. Not in this configmap (may be in a separate mails configmap or the externalsecret). Need to confirm.

3. **`AUTH_FRONTEND_BASE_URL`** — needed by password reset + the soft-cap email. Not in this configmap. Need to confirm it's set somewhere (else reset links break in prod, though that's pre-existing).

Let me check: (a) whether `APP_ENV` is set in the gateway deployment/values, and (b) the gateway values.yaml for the auth/smtp/frontend settings.






**Confirmed FINDING A2 — `APP_ENV` is NOT set anywhere in the gateway pod.** The deployment's `envFrom` pulls the configmap + externalsecret, plus three downward-API env vars (`POD_NAME`/`POD_NAMESPACE`/`POD_IP`). The configmap does **not** set `APP_ENV`, `ENV`, or `ENVIRONMENT`. The externalsecret doesn't either.

This is a **serious latent finding** because the entire fail-closed posture of the Go services keys off `isProdLikeEnv()` reading `APP_ENV`/`ENV`/`ENVIRONMENT`:

- `auth.Config.validate()`: cookie-secure enforcement, SameSite=Lax refusal, JWT-secret-required, DB-URL-required, admin-password-required guards — **all become no-ops** if `APP_ENV` is unset (it returns `""` → not prod-like).
- `container.isProdLikeEnvContainer()`: the **mandatory Redis rate-limiter** fail-closed guard — would fall through and **allow the in-memory dev limiter in production**.
- `breachCheckEnabled()`: HIBP defaults **off**.

However — I must not jump to a conclusion. `APP_ENV` could be injected via `values-production.yaml` as an extra configmap entry, or via a separate mechanism. The configmap template I read is the base; there may be conditional additions. But the configmap template has **no `APP_ENV` key at all**, so values can't inject it through this template. Let me verify by checking the gateway `values-production.yaml` and whether there's any `APP_ENV`/extraEnv mechanism, and the engine deployment (which also depends on `APP_ENV` for `internal_auth` and `auth.py`).




**FINDING A2 CONFIRMED — `APP_ENV` is never set in the gateway production deployment.** It's not in `values-production.yaml` `config.gateway`/`config.auth`, not in the base configmap template (no such key), and not in the externalsecret. The configmap template only emits the keys it hard-codes.

But wait — `values-production.yaml` sets `cookieSecure: "true"`, `cookieSameSite: "None"`. The `auth.Config.validate()` cookie guard for `None`+`Secure` works regardless of `APP_ENV` (that check is unconditional). And `cookieSecure:true` is set explicitly. So cookie security holds in prod **because the values set it explicitly**, not because of the prod guard. But the **fail-closed guards still silently disarm**:

- The **Redis attempt-limiter mandatory guard** (`isProdLikeEnvContainer()`): since `APP_ENV` is empty, it takes the `else if redisClient != nil` branch → it **does** wire the Redis limiter (because Redis is present in prod). So in practice the limiter is still Redis-backed. The *fail-closed enforcement* is disarmed, but the *actual behavior* is still correct because Redis is always present. So this is latent, not active breakage.
- **`breachCheckEnabled()`**: `APP_ENV` empty + `AUTH_BREACH_CHECK_ENABLED` unset → **returns false → HIBP breach check is OFF in production.** This is an **active gap**: item 7 is wired in code but **disabled in the prod deploy** because neither `APP_ENV` nor `AUTH_BREACH_CHECK_ENABLED` is set. Item 7 doesn't actually run in production.
- **JWT-secret-required / DB-URL-required / admin-password-required** prod guards: disarmed, but the values/externalsecret provide all three, so no active breakage.

This is real and must be fixed. The correct fix: **set `APP_ENV` in the gateway (and engine/execution/management) configmaps from a value**, defaulting to `production` in `values-production.yaml` and `staging` in `values-staging.yaml`. That single fix re-arms every fail-closed guard across all services and turns the HIBP check on in prod.

Let me confirm the same `APP_ENV` gap exists in the engine deployment (engine's `internal_auth._load_secret()` and `auth._get_jwt_secret()` both fail-fast in prod only when `APP_ENV` is prod-like — if unset, a **missing `ENGINE_INTERNAL_SHARED_SECRET` would NOT fail fast** and `/internal/*` would reject all calls, breaking the whole pipeline; and a missing JWT secret wouldn't fail fast). Let me read the engine configmap + deployment for `APP_ENV`.



No `APP_ENV` / `config.app.env` anywhere for execution either. The finding is fully confirmed across gateway, execution, management. The engine sets it; the three Go services do not.

I have enough verified evidence to act. The two findings are real, production-impacting, and exactly the kind of "incomplete wiring between code and deploy" you asked me to hunt. Let me fix both, then continue the audit (admin dashboard wiring question, execution/management HTTP CSRF, SPA auth). 

**Fix 1 (A2):** Add `APP_ENV` to the three Go-service configmaps, sourced from `.Values.config.app.env`, and set it in each `values-production.yaml` (`production`) and `values-staging.yaml` (`staging`), with a safe `development` default in base `values.yaml`. This re-arms all fail-closed guards and turns HIBP on in prod.

Let me do the gateway first (configmap + values). I'll add the key to the configmap and the value to base + prod + staging.




Now set `config.app.env` in the production and staging overlays for all three services. Let me check the staging files exist (gateway/execution/management each have values-staging.yaml per the helm tree — gateway and execution yes; let me set both prod and staging). I'll add the `app.env` block to each overlay. Production = `production`, staging = `staging`.


fix(helm): set config.app.env in gateway/execution/management overlays

AUDIT FINDING A2 (part 2): supply the real APP_ENV value per
environment so the ConfigMap key added in the previous commit
materialises as "production" / "staging" and the Go-service
fail-closed guards (HIBP, Redis attempt-limiter mandatory, cookie
security, secret-required) are armed in those clusters.

production overlays -> production; staging overlays -> staging.


--- helm/gateway/values-production.yaml
+++ helm/gateway/values-production.yaml
@@ -1,3 +1,8 @@
 config:
+  app:
+    # Arms every Go-service prod fail-closed guard (HIBP breach check,
+    # mandatory Redis attempt-limiter, cookie-Secure enforcement,
+    # JWT/DB/admin-secret required). Audit ref: A2.
+    env: "production"
   gateway:
     logLevel: "INFO"



--- helm/execution/values-production.yaml
+++ helm/execution/values-production.yaml
@@ -1,5 +1,9 @@
 config:
+  app:
+    # Arms the execution prod guards (ENGINE_INTERNAL_SHARED_SECRET
+    # required under BROKER_MODE=mt5, localhost-Redis refusal). A2.
+    env: "production"
   execution:
     # Real broker. The Python engine's broker bridge does the actual
     # MT5 socket work; this service just dispatches via HTTP.
     brokerMode: "mt5"



PLEASE NOTE: AS YOU CAN SEE THAT COMMIT ONE ALREADY LANDED AT THE auth-audit-appenv-and-engine-status BRANCH BUT THE SECOND COMMIT DIDN'T GO THROUGH WHICH I HAVE COPIED INTO THIS PLACE.

YOU SHOULD ALSO EXAMINE THE docs/security/TIER1_IDENTITY_HARDENING.md THOROUGHLY FROM THE BEGINNING TO THE END TO UNDERSTAND ALL WE DID FOR THE TIER 1 (IDENTITY & AUTHENTICATION)




 docs/security/TIER1_IDENTITY_HARDENING.md            | 112 ++++++++++++++++++++++++++++++
 src/auth/attempt_limiter.go                          | 225 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 src/auth/attempt_limiter_test.go                     |  78 +++++++++++++++++++++
 src/auth/breach.go                                   | 134 +++++++++++++++++++++++++++++++++++
 src/auth/handlers.go                                 | 354 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 src/auth/models.go                                   |  76 +++++++++++++++-----
 src/auth/password.go                                 | 361 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 src/auth/password_reset_handlers.go                  |  31 ++++++++-
 src/auth/password_test.go                            | 134 +++++++++++++++++++++++++++++++++++
 src/auth/ratelimit.go                                |  35 ----------
 src/auth/store.go                                    | 182 +++++++++++++++++++++++++++++++++++++++++++++++-
 src/auth/token.go                                    |  87 +++++++++++++++++++++--
 src/auth/token_epoch_test.go                         | 121 ++++++++++++++++++++++++++++++++
 src/execution/cmd/execution/main.go                  |  15 ++--
 src/execution/cmd/execution/reconcile_identity.go    |   4 +-
 src/gateway/cmd/gateway/main.go                      |  42 +++++++++++
 src/gateway/internal/container/container.go          |  50 ++++++++++++++
 src/gateway/internal/server/redis_attempt_limiter.go | 152 ++++++++++++++++++++++++++++++++++++++++
 src/mails/security_alert_template.go                 | 141 +++++++++++++++++++++++++++++++++++++
 src/mails/security_alert_template_test.go            |  45 ++++++++++++
 src/management/cmd/management/main.go                |  11 ++-
 src/management/internal/monitoring/supervisor.go     |   4 +-
 22 files changed, 2323 insertions(+), 71 deletions(-)
 create mode 100644 docs/security/TIER1_IDENTITY_HARDENING.md
 create mode 100644 src/auth/attempt_limiter.go
 create mode 100644 src/auth/attempt_limiter_test.go
 create mode 100644 src/auth/breach.go
 create mode 100644 src/auth/password.go
 create mode 100644 src/auth/password_test.go
 create mode 100644 src/auth/token_epoch_test.go
 create mode 100644 src/gateway/internal/server/redis_attempt_limiter.go
 create mode 100644 src/mails/security_alert_template.go
 create mode 100644 src/mails/security_alert_template_test.go