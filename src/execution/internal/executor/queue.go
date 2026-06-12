package executor

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// BurstQueue is a per-user FIFO order intake gate with a global
// concurrency ceiling. Section 3 of CHECKLIST.
//
// Why per-user: a single user submitting a burst of N orders must not
// block every other user's orders. A flat global queue would let one
// noisy user starve everyone else.
//
// Why also a global cap: the broker has a hard concurrency ceiling
// (a single mt-node Pod cannot handle 50 concurrent ORDER_SEND ZMQ
// requests; MetaAPI rate-limits per account). The global cap bounds
// the total number of in-flight broker calls cluster-wide.
//
// Why deadlines: an order that sits in queue for >2s is no longer
// the same trade idea - the broker price has moved. Better to drop
// it with a clear error than to fire stale orders.
type BurstQueue struct {
	maxConcurrent   int
	perUserCap      int
	defaultDeadline time.Duration

	mu        sync.Mutex
	perUser   map[string]int // count of in-flight per user_id
	globalSem chan struct{}  // bounded by maxConcurrent

	log zerolog.Logger
}

// QueueConfig holds the BurstQueue tunables. Zero values fall back to
// production-safe defaults (MaxConcurrent=8, PerUserCap=4, Deadline=2s).
type QueueConfig struct {
	MaxConcurrent   int
	PerUserCap      int
	DefaultDeadline time.Duration
}

var (
	QueueDepth = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "etradie_execution_queue_depth",
		Help: "In-flight order placement count by user_id",
	}, []string{"user_id"})

	QueueWaitSeconds = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_execution_queue_wait_seconds",
		Help:    "Time spent in the BurstQueue before execution",
		Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0},
	})

	QueueDrops = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_queue_drops_total",
		Help: "Orders dropped at the BurstQueue",
	}, []string{"reason"}) // reason: deadline | per_user_overflow | shutdown
)

// NewBurstQueue constructs the queue. Pass a fully-populated
// QueueConfig; zero values are replaced with defaults inline.
func NewBurstQueue(cfg QueueConfig) *BurstQueue {
	if cfg.MaxConcurrent <= 0 {
		cfg.MaxConcurrent = 8
	}
	if cfg.PerUserCap <= 0 {
		cfg.PerUserCap = 4
	}
	if cfg.DefaultDeadline <= 0 {
		cfg.DefaultDeadline = 2 * time.Second
	}
	return &BurstQueue{
		maxConcurrent:   cfg.MaxConcurrent,
		perUserCap:      cfg.PerUserCap,
		defaultDeadline: cfg.DefaultDeadline,
		perUser:         make(map[string]int),
		globalSem:       make(chan struct{}, cfg.MaxConcurrent),
		log:             observability.Logger("burst_queue"),
	}
}

// Enter blocks until the caller acquires a queue slot OR the deadline
// passes. Returns (release, nil) on success; the caller MUST call
// release() exactly once (defer is the recommended pattern). Returns
// an error on per-user overflow, deadline expiry, or shutdown.
func (q *BurstQueue) Enter(ctx context.Context, userID string) (func(), error) {
	start := time.Now()

	// Fast-path overflow check: do NOT block if this user is already
	// at the per-user cap. Surface the rejection immediately so the
	// gRPC server can return QUEUED_OVERFLOW to the caller.
	q.mu.Lock()
	if q.perUser[userID] >= q.perUserCap {
		q.mu.Unlock()
		QueueDrops.WithLabelValues("per_user_overflow").Inc()
		q.log.Warn().
			Str("user_id", userID).
			Int("in_flight", q.perUserCap).
			Int("cap", q.perUserCap).
			Msg("per_user_overflow_rejecting")
		return nil, fmt.Errorf("queue: per-user overflow (cap=%d in-flight for %s)", q.perUserCap, userID)
	}
	q.mu.Unlock()

	deadline := q.defaultDeadline
	if d, ok := ctx.Deadline(); ok {
		if remaining := time.Until(d); remaining > 0 && remaining < deadline {
			deadline = remaining
		}
	}

	timer := time.NewTimer(deadline)
	defer timer.Stop()

	select {
	case q.globalSem <- struct{}{}:
		// Acquired.
	case <-timer.C:
		QueueDrops.WithLabelValues("deadline").Inc()
		return nil, fmt.Errorf("queue: deadline exceeded after %s waiting for slot", deadline)
	case <-ctx.Done():
		QueueDrops.WithLabelValues("shutdown").Inc()
		return nil, fmt.Errorf("queue: ctx cancelled while waiting: %w", ctx.Err())
	}

	// Slot acquired - bump per-user counter and metric.
	q.mu.Lock()
	q.perUser[userID]++
	depth := q.perUser[userID]
	q.mu.Unlock()
	QueueDepth.WithLabelValues(userID).Set(float64(depth))
	QueueWaitSeconds.Observe(time.Since(start).Seconds())

	release := func() {
		q.mu.Lock()
		q.perUser[userID]--
		if q.perUser[userID] <= 0 {
			delete(q.perUser, userID)
			QueueDepth.DeleteLabelValues(userID)
		} else {
			QueueDepth.WithLabelValues(userID).Set(float64(q.perUser[userID]))
		}
		q.mu.Unlock()
		<-q.globalSem
	}
	return release, nil
}
