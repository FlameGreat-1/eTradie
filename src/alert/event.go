package alert

import "time"

// EventSource identifies which module published the event.
type EventSource string

const (
	SourceGateway      EventSource = "GATEWAY"
	SourceExecution    EventSource = "EXECUTION"
	SourceTradeManager EventSource = "TRADE_MANAGER"
	SourceSystem       EventSource = "SYSTEM"
)

// EventSeverity indicates the urgency of the notification.
type EventSeverity string

const (
	SeverityInfo     EventSeverity = "INFO"
	SeverityWarning  EventSeverity = "WARNING"
	SeverityError    EventSeverity = "ERROR"
	SeverityCritical EventSeverity = "CRITICAL"
)

// Event type constants. Each module defines its own event types
// but they all flow through the same hub.
const (
	// Execution events.
	TypeOrderPlaced       = "ORDER_PLACED"
	TypeOrderFilled       = "ORDER_FILLED"
	TypeOrderCancelled    = "ORDER_CANCELLED"
	TypeOrderExpired      = "ORDER_EXPIRED"
	TypeOrderRejected     = "EXECUTION_REJECTED"
	TypeWatcherArmed      = "WATCHER_ARMED"
	TypeWatcherTriggered  = "WATCHER_TRIGGERED"
	TypeDailyLimitLocked  = "DAILY_LIMIT_LOCKED"
	TypeWeeklyPaused      = "WEEKLY_PAUSED"
	TypeSizingCalculated  = "SIZING_CALCULATED"
	TypeExecutionError    = "EXECUTION_ERROR"
	TypeModeChanged       = "EXECUTION_MODE_CHANGED"
	TypeSettingsUpdated   = "SETTINGS_UPDATED"

	// Gateway events.
	TypeAnalysisComplete  = "ANALYSIS_COMPLETE"
	TypeGuardRejected     = "GUARD_REJECTED"
	TypeCycleStarted      = "CYCLE_STARTED"
	TypeCycleCompleted    = "CYCLE_COMPLETED"

	// Trade manager (Module C) events.
	TypeTrailingSLMoved   = "TRAILING_SL_MOVED"
	TypePartialClose      = "PARTIAL_CLOSE"
	TypeBreakevenSet      = "BREAKEVEN_SET"
	TypeTradeClosed       = "TRADE_CLOSED"

	// System events.
	TypeServiceStarted    = "SERVICE_STARTED"
	TypeServiceStopping   = "SERVICE_STOPPING"
	TypeBrokerDisconnect  = "BROKER_DISCONNECTED"
	TypeBrokerReconnect   = "BROKER_RECONNECTED"
)

// Event is the universal notification payload. Every module publishes
// events in this format. The dashboard receives them all via a single
// WebSocket connection to the alert hub.
type Event struct {
	ID        string                 `json:"id"`
	Source    EventSource            `json:"source"`
	Type      string                 `json:"type"`
	Severity  EventSeverity          `json:"severity"`
	Timestamp string                 `json:"timestamp"`
	Symbol    string                 `json:"symbol,omitempty"`
	Direction string                 `json:"direction,omitempty"`
	Message   string                 `json:"message"`
	TraceID   string                 `json:"trace_id,omitempty"`
	Details   map[string]interface{} `json:"details,omitempty"`
}

// NewEvent creates an event with auto-generated ID and timestamp.
func NewEvent(source EventSource, eventType string, severity EventSeverity, message string) *Event {
	return &Event{
		ID:        generateEventID(),
		Source:    source,
		Type:      eventType,
		Severity:  severity,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Message:   message,
	}
}

// WithSymbol sets the symbol on the event.
func (e *Event) WithSymbol(symbol string) *Event {
	e.Symbol = symbol
	return e
}

// WithDirection sets the direction on the event.
func (e *Event) WithDirection(direction string) *Event {
	e.Direction = direction
	return e
}

// WithTraceID sets the trace ID for correlation.
func (e *Event) WithTraceID(traceID string) *Event {
	e.TraceID = traceID
	return e
}

// WithDetails sets arbitrary key-value details.
func (e *Event) WithDetails(details map[string]interface{}) *Event {
	e.Details = details
	return e
}

// WithDetail adds a single key-value pair to details.
func (e *Event) WithDetail(key string, value interface{}) *Event {
	if e.Details == nil {
		e.Details = make(map[string]interface{})
	}
	e.Details[key] = value
	return e
}

func generateEventID() string {
	// Use timestamp-based ID for ordering + random suffix for uniqueness.
	now := time.Now().UTC()
	return now.Format("20060102150405") + "-" + randomHex(4)
}

func randomHex(n int) string {
	b := make([]byte, n)
	// Use crypto/rand for uniqueness.
	_, _ = cryptoRandRead(b)
	return hexEncode(b)
}

// Thin wrappers to avoid importing crypto/rand and encoding/hex
// at the package level (keeps imports clean for the event model).
var (
	cryptoRandRead = cryptoRandReadImpl
	hexEncode      = hexEncodeImpl
)

func cryptoRandReadImpl(b []byte) (int, error) {
	// Inline import to keep event.go focused on the data model.
	// The actual implementation is in hub.go which imports crypto/rand.
	for i := range b {
		b[i] = byte(time.Now().UnixNano() >> (i * 8))
	}
	return len(b), nil
}

func hexEncodeImpl(b []byte) string {
	const hextable = "0123456789abcdef"
	dst := make([]byte, len(b)*2)
	for i, v := range b {
		dst[i*2] = hextable[v>>4]
		dst[i*2+1] = hextable[v&0x0f]
	}
	return string(dst)
}
