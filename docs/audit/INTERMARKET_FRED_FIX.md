# Intermarket / DXY data source fix

## Problem (operator-confirmed)

The DXY and intermarket collectors' only providers were:
  - `TwelveDataProvider` (macro), using tickers like USDX/US02Y/SPX/VIX/CL/HG/NG
    that the configured TwelveData plan does not serve, and a multi-symbol
    response-parse shape that did not match single-symbol responses; and
  - `CommodityProxyProvider`, scraping iron-ore/dairy HTML with loose regexes.

Neither returned data in production. Result: `dxy_value`, the 2/10/30y yields,
`vix`, `sp500`, and the commodity fields were all None -- so the DXY collector's
momentum/trend/bias defaulted to FLAT/NEUTRAL and the risk-environment
yield-curve + VIX inputs were empty. DXY and intermarket were effectively dead.

## Fix

Added `FREDIntermarketProvider`, using the same FRED API + `observations[].value`
shape the central-bank rate providers already use reliably (operator-verified
that DGS10/VIXCLS/DTWEXBGS return clean JSON). Series:

| Field | FRED series |
|-------|-------------|
| dxy_value | DTWEXBGS (broad USD index) |
| us2y_yield | DGS2 |
| us10y_yield | DGS10 |
| us30y_yield | DGS30 |
| vix | VIXCLS |
| sp500 | SP500 |
| oil_price | DCOILWTICO (WTI) |

Wired into BOTH the DXY and intermarket collectors. Deleted the dead
TwelveDataProvider + CommodityProxyProvider and their commodity-proxy config.

The SEPARATE TwelveData CANDLE client (engine.ta.broker.twelve_data, used as a
TA broker fallback) is untouched -- different object, still uses the retained
twelvedata_* config.

## Gold/silver source (Yahoo) + trend signals

- Gold/silver come from `YahooMetalsProvider` (Yahoo Finance chart API, GC=F/SI=F,
  operator-verified). Best-effort: an unofficial endpoint, so a Yahoo outage
  leaves gold/silver None without affecting the FRED-sourced fields. Merged with
  the FRED snapshot via the collector's _merge_snapshots.
- Trend signals (direction + change) were added for the three fields whose
  trajectory is a genuine risk signal -- VIX, US 10Y yield, gold -- computed
  against the previous stored snapshot and emitted in correlation_signals
  (vix_trend/vix_change, us10y_trend/us10y_change_bps, gold_trend/gold_change_pct).
  DXY (already trended in its own collector), S&P/oil/silver/gas and the monthly
  iron-ore/copper are intentionally not trended. They reach the LLM via the
  opaque intermarket map (no gateway change needed).

## Limitations / not-guessed

- gold, silver, copper, natural gas, iron ore, dairy are left None: no verified
  FRED series for these yet. They are nullable on IntermarketSnapshot and will
  be wired once a working source is confirmed -- not guessed.
- DTWEXBGS is the BROAD trade-weighted dollar index (~119), not the ICE DXY
  futures level (~104). The DXY collector derives momentum/trend/bias from
  RELATIVE change, so direction is correct regardless of absolute scale.

## Other audit findings addressed in this MR

### Finding F (HIGH) -- FIXED: dashboard rerun signal drift
signal_extractors.derive_macro_signals (used by /api/analysis/rerun) had drifted
from the Go gateway's extractCentralBank: it only handled FED/ECB tone and
conflated rate presence with rate change. Aligned it -- all eight bank tones via
a clobber-safe <bank>_tone setter, a distinct has_rate_change (nonzero bps,
newest-per-bank direction), plus rate_change_bank/direction -- and made the
rerun RAG call + query-text OR has_rate_change into has_rate_decision and emit
the "{bank} rate {direction}" term, exactly as the gateway builder does. The
rerun now produces the same RAG query as the live pipeline.

### Finding C (LOW) -- FIXED: OECD quarterly date parsing
OECD quarterly periods (YYYY-Qn, e.g. GDP) failed ISO parsing and fell back to
now(UTC). Added explicit YYYY-Qn -> quarter-start-month handling.

### Finding D (LOW) -- FIXED: removed uncalled repo read-methods
Verified every runtime consumer (collectors, analysis router, gateway news
guard, retention pruner, helpers, health/admin) -- zero callers. Removed:
  - COTRepository: get_latest_by_currency, get_latest_all_currencies,
    get_wow_pair, get_history (kept get_previous_net, get_52_week_net_range).
  - DXYRepository: get_history, get_daily_history
    (kept get_latest, get_recent_values, upsert_snapshot).
  - IntermarketRepository: get_daily_history (kept get_latest, upsert_snapshot).
  - CalendarRepository: get_upcoming, get_high_impact_within_window,
    get_by_currency (now write-only via bulk_upsert).
  - SentimentRepository: get_latest_by_currency, get_all_latest (write-only).
Unused imports cleaned in each file. Matches the 2026-05 economic-repo cleanup.
If CI surfaces a test referencing a removed method, that test covered dead code
and should be removed with it.
