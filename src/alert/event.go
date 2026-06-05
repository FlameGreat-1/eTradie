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
	// TypeExecutionHalted fires when the global or per-user execution
	// kill switch blocks an order (CHECKLIST Section 8). SeverityCritical.
	TypeExecutionHalted  = "EXECUTION_HALTED"
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
	TypeExecutionHandoff      = "EXECUTION_HANDOFF"
	TypeManagementHandoffFailed = "MANAGEMENT_HANDOFF_FAILED"
	TypeIntervalChanged       = "INTERVAL_CHANGED"
	TypeSymbolsChanged        = "SYMBOLS_CHANGED"

	// TA / Market events (Invalidator sources).
	TypeCandleClosed        = "CANDLE_CLOSED"
	TypeCOTFlip             = "COT_FLIP"
	TypeMacroCalendarUpdate = "MACRO_CALENDAR_UPDATE"

	// Trade manager (Module C) events.
	TypeTrailingSLMoved     = "TRAILING_SL_MOVED"
	TypePartialClose        = "PARTIAL_CLOSE"
	TypeBreakevenSet        = "BREAKEVEN_SET"
	TypeTradeClosed         = "TRADE_CLOSED"
	TypePerformanceReport   = "PERFORMANCE_REPORT"
	TypeTradeSynced         = "TRADE_SYNCED"

	// System events.
	TypeServiceStarted   = "SERVICE_STARTED"
	TypeServiceStopping  = "SERVICE_STOPPING"
	TypeBrokerDisconnect = "BROKER_DISCONNECTED"
	TypeBrokerReconnect  = "BROKER_RECONNECTED"

	// Billing / subscription events.
	//
	// Emitted by the billing service after a webhook is committed (see
	// src/billing/service/subscription.go::HandleEvent post-commit block).
	// The gateway's alertredis.Transport subscriber relays each event to
	// the connected dashboard so the SPA refetches ['billing'] and
	// ['auth', 'me'] without waiting for React Query staleTime.
	//
	// Direction is decided by tier rank in
	// service.classifySubscriptionChange:
	//   - TypeSubscriptionUpgraded:      free / unknown -> paid, or a
	//                                    less-expensive paid tier -> a
	//                                    more-expensive one.
	//   - TypeSubscriptionDowngraded:    paid -> free.
	//   - TypeSubscriptionStatusChanged: same tier, different status
	//                                    (active -> past_due, etc.) so
	//                                    the SPA refreshes status badges
	//                                    even when entitlement didn't move.
	//
	// The string values are the wire types the SPA matches on in
	// cotradee/src/features/realtime/types.ts and eventMap.ts; keep them
	// in lock-step with that file.
	TypeSubscriptionUpgraded      = "SUBSCRIPTION_UPGRADED"
	TypeSubscriptionDowngraded    = "SUBSCRIPTION_DOWNGRADED"
	TypeSubscriptionStatusChanged = "SUBSCRIPTION_STATUS_CHANGED"

	// TypeSubscriptionRequired fires when a user-facing action is
	// refused because the caller's current tier does not cover it
	// (e.g. Free user reaches the trade-execution router). It is the
	// canonical SAAS-tier upsell signal, distinct from the three
	// SUBSCRIPTION_* events above which are emitted by the billing
	// service after a webhook is committed and reflect an actual
	// state transition in billing_subscriptions.
	//
	// SeverityInfo on the wire — this is an upsell, not an alarm.
	// The SPA's eventMap.ts invalidates ['billing'] and ['auth', 'me']
	// on receipt so the upgrade modal opens against the freshest
	// authoritative tier; execution-state queries are intentionally
	// NOT invalidated because nothing changed there.
	TypeSubscriptionRequired = "SUBSCRIPTION_REQUIRED"

	// TypeLLMQuotaExceeded fires when a platform-key user (pro_managed
	// or admin) is blocked by the gateway's metering layer or by the
	// pre-flight check on /api/v1/cycle/run. Distinct from the
	// provider-side event below because the cause, the remediation,
	// and the SPA modal copy are all different: this one points the
	// user at the platform's monthly window reset date and (for admins)
	// at the admin quota panel; the BYOK one points them at their own
	// provider dashboard.
	//
	// Details carry:
	//   dimension   (daily_input / daily_output / monthly_input /
	//                monthly_output / per_call_input)
	//   limit       (int64) -- the cap the user breached
	//   used        (int64) -- consumed tokens in the window
	//   resets_at   (RFC3339 string) -- when the window rolls
	//   is_admin    (bool)   -- whether the user is an admin (the SPA
	//                surfaces a "Edit Policy" CTA in that case)
	TypeLLMQuotaExceeded = "LLM_QUOTA_EXCEEDED"

	// TypeLLMProviderQuotaExceeded fires when a BYOK user's own
	// provider returns a rate-limit / quota-exhaustion error
	// (Anthropic 429, OpenAI insufficient_quota, Gemini
	// RESOURCE_EXHAUSTED, self-hosted 503, etc.). The platform metering
	// layer never debits a reservation for BYOK users because
	// uses_platform_key is false; the error flows from the provider
	// SDK through the typed LLMRateLimitedError and is surfaced to the
	// user by this event so they know to check their provider account
	// instead of contacting platform support.
	//
	// Details carry:
	//   provider (string)   -- anthropic / openai / gemini / self_hosted
	//   model    (string)   -- the model the user had configured
	//   detail   (string)   -- the provider's raw error message,
	//                          truncated to 256 chars so a verbose
	//                          SDK message cannot blow the alert
	//                          payload size budget
	TypeLLMProviderQuotaExceeded = "LLM_PROVIDER_QUOTA_EXCEEDED"
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
	UserID    string                 `json:"user_id,omitempty"`
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

// WithUserID sets the user ID on the event for multi-tenant scoping.
// Events with a UserID are only delivered to that user's WebSocket
// connections and filtered in event history queries. Events without
// a UserID (empty string) are system events visible to all users.
func (e *Event) WithUserID(userID string) *Event {
	e.UserID = userID
	return e
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
