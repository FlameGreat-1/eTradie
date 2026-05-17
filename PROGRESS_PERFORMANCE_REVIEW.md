# Exoper AI — Weekly / Monthly Performance Review — Implementation Tracker

> Live progress tracker. Updated at the end of every batch commit so the
> implementation is fully recoverable if the chat session ends.
>
> Goal (from `PLAN.md`): An AI performance analyst that runs **weekly**
> and **monthly** over the user's full trading history **plus** their
> defined Trading System, and returns the 14-section institutional-grade
> review described in `PLAN.md` (Executive Summary, Performance Metrics,
> Behavioral Analysis, System Adherence Score, Emotional Intelligence,
> Setup Quality, Session Analysis, Risk Analysis, Improvement
> Recommendations, Next Week Focus, AI Confidence & Data Quality,
> Trader Evolution Tracking, Performance vs System Alignment, AI
> Psychological Warnings).
>
> Surface: new sidebar entry on the dashboard → new page that lists the
> latest weekly review, the latest monthly review, full history, and a
> manual "Run review now" CTA (admin / paid tiers).

---

## Verified architectural decisions (no guesses)

These are read directly from the existing code, **not** assumed:

| Concern | Where it lives | Why we reuse it |
| --- | --- | --- |
| Closed-trade history (every trade with grade, R-multiple, setup type, session, style, SL adjustments, partial closes, opened/closed timestamps) | `src/management/internal/journal/{models,repository}.go` | This is the canonical journal; **already** user-scoped via `user_id`, **already** the data source for `useTradeJournal` / `usePerformanceMetrics` in the SPA. The review aggregator reads from the same Postgres tables — no duplication. |
| Trader's defined Trading System / framework | `src/tradingsystem/` (Go gateway domain) + `src/gateway/internal/...` | The framework the LLM compares actual behavior against (PLAN.md §13 "Performance vs Trading System Alignment"). |
| Per-user LLM call with retries, JSON parsing, structured response shaping, callback to gateway, failure callback | `src/engine/processor/trading_plan/generator.py` | Exact pattern we mirror — same `Container.processor_llm_client`, same `schedule_once` cooldown + single-flight + bounded timeout, same `/internal/.../{dispatch,callback,fail}` triad. **Zero duplication of LLM infrastructure**; we only add a new prompt + a new generator + a new internal router. |
| Background scheduling | `src/engine/macro/scheduler_jobs.py` (already used for hourly macro polls) | We add weekly + monthly cron entries here using the same `register_*_jobs` pattern. |
| Sidebar nav, lazy routes, feature folder structure (`features/<name>/{api,components,hooks,lib,types}`), React-Query + axios `api.gateway` / `api.management`, CSRF + cookie auth | `cotradee/src/components/layout/Sidebar.tsx`, `cotradee/src/routes/index.tsx`, `cotradee/src/features/tradingplan/*` | Mirror exactly so the new feature is indistinguishable from the existing ones. |

---

## Data flow (end-to-end, no patchwork)

```
┌─ APScheduler in engine (weekly Mon 06:00 UTC, monthly 1st 06:00) ┐
│ for each eligible user_id:                                       │
│   POST /internal/performance-review/dispatch  (engine self-call) │
└───────────────────────────┬────────────────────────────────────────────┘
                            ▼
┌─ engine/routers/performance_review.py ────────────────────────┐
│  - verifies internal HMAC                                        │
│  - background_tasks.schedule_once(cooldown, timeout)             │
│      → PerformanceReviewGenerator.run(req)                       │
└───────────────────────────┬────────────────────────────────────────────┘
                            ▼
┌─ PerformanceReviewGenerator.run(req) ────────────────────────┐
│ 1. GET gateway /internal/performance-review/aggregate?...        │
│      → gateway proxies to management /internal/analytics/...     │
│      → returns the full deterministic aggregation                │
│        (metrics, behavior, sessions, setups, risk, adherence,    │
│         emotional tags, drawdown/recovery, sample size, gaps)    │
│ 2. GET gateway /internal/trading-system/:user_id                  │
│      → user's defined operating framework                        │
│ 3. Build prompt (calm institutional tone) with both inputs       │
│ 4. Call platform LLM (Container.processor_llm_client)            │
│ 5. Parse + shape into the 14-section wire schema                 │
│ 6. POST /internal/performance-review/callback {user_id, review}  │
│      → gateway store.Save() flips row to status='ready'          │
│      → on any failure → /fail callback → row='failed'            │
└────────────────────────────────────────────────────────────────┘

┌─ User-facing REST (gateway, cookie + CSRF, multi-tenant) ───────┐
│ GET  /api/v1/performance-review/latest?period=weekly|monthly     │
│ GET  /api/v1/performance-review/history?period=&offset=&limit=   │
│ GET  /api/v1/performance-review/:id                              │
│ POST /api/v1/performance-review/generate {period}                │
│      → enforces tier + per-user rate limit                       │
│      → calls engine /internal/performance-review/dispatch        │
└────────────────────────────────────────────────────────────────┘

┌─ SPA: /dashboard/performance ───────────────────────────────────┐
│ - Sidebar entry "Performance" (TrendingUp icon)                  │
│ - Page tabs: Weekly / Monthly / History                          │
│ - Renders the 14 PLAN.md sections, responsive desktop/tablet/    │
│   mobile, dark/light, no fluff.                                  │
│ - "Run now" CTA (POST /generate) with optimistic refetch.        │
└────────────────────────────────────────────────────────────────┘
```

---

## Batches (executed in order, one commit per batch)

| # | Batch | Files | Status | Commit |
| - | ----- | ----- | ------ | ------ |
| 0 | Progress tracker | `PROGRESS_PERFORMANCE_REVIEW.md` | done | this commit |
| 1 | Gateway domain — schema + models + validation | `src/performancereview/{models,schema,validation}.go` | pending | |
| 2 | Gateway domain — store + ratelimit + metrics | `src/performancereview/{store,ratelimit,metrics}.go` | pending | |
| 3 | Gateway domain — handlers + adapter | `src/performancereview/handlers.go`, `src/gateway/internal/performancereviewadapter/adapter.go` | pending | |
| 4 | Gateway wiring (container + routes) | `src/gateway/internal/container/container.go`, `src/gateway/internal/server/*` | pending | |
| 5 | Management — analytics aggregator + HTTP route | `src/management/internal/analytics/performance_aggregator.go`, `src/management/internal/http/server.go`, gateway management client | pending | |
| 6 | Engine — performance_review module (prompt + generator + types) | `src/engine/processor/performance_review/{__init__,prompt,generator,client}.py` | pending | |
| 7 | Engine — internal router + scheduler jobs + main.py wiring | `src/engine/routers/performance_review.py`, `src/engine/macro/scheduler_jobs.py`, `src/engine/main.py` | pending | |
| 8 | Frontend — feature module (types, api, hooks, components) | `cotradee/src/features/performance/{types,api,hooks,components}/...`, `index.ts` | pending | |
| 9 | Frontend — page + sidebar + route registration | `cotradee/src/routes/pages/PerformancePage.tsx`, `cotradee/src/components/layout/Sidebar.tsx`, `cotradee/src/routes/index.tsx` | done | this batch |

---

## Implementation complete

All 9 batches landed on `main`. The feature is wired end-to-end:

- Gateway domain (`src/performancereview/`): models, schema, validation, store, ratelimit, metrics, handlers + adapter.
- Gateway wiring: main.go, container, http_server.
- Management aggregator + `/internal/performance-review/aggregate`.
- Engine generator (`src/engine/processor/performance_review/`): prompt, generator, scheduler.
- Engine internal router + cron registration in `engine/main.py`.
- Gateway internal endpoints: `/internal/performance-review/{callback,fail,prior,active-users}`.
- Frontend feature module (`cotradee/src/features/performance/`): types, api, hooks, primitives, GenerationBanner, PerformanceReviewView, PerformanceReviewSections (all 14), PerformanceReviewHistory.
- Frontend page + Sidebar entry + lazy route.

**Cron cadence:** Weekly Mon 06:00 UTC (prior 7 days). Monthly 1st 06:00 UTC (prior calendar month).

**Manual generation:** `POST /api/v1/performance-review/generate {period}` — enforced by tier + 5/h per-user rate limit, with cooldown + single-flight at the engine layer.

**Tone enforcement:** System prompt + validator banned-phrase list reject motivational / guru language (PLAN.md 'Most Important Architectural Decision').

**Confidence transparency:** Aggregator stamps a deterministic band; LLM is bound by it via prompt + post-shape overwrite; gateway validator double-checks (PLAN.md §11).

---

## Non-negotiable invariants (enforced in every batch)

1. **Multi-tenant safety** — every Postgres query is scoped by `user_id`. Every gateway handler verifies the authenticated user owns the row. No exceptions.
2. **No duplication of LLM plumbing** — we reuse `Container.processor_llm_client`, `Container.background_tasks.schedule_once`, the internal HMAC dependency, and the gateway's internal HTTP shape. Zero new LLM clients.
3. **No duplication of trade data** — the aggregator reads `management_trades` + `management_events` in place. We do **not** copy trade rows into a new table.
4. **Idempotent schema** — all DDL is `CREATE TABLE IF NOT EXISTS` + additive `ALTER TABLE` guarded by `information_schema` checks (matches the existing `journal` schema convention).
5. **Strict response contract** — the LLM output is parsed, shaped, and validated against a typed schema in both the engine (`_shape_review`) and the gateway (`validation.go`). A 422 from the gateway → `/fail` callback → row marked `failed` with a user-safe message → SPA renders a "Regenerate" CTA. **No silent partial saves.**
6. **Cooldown + single-flight + timeout** — same `schedule_once` policy used by trading_plan: weekly review cooldown 5 minutes, monthly 5 minutes (the cron is the throttle; cooldown is defense-in-depth against runaway clients triggering /generate).
7. **Tier-aware rate limits** — free tier: read-only (no `/generate`). Paid tier: 1 manual generation per period per 24h, scheduler runs always. Admin: unlimited.
8. **Confidence transparency** — the aggregator stamps the response with `sample_size` and `confidence_band` (high ≥ 20 closed trades, medium 8–19, low 3–7, insufficient < 3). The LLM is prompted to refuse fake precision when confidence is low (PLAN.md §11).
9. **Tone** — the system prompt enforces calm, institutional, analytical wording. No motivational, chatty, or guru language (PLAN.md "Most Important Architectural Decision").
10. **Responsive + accessible** — every new UI surface is responsive (mobile/tablet/desktop), supports dark/light, focus-ring, keyboard nav, semantic landmarks — mirrors `Sidebar.tsx` / `tradingplan/components` conventions.

---

## How to resume after a chat-session reset

1. Read this file top-to-bottom.
2. Find the first row in the Batches table marked `pending`.
3. Pick up from there. The verified architectural decisions and data flow above are stable — no re-discovery required.
