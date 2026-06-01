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

Added `FedRateProvider` (`providers/central_bank/fed_rate.py`) sourcing the
authoritative machine-readable target rate the Fed publishes via FRED:

- `DFEDTARU` -- Federal Funds Target Range, Upper Limit (headline ceiling).
- `DFEDTARL` -- Federal Funds Target Range, Lower Limit.

These daily series only step on an FOMC decision, so the most recent change in
the upper-limit series IS the latest rate decision. The provider finds the two
most recent distinct levels and emits a single `RateDecision` with the current
rate, the previous rate, the bps change, and the effective decision date.

Wired into the `CentralBankCollector` provider list in `dependencies.py`
(reusing the existing `fred_api_key` / `fred_base_url` settings). No collector
or gateway changes were required -- the existing `RateDecision` categorization
and opaque gateway forwarding carry the data to the LLM unchanged.

## Scope / limitations

- US only. Other central banks have no equivalent free structured target-rate
  series, so they keep providing tone/QE-QT from RSS. (ECB rate could later be
  added from ECB SDW; out of scope here.)
- When the FRED key is unset or the series is unavailable, the provider returns
  no decision (non-fatal): the tone-only signal remains intact.
- A flat-rate window (no change in the lookback) reports the current level with
  `rate_change_bps = 0` so the LLM still receives the authoritative current
  rate.
