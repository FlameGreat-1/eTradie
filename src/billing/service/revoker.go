// Package service contains the provider-agnostic billing business logic.
//
// It owns the transaction that ties idempotency, race-safe subscription
// upsert, and audit-trail append into one atomic unit, plus the side-effect
// of revoking the affected user's sessions on tier change.
//
// The package depends on the store and events packages but NOT on auth.
// Session revocation is delegated through the SessionRevoker interface so
// the auth and billing trees stay decoupled — main.go wires *auth.SessionStore
// in as the implementation.
package service

import "context"

// SessionRevoker is the narrow contract the billing service needs from auth.
// *auth.SessionStore satisfies it directly via its RevokeAllUserSessions
// method, so no adapter is required.
type SessionRevoker interface {
	RevokeAllUserSessions(ctx context.Context, userID string) error
}

// NoopRevoker is a test-time stand-in. Production callers must wire a real
// SessionStore.
type NoopRevoker struct{}

func (NoopRevoker) RevokeAllUserSessions(_ context.Context, _ string) error { return nil }
