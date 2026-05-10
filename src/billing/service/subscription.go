package service

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/billing/events"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

// Service is the billing business-logic core. It is provider-agnostic: it
// only consumes events.NormalizedEvent and never touches HMAC, JSON, or
// HTTP. Construct one per process; safe for concurrent use.
type Service struct {
	subs      *store.SubscriptionStore
	processed *store.ProcessedEventStore
	audit     *store.SubscriptionEventStore
	revoker   SessionRevoker
	log       zerolog.Logger
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
// After commit, revoke the user's sessions iff tier or status changed.
// Revocation runs outside the transaction because it is best-effort — a
// transient revoke failure must not roll back a successfully-recorded
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
	customerID := nullableString(ev.ProviderCustomerID)
	subID := nullableString(ev.ProviderSubscriptionID)
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
	applied, prevTier, prevStatus, err := s.subs.UpsertSubscriptionTx(ctx, tx, row)
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

	// 4) Post-commit side effects: revoke sessions when tier OR status changed
	// so a downgraded user immediately loses Pro access and a fresh upgraded
	// user gets a fresh JWT carrying the new tier on next refresh.
	if applied && (outcome.TierChanged || outcome.StatusChanged) {
		if err := s.revoker.RevokeAllUserSessions(ctx, ev.UserID); err != nil {
			// Best-effort. Log loudly so operators can react.
			s.log.Error().
				Str("user_id", ev.UserID).
				Str("provider", ev.Provider).
				Str("event_id", ev.EventID).
				Err(err).
				Msg("billing_session_revoke_failed")
		}
	}

	return outcome, nil
}

func nullableString(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}
