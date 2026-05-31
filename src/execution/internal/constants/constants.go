package constants

// ValidationCheck identifies which pre-execution check ran.
type ValidationCheck int32

const (
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
)

// ValidationOutcome is the result of a failed validation check.
type ValidationOutcome string

const (
	OutcomeReject ValidationOutcome = "REJECT"
	OutcomeQueue  ValidationOutcome = "QUEUE"
	OutcomeLock   ValidationOutcome = "LOCK"
	OutcomePause  ValidationOutcome = "PAUSE"
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
	StatusPending         OrderStatus = "PENDING"
	StatusWatching        OrderStatus = "WATCHING"
	StatusFilled          OrderStatus = "FILLED"
	StatusCancelled       OrderStatus = "CANCELLED"
	StatusExpired         OrderStatus = "EXPIRED"
	StatusRejected        OrderStatus = "REJECTED"
	StatusQueued          OrderStatus = "QUEUED"
	StatusLocked          OrderStatus = "LOCKED"
	StatusPaused          OrderStatus = "PAUSED"
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

// News lockout windows in minutes from Rulebook Section 4.3.
const (
	NewsLockoutMinutesNormal   = 30
	NewsLockoutMinutesScalping = 45
)

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
