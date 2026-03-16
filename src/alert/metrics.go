package alert

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// AlertEventsPublished counts events published to the hub, labeled by
	// source (GATEWAY, EXECUTION, etc.) and event type.
	AlertEventsPublished = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_alert_events_published_total",
		Help: "Total events published to the alert hub",
	}, []string{"source", "type", "severity"})

	// AlertEventsDropped counts events dropped because a subscriber's
	// channel buffer was full. A sustained non-zero rate here means
	// the dashboard is not consuming events fast enough.
	AlertEventsDropped = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_alert_events_dropped_total",
		Help: "Events dropped due to subscriber buffer full",
	}, []string{"subscriber_id"})

	// AlertActiveSubscribers tracks the current number of connected
	// WebSocket clients consuming events from the hub.
	AlertActiveSubscribers = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_alert_active_subscribers",
		Help: "Number of active WebSocket subscribers",
	})

	// AlertRedisPublished counts events published to the Redis pub/sub channel.
	AlertRedisPublished = promauto.NewCounter(prometheus.CounterOpts{
		Name: "etradie_alert_redis_published_total",
		Help: "Events published to Redis pub/sub channel",
	})

	// AlertRedisReceived counts events received from the Redis pub/sub channel.
	AlertRedisReceived = promauto.NewCounter(prometheus.CounterOpts{
		Name: "etradie_alert_redis_received_total",
		Help: "Events received from Redis pub/sub channel",
	})

	// AlertRedisErrors counts Redis pub/sub publish or subscribe errors.
	AlertRedisErrors = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_alert_redis_errors_total",
		Help: "Redis pub/sub errors by operation",
	}, []string{"operation"})

	// AlertHistorySize tracks the current number of events in the
	// in-memory ring buffer used for event replay.
	AlertHistorySize = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_alert_history_size",
		Help: "Current number of events in the history ring buffer",
	})
)
