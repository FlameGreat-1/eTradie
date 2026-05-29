package main

import (
	"context"
	"fmt"

	"github.com/flamegreat-1/etradie/src/auth"
)

// userLookup is the narrow surface reconcileIdentityProvider needs
// from auth.UserStore. Kept as a local interface for test seams.
type userLookup interface {
	GetUserByID(ctx context.Context, userID string) (*auth.User, error)
}

// tokenIssuer is the narrow surface for issuing service tokens.
type tokenIssuer interface {
	IssueServiceToken(userID, username string, role auth.Role, tier, status string) (string, error)
}

// reconcileIdentityProvider implements state.IdentityProvider by
// looking up the user record and minting a short-lived service token
// per call. Keeps no in-memory cache - this is a low-frequency code
// path (one cycle per ReconcileIntervalSecs, default 60s) so the
// extra DB hit is negligible and avoids the staleness/leak risks of
// a per-user token cache.
type reconcileIdentityProvider struct {
	users  userLookup
	tokens tokenIssuer
}

func newReconcileIdentityProvider(users userLookup, tokens tokenIssuer) *reconcileIdentityProvider {
	return &reconcileIdentityProvider{users: users, tokens: tokens}
}

func (p *reconcileIdentityProvider) IdentityContext(ctx context.Context, userID string) (context.Context, error) {
	u, err := p.users.GetUserByID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("reconcile identity: get user %s: %w", userID, err)
	}
	if u == nil || !u.Active {
		return nil, fmt.Errorf("reconcile identity: user %s missing or inactive", userID)
	}
	token, err := p.tokens.IssueServiceToken(u.ID, u.Username, u.Role, u.Tier, u.Status)
	if err != nil {
		return nil, fmt.Errorf("reconcile identity: issue service token for %s: %w", userID, err)
	}
	out := auth.InjectIdentity(ctx, u.ID, u.Username, u.Role, u.Tier, u.Status)
	out = auth.InjectTokenIntoContext(out, token)
	return out, nil
}
