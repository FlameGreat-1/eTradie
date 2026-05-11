package store

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// PortalAuditStore writes append-only rows to billing_portal_access_events.
// One row per /api/v1/billing/portal request (success OR failure).
//
// Compliance: SOC 2 CC6.1 and PCI-DSS 10.2.5 both require an audit trail
// of every authenticated access to subscription-management surfaces.
// This is that trail. Rows are immutable (no UPDATE / DELETE path).
type PortalAuditStore struct {
	db *pgxpool.Pool
}

// NewPortalAuditStore constructs a store bound to the supplied pool.
func NewPortalAuditStore(db *pgxpool.Pool) *PortalAuditStore {
	return &PortalAuditStore{db: db}
}

// PortalAuditEvent is the row payload. Provider may be empty on a
// 'no active subscription' failure; client_ip and user_agent are
// best-effort (depend on the gateway's proxy configuration).
type PortalAuditEvent struct {
	UserID    string
	Provider  string
	ClientIP  string
	UserAgent string
	Status    string // 'success' | 'not_found' | 'not_supported' | 'rate_limited' | 'upstream_error' | 'error'
	Error     string // free-form, empty on success
	CreatedAt time.Time
}

// Append writes one immutable audit row. Returns an error only on a
// genuine infrastructure failure; callers should log and continue.
// The user-facing request must never be blocked by this write.
func (s *PortalAuditStore) Append(ctx context.Context, ev *PortalAuditEvent) error {
	if ev.CreatedAt.IsZero() {
		ev.CreatedAt = time.Now().UTC()
	}
	const q = `
		INSERT INTO billing_portal_access_events (
			user_id, provider, client_ip, user_agent, status, error, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7)
	`
	_, err := s.db.Exec(ctx, q,
		ev.UserID,
		nullableString(ev.Provider),
		nullableString(ev.ClientIP),
		nullableString(ev.UserAgent),
		ev.Status,
		nullableString(ev.Error),
		ev.CreatedAt,
	)
	return err
}
