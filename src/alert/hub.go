package alert

import (
	"crypto/rand"
	"encoding/hex"
	"os"
	"sync"
	"sync/atomic"

	"github.com/rs/zerolog"
)

const subscriberBufferSize = 128

// severityRank maps severity to a numeric rank for comparison.
var severityRankMap = map[EventSeverity]int{
	SeverityInfo:     0,
	SeverityWarning:  1,
	SeverityError:    2,
	SeverityCritical: 3,
}

// SeverityRank returns the numeric rank for a severity level.
// Higher rank means more severe. Used by the redis transport
// for filtered history queries.
func SeverityRank(s EventSeverity) int {
	return severityRankMap[s]
}

// Subscriber receives events from the hub.
type Subscriber struct {
	C  chan *Event
	id string
	// userID scopes event delivery to a specific user. When non-empty,
	// only events with a matching UserID or system events (empty UserID)
	// are delivered. When empty, all events are delivered (system subscriber).
	userID string
	// minSeverity filters events delivered to this subscriber.
	// Empty string means no filter (receive all events).
	minSeverity EventSeverity
	closed      atomic.Bool
}

// meetsMinSeverity returns true if the event severity is at or above
// the subscriber's minimum severity filter.
func (s *Subscriber) meetsMinSeverity(evt *Event) bool {
	if s.minSeverity == "" {
		return true
	}
	return severityRankMap[evt.Severity] >= severityRankMap[s.minSeverity]
}

// meetsUserScope returns true if the event should be delivered to this
// subscriber based on user scoping rules:
//   - System subscribers (userID == ""): receive ALL events.
//   - User subscribers (userID != ""): receive system events (evt.UserID == "")
//     and events owned by the same user (evt.UserID == sub.userID).
func (s *Subscriber) meetsUserScope(evt *Event) bool {
	if s.userID == "" {
		return true // System subscriber: no user filter.
	}
	if evt.UserID == "" {
		return true // System event: visible to all users.
	}
	return evt.UserID == s.userID
}

// Hub is the in-process pub/sub dispatcher for WebSocket clients.
// Services publish events here for real-time delivery. For cross-service
// communication and persistence, use redis.Transport which bridges
// Redis pub/sub to this Hub.
//
// Thread-safe. Non-blocking publish (drops events for slow subscribers).
type Hub struct {
	mu          sync.RWMutex
	subscribers map[*Subscriber]struct{}
	log         zerolog.Logger
}

// NewHub creates a notification hub.
func NewHub() *Hub {
	return &Hub{
		subscribers: make(map[*Subscriber]struct{}),
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
// This creates a system-level subscriber with no user scoping.
func (h *Hub) SubscribeWithFilter(minSeverity EventSeverity) *Subscriber {
	return h.subscribe("", minSeverity)
}

// SubscribeForUser registers a user-scoped subscriber that only receives
// events belonging to the given user or system events (empty UserID).
// Used by WebSocket handlers to ensure dashboard clients only see their
// own events. Pass empty minSeverity for all severity levels.
func (h *Hub) SubscribeForUser(userID string, minSeverity EventSeverity) *Subscriber {
	return h.subscribe(userID, minSeverity)
}

// subscribe is the shared subscriber creation logic.
func (h *Hub) subscribe(userID string, minSeverity EventSeverity) *Subscriber {
	sub := &Subscriber{
		C:           make(chan *Event, subscriberBufferSize),
		id:          generateSubscriberID(),
		userID:      userID,
		minSeverity: minSeverity,
	}

	h.mu.Lock()
	h.subscribers[sub] = struct{}{}
	count := len(h.subscribers)
	h.mu.Unlock()

	AlertActiveSubscribers.Set(float64(count))

	h.log.Info().
		Str("subscriber_id", sub.id).
		Str("user_id", userID).
		Str("min_severity", string(minSeverity)).
		Int("total_subscribers", count).
		Msg("subscriber_added")

	return sub
}

// Unsubscribe removes a client and closes its channel.
func (h *Hub) Unsubscribe(sub *Subscriber) {
	if sub.closed.Swap(true) {
		return
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

// Publish fans out an event to all connected subscribers whose severity
// filter matches. Increments the published metric. Non-blocking: if a
// subscriber's buffer is full, the event is dropped for that subscriber
// and a metric is incremented.
// Publishing must never block the caller (pipeline, gateway, etc.).
func (h *Hub) Publish(evt *Event) {
	AlertEventsPublished.WithLabelValues(string(evt.Source), evt.Type, string(evt.Severity)).Inc()
	h.deliverToSubscribers(evt)
}

// DeliverRemote fans out an event received from Redis pub/sub to local
// WebSocket subscribers. Does NOT increment the published metric to
// avoid double-counting events that were already counted when the
// originating service called Publish.
func (h *Hub) DeliverRemote(evt *Event) {
	h.deliverToSubscribers(evt)
}

// deliverToSubscribers is the shared fan-out logic used by both
// Publish (local events) and DeliverRemote (Redis events).
func (h *Hub) deliverToSubscribers(evt *Event) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	for sub := range h.subscribers {
		if sub.closed.Load() {
			continue
		}
		if !sub.meetsUserScope(evt) {
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
func newLogger(component string) zerolog.Logger {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs
	return zerolog.New(os.Stdout).With().
		Timestamp().
		Str("service", "alert").
		Str("component", component).
		Logger()
}
