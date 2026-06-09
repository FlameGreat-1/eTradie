# TIER 4 — Abuse Prevention: operator runbook

Operator-only steps for the TIER 4 abuse-prevention controls (Envoy L7
backstop, Cloudflare WAF/rate-limit/bot, gateway/execution/engine
per-user rate limits, JWT audience). Everything in the repo is code and
flows through CI + ArgoCD; the steps below are the ones a human must run
or decide because they need live credentials, a plan-tier decision, or a
timed two-deploy sequence.

See also: `docs/security/TIER4_ABUSE_PREVENTION_PLAN.md` (the design and
the full task list).

---

## 1. Pre-deploy validation (run locally or in CI before merging)

All of these are wired into `make platform-ci`; run them individually
while iterating:

```bash
make tf-validate-cloudflare     # terraform validate on infrastructure/cloudflare
make tf-plan-cloudflare         # terraform plan (needs CF creds; see step 2)
make helm-template-production   # render envoy + gateway charts
make promtool-check             # validate gateway+engine PrometheusRule PromQL
make envoy-config-validate      # envoy --mode validate the rendered envoy.yaml
make platform-ci                # the full bundle (all of the above + more)
```

`promtool-check` and `envoy-config-validate` skip cleanly with a notice
if `promtool` / `yq` / `envoy` are not installed locally; CI has them.

---

## 2. Cloudflare edge controls (terraform apply)

The WAF managed ruleset and the per-IP rate-limit rules on `/api/*` and
`/auth/*` work on **any paid plan** and are ON by default
(`enable_waf`, `enable_rate_limiting`).

### 2a. Choose the bot-protection path for the zone's plan

**Exactly one** of these — never both (a terraform precondition enforces
it):

| Cloudflare plan | Variable to set | Resource |
|-----------------|-----------------|----------|
| Pro / Business  | `enable_super_bot_fight_mode = true` | zone bot-fight-mode setting |
| Enterprise (Bot Management add-on) | `enable_bot_management = true` | `cloudflare_bot_management` |
| Unknown / not entitled | leave **both** `false` (default) | none — apply still succeeds |

Enabling `enable_bot_management` on a non-Enterprise zone, or
`enable_super_bot_fight_mode` without a Pro/Business plan, fails
`terraform apply`. When in doubt, leave both off; WAF + rate limiting
still deploy.

### 2b. Apply

```bash
cd infrastructure/cloudflare
terraform init
terraform plan  -var environment=production -var zone_id=<ZONE_ID> \
  -var 'hostnames={ "api.exoper.com" = "<tunnel-id>.cfargotunnel.com" }' \
  -var enable_super_bot_fight_mode=true   # OR enable_bot_management=true on Enterprise
terraform apply <same vars>
```

Expect **additions only** (WAF ruleset, rate-limit ruleset, optionally a
bot resource). The existing zone-TLS, AOP, and DNS resources must show
**no changes**; the DNS record carries `prevent_destroy`.

---

## 3. Envoy + gateway (ArgoCD)

The Envoy `local_ratelimit` + per-route request-byte caps and the
gateway PrometheusRule deploy automatically via the
`envoy-production` / `gateway-production` ArgoCD apps (they track `main`
+ base + production values). No manual step beyond merging.

**Prerequisite:** the PrometheusRule kind requires the Prometheus
Operator CRDs in-cluster. They are already assumed (the engine chart
ships a PrometheusRule too). If a cluster lacks them, set
`prometheusRule.enabled=false` in the gateway values for that env until
the operator is installed, to avoid an ArgoCD sync error on an unknown
kind.

Staging note: the Envoy `local_ratelimit` is ENABLED but enforced at 0%
in staging (`enforcedFraction: 0`) so the 429 path is exercised in
metrics/logs without rejecting traffic. Flip to 100 in a staging soak
before trusting the production value.

---

## 4. JWT audience rollout (two deploys, timed)

`aud` is issued + verified, but enforcement is staged so no live session
is invalidated:

1. **Deploy 1 (current default):** `AUTH_REQUIRE_AUDIENCE=false`. Every
   newly issued token carries `aud`; verification tolerates a token
   with no `aud` (pre-rollout tokens keep working).
2. **Wait** at least `AUTH_ACCESS_TOKEN_TTL_SECONDS` (default 15m, but
   wait for the refresh-token TTL to be safe) so every pre-rollout
   access token has expired.
3. **Deploy 2:** set `AUTH_REQUIRE_AUDIENCE=true`. Now every token MUST
   carry a matching `aud` or it is rejected.

Do NOT flip to `true` in deploy 1 — it would 401 every in-flight
pre-rollout session.

---

## 5. Still-open operator actions (cannot be done in code)

- **F5 — committed secrets:** rotate/revoke the NVIDIA `nvapi-...` key
  and the SSH credentials referenced in `CLOUDFLARE.md`, then purge them
  from git history (e.g. `git filter-repo`). Until done, treat those
  credentials as compromised.
- **Origin firewall:** confirm the origin only accepts TCP/443 from
  Cloudflare published ranges (pairs with edge-ingress AOP mTLS). Refresh
  the ranges with `make cf-refresh-ips`.
- **Bot-management entitlement:** confirm the zone's plan before setting
  either bot toggle in step 2a.

---

## 6. Verifying it works after deploy

- WAF / rate limits: Cloudflare dashboard → Security → Events; or hit
  `/auth/*` past the per-IP budget and expect `429`.
- Envoy backstop: `envoy_http_local_rate_limiter_*` stats on the Envoy
  admin/metrics endpoint; the `EnvoyLocalRateLimitActive` alert fires on
  a sustained spike.
- Gateway/execution per-user limits: `etradie_gateway_rate_limited_total`
  / `etradie_execution_rate_limited_total`; the `GatewayRateLimitSpike` /
  `ExecutionRateLimitSpike` alerts cover sustained spikes.
- Engine rerun limit: `ratelimit:analysis_rerun:user:<id>` keys in Redis;
  exceeding 10/60s on `/api/analysis/rerun` returns `429`.
