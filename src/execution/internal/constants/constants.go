package constants

// ValidationCheck identifies which pre-execution check ran.
type ValidationCheck int32

const (
	// CheckKillSwitch is the pre-everything backstop. It runs FIRST in
	// the validator chain (before the gateway-owned 1-3 and Module B's
	// 4-14) so an engaged global or per-user kill switch blocks order
	// placement at the cheapest possible point. CHECKLIST Section 8.
	CheckKillSwitch          ValidationCheck = 0
	CheckNewsLockout         ValidationCheck = 4
	CheckSessionFilter       ValidationCheck = 5
	CheckSamePairPosition    ValidationCheck = 6
	CheckCorrelatedExposure  ValidationCheck = 7
	CheckMaxConcurrentTrades ValidationCheck = 8
	CheckDailyLossLimit      ValidationCheck = 9
	CheckWeeklyDrawdown      ValidationCheck = 10
	CheckSpread              ValidationCheck = 11
	CheckMinRR               ValidationCheck = 12
	CheckWeekendDayFilter    ValidationCheck = 13
	CheckMinStopDistance     ValidationCheck = 14
)

// MinStopPipsByTimeframe is the minimum stop-loss distance (in pips)
// allowed for an order whose entry candidate formed on the given
// timeframe.  It is the execution-side defensive backstop for the
// structural SL computed upstream in the TA engine.
//
// WHY THIS EXISTS: position size is riskAmount / (slPips * pipValue).
// A vanishingly small slPips inflates lot size without bound (capped
// only by MaxLotSize, which then silently breaks the risk model). A
// few-point stop on a spiking synthetic is also a near-certain
// stop-out. This check rejects such an order BEFORE sizing.
//
// The values mirror
// engine.ta.common.utils.price.stop_loss.TIMEFRAME_SL_FLOOR_PIPS so
// the backstop is consistent with the source-side structural floor.
// They are a floor only: a wider structural SL always passes. Values
// are in pips and converted to price distance per instrument via
// InstrumentInfo.PipSize (FX 0.0001, JPY/metals 0.01,
// indices/crypto/synthetics 1.0), so one map covers every class.
var MinStopPipsByTimeframe = map[string]float64{
	"M1":  8.0,
	"M5":  12.0,
	"M15": 18.0,
	"M30": 25.0,
	"H1":  35.0,
	"H3":  55.0,
	"H4":  70.0,
	"H6":  90.0,
	"H8":  110.0,
	"H12": 140.0,
	"D1":  200.0,
	"W1":  400.0,
	"MN1": 700.0,
}

// DefaultMinStopPips is the floor used when the entry candidate's
// timeframe is absent or unrecognized.  It equals the H1 floor: a
// conservative mid-band value that is safe for an unknown setup
// without being so large it rejects legitimate LTF stops.
const DefaultMinStopPips = 35.0

// MinStopPipsForTimeframe returns the minimum stop distance in pips
// for the given entry timeframe, falling back to DefaultMinStopPips
// for an empty or unrecognized timeframe string.
func MinStopPipsForTimeframe(timeframe string) float64 {
	if p, ok := MinStopPipsByTimeframe[timeframe]; ok {
		return p
	}
	return DefaultMinStopPips
}

// ValidationOutcome is the result of a failed validation check.
type ValidationOutcome string

const (
	OutcomeReject ValidationOutcome = "REJECT"
	OutcomeQueue  ValidationOutcome = "QUEUE"
	OutcomeLock   ValidationOutcome = "LOCK"
	OutcomePause  ValidationOutcome = "PAUSE"
	// OutcomeHalted is returned when the global or per-user execution
	// kill switch is engaged. Analysis still runs upstream; only order
	// placement is blocked. CHECKLIST Section 8 (Kill Switches).
	OutcomeHalted ValidationOutcome = "HALTED"
)

// ExecutionMode is the order placement strategy.
type ExecutionMode string

const (
	ModeLimit   ExecutionMode = "LIMIT"
	ModeInstant ExecutionMode = "INSTANT"
	ModeAuto    ExecutionMode = "AUTO"
)

// OrderStatus tracks the lifecycle of an order.
type OrderStatus string

const (
	StatusPending   OrderStatus = "PENDING"
	StatusWatching  OrderStatus = "WATCHING"
	StatusFilled    OrderStatus = "FILLED"
	StatusCancelled OrderStatus = "CANCELLED"
	StatusExpired   OrderStatus = "EXPIRED"
	StatusRejected  OrderStatus = "REJECTED"
	StatusQueued    OrderStatus = "QUEUED"
	StatusLocked    OrderStatus = "LOCKED"
	StatusPaused    OrderStatus = "PAUSED"
	// StatusHalted is the order status when the global or per-user
	// execution kill switch blocked placement. CHECKLIST Section 8.
	StatusHalted          OrderStatus = "HALTED"
	StatusPartiallyFilled OrderStatus = "PARTIALLY_FILLED"
	// StatusDuplicate is returned when an idempotency claim detects a
	// prior placement for the same (user_id, idempotency_key). The
	// response carries the prior broker_order_id; no new broker call
	// is made. CHECKLIST Section 1 ("Same order cannot execute twice").
	StatusDuplicate OrderStatus = "DUPLICATE"
)

// BrokerOrderType distinguishes limit vs market at the broker level.
type BrokerOrderType string

const (
	BrokerOrderLimit  BrokerOrderType = "LIMIT"
	BrokerOrderMarket BrokerOrderType = "MARKET"
)

// AuditAction identifies what Module B did.
type AuditAction string

const (
	ActionValidationPassed   AuditAction = "VALIDATION_PASSED"
	ActionValidationRejected AuditAction = "VALIDATION_REJECTED"
	ActionLotSizeCalculated  AuditAction = "LOT_SIZE_CALCULATED"
	ActionLimitOrderPlaced   AuditAction = "LIMIT_ORDER_PLACED"
	ActionWatcherArmed       AuditAction = "WATCHER_ARMED"
	ActionMarketOrderFired   AuditAction = "MARKET_ORDER_FIRED"
	ActionOrderFilled        AuditAction = "ORDER_FILLED"
	ActionOrderCancelled     AuditAction = "ORDER_CANCELLED"
	ActionOrderExpired       AuditAction = "ORDER_EXPIRED"
	ActionDailyLimitLocked   AuditAction = "DAILY_LIMIT_LOCKED"
	ActionWeeklyPaused       AuditAction = "WEEKLY_PAUSED"
	// ActionExecutionHalted records a placement blocked by the kill
	// switch (global or per-user). CHECKLIST Section 8.
	ActionExecutionHalted AuditAction = "EXECUTION_HALTED"
)

// CancelReason explains why a pending order was cancelled.
type CancelReason string

const (
	ReasonStructureBreak CancelReason = "STRUCTURE_BREAK"
	ReasonThesisChanged  CancelReason = "THESIS_CHANGED"
	ReasonManual         CancelReason = "MANUAL"
	ReasonTTLExpired     CancelReason = "TTL_EXPIRED"
	ReasonNewsLockout    CancelReason = "NEWS_LOCKOUT"
)

// TradingStyle from Rulebook Section 2.4.
type TradingStyle string

const (
	StyleScalping   TradingStyle = "SCALPING"
	StyleIntraday   TradingStyle = "INTRADAY"
	StyleSwing      TradingStyle = "SWING"
	StylePositional TradingStyle = "POSITIONAL"
)

// Direction for order placement.
type Direction string

const (
	DirectionLong  Direction = "LONG"
	DirectionShort Direction = "SHORT"
)

// BrokerDirection maps internal direction to broker-level BUY/SELL.
func BrokerDirection(d Direction) string {
	switch d {
	case DirectionLong:
		return "BUY"
	case DirectionShort:
		return "SELL"
	default:
		return string(d)
	}
}

// Risk thresholds from Rulebook Section 7.
const (
	DailyLossLimitPercent  = 3.0
	WeeklyDrawdownPercent  = 5.0
	MonthlyDrawdownPercent = 10.0
	MaxConcurrentTrades    = 3
)

// Risk allocation by grade from Rulebook Section 6.2.
const (
	RiskPercentAPlus = 1.0
	RiskPercentA     = 1.0
	RiskPercentB     = 0.5
)

// Minimum R:R by style from Rulebook Section 7.3.
var MinRRByStyle = map[TradingStyle]float64{
	StyleScalping:   2.0,
	StyleIntraday:   3.0,
	StyleSwing:      3.0,
	StylePositional: 5.0,
}

// Spread multiplier thresholds from Rulebook Section 10.
const (
	SpreadMultiplierNormal   = 2.0
	SpreadMultiplierScalping = 1.5
)

// News lockout policy is owned by the gateway (it holds the economic
// calendar). The execution service enforces news only via the gateway's
// CheckNewsWindow RPC; the previously-defined NewsLockoutMinutes* mirror
// constants here had no consumer and were removed to avoid dead code.
// The operator-tunable windows live in config (Config.NewsLockoutMinutes
// / Config.NewsLockoutMinutesScalping), and the rulebook values are
// owned by the gateway constants of the same name.

// Session time windows (UTC hours). From Rulebook Section 2.3.
type SessionWindow struct {
	Name      string
	StartHour int
	EndHour   int
}

var Sessions = []SessionWindow{
	{Name: "ASIAN", StartHour: 0, EndHour: 7},
	{Name: "LONDON_OPEN", StartHour: 7, EndHour: 13},
	{Name: "LONDON_NY_OVERLAP", StartHour: 13, EndHour: 17},
	{Name: "NEW_YORK", StartHour: 17, EndHour: 22},
	{Name: "ASIAN", StartHour: 22, EndHour: 24},
}

// Friday entry cutoff hours (UTC) by style from Rulebook Section 2.6.
var FridayCutoffHourByStyle = map[TradingStyle]int{
	StyleScalping:   12,
	StyleIntraday:   12,
	StyleSwing:      14,
	StylePositional: 24, // No restriction.
}

// Monday no-entry before London Open (07:00 UTC).
const MondayNoEntryBeforeHour = 7

// Correlated pair groups from Rulebook Section 7.2.
// Max 1 trade per group. The strongest setup wins.
var CorrelatedPairGroups = [][]string{
	{"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"},           // USD quote group (risk-on basket)
	{"USDJPY", "USDCHF", "USDCAD"},                     // USD base group
	{"EURJPY", "GBPJPY", "AUDJPY", "NZDJPY"},           // JPY cross group
	{"EURGBP", "EURAUD", "EURNZD", "EURCHF", "EURCAD"}, // EUR cross group
	{"XAUUSD", "XAGUSD"},                               // Metals group
}

// Position sizing bounds.
const (
	MinLotSize     = 0.01
	DefaultMaxLots = 10.0
)

// Limit order TTL in 4H candles by style.
var LimitTTLCandlesByStyle = map[TradingStyle]int{
	StyleScalping:   1,  // 1 candle (4H) = cancel quickly
	StyleIntraday:   4,  // 4 candles = ~1 session
	StyleSwing:      18, // 18 candles = ~3 days
	StylePositional: 42, // 42 candles = ~7 days
}

// Instant mode overshoot tolerance as multiplier of entry zone width.
const DefaultOvershootToleranceMultiplier = 1.5

// WatcherTimeoutMinutesByStyle defines how long an instant-mode watcher
// monitors the entry zone before timing out, per trading style.
//
// These values are aligned with LimitTTLCandlesByStyle because the
// entry zone validity is a property of the trading setup, not the
// execution mechanism. A swing zone valid for 3 days as a limit order
// must also be valid for 3 days as an instant-mode watcher.
//
// Derived from LimitTTLCandlesByStyle (each candle = 4 hours = 240 min):
//   - Scalping:    1 candle  x 240 =   240 min (4 hours)
//   - Intraday:    4 candles x 240 =   960 min (16 hours)
//   - Swing:      18 candles x 240 =  4320 min (3 days)
//   - Positional: 42 candles x 240 = 10080 min (7 days)
var WatcherTimeoutMinutesByStyle = map[TradingStyle]int{
	StyleScalping:   240,
	StyleIntraday:   960,
	StyleSwing:      4320,
	StylePositional: 10080,
}

// WatcherTimeoutForStyle returns the watcher timeout in minutes for
// the given trading style. Falls back to the provided default if the
// style is not recognized.
func WatcherTimeoutForStyle(style TradingStyle, fallbackMinutes int) int {
	if minutes, ok := WatcherTimeoutMinutesByStyle[style]; ok {
		return minutes
	}
	return fallbackMinutes
}
