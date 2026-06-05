package auth

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

// SchemaSQL returns the DDL for auth tables. Called once at startup.
//
// All statements are idempotent (CREATE ... IF NOT EXISTS,
// ADD COLUMN IF NOT EXISTS) so this can be re-run safely on every
// startup against a populated production database.
//
// password_hash is nullable to support federated identity providers
// (Google OAuth 2.0). Local accounts always have a non-empty hash;
// federated accounts have NULL and are rejected by CheckPassword.
//
// auth_oauth_flows holds the short-lived PKCE/state/nonce records used
// during the Authorization Code redirect dance. Single-use enforcement
// is via the consumed flag plus an expires_at TTL; a periodic janitor
// (CleanupExpiredOAuthFlows) deletes stale rows.
//
// auth_oauth_identities maps a (provider, provider_subject) pair to a
// platform user. The unique index makes account-linking idempotent and
// guarantees one Google account cannot be claimed by two local users.
func SchemaSQL() string {
	return `
CREATE TABLE IF NOT EXISTS auth_users (
    id              TEXT PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'etradie',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_auth_users_username ON auth_users (username);
CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users (email);
CREATE INDEX IF NOT EXISTS idx_auth_users_role ON auth_users (role);

-- Federated-identity additive columns. Defaults keep existing rows valid.
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS auth_provider  TEXT NOT NULL DEFAULT 'local';
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS avatar_url     TEXT NOT NULL DEFAULT '';
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;

-- Allow federated accounts to have no local password.
ALTER TABLE auth_users ALTER COLUMN password_hash DROP NOT NULL;
ALTER TABLE auth_users ALTER COLUMN password_hash SET DEFAULT '';

CREATE TABLE IF NOT EXISTS auth_sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    refresh_token   TEXT NOT NULL,
    user_agent      TEXT NOT NULL DEFAULT '',
    client_ip       TEXT NOT NULL DEFAULT '',
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked         BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_refresh_token ON auth_sessions (refresh_token);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions (expires_at);

CREATE TABLE IF NOT EXISTS auth_oauth_flows (
    flow_id         TEXT PRIMARY KEY,
    provider        TEXT NOT NULL,
    state           TEXT NOT NULL UNIQUE,
    code_verifier   TEXT NOT NULL,
    nonce           TEXT NOT NULL,
    redirect_uri    TEXT NOT NULL,
    return_to       TEXT NOT NULL DEFAULT '/',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    consumed        BOOLEAN NOT NULL DEFAULT FALSE,
    consumed_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_auth_oauth_flows_state      ON auth_oauth_flows (state);
CREATE INDEX IF NOT EXISTS idx_auth_oauth_flows_expires_at ON auth_oauth_flows (expires_at);

-- Account-linking additive columns. flow_kind discriminates between
-- 'signin' (unauthenticated, mints a TokenPair) and 'link'
-- (authenticated, binds a verified Google identity to user_id).
-- user_id is NULL for sign-in flows and NOT NULL for link flows; the
-- link callback handler enforces this invariant and refuses to
-- complete a link flow against any user other than user_id.
ALTER TABLE auth_oauth_flows ADD COLUMN IF NOT EXISTS flow_kind TEXT NOT NULL DEFAULT 'signin';
ALTER TABLE auth_oauth_flows ADD COLUMN IF NOT EXISTS user_id   TEXT;

CREATE INDEX IF NOT EXISTS idx_auth_oauth_flows_user_id ON auth_oauth_flows (user_id);

CREATE TABLE IF NOT EXISTS auth_oauth_identities (
    id                 TEXT PRIMARY KEY,
    user_id            TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    provider           TEXT NOT NULL,
    provider_subject   TEXT NOT NULL,
    email              TEXT NOT NULL,
    email_verified     BOOLEAN NOT NULL,
    name               TEXT NOT NULL DEFAULT '',
    picture            TEXT NOT NULL DEFAULT '',
    hosted_domain      TEXT NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at      TIMESTAMPTZ,
    UNIQUE (provider, provider_subject)
);

CREATE INDEX IF NOT EXISTS idx_auth_oauth_identities_user_id  ON auth_oauth_identities (user_id);
CREATE INDEX IF NOT EXISTS idx_auth_oauth_identities_provider ON auth_oauth_identities (provider);

-- Password reset tokens. The plaintext token lives only inside the
-- emailed reset link; the database holds a SHA-256 digest. Single-use
-- enforcement is via the consumed flag plus an expires_at TTL; the
-- partial-unique index makes "one outstanding token per user" an
-- invariant rather than a best-effort.
CREATE TABLE IF NOT EXISTS auth_password_resets (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token_hash    TEXT NOT NULL UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ NOT NULL,
    consumed      BOOLEAN NOT NULL DEFAULT FALSE,
    consumed_at   TIMESTAMPTZ,
    requested_ip  TEXT NOT NULL DEFAULT '',
    user_agent    TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_auth_password_resets_user_id    ON auth_password_resets (user_id);
CREATE INDEX IF NOT EXISTS idx_auth_password_resets_token_hash ON auth_password_resets (token_hash);
CREATE INDEX IF NOT EXISTS idx_auth_password_resets_expires_at ON auth_password_resets (expires_at);

-- Partial unique index: at most one unconsumed reset row per user.
-- Prior rows are logically consumed (consumed = TRUE) before a new one
-- is inserted, so this index never fails the legitimate single-issuer
-- path; it exists to harden against a race that slips past the
-- transactional check in the store.
CREATE UNIQUE INDEX IF NOT EXISTS uq_auth_password_resets_user_active
    ON auth_password_resets (user_id)
    WHERE consumed = FALSE;
`
}

// ---------------------------------------------------------------------------
// User Store
// ---------------------------------------------------------------------------

// UserStore handles user persistence in PostgreSQL.
type UserStore struct {
	pool *pgxpool.Pool
}

// NewUserStore creates a user store backed by the given connection pool.
func NewUserStore(pool *pgxpool.Pool) *UserStore {
	return &UserStore{pool: pool}
}

// CreateUser inserts a new user into the database.
//
// The auth_provider, avatar_url, and email_verified columns are
// populated explicitly so federated accounts created via Google get
// the correct values and existing local-account call sites that
// leave AuthProvider blank still default to "local".
func (s *UserStore) CreateUser(ctx context.Context, user *User) error {
	provider := user.AuthProvider
	if provider == "" {
		provider = AuthProviderLocal
		user.AuthProvider = provider
	}
	_, err := s.pool.Exec(ctx,
		`INSERT INTO auth_users (
		        id, username, email, password_hash, role, active,
		        auth_provider, avatar_url, email_verified,
		        created_at, updated_at
		 ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)`,
		user.ID, user.Username, user.Email, user.PasswordHash,
		string(user.Role), user.Active,
		provider, user.AvatarURL, user.EmailVerified,
		user.CreatedAt, user.UpdatedAt,
	)
	if err != nil {
		if strings.Contains(err.Error(), "duplicate key") {
			if strings.Contains(err.Error(), "username") {
				return fmt.Errorf("username %q already exists", user.Username)
			}
			if strings.Contains(err.Error(), "email") {
				return fmt.Errorf("email %q already exists", user.Email)
			}
			return fmt.Errorf("user already exists")
		}
		return fmt.Errorf("create user: %w", err)
	}
	return nil
}

// GetUserByID retrieves a user by their ID.
func (s *UserStore) GetUserByID(ctx context.Context, id string) (*User, error) {
	return s.scanUser(s.pool.QueryRow(ctx,
		`SELECT `+userColumns+` FROM auth_users a LEFT JOIN billing_subscriptions b ON a.id = b.user_id WHERE a.id = $1`, id))
}

// GetUserByUsername retrieves a user by their username (case-insensitive).
func (s *UserStore) GetUserByUsername(ctx context.Context, username string) (*User, error) {
	return s.scanUser(s.pool.QueryRow(ctx,
		`SELECT `+userColumns+` FROM auth_users a LEFT JOIN billing_subscriptions b ON a.id = b.user_id WHERE LOWER(a.username) = LOWER($1)`, username))
}

// GetUserByEmail retrieves a user by their email (case-insensitive).
func (s *UserStore) GetUserByEmail(ctx context.Context, email string) (*User, error) {
	return s.scanUser(s.pool.QueryRow(ctx,
		`SELECT `+userColumns+` FROM auth_users a LEFT JOIN billing_subscriptions b ON a.id = b.user_id WHERE LOWER(a.email) = LOWER($1)`, email))
}

// ListUsers returns all users. Admin only.
func (s *UserStore) ListUsers(ctx context.Context) ([]*User, error) {
	rows, err := s.pool.Query(ctx,
		`SELECT `+userColumns+` FROM auth_users a LEFT JOIN billing_subscriptions b ON a.id = b.user_id ORDER BY a.created_at ASC`)
	if err != nil {
		return nil, fmt.Errorf("list users: %w", err)
	}
	defer rows.Close()

	var users []*User
	for rows.Next() {
		u, err := s.scanUserFromRows(rows)
		if err != nil {
			return nil, err
		}
		users = append(users, u)
	}
	return users, rows.Err()
}

// ListActiveUsers returns all users where active=true.
func (s *UserStore) ListActiveUsers(ctx context.Context) ([]*User, error) {
	rows, err := s.pool.Query(ctx,
		`SELECT `+userColumns+` FROM auth_users a LEFT JOIN billing_subscriptions b ON a.id = b.user_id WHERE a.active = TRUE ORDER BY a.created_at ASC`)
	if err != nil {
		return nil, fmt.Errorf("list active users: %w", err)
	}
	defer rows.Close()

	var users []*User
	for rows.Next() {
		u, err := s.scanUserFromRows(rows)
		if err != nil {
			return nil, err
		}
		users = append(users, u)
	}
	return users, rows.Err()
}

// UpdateProfileFromOAuth refreshes the auth-provider-managed fields
// (avatar URL, email verification flag, last_login_at) for an existing
// user. Used by the Google OAuth callback so a user who updates their
// Google profile picture sees the change reflected in eTradie on next
// sign-in. Username and email are deliberately left untouched here:
// rotating the email of a federated account is handled separately.
func (s *UserStore) UpdateProfileFromOAuth(ctx context.Context, userID string, avatarURL string, emailVerified bool) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_users
		    SET avatar_url     = $1,
		        email_verified = $2,
		        last_login_at  = $3,
		        updated_at     = $3
		  WHERE id = $4`,
		avatarURL, emailVerified, now, userID)
	if err != nil {
		return fmt.Errorf("update profile from oauth: %w", err)
	}
	return nil
}

// UpdateProfileFromOAuthLink is the link-flow counterpart of
// UpdateProfileFromOAuth. It refreshes the provider-managed avatar
// and email_verified fields but deliberately does NOT touch
// last_login_at, because linking is not a sign-in event and recording
// it as one would corrupt session and audit telemetry.
func (s *UserStore) UpdateProfileFromOAuthLink(ctx context.Context, userID string, avatarURL string, emailVerified bool) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_users
		    SET avatar_url     = $1,
		        email_verified = $2,
		        updated_at     = $3
		  WHERE id = $4`,
		avatarURL, emailVerified, now, userID)
	if err != nil {
		return fmt.Errorf("update profile from oauth link: %w", err)
	}
	return nil
}

// UpdateProfileFromOAuthUnlink clears the provider-managed fields (avatar
// and email_verified) and ensures the auth_provider is reset to 'local'.
// This ensures the frontend correctly sees the account as fully disconnected.
func (s *UserStore) UpdateProfileFromOAuthUnlink(ctx context.Context, userID string) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_users
		    SET avatar_url     = '',
		        email_verified = FALSE,
		        auth_provider  = 'local',
		        updated_at     = $1
		  WHERE id = $2`,
		now, userID)
	if err != nil {
		return fmt.Errorf("update profile from oauth unlink: %w", err)
	}
	return nil
}

// UpdateLastLogin sets the last_login_at timestamp for a user.
func (s *UserStore) UpdateLastLogin(ctx context.Context, userID string) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_users SET last_login_at = $1, updated_at = $1 WHERE id = $2`,
		now, userID)
	if err != nil {
		return fmt.Errorf("update last login: %w", err)
	}
	return nil
}

// UpdatePassword changes a user's password hash.
func (s *UserStore) UpdatePassword(ctx context.Context, userID string, passwordHash string) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_users SET password_hash = $1, updated_at = $2 WHERE id = $3`,
		passwordHash, now, userID)
	if err != nil {
		return fmt.Errorf("update password: %w", err)
	}
	return nil
}

// DeactivateUser sets active=false for a user. Admin only.
func (s *UserStore) DeactivateUser(ctx context.Context, userID string) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_users SET active = FALSE, updated_at = $1 WHERE id = $2`,
		now, userID)
	if err != nil {
		return fmt.Errorf("deactivate user: %w", err)
	}
	return nil
}

// ActivateUser sets active=true for a user. Admin only.
func (s *UserStore) ActivateUser(ctx context.Context, userID string) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_users SET active = TRUE, updated_at = $1 WHERE id = $2`,
		now, userID)
	if err != nil {
		return fmt.Errorf("activate user: %w", err)
	}
	return nil
}

// CountAdmins returns the number of active admin users.
func (s *UserStore) CountAdmins(ctx context.Context) (int, error) {
	var count int
	err := s.pool.QueryRow(ctx,
		`SELECT COUNT(*) FROM auth_users WHERE role = 'admin' AND active = TRUE`).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("count admins: %w", err)
	}
	return count, nil
}

// userColumns is the canonical SELECT list for auth_users. Centralised
// so every read path scans the same columns in the same order.
const userColumns = `a.id, a.username, a.email, a.password_hash, a.role, a.active,
        a.auth_provider, a.avatar_url, a.email_verified,
        a.created_at, a.updated_at, a.last_login_at,
        COALESCE(b.tier, 'free'), COALESCE(b.status, 'active')`

func (s *UserStore) scanUser(row pgx.Row) (*User, error) {
	u := &User{}
	var passwordHash *string
	err := row.Scan(
		&u.ID, &u.Username, &u.Email, &passwordHash,
		&u.Role, &u.Active,
		&u.AuthProvider, &u.AvatarURL, &u.EmailVerified,
		&u.CreatedAt, &u.UpdatedAt, &u.LastLoginAt,
		&u.Tier, &u.Status,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("scan user: %w", err)
	}
	if passwordHash != nil {
		u.PasswordHash = *passwordHash
	}
	return u, nil
}

func (s *UserStore) scanUserFromRows(rows pgx.Rows) (*User, error) {
	u := &User{}
	var passwordHash *string
	err := rows.Scan(
		&u.ID, &u.Username, &u.Email, &passwordHash,
		&u.Role, &u.Active,
		&u.AuthProvider, &u.AvatarURL, &u.EmailVerified,
		&u.CreatedAt, &u.UpdatedAt, &u.LastLoginAt,
		&u.Tier, &u.Status,
	)
	if err != nil {
		return nil, fmt.Errorf("scan user row: %w", err)
	}
	if passwordHash != nil {
		u.PasswordHash = *passwordHash
	}
	return u, nil
}

// ---------------------------------------------------------------------------
// Session Store
// ---------------------------------------------------------------------------

// SessionStore handles refresh session persistence in PostgreSQL.
type SessionStore struct {
	pool *pgxpool.Pool
}

// NewSessionStore creates a session store backed by the given connection pool.
func NewSessionStore(pool *pgxpool.Pool) *SessionStore {
	return &SessionStore{pool: pool}
}

// CreateSession inserts a new refresh session. The refresh token is
// stored as a SHA-256 hash so it cannot be recovered from the DB.
func (s *SessionStore) CreateSession(ctx context.Context, sess *Session) error {
	hashed := hashToken(sess.RefreshToken)
	_, err := s.pool.Exec(ctx,
		`INSERT INTO auth_sessions (id, user_id, refresh_token, user_agent, client_ip, expires_at, created_at, revoked)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
		sess.ID, sess.UserID, hashed, sess.UserAgent, sess.ClientIP,
		sess.ExpiresAt, sess.CreatedAt, sess.Revoked,
	)
	if err != nil {
		return fmt.Errorf("create session: %w", err)
	}
	return nil
}

// GetSessionByToken looks up a session by the plaintext refresh token.
// The token is hashed before querying.
func (s *SessionStore) GetSessionByToken(ctx context.Context, refreshToken string) (*Session, error) {
	hashed := hashToken(refreshToken)
	sess := &Session{}
	err := s.pool.QueryRow(ctx,
		`SELECT id, user_id, refresh_token, user_agent, client_ip, expires_at, created_at, revoked
		 FROM auth_sessions WHERE refresh_token = $1`, hashed,
	).Scan(
		&sess.ID, &sess.UserID, &sess.RefreshToken, &sess.UserAgent,
		&sess.ClientIP, &sess.ExpiresAt, &sess.CreatedAt, &sess.Revoked,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("get session by token: %w", err)
	}
	return sess, nil
}

// RevokeSession marks a single session as revoked.
func (s *SessionStore) RevokeSession(ctx context.Context, sessionID string) error {
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_sessions SET revoked = TRUE WHERE id = $1`, sessionID)
	if err != nil {
		return fmt.Errorf("revoke session: %w", err)
	}
	return nil
}

// RevokeAllUserSessions revokes all sessions for a user (logout everywhere).
func (s *SessionStore) RevokeAllUserSessions(ctx context.Context, userID string) error {
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_sessions SET revoked = TRUE WHERE user_id = $1 AND revoked = FALSE`, userID)
	if err != nil {
		return fmt.Errorf("revoke all user sessions: %w", err)
	}
	return nil
}

// CountActiveSessions returns the number of non-revoked, non-expired
// sessions for a user.
func (s *SessionStore) CountActiveSessions(ctx context.Context, userID string) (int, error) {
	var count int
	err := s.pool.QueryRow(ctx,
		`SELECT COUNT(*) FROM auth_sessions
		 WHERE user_id = $1 AND revoked = FALSE AND expires_at > NOW()`,
		userID).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("count active sessions: %w", err)
	}
	return count, nil
}

// RevokeOldestSession revokes the oldest active session for a user.
// Used to enforce MaxSessionsPerUser.
func (s *SessionStore) RevokeOldestSession(ctx context.Context, userID string) error {
	_, err := s.pool.Exec(ctx,
		`UPDATE auth_sessions SET revoked = TRUE
		 WHERE id = (
		   SELECT id FROM auth_sessions
		   WHERE user_id = $1 AND revoked = FALSE AND expires_at > NOW()
		   ORDER BY created_at ASC
		   LIMIT 1
		 )`, userID)
	if err != nil {
		return fmt.Errorf("revoke oldest session: %w", err)
	}
	return nil
}

// CleanupExpiredSessions deletes sessions that expired more than
// 24 hours ago. Called periodically to keep the table small.
func (s *SessionStore) CleanupExpiredSessions(ctx context.Context) (int64, error) {
	cutoff := time.Now().UTC().Add(-24 * time.Hour)
	tag, err := s.pool.Exec(ctx,
		`DELETE FROM auth_sessions WHERE expires_at < $1`, cutoff)
	if err != nil {
		return 0, fmt.Errorf("cleanup expired sessions: %w", err)
	}
	return tag.RowsAffected(), nil
}

// ---------------------------------------------------------------------------
// Admin Seed
// ---------------------------------------------------------------------------

// SeedAdminUser creates the initial admin user if no admin exists.
// Called once at startup. If the admin already exists, this is a no-op.
//
// The matching billing_subscriptions row is also upserted here so the
// new admin starts with tier='pro_managed' / status='active' the
// instant they exist. The database trigger fn_billing_sync_admin_tier
// (installed by billing/store.SchemaSQL) covers this case as well,
// but writing the row explicitly keeps the invariant local to the
// seed path so a future schema-reordering change cannot break
// first-boot semantically. Both writes converge on the same end
// state and the upsert is idempotent.
func SeedAdminUser(ctx context.Context, store *UserStore, cfg *Config) error {
	count, err := store.CountAdmins(ctx)
	if err != nil {
		return fmt.Errorf("seed admin: count admins: %w", err)
	}
	if count > 0 {
		return nil // Admin already exists.
	}

	now := time.Now().UTC()
	user := &User{
		ID:        GenerateID(),
		Username:  cfg.AdminUsername,
		Email:     cfg.AdminEmail,
		Role:      RoleAdmin,
		Active:    true,
		CreatedAt: now,
		UpdatedAt: now,
	}

	// Use configured password or a generated one. The generated
	// fallback is produced by GenerateStrongPassword so it satisfies
	// the complexity policy SetPassword enforces (a hex-only token
	// would be rejected for having too few character classes).
	password := cfg.AdminPassword
	generated := false
	if !cfg.HasAdminSeedPassword() {
		gen, genErr := GenerateStrongPassword(20)
		if genErr != nil {
			return fmt.Errorf("seed admin: generate password: %w", genErr)
		}
		password = gen
		generated = true
	}

	if err := user.SetPassword(password); err != nil {
		return fmt.Errorf("seed admin: set password: %w", err)
	}

	if err := store.CreateUser(ctx, user); err != nil {
		return fmt.Errorf("seed admin: create user: %w", err)
	}

	// Defense in depth: ensure the billing row reflects the admin's
	// entitlement immediately. The trigger fires on the INSERT above
	// so this UPSERT is normally a no-op; it stays as belt-and-braces
	// so first-boot is correct even when the trigger has not yet
	// been installed (e.g. older deploy that has not run the latest
	// billing SchemaSQL).
	//
	// The query uses the SAME shape and race-safety guard as the
	// trigger so a real webhook landing at the same instant cannot
	// regress the result. Errors here are non-fatal: the trigger and
	// the startup backfill (also in billing/store.SchemaSQL) will
	// converge the row on the next deploy or the next role-touching
	// UPDATE. Logging the error keeps the operator informed without
	// blocking the admin's first login.
	if _, err := store.pool.Exec(ctx, `
		INSERT INTO billing_subscriptions (user_id, tier, status, event_timestamp, updated_at)
		VALUES ($1, 'pro_managed', 'active', NOW(), NOW())
		ON CONFLICT (user_id) DO UPDATE SET
		    tier            = 'pro_managed',
		    status          = 'active',
		    event_timestamp = NOW(),
		    updated_at      = NOW()
		WHERE billing_subscriptions.event_timestamp <= NOW()`,
		user.ID,
	); err != nil {
		// Non-fatal: see comment above.
		fmt.Printf("[WARN] seed admin: billing upsert skipped (%v); "+
			"trigger or backfill will converge next start\n", err)
	}

	if generated {
		// Log the generated password so the admin can log in.
		// This is printed ONCE at first startup only.
		// In production, set AUTH_ADMIN_PASSWORD explicitly.
		fmt.Printf("\n" +
			"==========================================================\n" +
			"  ADMIN ACCOUNT CREATED (first startup)\n" +
			"  Username: %s\n" +
			"  Password: %s\n" +
			"  \n" +
			"  CHANGE THIS PASSWORD IMMEDIATELY after first login.\n" +
			"  Set AUTH_ADMIN_PASSWORD env var to avoid this message.\n" +
			"==========================================================\n\n",
			user.Username, password)
	}

	return nil
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// hashToken produces a SHA-256 hex digest of a token string.
// Used to store refresh tokens securely in the database.
func hashToken(token string) string {
	h := sha256.Sum256([]byte(token))
	return hex.EncodeToString(h[:])
}
