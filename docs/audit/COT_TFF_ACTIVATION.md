# COT TFF (Traders in Financial Futures) activation

## Problem (verified)

The COT stack carried a full TFF capability that was DEAD end to end:

- `cot_reports` has `leveraged_long/short/net` and `asset_manager_long/short/net`
  columns; `TFFPosition` / `COTDataSet.tff_positions` / `has_tff_data` exist;
  the collector merges TFF by currency into each row; the gateway extracts
  `has_tff_data`, sets the `HasTFFData` RAG flag, and emits
  "leveraged funds net" / "asset managers net" query-text signals.
- But the ONLY provider that produced TFF data was `CFTCProvider` (Socrata,
  `publicreporting.cftc.gov`), which was never wired AND whose host now returns
  403 for every request. The wired COT provider (`CFTCDEAProvider`, the
  futures-only HTML scraper) always returns `tff_positions=[]`.
- Net: `has_tff_data` was ALWAYS false; every TFF column/flag/signal was dead.

## Fix

- Deleted the dead Socrata `CFTCProvider` (`cftc.py`) and its orphaned config
  (`cftc_api_base_url`, `cftc_app_token`).
- Added `CFTCDEATFFProvider`, scraping the official DEA TFF report on the SAME
  working host the futures-only scraper uses:
  `https://www.cftc.gov/dea/futures/financial_lf.htm`.
  The flat-text "Positions" row carries 14 numbers in a fixed column order
  (Dealer L/S/Sp, Asset Manager L/S/Sp, Leveraged L/S/Sp, Other L/S/Sp,
  Nonreportable L/S); the parser maps Asset Manager (idx 3/4) and Leveraged
  (idx 6/7) to `TFFPosition`. Cross-rate contracts (`... XRATE`) are excluded
  so EUR is not mis-mapped. NZD is not published in the TFF report, so it has
  no TFF row (handled gracefully by the per-currency merge).
- `COTCollector` gained an optional `tff_provider`, fetched best-effort AFTER
  the proven legacy-position failover. A TFF failure falls back to the primary
  report's (empty) tff_positions, so the core COT signal is never degraded.

## Result

`has_tff_data` is now true in steady state; the `leveraged_*`/`asset_manager_*`
columns populate; and the gateway's `HasTFFData` RAG flag and the leveraged-
funds / asset-manager query-text signals fire. No model/schema/gateway changes
were needed -- the stack was complete except for a working producer.

Currencies covered by the TFF report: CAD, CHF, GBP, JPY, EUR, AUD, MXN
(+ BRL). NZD is not in the CFTC TFF report.
