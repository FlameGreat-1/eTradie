package routing

import (
	"fmt"
	"strings"
	"time"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder"
)

// Is247Market reports whether a symbol trades 24/7 (synthetics, crypto).
// These instruments have no fiat economic-calendar exposure, so the
// news guards skip them. This is the single definition used across the
// gateway; the execution service calls the gateway's CheckNewsWindow RPC
// rather than re-deriving this, so there is one source of truth.
func Is247Market(symbol string) bool {
	s := strings.ToUpper(symbol)
	return strings.Contains(s, "CRASH") ||
		strings.Contains(s, "BOOM") ||
		strings.Contains(s, "VOLATILITY") ||
		strings.Contains(s, "STEP") ||
		strings.Contains(s, "JUMP") ||
		strings.Contains(s, "BTC") ||
		strings.Contains(s, "ETH")
}

// ParseSymbolCurrencies returns the set of currency codes a symbol is
// exposed to. A high-impact event only locks a symbol out when the
// event's currency is one of these.
//
// Handles the instrument universe this system trades:
//   - Standard 6-char FX pairs (EURUSD -> EUR, USD).
//   - Metals quoted against a fiat (XAUUSD -> XAU, USD; XAGUSD -> XAG, USD),
//     which share the same 3+3 layout so the split is identical.
//
// Returns nil for 24/7 markets and for any symbol that does not match a
// recognised layout; callers treat a nil/empty result as "no fiat
// calendar exposure" and skip the news lockout. The match is exact and
// deterministic; no guessing.
func ParseSymbolCurrencies(symbol string) []string {
	if Is247Market(symbol) {
		return nil
	}
	s := strings.ToUpper(strings.TrimSpace(symbol))
	s = strings.ReplaceAll(s, "/", "")
	s = strings.ReplaceAll(s, "_", "")

	var base, quote string
	switch {
	case len(s) == 6:
		base, quote = s[0:3], s[3:6]
	case len(s) == 7 && (strings.HasPrefix(s, "XAU") || strings.HasPrefix(s, "XAG")):
		// Metals against a fiat may appear as a 7-char symbol; the
		// base is the 3-char metal code, mirroring engine parse_pair.
		base, quote = s[0:3], s[3:]
	default:
		return nil
	}

	if len(quote) != 3 {
		return nil
	}
	if base == quote {
		return []string{base}
	}
	return []string{base, quote}
}

// NewsWindowStatus is the result of a news-proximity evaluation.
type NewsWindowStatus struct {
	// Locked is true when a new entry / fill / fire must be blocked.
	Locked bool
	// DataAvailable is false when no calendar dataset was provided.
	// Callers decide policy; the gateway guards fail closed (treat
	// missing data as Locked) because trading blind into a possible
	// news event is the unsafe outcome.
	DataAvailable bool
	Reason        string
	EventName     string
	Currency      string
	MinutesUntil  float64
}

// LockoutMinutesForStyle returns the news lockout window for a trading
// style. Scalping uses a wider window because scalps cannot absorb a
// news spike; everything else uses the normal window. Style values are
// the gateway's single source; the execution rulebook constants
// (NewsLockoutMinutesNormal/Scalping) mirror these exact numbers.
func LockoutMinutesForStyle(tradingStyle string) int {
	if strings.EqualFold(strings.TrimSpace(tradingStyle), "SCALPING") {
		return constants.NewsLockoutMinutesScalping
	}
	return constants.NewsLockoutMinutesNormal
}

// EvaluateNewsWindow determines whether `symbol` must be locked out now
// because a HIGH-impact calendar event affecting one of its currencies
// activates within `lockoutMinutes`.
//
// calendar is the MacroResult.Calendar map (may be nil). now must be UTC.
// The evaluation is currency-scoped (N2): a USD event never locks out a
// pair that carries no USD leg. When calendar is nil the result is
// Locked with DataAvailable=false so callers can fail closed (N3).
//
// 24/7 markets and symbols with no fiat exposure are never locked.
func EvaluateNewsWindow(
	calendar map[string]interface{},
	symbol string,
	now time.Time,
	lockoutMinutes int,
) NewsWindowStatus {
	currencies := ParseSymbolCurrencies(symbol)
	if len(currencies) == 0 {
		// No fiat calendar exposure (24/7 or unrecognised layout):
		// nothing to lock out, and missing calendar data is irrelevant.
		return NewsWindowStatus{Locked: false, DataAvailable: true, Reason: "Symbol has no fiat calendar exposure"}
	}

	if calendar == nil {
		return NewsWindowStatus{
			Locked:        true,
			DataAvailable: false,
			Reason:        "Economic-calendar data unavailable; failing closed to avoid trading blind into news",
		}
	}

	relevant := make(map[string]struct{}, len(currencies))
	for _, c := range currencies {
		relevant[c] = struct{}{}
	}

	events := querybuilder.GetSliceOfMapsExported(calendar, "events")
	for _, event := range events {
		impact := strings.ToUpper(querybuilder.GetStrDefaultExported(event, "impact", ""))
		if impact != "HIGH" {
			continue
		}

		eventCurrency := strings.ToUpper(querybuilder.GetStrDefaultExported(event, "currency", ""))
		if _, ok := relevant[eventCurrency]; !ok {
			// Event affects a currency this symbol does not carry (N2).
			continue
		}

		eventTimeStr := querybuilder.GetStrDefaultExported(event, "event_time", "")
		if eventTimeStr == "" {
			continue
		}
		eventTime, ok := parseEventTime(eventTimeStr)
		if !ok {
			continue
		}

		minutesUntil := eventTime.Sub(now).Minutes()
		if minutesUntil >= 0 && minutesUntil <= float64(lockoutMinutes) {
			eventName := querybuilder.GetStrDefaultExported(event, "event_name", "unknown")
			return NewsWindowStatus{
				Locked:        true,
				DataAvailable: true,
				EventName:     eventName,
				Currency:      eventCurrency,
				MinutesUntil:  minutesUntil,
				Reason: fmt.Sprintf(
					"High-impact %s event '%s' in %d minutes (lockout: %dmin)",
					eventCurrency, eventName, int(minutesUntil), lockoutMinutes,
				),
			}
		}
	}

	return NewsWindowStatus{
		Locked:        false,
		DataAvailable: true,
		Reason:        "No high-impact events within lockout window",
	}
}

// parseEventTime parses a calendar event_time string. The collector
// serialises datetimes as RFC3339 (with a trailing Z); a naive
// (timezone-less) fallback is also accepted and interpreted as UTC.
func parseEventTime(s string) (time.Time, bool) {
	if t, err := time.Parse(time.RFC3339, s); err == nil {
		return t.UTC(), true
	}
	if t, err := time.Parse("2006-01-02T15:04:05", s); err == nil {
		return t.UTC(), true
	}
	return time.Time{}, false
}
