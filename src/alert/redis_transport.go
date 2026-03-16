package alert

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
	zerolog "github.com/rs/zerolog"
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

// RedisTransportConfig holds configuration for the Redis transport.
type RedisTransportConfig struct {
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

func (c *RedisTransportConfig) applyDefaults() {
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

// RedisTransport bridges Redis pub/sub to a local Hub for cross-service
// event delivery and persistent event history.
//
// Architecture (Option B):
//   - Publish() sends the event to Redis pub/sub AND stores it in a
//     Redis sorted set for history/replay.
//   - A background goroutine subscribes to the Redis channel and feeds
//     received events into the local Hub for WebSocket fan-out.
//   - Recent() / RecentFiltered() query the Redis sorted set so
//     reconnecting dashboards can catch up on missed events.
type RedisTransport struct {
	client  *redis.Client
	hub     *Hub
	cfg     RedisTransportConfig
	cancel  context.CancelFunc
	log     zerolog.Logger
}

// NewRedisTransport creates a transport that bridges Redis pub/sub to
// the given local Hub. Call Start() to begin receiving events.
func NewRedisTransport(client *redis.Client, hub *Hub, cfg RedisTransportConfig) *RedisTransport {
	cfg.applyDefaults()
	return &RedisTransport{
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
func (t *RedisTransport) Start(ctx context.Context) {
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
func (t *RedisTransport) Publish(ctx context.Context, evt *Event) {
	data, err := json.Marshal(evt)
	if err != nil {
		AlertRedisErrors.WithLabelValues("marshal").Inc()
		t.log.Error().Err(err).Str("event_id", evt.ID).Msg("redis_transport_marshal_failed")
		return
	}

	// Publish to local Hub immediately (no Redis round-trip latency).
	t.hub.Publish(evt)

	// Publish to Redis pub/sub channel for other services.
	if err := t.client.Publish(ctx, t.cfg.Channel, data).Err(); err != nil {
		AlertRedisErrors.WithLabelValues("publish").Inc()
		t.log.Error().Err(err).Str("event_id", evt.ID).Msg("redis_transport_publish_failed")
		return
	}
	AlertRedisPublished.Inc()

	// Store in sorted set for history. Score is Unix nanosecond timestamp
	// for precise ordering. Using nanoseconds avoids score collisions
	// when multiple events fire within the same millisecond.
	score := float64(time.Now().UnixNano())
	if err := t.client.ZAdd(ctx, t.cfg.HistoryKey, redis.Z{
		Score:  score,
		Member: data,
	}).Err(); err != nil {
		AlertRedisErrors.WithLabelValues("history_write").Inc()
		t.log.Error().Err(err).Str("event_id", evt.ID).Msg("redis_transport_history_write_failed")
		return
	}

	// Trim history to max size (remove oldest entries beyond limit).
	// ZREMRANGEBYRANK removes elements from index 0 (lowest score/oldest)
	// up to -(maxHistory+1), keeping only the newest maxHistory entries.
	excess := t.client.ZCard(ctx, t.cfg.HistoryKey).Val() - t.cfg.MaxHistory
	if excess > 0 {
		t.client.ZRemRangeByRank(ctx, t.cfg.HistoryKey, 0, excess-1)
	}

	// Refresh TTL as a safety net against orphaned keys.
	t.client.Expire(ctx, t.cfg.HistoryKey, t.cfg.HistoryTTL)

	AlertHistorySize.Set(float64(t.client.ZCard(ctx, t.cfg.HistoryKey).Val()))
}

// Recent returns the last n events from Redis history, ordered oldest
// to newest. Returns nil if no events exist or on error.
func (t *RedisTransport) Recent(ctx context.Context, n int64) []*Event {
	if n <= 0 {
		return nil
	}

	// ZREVRANGE returns newest first; we want oldest-to-newest, so we
	// fetch the last n and reverse.
	results, err := t.client.ZRevRange(ctx, t.cfg.HistoryKey, 0, n-1).Result()
	if err != nil {
		AlertRedisErrors.WithLabelValues("history_read").Inc()
		t.log.Error().Err(err).Msg("redis_transport_recent_failed")
		return nil
	}

	if len(results) == 0 {
		return nil
	}

	// Reverse to chronological order (oldest first).
	events := make([]*Event, 0, len(results))
	for i := len(results) - 1; i >= 0; i-- {
		var evt Event
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
func (t *RedisTransport) RecentFiltered(ctx context.Context, n int64, minSeverity EventSeverity) []*Event {
	if minSeverity == "" {
		return t.Recent(ctx, n)
	}

	minRank := severityRank[minSeverity]

	// Fetch more than n to account for filtering. We fetch up to 4x
	// the requested count, capped at the max history size.
	fetchCount := n * 4
	if fetchCount > t.cfg.MaxHistory {
		fetchCount = t.cfg.MaxHistory
	}

	results, err := t.client.ZRevRange(ctx, t.cfg.HistoryKey, 0, fetchCount-1).Result()
	if err != nil {
		AlertRedisErrors.WithLabelValues("history_read").Inc()
		t.log.Error().Err(err).Msg("redis_transport_recent_filtered_failed")
		return nil
	}

	// Walk from newest to oldest, collecting matches up to n.
	matched := make([]*Event, 0, n)
	for _, raw := range results {
		if int64(len(matched)) >= n {
			break
		}
		var evt Event
		if err := json.Unmarshal([]byte(raw), &evt); err != nil {
			continue
		}
		if severityRank[evt.Severity] >= minRank {
			matched = append(matched, &evt)
		}
	}

	// Reverse to chronological order (oldest first).
	for i, j := 0, len(matched)-1; i < j; i, j = i+1, j-1 {
		matched[i], matched[j] = matched[j], matched[i]
	}

	return matched
}

// Close stops the background subscriber and releases resources.
func (t *RedisTransport) Close() {
	if t.cancel != nil {
		t.cancel()
	}
	t.log.Info().Msg("redis_transport_closed")
}

// subscribeLoop runs the Redis pub/sub subscriber. It reconnects
// automatically on errors (go-redis handles reconnection internally).
func (t *RedisTransport) subscribeLoop(ctx context.Context) {
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

			AlertRedisReceived.Inc()

			var evt Event
			if err := json.Unmarshal([]byte(msg.Payload), &evt); err != nil {
				AlertRedisErrors.WithLabelValues("unmarshal").Inc()
				t.log.Warn().Err(err).Msg("redis_subscriber_unmarshal_failed")
				continue
			}

			// Feed into local Hub for WebSocket fan-out.
			// Skip the metrics increment in Hub.Publish since we already
			// counted this event when it was originally published.
			t.hub.deliverToSubscribers(&evt)
		}
	}
}

// HistoryCount returns the current number of events in Redis history.
func (t *RedisTransport) HistoryCount(ctx context.Context) int64 {
	count, err := t.client.ZCard(ctx, t.cfg.HistoryKey).Result()
	if err != nil {
		t.log.Warn().Err(err).Msg("redis_transport_history_count_failed")
		return 0
	}
	return count
}

// RecentSince returns events from Redis history that occurred after the
// given event ID. This enables efficient catch-up: the dashboard sends
// the last event ID it received, and gets only newer events.
// Returns events in chronological order (oldest first).
func (t *RedisTransport) RecentSince(ctx context.Context, lastEventID string, maxCount int64) []*Event {
	if lastEventID == "" {
		return t.Recent(ctx, maxCount)
	}

	// Parse the timestamp prefix from the event ID (format: "20060102150405-hexbytes").
	// We use this as the minimum score for the range query.
	parts := splitEventID(lastEventID)
	if parts == "" {
		return t.Recent(ctx, maxCount)
	}

	parsedTime, err := time.Parse("20060102150405", parts)
	if err != nil {
		return t.Recent(ctx, maxCount)
	}

	// Use the parsed time as the minimum score (exclusive).
	minScore := fmt.Sprintf("(%d", parsedTime.UnixNano())

	results, err := t.client.ZRangeByScore(ctx, t.cfg.HistoryKey, &redis.ZRangeBy{
		Min:   minScore,
		Max:   "+inf",
		Count: maxCount,
	}).Result()
	if err != nil {
		AlertRedisErrors.WithLabelValues("history_read").Inc()
		t.log.Error().Err(err).Msg("redis_transport_recent_since_failed")
		return nil
	}

	events := make([]*Event, 0, len(results))
	for _, raw := range results {
		var evt Event
		if err := json.Unmarshal([]byte(raw), &evt); err != nil {
			continue
		}
		// Skip the event with the given ID itself.
		if evt.ID == lastEventID {
			continue
		}
		events = append(events, &evt)
	}

	return events
}

// splitEventID extracts the timestamp prefix from an event ID.
// Event IDs have format "20060102150405-hexbytes".
func splitEventID(id string) string {
	if len(id) < 14 {
		return ""
	}
	// Validate that the first 14 chars are digits.
	for i := 0; i < 14; i++ {
		if id[i] < '0' || id[i] > '9' {
			return ""
		}
	}
	return id[:14]
}

// Ensure strconv is used (for potential future use in score formatting).
var _ = strconv.Itoa
