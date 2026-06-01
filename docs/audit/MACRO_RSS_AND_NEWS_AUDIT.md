# Macro RSS + news-protection audit (final sweep findings)

## Finding 11 (HIGH, latent) -- FIXED: RSSParser dropped entries across polls

`RSSParser` held an instance-level `_seen_guids` set and skipped any GUID seen
on a previous call. It is a single SHARED instance injected into all 8 central
bank RSS providers and the economic-calendar provider.

The RSS-backed collectors are point-in-time snapshot producers: each poll's
dataset/cache/durable-snapshot REPLACES the previous value. With cross-call
dedup, the 2nd+ scheduler polls returned only brand-new entries, so after the
feeds stabilised the central-bank tone/QE-QT and the calendar's
`high_impact_events` shrank toward empty and overwrote the good snapshot. The
set also leaked for the process lifetime, and `reset_seen()` was dead.

Fix: made `RSSParser` stateless -- each fetch returns the full current feed
(bounded by `max_entries`). Persistence dedup already lives where it belongs
(each collector upserts on a natural key). Removed the dead `reset_seen()`.

## Finding 10 (HIGH, trading safety) -- DATA-SOURCE GAP, tracked

The MANDATORY "no high-impact news within the lockout window" protection is
effectively INERT, for one reason: the data feed cannot supply scheduled
future event times.

Evidence (read in code, not assumed):
- `EvaluateNewsWindow` (gateway routing/news.go) only locks when
  `minutesUntil >= 0 && minutesUntil <= lockoutMinutes`, i.e. the event must be
  in the FUTURE within the window. This logic is correct and fails CLOSED when
  the calendar map is entirely absent.
- `InvestingRSSCalendarProvider._parse_entry` sets
  `event_time = entry.published_at`, and `RSSParser` sets `published_at` from
  the feed's `published_parsed` (the article PUBLISH time -- in the PAST for a
  news item). The provider has NO logic to extract a scheduled future event
  time.
- The configured feed is `INVESTING_CALENDAR_RSS_URL =
  https://www.investing.com/rss/news_285.rss`, which is a NEWS feed, not the
  structured economic calendar.

Net effect: events exist in the dataset but every `event_time` is in the past,
so `minutesUntil < 0` and the lockout NEVER fires from this feed. A trade could
be entered moments before an actual rate decision / NFP. The guard is present
and correct; the DATA driving it is wrong.

Why this is NOT patched in code here (honest scope):
- Faking a future `event_time` (e.g. shifting publish time forward) would be a
  guess and could WRONGLY block valid trades -- worse than the current state.
- The real remediation is a proper forward-looking economic-calendar data
  source with scheduled event timestamps (a structured calendar API, or the
  correct Investing.com economic-calendar export), plus parsing the scheduled
  time into `CalendarEvent.event_time`. That is a data-sourcing decision, not a
  safe code patch, so it is tracked here for an explicit owner decision rather
  than guessed.

Required remediation (for the owner):
1. Replace `INVESTING_CALENDAR_RSS_URL` with a feed/API that carries scheduled
   FUTURE event times (and ideally explicit impact + currency fields).
2. Update `InvestingRSSCalendarProvider` (or a new structured provider) to set
   `event_time` to the scheduled event time, not the article publish time.
3. Keep the gateway guard as-is -- it is correct and already fails closed on
   missing data.

Interim safety posture until then: the guard fails closed only when the
calendar dataset is ABSENT. Operators who want hard safety today can disable
the calendar collector (so calendar is nil -> guard locks out, fail-closed) or
accept that news lockout is not enforced. This trade-off must be an explicit
operator decision.
