package auth

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
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
func (s *UserStore) CreateUser(ctx context.Context, user *User) error {
	_, err := s.pool.Exec(ctx,
		`INSERT INTO auth_users (id, username, email, password_hash, role, active, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
		user.ID, user.Username, user.Email, user.PasswordHash,
		string(user.Role), user.Active, user.CreatedAt, user.UpdatedAt,
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
		`SELECT id, username, email, password_hash, role, active, created_at, updated_at, last_login_at
		 FROM auth_users WHERE id = $1`, id))
}

// GetUserByUsername retrieves a user by their username (case-insensitive).
func (s *UserStore) GetUserByUsername(ctx context.Context, username string) (*User, error) {
	return s.scanUser(s.pool.QueryRow(ctx,
		`SELECT id, username, email, password_hash, role, active, created_at, updated_at, last_login_at
		 FROM auth_users WHERE LOWER(username) = LOWER($1)`, username))
}

// GetUserByEmail retrieves a user by their email (case-insensitive).
func (s *UserStore) GetUserByEmail(ctx context.Context, email string) (*User, error) {
	return s.scanUser(s.pool.QueryRow(ctx,
		`SELECT id, username, email, password_hash, role, active, created_at, updated_at, last_login_at
		 FROM auth_users WHERE LOWER(email) = LOWER($1)`, email))
}

// ListUsers returns all users. Admin only.
func (s *UserStore) ListUsers(ctx context.Context) ([]*User, error) {
	rows, err := s.pool.Query(ctx,
		`SELECT id, username, email, password_hash, role, active, created_at, updated_at, last_login_at
		 FROM auth_users ORDER BY created_at ASC`)
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

func (s *UserStore) scanUser(row pgx.Row) (*User, error) {
	u := &User{}
	err := row.Scan(
		&u.ID, &u.Username, &u.Email, &u.PasswordHash,
		&u.Role, &u.Active, &u.CreatedAt, &u.UpdatedAt, &u.LastLoginAt,
	)
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("scan user: %w", err)
	}
	return u, nil
}

func (s *UserStore) scanUserFromRows(rows pgx.Rows) (*User, error) {
	u := &User{}
	err := rows.Scan(
		&u.ID, &u.Username, &u.Email, &u.PasswordHash,
		&u.Role, &u.Active, &u.CreatedAt, &u.UpdatedAt, &u.LastLoginAt,
	)
	if err != nil {
		return nil, fmt.Errorf("scan user row: %w", err)
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
		if err == pgx.ErrNoRows {
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

	// Use configured password or a generated one.
	password := cfg.AdminPassword
	generated := false
	if !cfg.HasAdminSeedPassword() {
		password = GenerateRefreshToken()[:16] // 16-char random password
		generated = true
	}

	if err := user.SetPassword(password); err != nil {
		return fmt.Errorf("seed admin: set password: %w", err)
	}

	if err := store.CreateUser(ctx, user); err != nil {
		return fmt.Errorf("seed admin: create user: %w", err)
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
