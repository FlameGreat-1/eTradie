package alert

import (
	"crypto/rand"
	"encoding/hex"
	"os"
	"sync"
	"sync/atomic"

	"github.com/rs/zerolog"
)

const (
	subscriberBufferSize = 128
	defaultHistorySize   = 500
)

// Subscriber receives events from the hub.
type Subscriber struct {
	C      chan *Event
	id     string
	closed atomic.Bool
	// minSeverity filters events by severity. Only events at or above
	// this severity are delivered. Zero value (empty string) means all.
	minSeverity EventSeverity
}

// severityRank maps severity to a numeric rank for comparison.
var severityRank = map[EventSeverity]int{
	SeverityInfo:     0,
	SeverityWarning:  1,
	SeverityError:    2,
	SeverityCritical: 3,
}

// meetsMinSeverity returns true if the event severity is at or above
// the subscriber's minimum severity filter.
func (s *Subscriber) meetsMinSeverity(evt *Event) bool {
	if s.minSeverity == "" {
		return true
	}
	return severityRank[evt.Severity] >= severityRank[s.minSeverity]
}

// Hub is the central pub/sub dispatcher for all application notifications.
// Any module publishes events here; all connected dashboard clients
// receive them via WebSocket. Thread-safe.
type Hub struct {
	mu          sync.RWMutex
	subscribers map[*Subscriber]struct{}
	history     []*Event
	historySize int
	historyIdx  int
	historyFull bool
	log         zerolog.Logger
}

// NewHub creates a notification hub with a default history ring buffer.
func NewHub() *Hub {
	return NewHubWithHistory(defaultHistorySize)
}

// NewHubWithHistory creates a notification hub with a custom history size.
// Set historySize to 0 to disable event history.
func NewHubWithHistory(historySize int) *Hub {
	var history []*Event
	if historySize > 0 {
		history = make([]*Event, historySize)
	}
	return &Hub{
		subscribers: make(map[*Subscriber]struct{}),
		history:     history,
		historySize: historySize,
		log:         newLogger("alert_hub"),
	}
}

// Subscribe registers a new client with no severity filter.
// Returns a Subscriber whose C channel receives events.
// Caller must call Unsubscribe when done.
func (h *Hub) Subscribe() *Subscriber {
	return h.SubscribeWithFilter("")
}

// SubscribeWithFilter registers a new client that only receives events
// at or above the given severity. Pass empty string for all events.
func (h *Hub) SubscribeWithFilter(minSeverity EventSeverity) *Subscriber {
	sub := &Subscriber{
		C:           make(chan *Event, subscriberBufferSize),
		id:          generateSubscriberID(),
		minSeverity: minSeverity,
	}

	h.mu.Lock()
	h.subscribers[sub] = struct{}{}
	count := len(h.subscribers)
	h.mu.Unlock()

	AlertActiveSubscribers.Set(float64(count))

	h.log.Info().
		Str("subscriber_id", sub.id).
		Str("min_severity", string(minSeverity)).
		Int("total_subscribers", count).
		Msg("subscriber_added")

	return sub
}

// Unsubscribe removes a client and closes its channel.
func (h *Hub) Unsubscribe(sub *Subscriber) {
	if sub.closed.Swap(true) {
		return // Already closed.
	}

	h.mu.Lock()
	delete(h.subscribers, sub)
	count := len(h.subscribers)
	h.mu.Unlock()

	close(sub.C)
	AlertActiveSubscribers.Set(float64(count))

	h.log.Info().
		Str("subscriber_id", sub.id).
		Int("total_subscribers", count).
		Msg("subscriber_removed")
}

// Publish sends an event to all connected subscribers and stores it
// in the history ring buffer. Non-blocking: if a subscriber's buffer
// is full, the event is dropped for that subscriber (logged + metric).
// Publishing must never block the caller.
func (h *Hub) Publish(evt *Event) {
	AlertEventsPublished.WithLabelValues(string(evt.Source), evt.Type, string(evt.Severity)).Inc()

	h.mu.Lock()
	// Store in ring buffer.
	if h.historySize > 0 && h.history != nil {
		h.history[h.historyIdx] = evt
		h.historyIdx++
		if h.historyIdx >= h.historySize {
			h.historyIdx = 0
			h.historyFull = true
		}
	}
	h.mu.Unlock()

	if h.historySize > 0 {
		var currentSize float64
		if h.historyFull {
			currentSize = float64(h.historySize)
		} else {
			currentSize = float64(h.historyIdx)
		}
		AlertHistorySize.Set(currentSize)
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	for sub := range h.subscribers {
		if sub.closed.Load() {
			continue
		}
		if !sub.meetsMinSeverity(evt) {
			continue
		}
		select {
		case sub.C <- evt:
		default:
			AlertEventsDropped.WithLabelValues(sub.id).Inc()
			h.log.Warn().
				Str("subscriber_id", sub.id).
				Str("event_type", evt.Type).
				Str("event_id", evt.ID).
				Msg("event_dropped_subscriber_buffer_full")
		}
	}
}

// Recent returns the last n events from the history ring buffer,
// ordered oldest to newest. Returns fewer than n if the buffer
// doesn't have that many events yet.
func (h *Hub) Recent(n int) []*Event {
	if h.historySize == 0 || h.history == nil {
		return nil
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	var total int
	if h.historyFull {
		total = h.historySize
	} else {
		total = h.historyIdx
	}

	if total == 0 {
		return nil
	}
	if n > total {
		n = total
	}

	result := make([]*Event, n)

	// Read the last n entries from the ring buffer in chronological order.
	for i := 0; i < n; i++ {
		idx := h.historyIdx - n + i
		if idx < 0 {
			idx += h.historySize
		}
		result[i] = h.history[idx]
	}

	return result
}

// RecentFiltered returns the last n events matching the given minimum
// severity, ordered oldest to newest.
func (h *Hub) RecentFiltered(n int, minSeverity EventSeverity) []*Event {
	if minSeverity == "" {
		return h.Recent(n)
	}

	if h.historySize == 0 || h.history == nil {
		return nil
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	var total int
	if h.historyFull {
		total = h.historySize
	} else {
		total = h.historyIdx
	}

	if total == 0 {
		return nil
	}

	minRank := severityRank[minSeverity]
	result := make([]*Event, 0, n)

	// Walk backwards from newest to oldest, collecting matches.
	for i := 0; i < total && len(result) < n; i++ {
		idx := h.historyIdx - 1 - i
		if idx < 0 {
			idx += h.historySize
		}
		evt := h.history[idx]
		if evt != nil && severityRank[evt.Severity] >= minRank {
			result = append(result, evt)
		}
	}

	// Reverse to chronological order (oldest first).
	for i, j := 0, len(result)-1; i < j; i, j = i+1, j-1 {
		result[i], result[j] = result[j], result[i]
	}

	return result
}

// SubscriberCount returns the current number of connected subscribers.
func (h *Hub) SubscriberCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.subscribers)
}

// Close shuts down the hub and drains all subscribers.
func (h *Hub) Close() {
	h.mu.Lock()
	for sub := range h.subscribers {
		if !sub.closed.Swap(true) {
			close(sub.C)
		}
		delete(h.subscribers, sub)
	}
	h.mu.Unlock()

	AlertActiveSubscribers.Set(0)
	h.log.Info().Msg("alert_hub_closed")
}

func generateSubscriberID() string {
	b := make([]byte, 6)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// newLogger creates a zerolog logger for the alert package.
// Standalone to avoid importing execution's observability package.
func newLogger(component string) zerolog.Logger {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs
	return zerolog.New(os.Stdout).With().
		Timestamp().
		Str("service", "alert").
		Str("component", component).
		Logger()
}
