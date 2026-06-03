package constants

import "strings"

// TradingStyle from Rulebook Section 2.4.
type TradingStyle string

const (
	StyleScalping   TradingStyle = "SCALPING"
	StyleIntraday   TradingStyle = "INTRADAY"
	StyleSwing      TradingStyle = "SWING"
	StylePositional TradingStyle = "POSITIONAL"
)

// TradeStatus tracks the lifecycle of a managed trade.
type TradeStatus string

const (
	StatusActive    TradeStatus = "ACTIVE"
	StatusBreakeven TradeStatus = "BREAKEVEN"
	StatusTrailing  TradeStatus = "TRAILING"
	StatusClosing   TradeStatus = "CLOSING"
	StatusClosed    TradeStatus = "CLOSED"
)

// TradeOutcome is the final result of a closed trade.
type TradeOutcome string

const (
	OutcomeWin       TradeOutcome = "WIN"
	OutcomeLoss      TradeOutcome = "LOSS"
	OutcomeBreakeven TradeOutcome = "BREAKEVEN"
)

// EventType identifies trade management events for journaling and alerts.
type EventType string

const (
	EventTP1Hit                EventType = "TP1_HIT"
	EventTP2Hit                EventType = "TP2_HIT"
	EventTP3Hit                EventType = "TP3_HIT"
	EventSLHit                 EventType = "SL_HIT"
	EventBreakevenSet          EventType = "BREAKEVEN_SET"
	EventTrailingSLMoved       EventType = "TRAILING_SL_MOVED"
	EventPartialClose          EventType = "PARTIAL_CLOSE"
	EventTradeClosed           EventType = "TRADE_CLOSED"
	EventEODClosure            EventType = "EOD_CLOSURE"
	EventInvalidationClosure   EventType = "INVALIDATION_CLOSURE"
	EventTimeLimitClosure      EventType = "TIME_LIMIT_CLOSURE"
	EventStructuralBreak       EventType = "STRUCTURAL_BREAK"
	EventCOTFlip               EventType = "COT_FLIP"
	EventSLTightened           EventType = "SL_TIGHTENED"
	EventNewsProtection        EventType = "NEWS_PROTECTION"
	EventCorrelationProtection EventType = "CORRELATION_PROTECTION"
	EventExternalClose         EventType = "EXTERNAL_CLOSE"
)

// Redis Pub/Sub channels from Rulebook Section 13.
const (
	ChannelMacroCalendar = "etradie:alerts:macro_calendar"
	ChannelTradeClosed   = "etradie:alerts:trade_closed"
)

// Direction for position tracking.
type Direction string

const (
	DirectionBuy  Direction = "BUY"
	DirectionSell Direction = "SELL"
)

// StyleManualDefault is the trading style assigned to a reconciler-
// imported position that is GENUINELY manual/external -- i.e. it has no
// corresponding system trade row to recover the real style from. It is
// POSITIONAL on purpose: positional has the least aggressive automated
// interference (no 3-hour intraday SL tightening, no 16:30 UTC intraday
// EOD hard-close, widest trailing timeframe), so a trade whose intent
// the engine cannot know is never closed or tightened prematurely. The
// broker-side SL/TP set by the trader still protects the position.
//
// A reconciled position that IS one of our own trades does NOT use this
// default: the reconciler recovers its true style from the journal row
// (EM-F2). This constant applies only to the no-system-row fallback.
const StyleManualDefault = StylePositional

// TP split percentages by style from Rulebook Section 8.3.
var TPSplitByStyle = map[TradingStyle][3]int32{
	StyleScalping:   {60, 40, 0},
	StyleIntraday:   {40, 30, 30},
	StyleSwing:      {30, 30, 40},
	StylePositional: {25, 25, 50},
}

// SyntheticSymbolMarkers are the case-insensitive substrings that identify
// Deriv-style synthetic instruments. Kept in one place so the pip model is
// defined once and stays in lockstep with the execution sizing engine
// (src/execution/internal/broker/mt5/bridge.go GetInstrumentInfo).
var SyntheticSymbolMarkers = []string{
	"VOLATILITY", "BOOM", "CRASH", "STEP", "JUMP", "V75", "DEX", "RANGE",
}

// IsSyntheticSymbol reports whether symbol is a synthetic index whose pip
// is one full index point (1.0) rather than an FX fraction.
func IsSyntheticSymbol(symbol string) bool {
	upper := strings.ToUpper(symbol)
	for _, m := range SyntheticSymbolMarkers {
		if strings.Contains(upper, m) {
			return true
		}
	}
	return false
}

// PipSize returns the price distance of one pip for the instrument, using
// the SAME convention as the execution sizing engine
// (mt5/bridge.go GetInstrumentInfo):
//
//   - synthetic indices            => 1.0 (one full index point)
//   - 2-digit instruments (metals) => point   (1 pip = 1 point)
//   - 3/5-digit FX                 => point*10 (1 pip = 10 points)
//
// When point <= 0 the caller has no broker metadata; PipSize returns 0 so
// the caller can decide on a fallback (it never silently invents a scale).
func PipSize(symbol string, point float64, digits int) float64 {
	if IsSyntheticSymbol(symbol) {
		return 1.0
	}
	if point <= 0 {
		return 0
	}
	if digits <= 2 {
		return point
	}
	return point * 10
}

// Break-even rules from Rulebook Section 9.1.
const (
	// SpreadBufferPips is added to entry when moving SL to break-even.
	SpreadBufferPips = 2.5
	// ScalpBEThreshold: scalping triggers BE at 60% of distance to TP1.
	ScalpBEThreshold = 0.60
	// IntradayBETimeoutHours: if TP1 not reached in 3 hours, tighten SL.
	IntradayBETimeoutHours = 3
	// IntradaySLReductionPct: tighten SL to 50% of original risk.
	IntradaySLReductionPct = 0.50
)

// Trailing stop recalculation timeframes from Rulebook Section 9.2.
type TrailTimeframe string

const (
	Trail15M TrailTimeframe = "15M"
	Trail1H  TrailTimeframe = "1H"
	Trail4H  TrailTimeframe = "4H"
	Trail1D  TrailTimeframe = "1D"
	Trail1W  TrailTimeframe = "1W"
)

// TrailConfigByStyle maps each trading style to its initial and
// post-TP1 trailing timeframe from Rulebook Section 9.2.
type TrailConfig struct {
	Initial TrailTimeframe
	PostTP1 TrailTimeframe
}

var TrailConfigByStyle = map[TradingStyle]TrailConfig{
	StyleScalping:   {Initial: Trail15M, PostTP1: Trail15M},
	StyleIntraday:   {Initial: Trail1H, PostTP1: Trail4H},
	StyleSwing:      {Initial: Trail4H, PostTP1: Trail1D},
	StylePositional: {Initial: Trail1D, PostTP1: Trail1W},
}

// End-of-period protocol times (UTC) from Rulebook Section 9.3.
const (
	// ScalpMaxDurationMinutes: maximum 2 hours (120 minutes) from entry.
	ScalpMaxDurationMinutes = 120
	// IntradayEODHour: 16:30 UTC → represented as hour 16, minute 30.
	IntradayEODHour   = 16
	IntradayEODMinute = 30
	// SwingWeekendHour: Friday 16:00 UTC.
	SwingWeekendHour   = 16
	SwingWeekendMinute = 0
	// SwingWeekendDay: Friday = 5 (time.Weekday).
	SwingWeekendDay = 5
)
