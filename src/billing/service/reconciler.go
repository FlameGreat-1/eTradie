package service

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/billing/store"
)

// reconcilerEventName is recorded in billing_subscription_events when a
// reaper-driven demotion happens. It is NOT a provider event name so it
// cannot collide with any handled provider event.
const reconcilerEventName = "reconciler.period_end_expired"

// reconcilerProvider labels reaper-originated rows in the audit table.
// Distinct from "paddle" / "lemonsqueezy" so support and analytics queries
// can filter reaper actions vs. genuine provider events.
const reconcilerProvider = "reconciler"

// demotionChunkSize bounds the number of expired subscriptions processed in
// a single reconciler tick. Each user is demoted inside its own short
// transaction so a slow user record cannot block the rest.
const demotionChunkSize = 200

// ReconcilerMetrics is the narrow Prometheus surface the reconciler reports
// against. Implemented by *server.Metrics; an interface here so the
// reconciler package never imports the server package (no cycle), and so
// unit tests can supply a no-op stub.
type ReconcilerMetrics interface {
	ObserveReconcilerRun(outcome string, duration time.Duration)
	IncReconcilerDemoted(previousTier string)
	IncReconcilerError(stage string)
	AddIdempotencyPruned(rows int64)
}

// NoopReconcilerMetrics is the test-time stand-in.
type NoopReconcilerMetrics struct{}

func (NoopReconcilerMetrics) ObserveReconcilerRun(string, time.Duration) {}
func (NoopReconcilerMetrics) IncReconcilerDemoted(string)                {}
func (NoopReconcilerMetrics) IncReconcilerError(string)                  {}
func (NoopReconcilerMetrics) AddIdempotencyPruned(int64)                 {}

// ReconcilerConfig collects the runtime knobs the reconciler reads.
type ReconcilerConfig struct {
	// Interval between ticks. Each tick runs one full sweep + one prune.
	Interval time.Duration
	// IdempotencyRetentionDays controls how aggressively we prune
	// processed_webhook_events. Idempotency only matters during the
	// provider retry window (≤72h) but operators may want a longer
	// trail for debugging — the default in config.go is 30 days.
	IdempotencyRetentionDays int
}

// Reconciler runs the period-end demotion sweep and the idempotency-table
// retention janitor on a ticker.
//
// Optional dependencies (wired via setter methods so the constructor
// signature stays stable for existing callers):
//   - intents: when non-nil, the janitor also prunes
//     billing_checkout_intents rows whose expires_at has elapsed.
//   - usage: when non-nil, the janitor reaps stale LLM reservations
//     (status='held' AND expires_at <= NOW()) and calls MonthlyReset
//     on every subscription that just renewed.
type Reconciler struct {
	subs      *store.SubscriptionStore
	processed *store.ProcessedEventStore
	audit     *store.SubscriptionEventStore
	revoker   SessionRevoker
	metrics   ReconcilerMetrics
	log       zerolog.Logger
	cfg       ReconcilerConfig

	intents *store.CheckoutIntentStore // optional; nil disables intent prune
	usage   *store.UsageStore          // optional; nil disables LLM janitor
}

// WithCheckoutIntents attaches the checkout-intent store so the janitor
// prunes expired idempotency rows. Optional; main.go wires it after
// NewReconciler so the constructor signature does not change.
func (r *Reconciler) WithCheckoutIntents(intents *store.CheckoutIntentStore) {
	r.intents = intents
}

// WithUsageStore attaches the usage store so the reconciler can:
//  1. Reap stale LLM reservations (held + expired) as Refunds.
//  2. Call MonthlyReset on every user whose subscription just renewed.
//
// Optional; main.go wires it after NewReconciler.
func (r *Reconciler) WithUsageStore(usage *store.UsageStore) {
	r.usage = usage
}

// NewReconciler wires the dependencies. All parameters except metrics are
// required; pass NoopReconcilerMetrics if you have no Prometheus.
func NewReconciler(
	subs *store.SubscriptionStore,
	processed *store.ProcessedEventStore,
	audit *store.SubscriptionEventStore,
	revoker SessionRevoker,
	metrics ReconcilerMetrics,
	log zerolog.Logger,
	cfg ReconcilerConfig,
) (*Reconciler, error) {
	if subs == nil {
		return nil, errors.New("reconciler: subscription store is required")
	}
	if processed == nil {
		return nil, errors.New("reconciler: processed event store is required")
	}
	if audit == nil {
		return nil, errors.New("reconciler: audit store is required")
	}
	if revoker == nil {
		return nil, errors.New("reconciler: revoker is required")
	}
	if metrics == nil {
		metrics = NoopReconcilerMetrics{}
	}
	if cfg.Interval <= 0 {
		return nil, errors.New("reconciler: interval must be positive")
	}
	if cfg.IdempotencyRetentionDays <= 0 {
		return nil, errors.New("reconciler: idempotency retention days must be positive")
	}
	return &Reconciler{
		subs:      subs,
		processed: processed,
		audit:     audit,
		revoker:   revoker,
		metrics:   metrics,
		log:       log,
		cfg:       cfg,
	}, nil
}

// Run blocks until ctx is cancelled, running one sweep immediately and one
// per Interval thereafter. Safe to call once from main.go in a goroutine.
func (r *Reconciler) Run(ctx context.Context) {
	r.log.Info().
		Dur("interval", r.cfg.Interval).
		Int("idempotency_retention_days", r.cfg.IdempotencyRetentionDays).
		Msg("billing_reconciler_started")

	// Run once immediately so a freshly-started binary catches up on any
	// already-elapsed expirations without waiting a full interval.
	r.runOnce(ctx)

	ticker := time.NewTicker(r.cfg.Interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			r.log.Info().Msg("billing_reconciler_stopped")
			return
		case <-ticker.C:
			r.runOnce(ctx)
		}
	}
}

// runOnce executes a single sweep + prune cycle. Errors at any stage are
// logged and counted but do not abort the cycle; the next tick will retry.
func (r *Reconciler) runOnce(ctx context.Context) {
	start := time.Now()

	demoted, sweepErr := r.sweepExpired(ctx)
	pruned, pruneErr := r.pruneIdempotency(ctx)

	dur := time.Since(start)
	outcome := "ok"
	switch {
	case sweepErr != nil && pruneErr != nil:
		outcome = "sweep_and_prune_error"
	case sweepErr != nil:
		outcome = "sweep_error"
	case pruneErr != nil:
		outcome = "prune_error"
	}
	r.metrics.ObserveReconcilerRun(outcome, dur)

	r.log.Info().
		Int("demoted", demoted).
		Int64("idempotency_pruned", pruned).
		Dur("duration", dur).
		Str("outcome", outcome).
		Msg("billing_reconciler_tick")
}

// sweepExpired walks the expired-subscription set in chunks and demotes
// each user individually. Per-user errors are logged and counted but never
// abort the sweep.
func (r *Reconciler) sweepExpired(ctx context.Context) (int, error) {
	demoted := 0
	for {
		if err := ctx.Err(); err != nil {
			return demoted, err
		}

		now := time.Now().UTC()
		expired, err := r.subs.ListExpiredForDemotion(ctx, now, demotionChunkSize)
		if err != nil {
			r.metrics.IncReconcilerError("list")
			r.log.Error().Err(err).Msg("billing_reconciler_list_failed")
			return demoted, err
		}
		if len(expired) == 0 {
			return demoted, nil
		}

		for _, e := range expired {
			if err := ctx.Err(); err != nil {
				return demoted, err
			}
			if r.demoteOne(ctx, e, now) {
				demoted++
			}
		}

		// If the chunk wasn't full, we've processed every eligible row
		// for this tick. Avoid a final empty query.
		if len(expired) < demotionChunkSize {
			return demoted, nil
		}
	}
}

// demoteOne handles the transaction + audit + revocation for a single
// expired subscription. Returns true iff a row was actually demoted in this
// tick (false means the demotion was a no-op because a newer event won the
// event_timestamp race or the txn failed).
func (r *Reconciler) demoteOne(ctx context.Context, e store.ExpiredSubscription, now time.Time) bool {
	tx, err := r.subs.Pool().BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
	if err != nil {
		r.metrics.IncReconcilerError("begin_tx")
		r.log.Error().Err(err).Str("user_id", e.UserID).Msg("billing_reconciler_begin_tx_failed")
		return false
	}
	defer func() { _ = tx.Rollback(ctx) }()

	applied, prevTier, prevStatus, err := r.subs.DemoteToFreeTx(ctx, tx, e.UserID, now)
	if err != nil {
		r.metrics.IncReconcilerError("demote")
		r.log.Error().Err(err).Str("user_id", e.UserID).Msg("billing_reconciler_demote_failed")
		return false
	}
	if !applied {
		// A newer event landed concurrently — leave the result alone.
		r.log.Info().
			Str("user_id", e.UserID).
			Str("previous_tier", e.Tier).
			Str("previous_status", e.Status).
			Msg("billing_reconciler_demote_skipped_out_of_order")
		return false
	}

	// Append the audit row inside the same transaction so a demotion
	// without a paired audit cannot happen. The event_id is a synthesised
	// idempotent key in case the same reconciler tick somehow runs twice
	// concurrently against the same user (different replicas, etc.).
	auditEventID := fmt.Sprintf("reconciler:%s:%d", e.UserID, e.CurrentPeriodEnd.Unix())
	if err := r.audit.AppendTx(ctx, tx, &store.SubscriptionEvent{
		UserID:         e.UserID,
		Provider:       reconcilerProvider,
		EventName:      reconcilerEventName,
		EventID:        auditEventID,
		PreviousTier:   prevTier,
		NewTier:        "free",
		PreviousStatus: prevStatus,
		NewStatus:      "canceled",
		EventTimestamp: now,
	}); err != nil {
		r.metrics.IncReconcilerError("audit")
		r.log.Error().Err(err).Str("user_id", e.UserID).Msg("billing_reconciler_audit_failed")
		return false
	}

	if err := tx.Commit(ctx); err != nil {
		r.metrics.IncReconcilerError("commit")
		r.log.Error().Err(err).Str("user_id", e.UserID).Msg("billing_reconciler_commit_failed")
		return false
	}

	r.metrics.IncReconcilerDemoted(prevTier)
	r.log.Info().
		Str("user_id", e.UserID).
		Str("previous_tier", prevTier).
		Str("previous_status", prevStatus).
		Str("provider", e.Provider).
		Str("provider_subscription_id", e.ProviderSubscriptionID).
		Time("period_ended_at", e.CurrentPeriodEnd).
		Msg("billing_reconciler_demoted")

	// Post-commit: revoke sessions so the next JWT refresh carries free.
	// Best-effort; a transient revoke failure must not roll back the
	// already-committed demotion. Run with a short detached context so
	// the reconciler is not blocked by a stuck auth_sessions update.
	revokeCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := r.revoker.RevokeAllUserSessions(revokeCtx, e.UserID); err != nil {
		r.log.Error().Err(err).Str("user_id", e.UserID).Msg("billing_reconciler_revoke_failed")
	}

	// Post-commit: reset the monthly LLM token counters so the user's
	// quota window starts fresh on their next billing period. Best-effort;
	// a failure here does not roll back the already-committed demotion.
	if r.usage != nil {
		resetCtx, resetCancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer resetCancel()
		if err := r.usage.MonthlyReset(resetCtx, e.UserID, now); err != nil {
			r.log.Error().Err(err).Str("user_id", e.UserID).Msg("billing_reconciler_monthly_reset_failed")
		} else {
			r.log.Info().Str("user_id", e.UserID).Msg("billing_reconciler_monthly_reset_applied")
		}
	}

	return true
}

// pruneIdempotency deletes processed_webhook_events older than the
// retention window, expired billing_checkout_intents rows (when the
// intent store is wired), and stale LLM reservations (when the usage
// store is wired). The DELETEs are index-scanned so the wall-clock
// cost is bounded even against a multi-million-row table.
func (r *Reconciler) pruneIdempotency(ctx context.Context) (int64, error) {
	cutoff := time.Now().UTC().Add(-time.Duration(r.cfg.IdempotencyRetentionDays) * 24 * time.Hour)
	n, err := r.processed.PruneOlderThan(ctx, cutoff)
	if err != nil {
		r.metrics.IncReconcilerError("prune")
		r.log.Error().Err(err).Msg("billing_reconciler_prune_failed")
		return 0, err
	}
	if n > 0 {
		r.metrics.AddIdempotencyPruned(n)
		r.log.Info().Int64("rows", n).Time("cutoff", cutoff).Msg("billing_reconciler_pruned")
	}

	// Optional: prune expired checkout intents. Errors do not abort the
	// tick; the next pass retries. We count failures under the same
	// `prune` stage label so existing dashboards see one consistent
	// signal for janitor health.
	if r.intents != nil {
		intentRows, intentErr := r.intents.PruneExpired(ctx)
		if intentErr != nil {
			r.metrics.IncReconcilerError("prune")
			r.log.Error().Err(intentErr).Msg("billing_reconciler_intent_prune_failed")
		} else if intentRows > 0 {
			r.log.Info().Int64("rows", intentRows).Msg("billing_reconciler_intent_pruned")
		}
	}

	// Optional: reap stale LLM reservations (held + TTL elapsed).
	// These are reservations where the engine called Reserve but never
	// called Commit or Refund (engine crash, network partition, etc.).
	// Treating them as Refunds returns the provisional debit to the
	// user's quota so they are not permanently penalised for a failed
	// call. The janitor runs at most 500 rows per tick to bound the
	// wall-clock cost.
	if r.usage != nil {
		reaped, reapErr := r.usage.JanitorReapStaleReservations(ctx)
		if reapErr != nil {
			r.metrics.IncReconcilerError("prune")
			r.log.Error().Err(reapErr).Msg("billing_reconciler_llm_reservation_reap_failed")
		} else if reaped > 0 {
			r.log.Info().Int64("rows", reaped).Msg("billing_reconciler_llm_reservations_reaped")
		}
	}

	return n, nil
}
