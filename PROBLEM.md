Excellent — every required key is present with a real value (no empty, no placeholder). The dump confirms:

- TwelveData: 32 chars (their standard key length) ✓
- FRED: 32 chars (St. Louis Fed standard) ✓
- MaxMind license: 40 chars + account ID 7 chars (their standard format) ✓
- CFTC: 46 chars (Socrata token format) ✓
- Anthropic: 108 chars ✓
- OpenAI: 167 chars ✓
- Gemini: 39 chars ✓
- MetaApi: 2078 chars (their JWT-style token — that's normal, MetaApi tokens are huge) ✓

To your question — **yes, those nine are the ONLY operator-supplied secrets we read from `.env`.** Here's the full picture so you can see what gets written to Vault and where each value comes from. Nothing is hidden, nothing is skipped.

#### Complete inventory: every value written to Vault in Phase 8

**A. From your `.env` (9 values)** — operator-supplied real API keys:

| `.env` variable | Vault path | Property name |
|---|---|---|
| `MAXMIND_LICENSE_KEY` | `etradie/services/edge-ingress/staging/maxmind` | `license_key` |
| `MAXMIND_ACCOUNT_ID` | `etradie/services/edge-ingress/staging/maxmind` | `account_id` |
| `TWELVEDATA_API_KEY` | `etradie/services/engine/staging` | `twelvedata_api_key` |
| `FRED_API_KEY` | `etradie/services/engine/staging` | `fred_api_key` |
| `CFTC_APP_TOKEN` | `etradie/services/engine/staging` | `cftc_app_token` |
| `PROCESSOR_ANTHROPIC_API_KEY` | `etradie/services/engine/staging` | `processor_anthropic_api_key` |
| `PROCESSOR_OPENAI_API_KEY` | `etradie/services/engine/staging` | `processor_openai_api_key` |
| `PROCESSOR_GEMINI_API_KEY` | `etradie/services/engine/staging` | `processor_gemini_api_key` |
| `MT5_METAAPI_TOKEN` | `etradie/services/engine/staging` | `mt5_metaapi_token` |

**B. Generated fresh in §8.2 (9 values)** — must be unique per-environment:

| Generated variable | Where used (Vault property names) |
|---|---|
| `DB_PASS` | postgres `postgres_password` + gateway/engine/billing `postgres_password` + embedded in DSN URLs |
| `REDIS_PASS` | redis `redis_password` + engine `redis_password` + embedded in REDIS URLs |
| `JWT_SECRET` | gateway/engine/execution/management `auth_jwt_secret` |
| `BROKER_KEY` | engine-only `broker_encryption_key` (Tier 3: sole consumer) |
| `CHROMA_TOKEN` | data-layer/chromadb `auth_token` (single source, both server + engine read) |
| `ADMIN_PASS` | gateway `auth_admin_password` (rotate after first dashboard login) |
| `ENGINE_SHARED` | gateway/engine/execution/management `engine_internal_shared_secret` |
| `BILLING_SHARED` | gateway `billing_internal_shared_secret` AND billing `internal_shared_secret` (different KEY names, same VALUE) |
| `MT_DEFAULT_ZMQ` | mt-node `default_zmq_auth_token` |

**C. Captured from Phase 6/7 outputs (4 file references)** — already on disk:

| Source file | Vault path | Property name |
|---|---|---|
| `~/cloudflare-staging-tunnel-token.txt` | `etradie/services/edge-ingress/staging/cloudflare/tunnel` | `tunnel_token` |
| `~/eTradie/ca.crt` | `etradie/platform/linkerd/production` | `trust_anchor_pem` |
| `~/eTradie/issuer.crt` | `etradie/platform/linkerd/production` | `issuer_tls_crt` |
| `~/eTradie/issuer.key` | `etradie/platform/linkerd/production` | `issuer_tls_key` |
| `~/cf-origin-staging-api.crt` | `etradie/services/edge-ingress/staging/tls` | `staging_api_cert` |
| `~/cf-origin-staging-api.key` | `etradie/services/edge-ingress/staging/tls` | `staging_api_key` |
| `~/cf-origin-wildcard-staging.crt` | `etradie/services/edge-ingress/staging/tls` | `staging_wildcard_cert` |
| `~/cf-origin-wildcard-staging.key` | `etradie/services/edge-ingress/staging/tls` | `staging_wildcard_key` |

**D. Fetched live from a public endpoint (1 value)**:

| Source | Vault path | Property name |
|---|---|---|
| `curl https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem` | `etradie/services/edge-ingress/staging/cloudflare/aop_ca` | `aop_ca` |

**E. Constants (3 values)** — hard-coded in Phase 8 because the data-layer chart pins them:

| Constant | Where |
|---|---|
| `etradie` (postgres user) | postgres + gateway + engine `postgres_user` |
| `etradie` (postgres DB) | postgres + gateway `postgres_db` |
| `require` (postgres sslmode) | gateway + billing `postgres_sslmode` |

**F. Staging placeholders generated in §8.10 (9 values)** — per Phase 0 decision, billing creds are NOT in hand:

| Placeholder variable | Vault property |
|---|---|
| `PLACEHOLDER_LONG` (used twice — re-randomised between fields would also be fine) | `paddle_webhook_secret`, `lemonsqueezy_webhook_secret` |
| `PLACEHOLDER_API_KEY` (used twice) | `paddle_api_key`, `lemonsqueezy_api_key` |
| `PLACEHOLDER_PRICE_BYOK` | `paddle_price_pro_byok` |
| `PLACEHOLDER_PRICE_MANAGED` | `paddle_price_pro_managed` |
| `PLACEHOLDER_LS_STORE` | `lemonsqueezy_store_id` |
| `PLACEHOLDER_LS_VARIANT_BYOK` | `lemonsqueezy_variant_pro_byok` |
| `PLACEHOLDER_LS_VARIANT_MANAGED` | `lemonsqueezy_variant_pro_managed` |

**G. Computed DSN/URL strings (4 values)** — composed from `DB_PASS` + `REDIS_PASS` + in-cluster service FQDNs:

| Computed variable | Where used |
|---|---|
| `DB_URL_GO` | gateway `auth_database_url`, execution `execution_database_url`, management `management_database_url`, billing `billing_database_url` |
| `DB_URL_PY` | engine `database_url` |
| `REDIS0` | gateway `gateway_redis_url`, engine `redis_url`, billing `billing_redis_url` |
| `REDIS1` | execution `execution_redis_url`, management `management_redis_url` |

#### Why your `.env` has 300+ variables but we only read 9

Most `.env` variables are **non-secret configuration** — log levels, timeouts, polling intervals, RAG tuning, SMC/SND thresholds, RSS feed URLs, etc. Those live in chart `ConfigMap`s (rendered by Helm from `values.yaml` / `values-staging.yaml`), NOT in Vault. The pattern is:

- **Vault** = secrets (anything that, if leaked, materially harms the business: passwords, API keys, signing keys, certs).
- **ConfigMap** = everything else (operational tunables, public URLs, feature flags).

The chart values files (`helm/<svc>/values-staging.yaml` plus the base `values.yaml`) already carry the right non-secret values for staging. They were tuned by whoever set up the original BUDGET.md Table 2B profile, and we don't touch them in Phase 8.

#### Specific `.env` variables we intentionally do NOT write to Vault

This is the explicit list of "in your `.env`, NOT in our Phase 8 plan, by design":

| `.env` variable | Why excluded |
|---|---|
| `AUTH_JWT_SECRET` | Per the audit: gateway/engine ESO templates use the staging-generated value, NOT the .env one (each env needs its own JWT secret). |
| `ENGINE_INTERNAL_SHARED_SECRET` | Same reason — generated fresh per env. |
| `BILLING_INTERNAL_SHARED_SECRET`, `GATEWAY_BILLING_INTERNAL_SHARED_SECRET`, `GATEWAY_ENGINE_INTERNAL_SHARED_SECRET` | Same — generated fresh per env. |
| `BROKER_ENCRYPTION_KEY` | Generated fresh per env (Tier 3 KEK). |
| `LLM_ENCRYPTION_KEY` | DEAD KEY — engine ESO template explicitly says `dead LLM_ENCRYPTION_KEY is intentionally NOT mapped here`. Engine uses `BROKER_ENCRYPTION_KEY` for both broker + LLM credentials (shared cipher). Do not write this to Vault. |
| `MT5_ZMQ_AUTH_TOKEN` | Per-tenant; generated by engine's HostedProvisioner at runtime. The §8.11 platform-level `default_zmq_auth_token` is the fallback for when no per-tenant override exists. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` | Written into the right Vault paths in §8.4/8.7/8.8/8.10 via the generated `DB_PASS` + the constants — NOT sourced from .env. |
| `REDIS_PASSWORD`, `REDIS_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | Written into Vault via generated `REDIS_PASS` and computed URLs. |
| `DATABASE_URL` | Computed from `DB_PASS` (`DB_URL_PY`/`DB_URL_GO`), not copied from .env. |
| `AUTH_GOOGLE_CLIENT_ID`, `AUTH_GOOGLE_CLIENT_SECRET`, `AUTH_GOOGLE_REDIRECT_URI`, `AUTH_GOOGLE_LINK_REDIRECT_URI` | **Not currently in ANY chart ExternalSecret template**. If you want Google OAuth in staging, this is a chart update first (add a new ExternalSecret), not a Phase 8 write. |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` | **Not in any ExternalSecret template**. Same as above — chart-update first. |
| `SUPPORT_*` (WhatsApp/Telegram/Discord) | **Not in any ExternalSecret template**. Chart-update first. |
| `CONSENT_IP_HASH_SALT` | **Not in any ExternalSecret template**. Chart-update first. |
| `TRADINGVIEW_WEBHOOK_SECRET` | **Not in any ExternalSecret template**. Chart-update first. |
| `BUILD_DATE`, `GIT_COMMIT` | Build-time labels, not runtime secrets. |
| `BILLING_PUBLIC_BASE_URL`, `BILLING_CHECKOUT_*`, `BILLING_SERVICE_URL`, `BILLING_HTTP_PORT`, `BILLING_LOG_*`, `BILLING_RECONCILER_*`, `BILLING_WEBHOOK_*`, `BILLING_IDEMPOTENCY_RETENTION_DAYS` | These are billing's NON-secret config — set by `helm/billing/values-staging.yaml::config.billing.*`, rendered into the billing ConfigMap. NOT secrets. |
| `PADDLE_API_BASE_URL`, `LEMONSQUEEZY_API_BASE_URL` | Non-secret URLs, set by `helm/billing/values-staging.yaml` (staging uses Paddle sandbox per the overlay). NOT secrets. |
| All `*_RSS_URL`, `*_BASE_URL`, `*_TIMEOUT_*`, `*_RETRY_*`, `*_CACHE_TTL_*`, `*_INTERVAL_*` | Non-secret tunables, in ConfigMaps via Helm values. NOT secrets. |
| All `SMC_*`, `SND_*`, `TA_*`, `RAG_*` | Strategy/algorithm tunables. ConfigMaps via Helm values. NOT secrets. |
| `AUTH_TIER_*`, `AUTH_OAUTH_*`, `AUTH_PASSWORD_*`, `AUTH_LLM_*`, `AUTH_BCRYPT_*`, `AUTH_MAX_*`, `AUTH_TRUSTED_*`, `AUTH_TRUST_*`, `AUTH_RETURN_*`, `AUTH_CSRF_*`, `AUTH_COOKIE_*`, `AUTH_ACCESS_*`, `AUTH_REFRESH_*`, `AUTH_ALLOW_*`, `AUTH_ISSUER` | Auth POLICY (non-secret). ConfigMaps via Helm values. |
| `AUTH_ADMIN_USERNAME`, `AUTH_ADMIN_EMAIL` | Public-ish (the email shows up in dashboard "created by admin" rows). ConfigMap, not Vault. The PASSWORD goes to Vault as `auth_admin_password`. |
| `AUTH_FRONTEND_BASE_URL` | Public URL. ConfigMap. |
| `OTEL_*`, `METERING_*`, `CIRCUIT_BREAKER_*`, `HTTP_*`, `RATE_LIMIT_*` | Operational tunables. ConfigMaps. |
| `CHROMA_AUTH_TOKEN`, `RAG_CHROMA_AUTH_TOKEN` | Both env-var names point at the SAME underlying value, written ONCE to Vault as `etradie/data-layer/chromadb/staging:auth_token` (generated by §8.4's `CHROMA_TOKEN`). The chart materialises it into the K8s Secret keyed correctly for each consumer. |
| `MT5_ZMQ_HOST`, `MT5_ZMQ_PORT`, `MT5_PROVIDER`, `MT5_TERMINAL_PATH`, `MT5_MAGIC_NUMBER`, `MT5_ENABLED`, `MT5_TIMEOUT_*`, `MT5_CONNECTION_*`, `MT5_MAX_*`, `MT5_ENABLE_*`, `MT5_METAAPI_REGION` | Per-user broker connection settings (managed via dashboard at runtime per `.env.example`). NOT in any ExternalSecret. |

#### Sanity: if you ever want to verify "is this `.env` variable's name in ANY ExternalSecret template"

```bash
cd ~/eTradie
# Substitute the var name in lowercase + the upper transform, search both shapes
for var in TWELVEDATA_API_KEY MAXMIND_LICENSE_KEY YOUR_QUESTION_HERE; do
  lower=$(echo "$var" | tr '[:upper:]' '[:lower:]')
  hits=$(grep -rn "property: $lower" helm/*/templates/ 2>/dev/null | wc -l)
  hits2=$(grep -rn "secretKey: $var" helm/*/templates/ 2>/dev/null | wc -l)
  echo "$var: property-form=$hits, secretKey-form=$hits2"
done
```

If both hits are 0, the variable is not read by any chart from Vault, regardless of what `.env` says.

#### So — confirmation

**You're not missing anything.** Phase 8 writes exactly:
- 9 .env-sourced values (✓ all present, all real)
- 9 freshly generated values
- 8 file-based values (Phase 6/7 outputs + Cloudflare Origin Certs)
- 1 live-fetched value (AOP CA)
- 9 staging-only billing placeholders
- 3 constants + 4 computed URLs

Total: 43 properties across 12 Vault paths.

Everything that's a secret AND consumed by a chart's ExternalSecret template at runtime gets written. Everything that's non-secret stays in the chart `values-staging.yaml` (already in place, no operator action). Everything in `.env` that's not in any ExternalSecret is either build/dev-only or deliberately omitted (dead keys, dashboard-managed runtime values, future Google-OAuth chart-update).

#### Last pre-flight check before we run §8.0

Please run the sanity-check block I asked for in the previous message — tunnel + vault-0 status + the file listings:

```bash
kubectl get nodes
kubectl -n vault get pod vault-0 -o jsonpath='{.status.phase} {.status.conditions[?(@.type=="Ready")].status}{"\n"}'
ls -la ~/vault-init.txt ~/cloudflare-staging-tunnel-token.txt \
       ~/cf-origin-staging-api.crt ~/cf-origin-staging-api.key \
       ~/cf-origin-wildcard-staging.crt ~/cf-origin-wildcard-staging.key
ls -la ~/eTradie/ca.crt ~/eTradie/ca.key ~/eTradie/issuer.crt ~/eTradie/issuer.key
```

Expected:
- `vmi3362776 Ready ...`
- `Running True`
- Six `~/...` files, all `-rw-------`.
- Four mesh CA files at repo root, also `-rw-------`.

Paste the output and we run Phase 8.0 (the pre-flight script the new README ships) immediately after. Then 8.1 through 8.11 in sequence.