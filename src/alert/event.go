package alert

import (
	"crypto/rand"
	"encoding/hex"
	"time"
)

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
	TypeOrderPlaced      = "ORDER_PLACED"
	TypeOrderFilled      = "ORDER_FILLED"
	TypeOrderCancelled   = "ORDER_CANCELLED"
	TypeOrderExpired     = "ORDER_EXPIRED"
	TypeOrderRejected    = "EXECUTION_REJECTED"
	TypeWatcherArmed     = "WATCHER_ARMED"
	TypeWatcherTriggered = "WATCHER_TRIGGERED"
	TypeDailyLimitLocked = "DAILY_LIMIT_LOCKED"
	TypeWeeklyPaused     = "WEEKLY_PAUSED"
	TypeSizingCalculated = "SIZING_CALCULATED"
	TypeExecutionError   = "EXECUTION_ERROR"
	TypeModeChanged      = "EXECUTION_MODE_CHANGED"
	TypeSettingsUpdated  = "SETTINGS_UPDATED"

	// Gateway events.
	TypeCycleStarted          = "CYCLE_STARTED"
	TypeCycleCompleted        = "CYCLE_COMPLETED"
	TypeCycleFailed           = "CYCLE_FAILED"
	TypeCycleRetrying         = "CYCLE_RETRYING"
	TypeAnalysisComplete      = "ANALYSIS_COMPLETE"
	TypeGuardRejected         = "GUARD_REJECTED"
	TypeGuardWarning          = "GUARD_WARNING"
	TypeTACollectionFailed    = "TA_COLLECTION_FAILED"
	TypeMacroCollectionFailed = "MACRO_COLLECTION_FAILED"
	TypeRAGRetrievalFailed    = "RAG_RETRIEVAL_FAILED"
	TypeProcessorLLMFailed    = "PROCESSOR_LLM_FAILED"
	TypeExecutionCallFailed   = "EXECUTION_CALL_FAILED"
	TypeTradeRouted           = "TRADE_ROUTED"
	TypeIntervalChanged       = "INTERVAL_CHANGED"
	TypeSymbolsChanged        = "SYMBOLS_CHANGED"

	// Trade manager (Module C) events.
	TypeTrailingSLMoved  = "TRAILING_SL_MOVED"
	TypePartialClose     = "PARTIAL_CLOSE"
	TypeBreakevenSet     = "BREAKEVEN_SET"
	TypeTradeClosed      = "TRADE_CLOSED"

	// System events.
	TypeServiceStarted   = "SERVICE_STARTED"
	TypeServiceStopping  = "SERVICE_STOPPING"
	TypeBrokerDisconnect = "BROKER_DISCONNECTED"
	TypeBrokerReconnect  = "BROKER_RECONNECTED"
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
	now := time.Now().UTC()
	b := make([]byte, 4)
	_, _ = rand.Read(b)
	return now.Format("20060102150405") + "-" + hex.EncodeToString(b)
}
