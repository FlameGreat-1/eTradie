package service

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/billing/events"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

// Service is the billing business-logic core. It is provider-agnostic: it
// only consumes events.NormalizedEvent and never touches HMAC, JSON, or
// HTTP. Construct one per process; safe for concurrent use.
//
// Optional dependencies (wired via setter methods so the constructor
// signature stays stable for existing callers and tests):
//   - usage: when non-nil, HandleEvent calls UsageStore.MonthlyReset on
//     fresh insertions into managed tiers, on managed-tier renewals
//     (current_period_end strictly advanced), and on upgrades INTO a
//     managed tier. This keeps the user's LLM-token quota window
//     aligned with the provider's billing cycle. Without it, the
//     monthly counters would only reset on demotion to free.
type Service struct {
	subs      *store.SubscriptionStore
	processed *store.ProcessedEventStore
	audit     *store.SubscriptionEventStore
	revoker   SessionRevoker
	log       zerolog.Logger

	usage *store.UsageStore // optional; nil disables LLM monthly-reset wiring
}

// NewService wires the dependencies. All parameters are required.
func NewService(
	subs *store.SubscriptionStore,
	processed *store.ProcessedEventStore,
	audit *store.SubscriptionEventStore,
	revoker SessionRevoker,
	log zerolog.Logger,
) *Service {
	return &Service{
		subs:      subs,
		processed: processed,
		audit:     audit,
		revoker:   revoker,
		log:       log,
	}
}

// WithUsageStore attaches the LLM usage store so HandleEvent can reset
// the monthly token counters whenever a managed-tier subscription is
// created, upgraded into, or renewed. Optional; main.go wires it after
// NewService so the constructor signature does not change.
func (s *Service) WithUsageStore(usage *store.UsageStore) {
	s.usage = usage
}

// Outcome describes what HandleEvent did so the HTTP layer can choose the
// right response code and the metrics layer can label the result.
type Outcome struct {
	AlreadyProcessed bool   // duplicate webhook — no DB write happened
	Applied          bool   // subscription row was inserted or updated
	OutOfOrder       bool   // newer event_timestamp already stored — dropped on purpose
	TierChanged      bool   // previous_tier != new_tier; sessions were revoked
	StatusChanged    bool   // previous_status != new_status
	UserID           string // resolved platform user id
}

// HandleEvent applies a verified, parsed webhook event to the system.
//
// All DB work is wrapped in a single transaction:
//
//	1) Mark the (provider, event_id) processed; if already processed, abort
//	   with AlreadyProcessed=true. The provider gets a 200 ACK and stops
//	   retrying.
//	2) UPSERT the subscription row, race-safe by event_timestamp.
//	3) Append an immutable audit record.
//
// After commit, three best-effort side effects fire:
//   - Revoke the user's sessions iff tier or status changed.
//   - Publish a SUBSCRIPTION_* realtime event for the SPA.
//   - Reset the user's monthly LLM token counters iff this event
//     represents a managed-tier subscription entering or renewing an
//     active billing cycle.
//
// All three run outside the transaction because they are best-effort: a
// transient failure must not roll back a successfully-recorded
// subscription change. We log and continue.
func (s *Service) HandleEvent(ctx context.Context, ev *events.NormalizedEvent) (Outcome, error) {
	if ev == nil {
		return Outcome{}, errors.New("billing: nil event")
	}
	if err := s.resolveUserID(ctx, ev); err != nil {
		return Outcome{}, err
	}
	if ev.UserID == "" {
		return Outcome{}, ErrCannotResolveUser
	}

	tx, err := s.subs.Pool().BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
	if err != nil {
		return Outcome{}, fmt.Errorf("billing: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	// 1) Idempotency.
	isNew, err := s.processed.MarkProcessedTx(ctx, tx, ev.Provider, ev.EventID, ev.EventName)
	if err != nil {
		return Outcome{}, fmt.Errorf("billing: mark processed: %w", err)
	}
	if !isNew {
		// Duplicate delivery. Don't touch state. The defer will roll back the
		// (no-op) transaction. Provider gets 200; retries stop.
		return Outcome{AlreadyProcessed: true, UserID: ev.UserID}, nil
	}

	// 2) Race-safe subscription upsert.
	provider := ev.Provider
	customerID := nullablePtr(ev.ProviderCustomerID)
	subID := nullablePtr(ev.ProviderSubscriptionID)
	row := &store.Subscription{
		UserID:                 ev.UserID,
		Tier:                   string(ev.Tier),
		Status:                 string(ev.Status),
		PaymentProvider:        &provider,
		ProviderCustomerID:     customerID,
		ProviderSubscriptionID: subID,
		CurrentPeriodEnd:       ev.CurrentPeriodEnd,
		EventTimestamp:         ev.EventTimestamp,
	}
	applied, prevTier, prevStatus, prevPeriodEnd, err := s.subs.UpsertSubscriptionTx(ctx, tx, row)
	if err != nil {
		return Outcome{}, fmt.Errorf("billing: upsert subscription: %w", err)
	}

	outcome := Outcome{
		Applied:    applied,
		OutOfOrder: !applied,
		UserID:     ev.UserID,
	}

	// 3) Audit (only on applied changes — we don't want audit rows for
	// out-of-order events that didn't change state).
	if applied {
		outcome.TierChanged = prevTier != string(ev.Tier) && prevTier != ""
		outcome.StatusChanged = prevStatus != string(ev.Status) && prevStatus != ""
		// On insert (no prev), still record "changed from nothing" as a tier change
		// so the revocation path runs and the audit row is meaningful.
		if prevTier == "" && string(ev.Tier) != "" {
			outcome.TierChanged = true
		}
		if prevStatus == "" && string(ev.Status) != "" {
			outcome.StatusChanged = true
		}

		if err := s.audit.AppendTx(ctx, tx, &store.SubscriptionEvent{
			UserID:         ev.UserID,
			Provider:       ev.Provider,
			EventName:      ev.EventName,
			EventID:        ev.EventID,
			PreviousTier:   prevTier,
			NewTier:        string(ev.Tier),
			PreviousStatus: prevStatus,
			NewStatus:      string(ev.Status),
			EventTimestamp: ev.EventTimestamp,
		}); err != nil {
			return Outcome{}, fmt.Errorf("billing: append audit: %w", err)
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return Outcome{}, fmt.Errorf("billing: commit: %w", err)
	}

	// 4) Post-commit side effects.
	//
	// Revocation forces the next /auth/refresh to mint a JWT carrying
	// the new tier so a downgraded user immediately loses Pro access
	// and a fresh upgraded user gets the new entitlement on the next
	// request.
	//
	// Publication is what the SPA listens for: without it the
	// dashboard would show the stale ['billing'] / ['auth', 'me']
	// query data for up to React Query's staleTime after a successful
	// payment. The publisher is reached via a type-assertion so the
	// Service constructor stays decoupled from the alert package; the
	// production wiring composes a single AlertRedisPublisher that
	// satisfies BOTH SessionRevoker and SubscriptionEventPublisher
	// (see src/billing/cmd/server/main.go).
	//
	// MonthlyReset zeroes the LLM token counters when this event
	// represents a managed-tier billing cycle entering or rolling over.
	// See shouldResetMonthlyLLM below for the precise predicate.
	//
	// All three side effects are best-effort. A transient failure must
	// not roll back the committed subscription change; we log loudly
	// so operators can react instead.
	if applied && (outcome.TierChanged || outcome.StatusChanged) {
		if err := s.revoker.RevokeAllUserSessions(ctx, ev.UserID); err != nil {
			s.log.Error().
				Str("user_id", ev.UserID).
				Str("provider", ev.Provider).
				Str("event_id", ev.EventID).
				Err(err).
				Msg("billing_session_revoke_failed")
		}

		if publisher, ok := s.revoker.(SubscriptionEventPublisher); ok {
			publisher.PublishSubscriptionChange(ctx, SubscriptionChange{
				UserID:         ev.UserID,
				Provider:       ev.Provider,
				EventID:        ev.EventID,
				PreviousTier:   prevTier,
				NewTier:        string(ev.Tier),
				PreviousStatus: prevStatus,
				NewStatus:      string(ev.Status),
				TierChanged:    outcome.TierChanged,
				StatusChanged:  outcome.StatusChanged,
			})
		} else {
			// The constructor accepts any SessionRevoker; in production
			// the wired type also implements SubscriptionEventPublisher.
			// If a deployment somehow loses the publisher (e.g. a test
			// using a bare revoker) the dashboard would silently miss
			// the realtime tier-refresh. Log once so the gap is visible
			// in operator logs instead of being a silent regression.
			s.log.Warn().
				Str("user_id", ev.UserID).
				Str("provider", ev.Provider).
				Str("event_id", ev.EventID).
				Msg("billing_subscription_publisher_unwired")
		}
	}

	// LLM monthly counter reset for managed-tier billing-cycle events.
	// Independent of the revocation/publish gate above because a renewal
	// of an already-active managed subscription (status unchanged, tier
	// unchanged, period_end advanced) MUST reset the counters even
	// though TierChanged and StatusChanged are both false.
	if applied && s.usage != nil && shouldResetMonthlyLLM(prevTier, prevPeriodEnd, ev) {
		resetCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		if err := s.usage.MonthlyReset(resetCtx, ev.UserID, ev.EventTimestamp); err != nil {
			s.log.Error().
				Str("user_id", ev.UserID).
				Str("provider", ev.Provider).
				Str("event_id", ev.EventID).
				Str("prev_tier", prevTier).
				Str("new_tier", string(ev.Tier)).
				Err(err).
				Msg("billing_monthly_llm_reset_failed")
		} else {
			s.log.Info().
				Str("user_id", ev.UserID).
				Str("provider", ev.Provider).
				Str("event_id", ev.EventID).
				Str("prev_tier", prevTier).
				Str("new_tier", string(ev.Tier)).
				Msg("billing_monthly_llm_reset_applied")
		}
		cancel()
	}

	return outcome, nil
}

// shouldResetMonthlyLLM decides whether HandleEvent must zero the user's
// monthly LLM token counters. The intent is to keep the LLM quota window
// aligned with the provider's billing cycle exactly, mirroring how
// industry-standard SaaS platforms (Stripe, Paddle, Lemon Squeezy)
// expose quota usage to their managed-AI customers.
//
// Trigger conditions (any one is sufficient):
//
//  1. Fresh insertion: no previous row existed AND the new tier is
//     managed/admin AND the new status is active. The user just
//     started a managed subscription; reset establishes a clean window.
//
//  2. Tier upgrade into managed: previous tier was non-managed (or
//     empty) AND new tier is managed/admin AND new status is active.
//     The user just upgraded from BYOK / free; reset gives them the
//     full new-window allocation.
//
//  3. Renewal: previous tier was already managed/admin AND new tier is
//     still managed/admin AND new status is active AND the incoming
//     CurrentPeriodEnd is strictly later than the previous one. This
//     catches subscription.renewed / subscription.updated events that
//     advance the billing period without changing tier or status.
//
// A user being demoted to free is handled separately by the reconciler,
// not here.
func shouldResetMonthlyLLM(
	prevTier string,
	prevPeriodEnd *time.Time,
	ev *events.NormalizedEvent,
) bool {
	if !isManagedTier(string(ev.Tier)) {
		return false
	}
	if string(ev.Status) != string(events.StatusActive) {
		return false
	}

	prevManaged := isManagedTier(prevTier)

	// Cases 1 and 2: insertion or upgrade INTO managed.
	if !prevManaged {
		return true
	}

	// Case 3: renewal — previous and new are both managed and active,
	// and the billing period has advanced. Without a previous
	// period_end we cannot prove the period rolled over; treat as
	// no-op so we do not over-reset on a same-period status flap
	// (e.g. past_due → active without a new invoice).
	if prevPeriodEnd == nil || ev.CurrentPeriodEnd == nil {
		return false
	}
	return ev.CurrentPeriodEnd.After(*prevPeriodEnd)
}

// isManagedTier reports whether the tier string represents a tier whose
// LLM calls hit the platform key and therefore consume the platform-side
// metered quota. Case-insensitive trim to match how the rest of the
// codebase normalises tier strings (see auth.Config.LLMQuotaPolicyForTier).
func isManagedTier(tier string) bool {
	switch strings.ToLower(strings.TrimSpace(tier)) {
	case "pro_managed", "admin":
		return true
	}
	return false
}

// nullablePtr converts an empty string to a nil *string so the optional
// pointer columns on store.Subscription (PaymentProvider, ProviderCustomerID,
// ProviderSubscriptionID) stay NULL rather than holding empty strings.
//
// This is intentionally distinct from store.nullableString, which returns
// any and targets pgx Exec parameters for the audit table's nullable
// text columns. The two helpers live in different packages, return
// different Go types, and serve different downstream consumers; merging
// them would force one consumer to convert at every call site.
func nullablePtr(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}
