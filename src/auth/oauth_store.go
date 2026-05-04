package auth

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ---------------------------------------------------------------------------
// OAuthFlowStore
//
// Holds the short-lived authorize-step records that bind state, PKCE
// verifier, and OIDC nonce to the eventual callback. Single-use is
// enforced atomically via UPDATE ... WHERE consumed = FALSE
// RETURNING ... so a replayed callback is rejected even when two
// requests race.
// ---------------------------------------------------------------------------

type OAuthFlowStore struct {
	pool *pgxpool.Pool
}

func NewOAuthFlowStore(pool *pgxpool.Pool) *OAuthFlowStore {
	return &OAuthFlowStore{pool: pool}
}

// Create persists a new authorize-step record. The caller is
// responsible for generating cryptographically-random state, nonce,
// flow_id, and PKCE verifier values via GenerateOAuthSecret.
func (s *OAuthFlowStore) Create(ctx context.Context, f *OAuthFlow) error {
	if f.Provider == "" || f.State == "" || f.FlowID == "" || f.CodeVerifier == "" || f.Nonce == "" {
		return fmt.Errorf("oauth flow: required fields missing")
	}
	_, err := s.pool.Exec(ctx,
		`INSERT INTO auth_oauth_flows (
		        flow_id, provider, state, code_verifier, nonce,
		        redirect_uri, return_to, created_at, expires_at, consumed
		 ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,FALSE)`,
		f.FlowID, f.Provider, f.State, f.CodeVerifier, f.Nonce,
		f.RedirectURI, f.ReturnTo, f.CreatedAt, f.ExpiresAt,
	)
	if err != nil {
		if strings.Contains(err.Error(), "duplicate key") {
			return fmt.Errorf("oauth flow: flow_id or state already exists")
		}
		return fmt.Errorf("oauth flow: insert: %w", err)
	}
	return nil
}

// ConsumeByState atomically marks the row identified by state as
// consumed and returns the original record. If the row does not exist,
// has already been consumed, or has expired, an error is returned and
// no state is mutated. The provider parameter is matched too so a
// state value minted for one provider cannot be replayed against
// another.
func (s *OAuthFlowStore) ConsumeByState(ctx context.Context, provider, state string) (*OAuthFlow, error) {
	if state == "" || provider == "" {
		return nil, fmt.Errorf("oauth flow: state and provider are required")
	}
	now := time.Now().UTC()
	row := s.pool.QueryRow(ctx,
		`UPDATE auth_oauth_flows
		    SET consumed    = TRUE,
		        consumed_at = $3
		  WHERE state      = $1
		    AND provider   = $2
		    AND consumed   = FALSE
		    AND expires_at > $3
		 RETURNING flow_id, provider, state, code_verifier, nonce,
		          redirect_uri, return_to, created_at, expires_at, TRUE`,
		state, provider, now)

	f := &OAuthFlow{}
	var consumed bool
	if err := row.Scan(
		&f.FlowID, &f.Provider, &f.State, &f.CodeVerifier, &f.Nonce,
		&f.RedirectURI, &f.ReturnTo, &f.CreatedAt, &f.ExpiresAt, &consumed,
	); err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("oauth flow: state is unknown, expired, or already consumed")
		}
		return nil, fmt.Errorf("oauth flow: consume: %w", err)
	}
	f.Consumed = consumed
	return f, nil
}

// CleanupExpiredOAuthFlows removes rows whose expires_at is in the
// past. Run periodically by the gateway janitor goroutine. Returns
// the number of deleted rows for observability.
func (s *OAuthFlowStore) CleanupExpiredOAuthFlows(ctx context.Context) (int64, error) {
	tag, err := s.pool.Exec(ctx,
		`DELETE FROM auth_oauth_flows WHERE expires_at < NOW()`)
	if err != nil {
		return 0, fmt.Errorf("oauth flow: cleanup: %w", err)
	}
	return tag.RowsAffected(), nil
}

// ---------------------------------------------------------------------------
// OAuthIdentityStore
//
// Persistent (provider, subject) -> user_id mapping plus a small set of
// display fields kept fresh on every login. Upsert is idempotent on
// (provider, subject).
// ---------------------------------------------------------------------------

type OAuthIdentityStore struct {
	pool *pgxpool.Pool
}

func NewOAuthIdentityStore(pool *pgxpool.Pool) *OAuthIdentityStore {
	return &OAuthIdentityStore{pool: pool}
}

const oauthIdentityColumns = `id, user_id, provider, provider_subject, email,
        email_verified, name, picture, hosted_domain,
        created_at, updated_at, last_login_at`

// GetByProviderSubject returns the identity for (provider, subject), or
// nil if not linked yet.
func (s *OAuthIdentityStore) GetByProviderSubject(ctx context.Context, provider, subject string) (*OAuthIdentity, error) {
	row := s.pool.QueryRow(ctx,
		`SELECT `+oauthIdentityColumns+`
		   FROM auth_oauth_identities
		  WHERE provider = $1 AND provider_subject = $2`,
		provider, subject)
	return s.scan(row)
}

// Upsert links (provider, subject) to userID, creating or updating the
// row in a single statement. Display fields (email, name, picture,
// hosted_domain, email_verified) are refreshed every call so a
// changed Google profile is reflected on next sign-in.
func (s *OAuthIdentityStore) Upsert(ctx context.Context, ident *OAuthIdentity) error {
	if ident.ID == "" || ident.UserID == "" || ident.Provider == "" || ident.ProviderSubject == "" {
		return fmt.Errorf("oauth identity: required fields missing")
	}
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`INSERT INTO auth_oauth_identities (
		        id, user_id, provider, provider_subject, email,
		        email_verified, name, picture, hosted_domain,
		        created_at, updated_at, last_login_at
		 ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$10,$10)
		 ON CONFLICT (provider, provider_subject) DO UPDATE SET
		        user_id        = EXCLUDED.user_id,
		        email          = EXCLUDED.email,
		        email_verified = EXCLUDED.email_verified,
		        name           = EXCLUDED.name,
		        picture        = EXCLUDED.picture,
		        hosted_domain  = EXCLUDED.hosted_domain,
		        updated_at     = EXCLUDED.updated_at,
		        last_login_at  = EXCLUDED.last_login_at`,
		ident.ID, ident.UserID, ident.Provider, ident.ProviderSubject, ident.Email,
		ident.EmailVerified, ident.Name, ident.Picture, ident.HostedDomain,
		now,
	)
	if err != nil {
		return fmt.Errorf("oauth identity: upsert: %w", err)
	}
	return nil
}

// ListByUserID returns every identity linked to a given user.
func (s *OAuthIdentityStore) ListByUserID(ctx context.Context, userID string) ([]*OAuthIdentity, error) {
	rows, err := s.pool.Query(ctx,
		`SELECT `+oauthIdentityColumns+`
		   FROM auth_oauth_identities
		  WHERE user_id = $1
		  ORDER BY created_at ASC`, userID)
	if err != nil {
		return nil, fmt.Errorf("oauth identity: list: %w", err)
	}
	defer rows.Close()

	var out []*OAuthIdentity
	for rows.Next() {
		ident, err := s.scanRows(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, ident)
	}
	return out, rows.Err()
}

func (s *OAuthIdentityStore) scan(row pgx.Row) (*OAuthIdentity, error) {
	i := &OAuthIdentity{}
	err := row.Scan(
		&i.ID, &i.UserID, &i.Provider, &i.ProviderSubject, &i.Email,
		&i.EmailVerified, &i.Name, &i.Picture, &i.HostedDomain,
		&i.CreatedAt, &i.UpdatedAt, &i.LastLoginAt,
	)
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("oauth identity: scan: %w", err)
	}
	return i, nil
}

func (s *OAuthIdentityStore) scanRows(rows pgx.Rows) (*OAuthIdentity, error) {
	i := &OAuthIdentity{}
	err := rows.Scan(
		&i.ID, &i.UserID, &i.Provider, &i.ProviderSubject, &i.Email,
		&i.EmailVerified, &i.Name, &i.Picture, &i.HostedDomain,
		&i.CreatedAt, &i.UpdatedAt, &i.LastLoginAt,
	)
	if err != nil {
		return nil, fmt.Errorf("oauth identity: scan row: %w", err)
	}
	return i, nil
}
