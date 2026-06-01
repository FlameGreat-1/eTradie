# Fed Rate Decision Data Fix

## Problem (verified, not assumed)

The `CentralBankDataSet` exposes a `rate_decisions: list[RateDecision]` field,
and `RateDecision` carries the structured numeric policy rate:

```python
class RateDecision(TimestampedModel):
    bank: CentralBank
    rate_current: float       # actual rate level, e.g. 3.75
    rate_previous: float      # prior level, e.g. 4.00
    rate_change_bps: int      # bps change, e.g. -25
    decision_date: datetime
```

The collector (`central_bank/collector.py`) already categorizes `RateDecision`
events and persists `rate_current` / `rate_previous`, and the gateway
(`collectors/macro_collector.go`) forwards the central-bank dataset to the LLM
as an opaque map. **But no provider ever produced a `RateDecision`.**

Every wired central-bank provider is RSS-based (`fed_rss.py` and siblings).
`BaseCentralBankProvider._parse_entry` only ever returns `ForwardGuidance`,
`MeetingMinutes`, or `CentralBankSpeech` -- even when `classify_event_type`
returns `RATE_DECISION` (that case falls through to `CentralBankSpeech`). An
RSS *headline* cannot carry the numeric rate, so:

- `isinstance(event, RateDecision)` in the collector was always False;
- `rate_decisions` was always `[]`;
- `rate_current` / `rate_previous` / `rate_change_bps` were always empty.

The LLM therefore received Fed **tone** (HAWKISH/DOVISH/NEUTRAL, keyword-matched
from the headline) and QE/QT, but **never the actual interest-rate number** --
the single most important macro data point. The rate fields, the `RateDecision`
model, and the collector's rate-decision branch were effectively dead code.

## Fix

Added a reusable `BaseFREDRateProvider` (`providers/central_bank/fed_rate.py`)
sourcing the authoritative machine-readable policy rate the central banks
publish via FRED, with two concrete providers:

- `FedRateProvider` -- US Fed funds target *range*: `DFEDTARU` (upper limit /
  headline ceiling) + `DFEDTARL` (lower limit, logged for context).
- `ECBRateProvider` -- ECB Deposit Facility Rate `ECBDFR` (the EUR policy rate
  markets watch; no range, so no lower series).

These daily series only step on a policy decision, so each level transition IS
a real decision. The provider fetches ~4 years (1500 daily obs), compresses the
series to its distinct level transitions, and emits ONE `RateDecision` per
decision, ordered newest-first. So `rate_decisions` now carries the full
hiking/cutting *trajectory* (e.g. 0.25 -> 5.50 across 2022-23, then cuts to
3.75), with element 0 being the current rate. The LLM can reason about where
we are in the cycle, and -- with both Fed and ECB present -- about the Fed-ECB
differential that drives EURUSD.

Wired into the `CentralBankCollector` provider list in `dependencies.py`
(reusing the existing `fred_api_key` / `fred_base_url` settings). No
model/dataset/migration/collector/gateway/prompt changes were required -- the
existing `RateDecision` categorization, the DB upsert (deduped per
`decision_date`), the cache/snapshot durability, and the gateway's opaque
forwarding of `macro_analysis` (serialised generically in
`processor/prompts/system_prompt.py::build_user_message`) all carry the full
series to the LLM unchanged.

## Scope / limitations

- Fed + ECB only. Other central banks have no equivalent free structured
  target-rate series on FRED, so they keep providing tone/QE-QT from RSS.
- When the FRED key is unset or a series is unavailable, that provider returns
  no decisions (non-fatal): the tone-only signal remains intact.
- The oldest level in the lookback window is anchored with
  `rate_previous == rate_current` and `0` bps (no prior reference inside the
  window), so the LLM always has the earliest level in the series.
- EFFR (NY Fed effective rate) was deliberately NOT added: it is a lagging
  daily average that only moves with the target range and carries no
  independent tradeable signal between FOMC decisions. The target range is the
  correct rate datum for the platform.
