// Package service contains the provider-agnostic billing business logic.
//
// It owns the transaction that ties idempotency, race-safe subscription
// upsert, and audit-trail append into one atomic unit, plus two post-
// commit side effects on every tier or status change:
//
//	1. Revoke the affected user's sessions so the next JWT refresh
//	   carries the new tier;
//	2. Publish a SUBSCRIPTION_* alert event on the shared channel so
//	   the SPA refetches billing state without waiting for React
//	   Query staleTime.
//
// The package depends on the store and events packages but NOT on auth.
// Session revocation and event publishing are delegated through the
// SessionRevoker / SubscriptionEventPublisher interfaces so the auth,
// billing, and alert trees stay decoupled — main.go composes the
// concrete AlertRedisPublisher that satisfies both at wiring time.
package service

import (
	"context"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
)

// SessionRevoker is the narrow contract the billing service needs
// from auth. *auth.SessionStore satisfies it directly via its
// RevokeAllUserSessions method, so no adapter is required.
type SessionRevoker interface {
	RevokeAllUserSessions(ctx context.Context, userID string) error
}

// NoopRevoker is a test-time stand-in. Production callers must wire a
// real SessionStore.
type NoopRevoker struct{}

func (NoopRevoker) RevokeAllUserSessions(_ context.Context, _ string) error { return nil }

// AlertPublisher is the narrow contract the billing service needs
// from the alert package. *alertredis.Transport satisfies it directly
// via its Publish method.
type AlertPublisher interface {
	Publish(ctx context.Context, evt *alert.Event)
}

// AlertRedisPublisher composes session revocation and SPA event
// publishing into a single type that satisfies BOTH SessionRevoker
// AND SubscriptionEventPublisher. main.go wires the same instance into
// service.NewService as the revoker so the existing
// post-commit code path (in subscription.go) reaches the publisher via
// type-assertion without changes to the service constructor signature.
type AlertRedisPublisher struct {
	Revoker   SessionRevoker
	Publisher AlertPublisher
	Log       zerolog.Logger
}

// RevokeAllUserSessions delegates to the wrapped SessionStore so
// AlertRedisPublisher is a drop-in replacement for the bare revoker.
func (a *AlertRedisPublisher) RevokeAllUserSessions(ctx context.Context, userID string) error {
	return a.Revoker.RevokeAllUserSessions(ctx, userID)
}

// PublishSubscriptionChange emits one alert.Event per tier/status
// change, with the user_id set so the gateway's hub routes it to ONLY
// that user's WebSocket subscribers. The event type is chosen based on
// the direction of change:
//
//   - SUBSCRIPTION_UPGRADED   when a free / unknown tier becomes paid,
//                             or a less-expensive paid tier becomes a
//                             more-expensive one;
//   - SUBSCRIPTION_DOWNGRADED when a paid tier becomes free;
//   - SUBSCRIPTION_STATUS_CHANGED in all other cases (e.g. active →
//                                 past_due) so the SPA can refresh
//                                 status badges.
//
// A short detached context is used so a slow publish cannot block the
// caller; Publish itself is best-effort by contract.
func (a *AlertRedisPublisher) PublishSubscriptionChange(_ context.Context, change SubscriptionChange) {
	evt := alert.NewEvent(
		alert.SourceSystem,
		classifySubscriptionChange(change),
		alert.SeverityInfo,
		buildSubscriptionMessage(change),
	).WithUserID(change.UserID).WithDetails(map[string]interface{}{
		"provider":        change.Provider,
		"event_id":        change.EventID,
		"previous_tier":   change.PreviousTier,
		"new_tier":        change.NewTier,
		"previous_status": change.PreviousStatus,
		"new_status":      change.NewStatus,
		"tier_changed":    change.TierChanged,
		"status_changed":  change.StatusChanged,
	})

	pubCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	a.Publisher.Publish(pubCtx, evt)
	a.Log.Info().
		Str("user_id", change.UserID).
		Str("event_type", evt.Type).
		Str("previous_tier", change.PreviousTier).
		Str("new_tier", change.NewTier).
		Str("previous_status", change.PreviousStatus).
		Str("new_status", change.NewStatus).
		Msg("billing_subscription_event_published")
}

// tierRank orders the platform's tiers by entitlement weight so
// classifySubscriptionChange can detect upgrades vs. downgrades.
// Higher = more entitled.
var tierRank = map[string]int{
	"":            -1, // never-seen sentinel
	"free":        0,
	"pro_byok":    1,
	"pro_managed": 2,
}

func classifySubscriptionChange(change SubscriptionChange) string {
	if change.TierChanged {
		prev := tierRank[change.PreviousTier]
		new := tierRank[change.NewTier]
		switch {
		case new > prev:
			return alert.TypeSubscriptionUpgraded
		case new < prev:
			return alert.TypeSubscriptionDowngraded
		}
	}
	return alert.TypeSubscriptionStatusChanged
}

func buildSubscriptionMessage(change SubscriptionChange) string {
	switch classifySubscriptionChange(change) {
	case alert.TypeSubscriptionUpgraded:
		return "Subscription upgraded to " + change.NewTier
	case alert.TypeSubscriptionDowngraded:
		return "Subscription downgraded to " + change.NewTier
	}
	return "Subscription status changed to " + change.NewStatus
}
