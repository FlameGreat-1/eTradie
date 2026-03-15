package notify

import (
	"encoding/json"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/constants"
	"github.com/flamegreat/etradie/src/execution/internal/models"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
)

// Event is a notification payload pushed to the dashboard.
type Event struct {
	Type      string                 `json:"type"`
	Timestamp string                 `json:"timestamp"`
	Symbol    string                 `json:"symbol,omitempty"`
	Direction string                 `json:"direction,omitempty"`
	Message   string                 `json:"message"`
	Details   map[string]interface{} `json:"details,omitempty"`
}

// Subscriber receives notification events.
type Subscriber chan Event

// Notifier dispatches pop-up notifications to connected dashboard
// clients via a pub/sub fan-out pattern. Thread-safe.
type Notifier struct {
	mu          sync.RWMutex
	subscribers map[Subscriber]struct{}
	log         zerolog.Logger
}

// NewNotifier creates a notification dispatcher.
func NewNotifier() *Notifier {
	return &Notifier{
		subscribers: make(map[Subscriber]struct{}),
		log:         observability.Logger("notifier"),
	}
}

// Subscribe registers a new dashboard client for notifications.
// Returns a channel that receives events. Caller must call
// Unsubscribe when done.
func (n *Notifier) Subscribe() Subscriber {
	ch := make(Subscriber, 64)
	n.mu.Lock()
	n.subscribers[ch] = struct{}{}
	n.mu.Unlock()
	return ch
}

// Unsubscribe removes a subscriber and closes its channel.
func (n *Notifier) Unsubscribe(ch Subscriber) {
	n.mu.Lock()
	delete(n.subscribers, ch)
	n.mu.Unlock()
	close(ch)
}

// NotifyOrderPlaced sends a notification when an order is placed.
func (n *Notifier) NotifyOrderPlaced(order *models.Order) {
	modeLabel := "Limit order placed"
	if order.ExecutionMode == constants.ModeInstant {
		modeLabel = "Price watcher armed"
	}

	n.publish(Event{
		Type:      "ORDER_PLACED",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Symbol:    order.Symbol,
		Direction: string(order.Direction),
		Message:   modeLabel + " for " + order.Symbol,
		Details: map[string]interface{}{
			"order_id":       order.OrderID,
			"entry_price":    order.EntryPrice,
			"stop_loss":      order.StopLoss,
			"lot_size":       order.LotSize,
			"risk_amount":    order.RiskAmount,
			"grade":          order.Grade,
			"execution_mode": string(order.ExecutionMode),
			"analysis_id":    order.AnalysisID,
		},
	})
}

// NotifyRejected sends a notification when execution is rejected.
func (n *Notifier) NotifyRejected(req *models.TradeRequest, result models.ValidationResult) {
	n.publish(Event{
		Type:      "EXECUTION_REJECTED",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Symbol:    req.Symbol,
		Direction: string(req.Direction),
		Message:   "Trade rejected: " + result.Reason,
		Details: map[string]interface{}{
			"check":       int32(result.FailedCheck),
			"outcome":     string(result.Outcome),
			"analysis_id": req.AnalysisID,
		},
	})
}

// NotifyDailyLocked sends a notification when daily loss limit is hit.
func (n *Notifier) NotifyDailyLocked(lossPct float64) {
	n.publish(Event{
		Type:      "DAILY_LIMIT_LOCKED",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Message:   "Execution locked: daily loss limit reached",
		Details:   map[string]interface{}{"daily_loss_pct": lossPct},
	})
}

// NotifyWeeklyPaused sends a notification when weekly drawdown is hit.
func (n *Notifier) NotifyWeeklyPaused(drawdownPct float64) {
	n.publish(Event{
		Type:      "WEEKLY_PAUSED",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Message:   "Execution paused: weekly drawdown limit reached",
		Details:   map[string]interface{}{"weekly_drawdown_pct": drawdownPct},
	})
}

// NotifyError sends a system error notification.
func (n *Notifier) NotifyError(symbol, message string) {
	n.publish(Event{
		Type:      "EXECUTION_ERROR",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Symbol:    symbol,
		Message:   message,
	})
}

func (n *Notifier) publish(evt Event) {
	n.mu.RLock()
	defer n.mu.RUnlock()

	for sub := range n.subscribers {
		select {
		case sub <- evt:
		default:
			// Subscriber buffer full; drop event to avoid blocking.
			n.log.Warn().
				Str("type", evt.Type).
				Str("symbol", evt.Symbol).
				Msg("notification_dropped_subscriber_full")
		}
	}

	if n.log.Debug().Enabled() {
		raw, _ := json.Marshal(evt)
		n.log.Debug().
			Str("type", evt.Type).
			Str("symbol", evt.Symbol).
			RawJSON("event", raw).
			Int("subscribers", len(n.subscribers)).
			Msg("notification_published")
	}
}
