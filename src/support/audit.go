package support

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

// AuditEvent is the wire representation of a single immutable row in
// the support_ticket_audit table. Returned by future admin-side
// queries; not exposed via any current public REST endpoint.
type AuditEvent struct {
	ID         string            `json:"id"`
	TicketID   *string           `json:"ticket_id,omitempty"`
	Action     TicketAction      `json:"action"`
	ActorKind  AuditActorKind    `json:"actor_kind"`
	ActorID    string            `json:"actor_id,omitempty"`
	IPAddress  string            `json:"ip_address,omitempty"`
	UserAgent  string            `json:"user_agent,omitempty"`
	Metadata   map[string]string `json:"metadata,omitempty"`
	CreatedAt  time.Time         `json:"created_at"`
}

// AuditParams is the input to Store.RecordAudit. TicketID is a
// pointer because some events (honeypot drops) are not tied to a
// persisted ticket.
type AuditParams struct {
	TicketID  *string
	Action    TicketAction
	ActorKind AuditActorKind
	ActorID   string
	IPAddress string
	UserAgent string
	Metadata  map[string]string
}

// RecordAudit writes a single immutable row to support_ticket_audit.
// Runs in its own short transaction-free Exec so an audit-write
// failure cannot abort the user-visible ticket operation that
// triggered it; callers should log and continue on error.
//
// All user-controlled fields are bounded by upstream validation (the
// user_agent is TruncateUserAgent-bounded; ip_address is produced
// by the trusted proxy resolver; metadata is constructed in-process
// by the handler and never echoes raw request data).
func (s *Store) RecordAudit(ctx context.Context, p AuditParams) error {
	if !p.Action.IsValid() {
		return fmt.Errorf("support: invalid audit action %q", p.Action)
	}
	if !p.ActorKind.IsValid() {
		return fmt.Errorf("support: invalid audit actor_kind %q", p.ActorKind)
	}

	meta := p.Metadata
	if meta == nil {
		meta = map[string]string{}
	}
	metaJSON, err := json.Marshal(meta)
	if err != nil {
		return fmt.Errorf("support: marshal audit metadata: %w", err)
	}

	_, err = s.pool.Exec(ctx,
		`INSERT INTO support_ticket_audit
		   (id, ticket_id, action, actor_kind, actor_id,
		    ip_address, user_agent, metadata, created_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)`,
		generateID(), p.TicketID, string(p.Action),
		string(p.ActorKind), p.ActorID,
		p.IPAddress, TruncateUserAgent(p.UserAgent),
		string(metaJSON), time.Now().UTC(),
	)
	if err != nil {
		return fmt.Errorf("support: insert audit row: %w", err)
	}
	return nil
}
