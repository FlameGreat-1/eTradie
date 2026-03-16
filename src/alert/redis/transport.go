package redis

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/alert"
)

const (
	// defaultChannel is the Redis pub/sub channel all services share.
	defaultChannel = "etradie:alerts"

	// defaultHistoryKey is the Redis sorted set storing event history.
	defaultHistoryKey = "etradie:alert_history"

	// defaultMaxHistory is the maximum number of events retained in Redis.
	defaultMaxHistory = 2000

	// defaultHistoryTTL is the TTL applied to the history sorted set key
	// as a safety net. Events are also trimmed by count.
	defaultHistoryTTL = 7 * 24 * time.Hour
)

// TransportConfig holds configuration for the Redis transport.
type TransportConfig struct {
	// Channel is the Redis pub/sub channel name. Default: "etradie:alerts".
	Channel string

	// HistoryKey is the Redis sorted set key for event persistence.
	// Default: "etradie:alert_history".
	HistoryKey string

	// MaxHistory is the maximum number of events stored in Redis.
	// Oldest events are trimmed when this limit is exceeded.
	// Default: 2000.
	MaxHistory int64

	// HistoryTTL is the TTL on the history key as a safety net.
	// Default: 7 days.
	HistoryTTL time.Duration
}

func (c *TransportConfig) applyDefaults() {
	if c.Channel == "" {
		c.Channel = defaultChannel
	}
	if c.HistoryKey == "" {
		c.HistoryKey = defaultHistoryKey
	}
	if c.MaxHistory <= 0 {
		c.MaxHistory = defaultMaxHistory
	}
	if c.HistoryTTL <= 0 {
		c.HistoryTTL = defaultHistoryTTL
	}
}

// Transport bridges Redis pub/sub to a local Hub for cross-service
// event delivery and persistent event history.
//
// Architecture (Option B):
//   - Publish() sends the event to Redis pub/sub AND stores it in a
//     Redis sorted set for history/replay.
//   - A background goroutine subscribes to the Redis channel and feeds
//     received events into the local Hub for WebSocket fan-out.
//   - Recent() / RecentFiltered() query the Redis sorted set so
//     reconnecting dashboards can catch up on missed events.
type Transport struct {
	client *goredis.Client
	hub    *alert.Hub
	cfg    TransportConfig
	cancel context.CancelFunc
	log    zerolog.Logger
}

// NewTransport creates a transport that bridges Redis pub/sub to
// the given local Hub. Call Start() to begin receiving events.
func NewTransport(client *goredis.Client, hub *alert.Hub, cfg TransportConfig) *Transport {
	cfg.applyDefaults()
	return &Transport{
		client: client,
		hub:    hub,
		cfg:    cfg,
		log:    newLogger("redis_transport"),
	}
}

// Start begins the background Redis subscriber goroutine. Events received
// from Redis are deserialized and published to the local Hub. This enables
// cross-service event delivery: execution publishes an event, gateway's
// Hub receives it and fans out to connected WebSocket clients.
//
// Call Close() to stop the subscriber.
func (t *Transport) Start(ctx context.Context) {
	subCtx, cancel := context.WithCancel(ctx)
	t.cancel = cancel

	go t.subscribeLoop(subCtx)

	t.log.Info().
		Str("channel", t.cfg.Channel).
		Str("history_key", t.cfg.HistoryKey).
		Int64("max_history", t.cfg.MaxHistory).
		Msg("redis_transport_started")
}

// Publish sends an event to the Redis pub/sub channel for real-time
// cross-service delivery AND stores it in the Redis sorted set for
// persistent history. The event is also published to the local Hub
// so local WebSocket clients receive it immediately without waiting
// for the Redis round-trip.
func (t *Transport) Publish(ctx context.Context, evt *alert.Event) {
	data, err := json.Marshal(evt)
	if err != nil {
		alert.AlertRedisErrors.WithLabelValues("marshal").Inc()
		t.log.Error().Err(err).Str("event_id", evt.ID).Msg("redis_transport_marshal_failed")
		return
	}

	// Publish to local Hub immediately (no Redis round-trip latency).
	t.hub.Publish(evt)

	// Publish to Redis pub/sub channel for other services.
	if err := t.client.Publish(ctx, t.cfg.Channel, data).Err(); err != nil {
		alert.AlertRedisErrors.WithLabelValues("publish").Inc()
		t.log.Error().Err(err).Str("event_id", evt.ID).Msg("redis_transport_publish_failed")
		return
	}
	alert.AlertRedisPublished.Inc()

	// Store in sorted set for history. Score is Unix nanosecond timestamp
	// for precise ordering. Using nanoseconds avoids score collisions
	// when multiple events fire within the same millisecond.
	score := float64(time.Now().UnixNano())
	if err := t.client.ZAdd(ctx, t.cfg.HistoryKey, goredis.Z{
		Score:  score,
		Member: data,
	}).Err(); err != nil {
		alert.AlertRedisErrors.WithLabelValues("history_write").Inc()
		t.log.Error().Err(err).Str("event_id", evt.ID).Msg("redis_transport_history_write_failed")
		return
	}

	// Trim history to max size (remove oldest entries beyond limit).
	excess := t.client.ZCard(ctx, t.cfg.HistoryKey).Val() - t.cfg.MaxHistory
	if excess > 0 {
		t.client.ZRemRangeByRank(ctx, t.cfg.HistoryKey, 0, excess-1)
	}

	// Refresh TTL as a safety net against orphaned keys.
	t.client.Expire(ctx, t.cfg.HistoryKey, t.cfg.HistoryTTL)

	alert.AlertHistorySize.Set(float64(t.client.ZCard(ctx, t.cfg.HistoryKey).Val()))
}

// Recent returns the last n events from Redis history, ordered oldest
// to newest. Returns nil if no events exist or on error.
func (t *Transport) Recent(ctx context.Context, n int64) []*alert.Event {
	if n <= 0 {
		return nil
	}

	// ZREVRANGE returns newest first; we reverse to oldest-first.
	results, err := t.client.ZRevRange(ctx, t.cfg.HistoryKey, 0, n-1).Result()
	if err != nil {
		alert.AlertRedisErrors.WithLabelValues("history_read").Inc()
		t.log.Error().Err(err).Msg("redis_transport_recent_failed")
		return nil
	}

	if len(results) == 0 {
		return nil
	}

	events := make([]*alert.Event, 0, len(results))
	for i := len(results) - 1; i >= 0; i-- {
		var evt alert.Event
		if err := json.Unmarshal([]byte(results[i]), &evt); err != nil {
			t.log.Warn().Err(err).Msg("redis_transport_history_unmarshal_skip")
			continue
		}
		events = append(events, &evt)
	}

	return events
}

// RecentFiltered returns the last n events from Redis history that match
// the given minimum severity, ordered oldest to newest.
func (t *Transport) RecentFiltered(ctx context.Context, n int64, minSeverity alert.EventSeverity) []*alert.Event {
	if minSeverity == "" {
		return t.Recent(ctx, n)
	}

	minRank := alert.SeverityRank(minSeverity)

	// Fetch more than n to account for filtering, capped at max history.
	fetchCount := n * 4
	if fetchCount > t.cfg.MaxHistory {
		fetchCount = t.cfg.MaxHistory
	}

	results, err := t.client.ZRevRange(ctx, t.cfg.HistoryKey, 0, fetchCount-1).Result()
	if err != nil {
		alert.AlertRedisErrors.WithLabelValues("history_read").Inc()
		t.log.Error().Err(err).Msg("redis_transport_recent_filtered_failed")
		return nil
	}

	matched := make([]*alert.Event, 0, n)
	for _, raw := range results {
		if int64(len(matched)) >= n {
			break
		}
		var evt alert.Event
		if err := json.Unmarshal([]byte(raw), &evt); err != nil {
			continue
		}
		if alert.SeverityRank(evt.Severity) >= minRank {
			matched = append(matched, &evt)
		}
	}

	// Reverse to chronological order (oldest first).
	for i, j := 0, len(matched)-1; i < j; i, j = i+1, j-1 {
		matched[i], matched[j] = matched[j], matched[i]
	}

	return matched
}

// RecentSince returns events from Redis history that occurred after the
// given event ID. This enables efficient catch-up: the dashboard sends
// the last event ID it received, and gets only newer events.
// Returns events in chronological order (oldest first).
func (t *Transport) RecentSince(ctx context.Context, lastEventID string, maxCount int64) []*alert.Event {
	if lastEventID == "" {
		return t.Recent(ctx, maxCount)
	}

	// Parse the timestamp prefix from the event ID (format: "20060102150405-hexbytes").
	timePart := splitEventID(lastEventID)
	if timePart == "" {
		return t.Recent(ctx, maxCount)
	}

	parsedTime, err := time.Parse("20060102150405", timePart)
	if err != nil {
		return t.Recent(ctx, maxCount)
	}

	// Use the parsed time as the minimum score (exclusive).
	minScore := fmt.Sprintf("(%d", parsedTime.UnixNano())

	results, err := t.client.ZRangeByScore(ctx, t.cfg.HistoryKey, &goredis.ZRangeBy{
		Min:   minScore,
		Max:   "+inf",
		Count: maxCount,
	}).Result()
	if err != nil {
		alert.AlertRedisErrors.WithLabelValues("history_read").Inc()
		t.log.Error().Err(err).Msg("redis_transport_recent_since_failed")
		return nil
	}

	events := make([]*alert.Event, 0, len(results))
	for _, raw := range results {
		var evt alert.Event
		if err := json.Unmarshal([]byte(raw), &evt); err != nil {
			continue
		}
		if evt.ID == lastEventID {
			continue
		}
		events = append(events, &evt)
	}

	return events
}

// HistoryCount returns the current number of events in Redis history.
func (t *Transport) HistoryCount(ctx context.Context) int64 {
	count, err := t.client.ZCard(ctx, t.cfg.HistoryKey).Result()
	if err != nil {
		t.log.Warn().Err(err).Msg("redis_transport_history_count_failed")
		return 0
	}
	return count
}

// Close stops the background subscriber and releases resources.
func (t *Transport) Close() {
	if t.cancel != nil {
		t.cancel()
	}
	t.log.Info().Msg("redis_transport_closed")
}

// subscribeLoop runs the Redis pub/sub subscriber. go-redis handles
// reconnection internally on transient errors.
func (t *Transport) subscribeLoop(ctx context.Context) {
	pubsub := t.client.Subscribe(ctx, t.cfg.Channel)
	defer pubsub.Close()

	t.log.Info().Str("channel", t.cfg.Channel).Msg("redis_subscriber_started")

	ch := pubsub.Channel()
	for {
		select {
		case <-ctx.Done():
			t.log.Info().Msg("redis_subscriber_stopped")
			return

		case msg, ok := <-ch:
			if !ok {
				t.log.Warn().Msg("redis_subscriber_channel_closed")
				return
			}

			alert.AlertRedisReceived.Inc()

			var evt alert.Event
			if err := json.Unmarshal([]byte(msg.Payload), &evt); err != nil {
				alert.AlertRedisErrors.WithLabelValues("unmarshal").Inc()
				t.log.Warn().Err(err).Msg("redis_subscriber_unmarshal_failed")
				continue
			}

			// Feed into local Hub for WebSocket fan-out.
			// Use DeliverRemote to avoid double-counting metrics
			// for events that originated from this same process.
			t.hub.DeliverRemote(&evt)
		}
	}
}

// splitEventID extracts the timestamp prefix from an event ID.
// Event IDs have format "20060102150405-hexbytes".
func splitEventID(id string) string {
	if len(id) < 14 {
		return ""
	}
	for i := 0; i < 14; i++ {
		if id[i] < '0' || id[i] > '9' {
			return ""
		}
	}
	return id[:14]
}

// newLogger creates a zerolog logger for the redis transport package.
func newLogger(component string) zerolog.Logger {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnixMs
	return zerolog.New(os.Stdout).With().
		Timestamp().
		Str("service", "alert").
		Str("component", component).
		Logger()
}
