# Macroeconomics Sub-Module — Implementation Order

> Every file in the project, listed in **strict dependency order**. Implement top-to-bottom.
> Files within the same step have **no inter-dependencies** and can be implemented in any order within that step.
> No file may be implemented before all files in prior steps are complete.

> [!IMPORTANT]
> **API-only** — no scraping. All external data pulled from documented REST/RSS APIs.
> **Environment variables** for all API keys and secrets — injected at runtime, validated at startup.
> **Selective persistence** — processed outputs always stored; raw data stored only for high-impact, revision-prone, or hard-to-re-fetch sources.
> **Per-source polling schedules** — each provider runs on its natural update cadence; analysis cycles read cached snapshots from DB.

---

## STEP 0 — Project Configuration (no code dependencies)

These files configure the build environment, dependencies, containers, and CI. They must exist before any code runs.

| # | File | Purpose |
|---|------|---------|
| 0.1 | `pyproject.toml` | Project metadata, build system, tool config (black, ruff, mypy, pytest) |
| 0.2 | `requirements/base.txt` | Production dependencies (fastapi, uvicorn, sqlalchemy, asyncpg, pydantic-settings, aiohttp, feedparser, apscheduler, redis, prometheus-client, opentelemetry-*, alembic) |
| 0.3 | `requirements/dev.txt` | Dev dependencies (pytest, pytest-asyncio, pytest-cov, httpx, factory-boy, ruff, mypy, pre-commit) |
| 0.4 | `requirements/security.txt` | Security scanning deps (bandit, safety, pip-audit) |
| 0.5 | `.env.example` | Documented env var template — every API key, DB URL, Redis URL, scheduler intervals |
| 0.6 | `alembic.ini` | Alembic config — points to migration env and DB URL from env var |
| 0.7 | `.pre-commit-config.yaml` | Pre-commit hooks (ruff, mypy, bandit) |
| 0.8 | `.gitignore` | Python/Docker ignores |
| 0.9 | `docker/postgres/init.sql` | DB initialization — create database, extensions (uuid-ossp), roles |
| 0.10 | `docker/prometheus/prometheus.yml` | Prometheus scrape config targeting engine service metrics endpoint |
| 0.11 | `docker/engine/Dockerfile` | Multi-stage Python 3.11+ image, non-root user, minimal layer |
| 0.12 | `docker/engine/.dockerignore` | Docker build context exclusions |
| 0.13 | `docker-compose.yml` | Service definitions: engine, postgres, redis, prometheus |
| 0.14 | `docker-compose.override.yml` | Dev overrides: volume mounts, debug ports, hot reload |
| 0.15 | `.github/workflows/ci.yml` | CI pipeline: lint, type-check, test, build |
| 0.16 | `.github/workflows/security-scan.yml` | Security scan pipeline: bandit, pip-audit, safety |

---

## STEP 1 — Application Configuration (depended on by everything)

| # | File | Purpose |
|---|------|---------|
| 1.1 | `src/__init__.py` | Package marker |
| 1.2 | `src/engine/__init__.py` | Package marker |
| 1.3 | `src/engine/config.py` | **Pydantic Settings** — all config from env vars. DB URL, Redis URL, API keys (CFTC, NewsAPI, TwelveData, Yahoo Finance, Investing.com, DailyFX, Reuters), RSS feed URLs (Fed/ECB/BOE/BOJ/Bloomberg), polling intervals per source, analysis cycle interval. **Fail-fast** on missing required vars at startup. |

---

## STEP 2 — Shared Infrastructure (depends on: config only)

No shared module depends on any macro domain module. Implement in the sub-order below.

### 2A — Foundation (no internal shared deps)

| # | File | Purpose |
|---|------|---------|
| 2A.1 | `src/engine/shared/__init__.py` | Package marker |
| 2A.2 | `src/engine/shared/exceptions.py` | Base exception hierarchy: `ETradeBaseError`, `ProviderError`, `CollectorError`, `ProcessorError`, `StorageError`, `ConfigurationError`, `RateLimitError`, `TimeoutError` |
| 2A.3 | `src/engine/shared/logging/__init__.py` | Package marker + re-exports |
| 2A.4 | `src/engine/shared/logging/logger.py` | Structured JSON logger factory (structlog). Correlation ID injection, log level from config. |

### 2B — Observability (depends on: 2A)

| # | File | Purpose |
|---|------|---------|
| 2B.1 | `src/engine/shared/metrics/__init__.py` | Package marker + re-exports |
| 2B.2 | `src/engine/shared/metrics/prometheus.py` | Prometheus metric definitions: counters (provider_fetch_total, collector_run_total, processor_run_total), histograms (fetch_duration, processing_duration), gauges (active_providers, cache_hit_ratio) |
| 2B.3 | `src/engine/shared/tracing/__init__.py` | Package marker + re-exports |
| 2B.4 | `src/engine/shared/tracing/otel.py` | OpenTelemetry tracer setup — OTLP exporter, span creation helpers, context propagation |

### 2C — Shared Domain Models (depends on: 2A)

| # | File | Purpose |
|---|------|---------|
| 2C.1 | `src/engine/shared/models/__init__.py` | Package marker + re-exports |
| 2C.2 | `src/engine/shared/models/base.py` | Base Pydantic model with frozen config, JSON serialization, timestamp mixin |
| 2C.3 | `src/engine/shared/models/currency.py` | `Currency` enum (USD, EUR, GBP, JPY, CHF, AUD, CAD, NZD, etc.), `CurrencyPair` model, currency grouping/correlation maps |
| 2C.4 | `src/engine/shared/models/events.py` | `EventImpact` enum (HIGH, MEDIUM, LOW), `EventType` enum, `MacroBias` enum (BULLISH, BEARISH, NEUTRAL), `DataPriority` enum (CRITICAL, HIGH, MEDIUM), `TradingSession` enum |

### 2D — Infrastructure Clients (depends on: 2A, 2B, config)

| # | File | Purpose |
|---|------|---------|
| 2D.1 | `src/engine/shared/http/__init__.py` | Package marker + re-exports |
| 2D.2 | `src/engine/shared/http/client.py` | Resilient async HTTP client (aiohttp). Exponential backoff + jitter, configurable timeouts, rate limiting, circuit breaker, request/response logging, Prometheus latency tracking. |
| 2D.3 | `src/engine/shared/rss/__init__.py` | Package marker + re-exports |
| 2D.4 | `src/engine/shared/rss/parser.py` | Async RSS/Atom feed parser (feedparser + aiohttp). Deduplication by guid, entry timestamp normalization to UTC. |
| 2D.5 | `src/engine/shared/cache/__init__.py` | Package marker + re-exports |
| 2D.6 | `src/engine/shared/cache/redis_cache.py` | Async Redis cache (redis.asyncio). TTL-based get/set/invalidate, key namespacing per data source, JSON serialization, connection pool management. |
| 2D.7 | `src/engine/shared/db/__init__.py` | Package marker + re-exports |
| 2D.8 | `src/engine/shared/db/connection.py` | Async SQLAlchemy engine + session factory (asyncpg driver). Connection pooling, health check, session context manager. |
| 2D.9 | `src/engine/shared/db/repositories/__init__.py` | Package marker + re-exports |
| 2D.10 | `src/engine/shared/db/repositories/base_repository.py` | Generic async CRUD repository base class. Type-safe, session-scoped, with upsert, bulk insert, query builder helpers. |
| 2D.11 | `src/engine/shared/scheduler/__init__.py` | Package marker + re-exports |
| 2D.12 | `src/engine/shared/scheduler/apscheduler.py` | APScheduler async wrapper. Job registration by cron/interval, graceful shutdown, missed job handling, job execution metrics. |

### 2E — Database Migrations (depends on: 2D.8)

| # | File | Purpose |
|---|------|---------|
| 2E.1 | `src/engine/shared/db/migrations/env.py` | Alembic env — async engine binding, auto-import of all schemas |
| 2E.2 | `src/engine/shared/db/migrations/script.py.mako` | Alembic migration template |
| 2E.3 | `src/engine/shared/db/migrations/versions/.gitkeep` | Keep empty versions dir in git |

---

## STEP 3 — Macro Domain Models (depends on: STEP 2 shared models only)

All models are pure data definitions (Pydantic). No business logic, no I/O, no circular dependencies. Implement in sub-order.

### 3A — Provider Response Models (shapes of data coming FROM external APIs)

| # | File | Purpose |
|---|------|---------|
| 3A.0 | `src/engine/macro/__init__.py` | Package marker |
| 3A.1 | `src/engine/macro/models/__init__.py` | Package marker + re-exports |
| 3A.2 | `src/engine/macro/models/provider/__init__.py` | Package marker + re-exports |
| 3A.3 | `src/engine/macro/models/provider/central_bank.py` | `RateDecision`, `CentralBankSpeech`, `MeetingMinutes`, `ForwardGuidance` — normalized shapes from Fed/ECB/BOE/BOJ RSS |
| 3A.4 | `src/engine/macro/models/provider/cot.py` | `COTReport`, `COTPosition` — normalized CFTC data (non-commercial net, commercial net, open interest, week-over-week change) |
| 3A.5 | `src/engine/macro/models/provider/economic.py` | `EconomicRelease` — CPI, PPI, NFP, GDP, PMI, Retail Sales (actual, forecast, previous, surprise, impact level) |
| 3A.6 | `src/engine/macro/models/provider/news.py` | `NewsItem` — headline, source, timestamp, currencies mentioned, impact classification |
| 3A.7 | `src/engine/macro/models/provider/calendar.py` | `CalendarEvent` — event name, currency, impact level, datetime, actual/forecast/previous values |
| 3A.8 | `src/engine/macro/models/provider/market_data.py` | `IntermarketSnapshot` — DXY value, Gold, Oil, Bond yields, timestamp |

### 3B — Collector Output Models (aggregated data after collection from multiple providers)

| # | File | Purpose |
|---|------|---------|
| 3B.1 | `src/engine/macro/models/collector/__init__.py` | Package marker + re-exports |
| 3B.2 | `src/engine/macro/models/collector/central_bank.py` | `CentralBankDataSet` — aggregated CB events from all 4 bank feeds |
| 3B.3 | `src/engine/macro/models/collector/cot.py` | `COTDataSet` — latest + historical COT positions per currency |
| 3B.4 | `src/engine/macro/models/collector/economic.py` | `EconomicDataSet` — aggregated economic releases from all providers |
| 3B.5 | `src/engine/macro/models/collector/news.py` | `NewsDataSet` — deduplicated news items from all news providers |
| 3B.6 | `src/engine/macro/models/collector/calendar.py` | `CalendarDataSet` — merged economic calendar from all calendar providers |
| 3B.7 | `src/engine/macro/models/collector/market_data.py` | `MarketDataSet` — merged intermarket data from all market data providers |

### 3C — Processor Output Models (analyzed/scored data after processing)

| # | File | Purpose |
|---|------|---------|
| 3C.1 | `src/engine/macro/models/processor/__init__.py` | Package marker + re-exports |
| 3C.2 | `src/engine/macro/models/processor/interest_rate.py` | `InterestRateAnalysis` — rate differential per pair, hawkish/dovish tone score, directional signal |
| 3C.3 | `src/engine/macro/models/processor/economic_release.py` | `EconomicReleaseAnalysis` — beat/miss classification, trend direction, per-currency impact score |
| 3C.4 | `src/engine/macro/models/processor/cot.py` | `COTAnalysis` — net positioning direction, WoW change, extreme positioning flag, reversal risk |
| 3C.5 | `src/engine/macro/models/processor/news.py` | `NewsAnalysis` — sentiment score, risk-on/risk-off classification, currency impact map |
| 3C.6 | `src/engine/macro/models/processor/sentiment.py` | `SentimentAnalysis` — institutional sentiment per currency, positioning lean |
| 3C.7 | `src/engine/macro/models/processor/dxy.py` | `DXYAnalysis` — DXY trend direction, key levels, macro structure assessment, bias (BULLISH/BEARISH/NEUTRAL) |
| 3C.8 | `src/engine/macro/models/processor/intermarket.py` | `IntermarketAnalysis` — Gold/Oil/Bond correlation signals, risk sentiment indicator |
| 3C.9 | `src/engine/macro/models/processor/event_risk.py` | `EventRiskAssessment` — upcoming high-impact events within 48hrs, 30-min lockout windows, risk level |
| 3C.10 | `src/engine/macro/models/processor/currency_bias.py` | `CurrencyBiasScore` — per-currency directional score (BULLISH/BEARISH/NEUTRAL) with individual factor contributions |

### 3D — Final Output Model (the macro pipeline's deliverable)

| # | File | Purpose |
|---|------|---------|
| 3D.1 | `src/engine/macro/models/output/__init__.py` | Package marker + re-exports |
| 3D.2 | `src/engine/macro/models/output/macro_bias.py` | `MacroBiasOutput` — per-currency bias (BULLISH/BEARISH/NEUTRAL), evidence chain, DXY conclusion, COT signal, event risk flags, run timestamp, data snapshot IDs. This is the final output of the macro sub-module consumed by the analysis pipeline. |

---

## STEP 4 — Storage Layer (depends on: STEP 2 shared/db + STEP 3 models)

### 4A — SQLAlchemy ORM Schemas (DB table definitions)

| # | File | Purpose |
|---|------|---------|
| 4A.1 | `src/engine/macro/storage/__init__.py` | Package marker |
| 4A.2 | `src/engine/macro/storage/schemas/__init__.py` | Package marker + re-exports + declarative Base import |
| 4A.3 | `src/engine/macro/storage/schemas/central_bank.py` | `CentralBankEventRow` — rate decisions, speeches, meeting minutes. Columns: id, bank, event_type, content, tone_score, timestamp, created_at |
| 4A.4 | `src/engine/macro/storage/schemas/cot.py` | `COTReportRow` — weekly COT snapshots. Columns: id, currency, non_commercial_net, commercial_net, open_interest, wow_change, extreme_flag, report_date, created_at |
| 4A.5 | `src/engine/macro/storage/schemas/economic.py` | `EconomicReleaseRow` — macro releases. Columns: id, currency, indicator, actual, forecast, previous, surprise, impact, release_time, created_at |
| 4A.6 | `src/engine/macro/storage/schemas/news.py` | `NewsItemRow` — high-impact news items. Columns: id, headline, source, currencies, sentiment, impact, published_at, created_at. Dedupe key: source+headline hash |
| 4A.7 | `src/engine/macro/storage/schemas/calendar.py` | `CalendarEventRow` — economic calendar. Columns: id, event_name, currency, impact, event_time, actual, forecast, previous, created_at |
| 4A.8 | `src/engine/macro/storage/schemas/dxy.py` | `DXYSnapshotRow` — DXY values and analysis. Columns: id, value, trend_direction, key_levels_json, bias, analyzed_at, created_at |
| 4A.9 | `src/engine/macro/storage/schemas/intermarket.py` | `IntermarketSnapshotRow` — Gold, Oil, Bonds. Columns: id, gold_price, oil_price, us10y_yield, dxy_value, correlation_signals_json, snapshot_at, created_at |
| 4A.10 | `src/engine/macro/storage/schemas/macro_output.py` | `MacroBiasOutputRow` — final processed output per run. Columns: id, run_id, currency, bias, score, evidence_chain_json, dxy_bias, cot_signal_json, event_risks_json, data_snapshot_ids_json, created_at |

### 4B — Repositories (async CRUD — one per schema domain)

| # | File | Purpose |
|---|------|---------|
| 4B.1 | `src/engine/macro/storage/repositories/__init__.py` | Package marker + re-exports |
| 4B.2 | `src/engine/macro/storage/repositories/central_bank/__init__.py` | Package marker |
| 4B.3 | `src/engine/macro/storage/repositories/central_bank/event.py` | `CentralBankRepository` — upsert events, query by bank/date range, get latest per bank |
| 4B.4 | `src/engine/macro/storage/repositories/cot/__init__.py` | Package marker |
| 4B.5 | `src/engine/macro/storage/repositories/cot/report.py` | `COTRepository` — store weekly reports, get latest per currency, get WoW comparison, detect extremes |
| 4B.6 | `src/engine/macro/storage/repositories/economic/__init__.py` | Package marker |
| 4B.7 | `src/engine/macro/storage/repositories/economic/release.py` | `EconomicReleaseRepository` — store releases, query by currency/indicator/date, get latest per indicator |
| 4B.8 | `src/engine/macro/storage/repositories/news/__init__.py` | Package marker |
| 4B.9 | `src/engine/macro/storage/repositories/news/item.py` | `NewsRepository` — store items with dedupe, query recent by currency/impact, purge stale items |
| 4B.10 | `src/engine/macro/storage/repositories/calendar/__init__.py` | Package marker |
| 4B.11 | `src/engine/macro/storage/repositories/calendar/event.py` | `CalendarRepository` — store events, query upcoming within window, flag high-impact within 30min |
| 4B.12 | `src/engine/macro/storage/repositories/dxy/__init__.py` | Package marker |
| 4B.13 | `src/engine/macro/storage/repositories/dxy/snapshot.py` | `DXYRepository` — store snapshots, get latest, get historical for trend calculation |
| 4B.14 | `src/engine/macro/storage/repositories/intermarket/__init__.py` | Package marker |
| 4B.15 | `src/engine/macro/storage/repositories/intermarket/snapshot.py` | `IntermarketRepository` — store snapshots, get latest, get daily history for correlation |
| 4B.16 | `src/engine/macro/storage/repositories/macro/__init__.py` | Package marker |
| 4B.17 | `src/engine/macro/storage/repositories/macro/output.py` | `MacroBiasOutputRepository` — store final outputs per run, query by run_id/currency/date range |

### 4C — Initial Migration

| # | File | Purpose |
|---|------|---------|
| 4C.1 | `src/engine/shared/db/migrations/versions/0001_initial_macro_schema.py` | Alembic migration — creates all macro tables defined in 4A with indexes, constraints, and foreign keys |

---

## STEP 5 — Providers (depends on: STEP 2 shared/http + shared/rss + shared/cache + STEP 3A provider models)

Providers are **API-only clients** — one per external data source. Each category has an abstract base defining the interface, then concrete implementations.

### 5A — Provider Abstraction Layer

| # | File | Purpose |
|---|------|---------|
| 5A.1 | `src/engine/macro/providers/__init__.py` | Package marker |
| 5A.2 | `src/engine/macro/providers/base.py` | `BaseProvider` ABC — `async fetch()`, `async health_check()`, rate limit tracking, retry config, timeout config, metrics instrumentation. All providers implement this. |

### 5B — Central Bank Providers (event-driven, poll every 5–15 min)

| # | File | Purpose |
|---|------|---------|
| 5B.1 | `src/engine/macro/providers/central_bank/__init__.py` | Package marker + re-exports |
| 5B.2 | `src/engine/macro/providers/central_bank/base.py` | `BaseCentralBankProvider(BaseProvider)` — shared RSS parsing, tone extraction, event classification for CB feeds |
| 5B.3 | `src/engine/macro/providers/central_bank/fed_rss.py` | `FedRSSProvider` — Federal Reserve RSS feed (rate decisions, speeches, FOMC minutes, forward guidance) |
| 5B.4 | `src/engine/macro/providers/central_bank/ecb_rss.py` | `ECBRSSProvider` — European Central Bank RSS feed |
| 5B.5 | `src/engine/macro/providers/central_bank/boe_rss.py` | `BOERSSProvider` — Bank of England RSS feed |
| 5B.6 | `src/engine/macro/providers/central_bank/boj_rss.py` | `BOJRSSProvider` — Bank of Japan RSS feed |

### 5C — COT Provider (weekly, Fridays)

| # | File | Purpose |
|---|------|---------|
| 5C.1 | `src/engine/macro/providers/cot/__init__.py` | Package marker + re-exports |
| 5C.2 | `src/engine/macro/providers/cot/base.py` | `BaseCOTProvider(BaseProvider)` — shared COT parsing, non-commercial extraction, extreme detection |
| 5C.3 | `src/engine/macro/providers/cot/cftc.py` | `CFTCProvider` — CFTC.gov official API for Commitments of Traders data |

### 5D — Economic Data Providers (event-driven, poll every 15–60 min)

| # | File | Purpose |
|---|------|---------|
| 5D.1 | `src/engine/macro/providers/economic_data/__init__.py` | Package marker + re-exports |
| 5D.2 | `src/engine/macro/providers/economic_data/base.py` | `BaseEconomicDataProvider(BaseProvider)` — shared release parsing, surprise calc, impact classification |
| 5D.3 | `src/engine/macro/providers/economic_data/forex_factory.py` | `ForexFactoryProvider` — Forex Factory **API** for CPI, PPI, NFP, GDP, PMI, Retail Sales |
| 5D.4 | `src/engine/macro/providers/economic_data/investing_com.py` | `InvestingComProvider` — Investing.com **API** for economic indicator releases |

### 5E — Market Data Providers (DXY every 4H, intermarket daily)

| # | File | Purpose |
|---|------|---------|
| 5E.1 | `src/engine/macro/providers/market_data/__init__.py` | Package marker + re-exports |
| 5E.2 | `src/engine/macro/providers/market_data/base.py` | `BaseMarketDataProvider(BaseProvider)` — shared OHLCV normalization, DXY calculation from constituent pairs |
| 5E.3 | `src/engine/macro/providers/market_data/twelve_data.py` | `TwelveDataProvider` — Twelve Data REST API for DXY, forex, metals, indices OHLCV |
| 5E.4 | `src/engine/macro/providers/market_data/yahoo_finance.py` | `YahooFinanceProvider` — Yahoo Finance API for Gold, Oil, Bond yields, DXY backup |

### 5F — Economic Calendar Providers (every cycle, more frequent near events)

| # | File | Purpose |
|---|------|---------|
| 5F.1 | `src/engine/macro/providers/calendar/__init__.py` | Package marker + re-exports |
| 5F.2 | `src/engine/macro/providers/calendar/base.py` | `BaseCalendarProvider(BaseProvider)` — shared event normalization, impact level mapping, deduplication |
| 5F.3 | `src/engine/macro/providers/calendar/forex_factory.py` | `ForexFactoryCalendarProvider` — Forex Factory **API** for economic calendar events |
| 5F.4 | `src/engine/macro/providers/calendar/investing_com.py` | `InvestingComCalendarProvider` — Investing.com **API** for economic calendar events |

### 5G — News Providers (every 15–30 min)

| # | File | Purpose |
|---|------|---------|
| 5G.1 | `src/engine/macro/providers/news/__init__.py` | Package marker + re-exports |
| 5G.2 | `src/engine/macro/providers/news/base.py` | `BaseNewsProvider(BaseProvider)` — shared headline parsing, currency extraction, impact classification |
| 5G.3 | `src/engine/macro/providers/news/newsapi.py` | `NewsAPIProvider` — NewsAPI REST API for geopolitical events and breaking news |
| 5G.4 | `src/engine/macro/providers/news/reuters_rss.py` | `ReutersRSSProvider` — Reuters RSS feed for financial news |
| 5G.5 | `src/engine/macro/providers/news/bloomberg_rss.py` | `BloombergRSSProvider` — Bloomberg RSS feed for market-moving news |

### 5H — Sentiment Providers (weekly)

| # | File | Purpose |
|---|------|---------|
| 5H.1 | `src/engine/macro/providers/sentiment/__init__.py` | Package marker + re-exports |
| 5H.2 | `src/engine/macro/providers/sentiment/base.py` | `BaseSentimentProvider(BaseProvider)` — shared positioning normalization, directional scoring |
| 5H.3 | `src/engine/macro/providers/sentiment/dailyfx.py` | `DailyFXProvider` — DailyFX API for institutional sentiment and SSI data |
| 5H.4 | `src/engine/macro/providers/sentiment/reuters.py` | `ReutersSentimentProvider` — Reuters API for positioning and sentiment data |

### 5I — Provider Registry (depends on ALL providers above)

| # | File | Purpose |
|---|------|---------|
| 5I.1 | `src/engine/macro/providers/registry.py` | `ProviderRegistry` — registers all concrete providers by category, resolves by type, provides health check aggregation, supports runtime enable/disable per provider. Central lookup for collectors. |

---

## STEP 6 — Collectors (depends on: STEP 5 providers + STEP 4 repositories + STEP 3B collector models)

Collectors orchestrate: fetch from providers → normalize → deduplicate → persist to DB → cache latest snapshot. Each collector handles one data domain using one or more providers.

| # | File | Purpose |
|---|------|---------|
| 6.1 | `src/engine/macro/collectors/__init__.py` | Package marker + re-exports |
| 6.2 | `src/engine/macro/collectors/base.py` | `BaseCollector` ABC — `async collect()`, provider failover (try primary, fall back to secondary), deduplication, persistence, caching, metrics, logging. All collectors implement this. |
| 6.3 | `src/engine/macro/collectors/central_bank/collector.py` | `CentralBankCollector` — collects from all 4 CB RSS providers, deduplicates, stores high-impact events. Poll: every 5–15 min. |
| 6.4 | `src/engine/macro/collectors/central_bank/__init__.py` | Package marker |
| 6.5 | `src/engine/macro/collectors/cot/collector.py` | `COTCollector` — collects from CFTC provider, stores weekly reports. Poll: weekly (Fridays). |
| 6.6 | `src/engine/macro/collectors/cot/__init__.py` | Package marker |
| 6.7 | `src/engine/macro/collectors/economic_data/collector.py` | `EconomicDataCollector` — collects from forex_factory + investing_com providers, merges, stores. Poll: every 15–60 min. |
| 6.8 | `src/engine/macro/collectors/economic_data/__init__.py` | Package marker |
| 6.9 | `src/engine/macro/collectors/news/collector.py` | `NewsCollector` — collects from newsapi + reuters + bloomberg, deduplicates by headline hash, stores. Poll: every 15–30 min. |
| 6.10 | `src/engine/macro/collectors/news/__init__.py` | Package marker |
| 6.11 | `src/engine/macro/collectors/calendar/collector.py` | `CalendarCollector` — collects from forex_factory + investing_com calendar APIs, merges, stores. Poll: every 15–60 min (increases near event times). |
| 6.12 | `src/engine/macro/collectors/calendar/__init__.py` | Package marker |
| 6.13 | `src/engine/macro/collectors/dxy/collector.py` | `DXYCollector` — collects DXY data from twelve_data (primary) + yahoo_finance (fallback), stores snapshots. Poll: every 4H. |
| 6.14 | `src/engine/macro/collectors/dxy/__init__.py` | Package marker |
| 6.15 | `src/engine/macro/collectors/intermarket/collector.py` | `IntermarketCollector` — collects Gold, Oil, Bond yields from yahoo_finance + twelve_data, stores. Poll: daily. |
| 6.16 | `src/engine/macro/collectors/intermarket/__init__.py` | Package marker |
| 6.17 | `src/engine/macro/collectors/sentiment/collector.py` | `SentimentCollector` — collects from dailyfx + reuters sentiment, merges positioning data. Poll: weekly. |
| 6.18 | `src/engine/macro/collectors/sentiment/__init__.py` | Package marker |

---

## STEP 7 — Processors (depends on: STEP 4 repositories + STEP 3C processor models)

Processors read cached/stored data and produce analyzed outputs. Implement in strict sub-order below — later processors depend on earlier ones' output models. **Processors read from DB, not directly from collectors.**

### 7A — Independent Processors (depend only on repositories + their own models)

| # | File | Purpose |
|---|------|---------|
| 7A.1 | `src/engine/macro/processors/__init__.py` | Package marker + re-exports |
| 7A.2 | `src/engine/macro/processors/base.py` | `BaseProcessor` ABC — `async process()`, reads from repository, produces typed analysis output, metrics, tracing. All processors implement this. |
| 7A.3 | `src/engine/macro/processors/interest_rate/__init__.py` | Package marker |
| 7A.4 | `src/engine/macro/processors/interest_rate/analyzer.py` | `InterestRateProcessor` — reads CB events from repo, calculates rate differentials per pair, classifies hawkish/dovish tone, outputs `InterestRateAnalysis` |
| 7A.5 | `src/engine/macro/processors/economic_release/__init__.py` | Package marker |
| 7A.6 | `src/engine/macro/processors/economic_release/analyzer.py` | `EconomicReleaseProcessor` — reads economic releases, classifies beat/miss/inline, identifies trend direction per indicator per currency, outputs `EconomicReleaseAnalysis` |
| 7A.7 | `src/engine/macro/processors/cot/__init__.py` | Package marker |
| 7A.8 | `src/engine/macro/processors/cot/analyzer.py` | `COTProcessor` — reads COT reports, calculates net positioning + WoW change, flags extremes (multi-year high/low), outputs `COTAnalysis` |
| 7A.9 | `src/engine/macro/processors/news/__init__.py` | Package marker |
| 7A.10 | `src/engine/macro/processors/news/scorer.py` | `NewsProcessor` — reads news items, scores sentiment per currency, classifies risk-on/risk-off, outputs `NewsAnalysis` |
| 7A.11 | `src/engine/macro/processors/sentiment/__init__.py` | Package marker |
| 7A.12 | `src/engine/macro/processors/sentiment/analyzer.py` | `SentimentProcessor` — reads institutional sentiment data, determines positioning lean per currency, outputs `SentimentAnalysis` |
| 7A.13 | `src/engine/macro/processors/dxy/__init__.py` | Package marker |
| 7A.14 | `src/engine/macro/processors/dxy/analyzer.py` | `DXYProcessor` — reads DXY snapshots, determines trend direction, key support/resistance levels, macro structure, outputs `DXYAnalysis`. **Runs first on every cycle — its output feeds into USD pair bias.** |
| 7A.15 | `src/engine/macro/processors/intermarket/__init__.py` | Package marker |
| 7A.16 | `src/engine/macro/processors/intermarket/analyzer.py` | `IntermarketProcessor` — reads intermarket snapshots, calculates Gold/Oil/Bond correlations, determines risk sentiment, outputs `IntermarketAnalysis` |
| 7A.17 | `src/engine/macro/processors/event_risk/__init__.py` | Package marker |
| 7A.18 | `src/engine/macro/processors/event_risk/classifier.py` | `EventRiskProcessor` — reads calendar events, identifies high-impact events within 48hrs, flags 30-min lockout windows, outputs `EventRiskAssessment` |

### 7B — Composite Processor (depends on: ALL 7A processor outputs)

| # | File | Purpose |
|---|------|---------|
| 7B.1 | `src/engine/macro/processors/currency_bias/__init__.py` | Package marker |
| 7B.2 | `src/engine/macro/processors/currency_bias/scorer.py` | `CurrencyBiasProcessor` — takes all individual analyses (interest rate, economic, COT, news, sentiment, DXY, intermarket, event risk), applies spec-defined weights (Section 4.1), produces per-currency `CurrencyBiasScore` (BULLISH/BEARISH/NEUTRAL with evidence chain). DXY bias is mandatory input for all USD pairs. |

### 7C — Final Aggregator (depends on: 7B currency bias output)

| # | File | Purpose |
|---|------|---------|
| 7C.1 | `src/engine/macro/processors/aggregator/__init__.py` | Package marker |
| 7C.2 | `src/engine/macro/processors/aggregator/aggregator.py` | `MacroBiasAggregator` — takes all `CurrencyBiasScore` outputs, packages into final `MacroBiasOutput` with complete evidence chain, snapshot IDs, DXY conclusion, COT signal summary, event risk flags. Persists to `MacroBiasOutputRepository`. This is the deliverable of the entire macro sub-module. |

---

## STEP 8 — Pipeline Orchestration (depends on: STEP 6 collectors + STEP 7 processors)

| # | File | Purpose |
|---|------|---------|
| 8.1 | `src/engine/macro/pipeline.py` | `MacroPipeline` — orchestrates the full macro analysis cycle: (1) trigger collectors in parallel by data source, (2) run DXY processor first, (3) run all other processors in parallel, (4) run currency bias scorer, (5) run aggregator, (6) persist output, (7) return `MacroBiasOutput`. Metrics for full cycle duration, per-step duration, failures. |

---

## STEP 9 — API Layer (depends on: STEP 8 pipeline + STEP 4 repositories)

| # | File | Purpose |
|---|------|---------|
| 9.1 | `src/engine/macro/router.py` | FastAPI router — endpoints: `GET /macro/bias/latest` (last run output), `GET /macro/bias/history` (historical runs), `GET /macro/health` (provider/collector health), `POST /macro/trigger` (manual cycle trigger), `GET /macro/providers/status` (provider status/health). All responses typed with Pydantic models. |
| 9.2 | `src/engine/macro/scheduler_jobs.py` | Job definitions for APScheduler: per-source collector schedules (CB RSS every 10min, News every 15min, Calendar every 30min, COT weekly Friday, DXY every 4H, Intermarket daily, Sentiment weekly), analysis cycle trigger (every 4H aligned to candle close). |

---

## STEP 10 — Application Bootstrap (depends on: ALL above)

| # | File | Purpose |
|---|------|---------|
| 10.1 | `src/engine/dependencies.py` | Dependency injection container — constructs and wires: DB session, Redis cache, all providers, provider registry, all collectors, all repositories, all processors, pipeline, scheduler. FastAPI `Depends()` integration. |
| 10.2 | `src/engine/main.py` | FastAPI application factory — startup (DB connection, cache warmup, scheduler start, migration check, health probe registration, metrics endpoint `/metrics`), shutdown (graceful scheduler stop, connection cleanup), router mounting, middleware (CORS, request ID, structured logging). |

---

## STEP 11 — Tests (depends on: ALL above — implement alongside each step)

### 11A — Test Fixtures

| # | File | Purpose |
|---|------|---------|
| 11A.1 | `tests/__init__.py` | Package marker |
| 11A.2 | `tests/engine/__init__.py` | Package marker |
| 11A.3 | `tests/engine/macro/__init__.py` | Package marker |
| 11A.4 | `tests/engine/macro/conftest.py` | Shared pytest fixtures: async DB session, mock Redis, mock HTTP client, test config, factory helpers |
| 11A.5 | `tests/engine/macro/fixtures/calendar_sample.json` | Sample calendar API response data |
| 11A.6 | `tests/engine/macro/fixtures/cb_rss_sample.xml` | Sample central bank RSS feed XML |
| 11A.7 | `tests/engine/macro/fixtures/cot_sample.json` | Sample CFTC COT API response |
| 11A.8 | `tests/engine/macro/fixtures/news_sample.json` | Sample NewsAPI response data |

### 11B — Unit Tests

| # | File | Purpose |
|---|------|---------|
| 11B.1 | `tests/engine/macro/unit/__init__.py` | Package marker |
| 11B.2 | `tests/engine/macro/unit/providers/__init__.py` | Package marker |
| 11B.3 | `tests/engine/macro/unit/providers/test_base_provider.py` | Tests for `BaseProvider` — retry logic, timeout handling, rate limiting, metrics emission |
| 11B.4 | `tests/engine/macro/unit/providers/test_provider_registry.py` | Tests for `ProviderRegistry` — registration, resolution, health aggregation, enable/disable |
| 11B.5 | `tests/engine/macro/unit/processors/__init__.py` | Package marker |
| 11B.6 | `tests/engine/macro/unit/processors/test_cot_analyzer.py` | Tests for `COTProcessor` — positioning calc, WoW change, extreme detection, reversal flagging |
| 11B.7 | `tests/engine/macro/unit/processors/test_dxy_analyzer.py` | Tests for `DXYProcessor` — trend direction, key levels, bias determination |
| 11B.8 | `tests/engine/macro/unit/processors/test_currency_bias_scorer.py` | Tests for `CurrencyBiasProcessor` — weight application, evidence chain, DXY integration |
| 11B.9 | `tests/engine/macro/unit/processors/test_event_risk_classifier.py` | Tests for `EventRiskProcessor` — lockout window calculation, high-impact classification |
| 11B.10 | `tests/engine/macro/unit/processors/test_macro_bias_aggregator.py` | Tests for `MacroBiasAggregator` — final output assembly, snapshot IDs, evidence completeness |

### 11C — Integration Tests

| # | File | Purpose |
|---|------|---------|
| 11C.1 | `tests/engine/macro/integration/__init__.py` | Package marker |
| 11C.2 | `tests/engine/macro/integration/test_collectors.py` | Integration tests: collector → mock provider → DB persistence, failover behavior, deduplication |
| 11C.3 | `tests/engine/macro/integration/test_pipeline.py` | Integration tests: full pipeline cycle — collectors → processors → aggregator → final output, end-to-end data flow |
| 11C.4 | `tests/engine/macro/integration/test_repositories.py` | Integration tests: repository CRUD against test PostgreSQL, upsert idempotency, query correctness |

---

## Dependency Graph Summary

```
STEP 0  Project Config
   ↓
STEP 1  Application Config (config.py)
   ↓
STEP 2  Shared Infrastructure (exceptions → logging → metrics/tracing → models → http/rss/cache/db/scheduler)
   ↓
STEP 3  Macro Domain Models (provider → collector → processor → output)
   ↓
STEP 4  Storage Layer (schemas → repositories → migration)
   ↓
STEP 5  Providers (base → category bases → concrete impls → registry)
   ↓
STEP 6  Collectors (base → 8 concrete collectors)
   ↓
STEP 7  Processors (base → 8 independent processors → currency_bias → aggregator)
   ↓
STEP 8  Pipeline (orchestrates collectors + processors)
   ↓
STEP 9  API + Scheduler Jobs (exposes pipeline via REST + schedules)
   ↓
STEP 10 Application Bootstrap (DI wiring + FastAPI app)
   ↓
STEP 11 Tests (parallel with each step above)
```

> [!CAUTION]
> **Circular import prevention**: Arrows go DOWN only. No file may import from a file in a later step. Models (STEP 3) never import from providers/collectors/processors. Storage (STEP 4) imports only from shared + models. Providers (STEP 5) import from shared + provider models only. Collectors (STEP 6) import from providers + collector models + repositories. Processors (STEP 7) import from repositories + processor models only. Pipeline (STEP 8) imports from collectors + processors. API (STEP 9) imports from pipeline + models.
