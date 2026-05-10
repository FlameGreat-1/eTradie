package service

import (
	"context"
	"errors"

	"github.com/flamegreat-1/etradie/src/billing/events"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

// ErrCannotResolveUser indicates the event arrived without user_id in custom
// data and no existing billing_subscriptions row matches
// (provider, provider_subscription_id). The HTTP layer maps this to 422 so
// the provider stops retrying — a manual reconciliation is required.
var ErrCannotResolveUser = errors.New("billing: cannot resolve user for event")

// resolveUserID fills NormalizedEvent.UserID when the parser left it empty.
// It looks up an existing subscription row by (provider, provider_subscription_id);
// if found, the row's user_id is the canonical owner of this subscription and
// is used for the upsert and revocation paths.
func (s *Service) resolveUserID(ctx context.Context, ev *events.NormalizedEvent) error {
	if ev.UserID != "" {
		return nil
	}
	if ev.ProviderSubscriptionID == "" {
		return ErrCannotResolveUser
	}
	existing, err := s.subs.GetByProviderSubscriptionID(ctx, ev.Provider, ev.ProviderSubscriptionID)
	if err != nil {
		if errors.Is(err, store.ErrSubscriptionNotFound) {
			return ErrCannotResolveUser
		}
		return err
	}
	ev.UserID = existing.UserID
	// If the parser couldn't determine a tier (status-only update on a paused
	// subscription whose price wasn't in the map), inherit the stored tier so
	// we don't accidentally regress to "".
	if ev.Tier == "" {
		ev.Tier = events.Tier(existing.Tier)
	}
	return nil
}
