// Package support implements the Exoper Support & Contact Us
// subsystem: customer-facing ticketing plus a public contact form,
// with cross-channel notification fan-out (email, Discord webhook,
// Telegram bot, WhatsApp Cloud API).
//
// Design principles:
//
//   - Messages are append-only. A ticket has a status that mutates,
//     but every reply is a fresh row in support_ticket_messages so
//     the audit trail is intact regardless of later edits.
//   - The package is independent of any specific transport. The
//     notifier accepts arbitrary configured channels and never
//     blocks the HTTP response; failures are logged and retried in
//     a background goroutine.
//   - The HTTP API is split into PUBLIC (contact form, community
//     links) and AUTHENTICATED (ticketing CRUD) surfaces. Public
//     endpoints are rate-limited and bounded in body size to defeat
//     volumetric abuse.
package support

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"strings"
	"time"
)

// SchemaSQL returns idempotent DDL for the support tables. Called
// once at gateway startup against the same pgxpool used by
// auth / billing / mails / consent.
//
// support_ticket_audit is an append-only audit trail; rows are NEVER
// updated or deleted by the application. The FK to support_tickets is
// ON DELETE SET NULL so even if a ticket is hard-deleted in the
// future (e.g. for GDPR right-to-erasure), the audit row survives
// with a NULL ticket_id and the original metadata.
func SchemaSQL() string {
	return `
CREATE TABLE IF NOT EXISTS support_tickets (
    id            TEXT PRIMARY KEY,
    public_ref    TEXT NOT NULL UNIQUE,
    user_id       TEXT,
    email         TEXT NOT NULL,
    name          TEXT NOT NULL DEFAULT '',
    subject       TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT 'general',
    priority      TEXT NOT NULL DEFAULT 'normal',
    status        TEXT NOT NULL DEFAULT 'open',
    channel       TEXT NOT NULL DEFAULT 'web',
    ip_address    TEXT NOT NULL DEFAULT '',
    user_agent    TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id
    ON support_tickets (user_id, created_at DESC)
    WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_support_tickets_status
    ON support_tickets (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_support_tickets_email
    ON support_tickets (email, created_at DESC);

CREATE TABLE IF NOT EXISTS support_ticket_messages (
    id          TEXT PRIMARY KEY,
    ticket_id   TEXT NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    author_kind TEXT NOT NULL,
    author_id   TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_messages_ticket
    ON support_ticket_messages (ticket_id, created_at ASC);

CREATE TABLE IF NOT EXISTS support_ticket_audit (
    id          TEXT PRIMARY KEY,
    ticket_id   TEXT REFERENCES support_tickets(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    actor_kind  TEXT NOT NULL,
    actor_id    TEXT NOT NULL DEFAULT '',
    ip_address  TEXT NOT NULL DEFAULT '',
    user_agent  TEXT NOT NULL DEFAULT '',
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_audit_ticket
    ON support_ticket_audit (ticket_id, created_at DESC)
    WHERE ticket_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_support_audit_action
    ON support_ticket_audit (action, created_at DESC);
`
}

// ----------------------------------------------------------------------
// Enums
// ----------------------------------------------------------------------

// TicketStatus is the lifecycle of a ticket.
type TicketStatus string

const (
	StatusOpen     TicketStatus = "open"
	StatusPending  TicketStatus = "pending"
	StatusResolved TicketStatus = "resolved"
	StatusClosed   TicketStatus = "closed"
)

// IsValid returns true for the canonical statuses.
func (s TicketStatus) IsValid() bool {
	switch s {
	case StatusOpen, StatusPending, StatusResolved, StatusClosed:
		return true
	}
	return false
}

// TicketPriority is the user's self-assessed urgency.
type TicketPriority string

const (
	PriorityLow    TicketPriority = "low"
	PriorityNormal TicketPriority = "normal"
	PriorityHigh   TicketPriority = "high"
	PriorityUrgent TicketPriority = "urgent"
)

// IsValid returns true for the canonical priorities.
func (p TicketPriority) IsValid() bool {
	switch p {
	case PriorityLow, PriorityNormal, PriorityHigh, PriorityUrgent:
		return true
	}
	return false
}

// TicketCategory partitions tickets by subject area.
type TicketCategory string

const (
	CategoryGeneral   TicketCategory = "general"
	CategoryBilling   TicketCategory = "billing"
	CategoryTechnical TicketCategory = "technical"
	CategoryAccount   TicketCategory = "account"
	CategoryFeedback  TicketCategory = "feedback"
	CategoryBug       TicketCategory = "bug"
	CategoryFeature   TicketCategory = "feature"
	CategorySecurity  TicketCategory = "security"
	CategoryComplaint TicketCategory = "complaint"
)

// IsValid enforces the closed enum at the API boundary.
func (c TicketCategory) IsValid() bool {
	switch c {
	case CategoryGeneral, CategoryBilling, CategoryTechnical,
		CategoryAccount, CategoryFeedback, CategoryBug,
		CategoryFeature, CategorySecurity, CategoryComplaint:
		return true
	}
	return false
}

// TicketChannel records how the ticket was opened.
type TicketChannel string

const (
	ChannelWeb     TicketChannel = "web"
	ChannelContact TicketChannel = "contact"
	ChannelEmail   TicketChannel = "email"
)

// IsValid returns true for the canonical channel values.
func (c TicketChannel) IsValid() bool {
	switch c {
	case ChannelWeb, ChannelContact, ChannelEmail:
		return true
	}
	return false
}

// MessageAuthorKind distinguishes user / staff / system replies.
type MessageAuthorKind string

const (
	AuthorKindUser   MessageAuthorKind = "user"
	AuthorKindStaff  MessageAuthorKind = "staff"
	AuthorKindSystem MessageAuthorKind = "system"
)

// IsValid returns true for the three canonical author kinds.
func (k MessageAuthorKind) IsValid() bool {
	switch k {
	case AuthorKindUser, AuthorKindStaff, AuthorKindSystem:
		return true
	}
	return false
}

// ----------------------------------------------------------------------
// Audit trail
// ----------------------------------------------------------------------

// TicketAction is the closed enum of state-changing operations
// captured in the support_ticket_audit table. The set is intentionally
// small so the audit log is easy to query and dashboard.
type TicketAction string

const (
	// ActionCreated fires once per successful ticket persistence,
	// regardless of which channel the request arrived on.
	ActionCreated TicketAction = "created"

	// ActionReplied fires once per user-side append on an existing
	// open / pending / resolved ticket.
	ActionReplied TicketAction = "replied"

	// ActionClosed fires when the user transitions a ticket to the
	// terminal closed state via the dashboard.
	ActionClosed TicketAction = "closed"

	// ActionReopened fires when a user reply on a 'resolved' ticket
	// flips its status back to 'open' as a side effect.
	ActionReopened TicketAction = "reopened"

	// ActionHoneypotDropped fires when the public contact form's
	// honeypot field is populated. The triggering request is
	// silently accepted (so the bot's success detector is fooled)
	// but no ticket is persisted; this row is the only durable
	// record of the event for forensics.
	ActionHoneypotDropped TicketAction = "honeypot_dropped"

	// ActionAutoClosed fires when the background janitor transitions
	// a resolved ticket to closed after the configured inactivity
	// period (SUPPORT_AUTO_CLOSE_AFTER) has elapsed without any new
	// user reply. The audit row's actor_kind is always 'system'.
	ActionAutoClosed TicketAction = "auto_closed"
)

// IsValid returns true for the closed enum of TicketAction values.
func (a TicketAction) IsValid() bool {
	switch a {
	case ActionCreated, ActionReplied, ActionClosed,
		ActionReopened, ActionHoneypotDropped, ActionAutoClosed:
		return true
	}
	return false
}

// AuditActorKind distinguishes who initiated the action. 'anonymous'
// covers the public-contact-form path where no user_id exists; the
// other three mirror MessageAuthorKind exactly so the two enums can
// be derived from each other without an explicit mapping table.
type AuditActorKind string

const (
	ActorUser      AuditActorKind = "user"
	ActorStaff     AuditActorKind = "staff"
	ActorSystem    AuditActorKind = "system"
	ActorAnonymous AuditActorKind = "anonymous"
)

// IsValid returns true for the four canonical actor kinds.
func (k AuditActorKind) IsValid() bool {
	switch k {
	case ActorUser, ActorStaff, ActorSystem, ActorAnonymous:
		return true
	}
	return false
}

// ----------------------------------------------------------------------
// Records (wire shapes)
// ----------------------------------------------------------------------

// Ticket is the canonical wire representation of a support ticket.
type Ticket struct {
	ID        string         `json:"id"`
	PublicRef string         `json:"public_ref"`
	UserID    *string        `json:"user_id,omitempty"`
	Email     string         `json:"email"`
	Name      string         `json:"name,omitempty"`
	Subject   string         `json:"subject"`
	Category  TicketCategory `json:"category"`
	Priority  TicketPriority `json:"priority"`
	Status    TicketStatus   `json:"status"`
	Channel   TicketChannel  `json:"channel"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	ClosedAt  *time.Time     `json:"closed_at,omitempty"`
	Messages  []Message      `json:"messages,omitempty"`
}

// Message is one entry in a ticket's append-only conversation log.
type Message struct {
	ID         string            `json:"id"`
	TicketID   string            `json:"ticket_id"`
	AuthorKind MessageAuthorKind `json:"author_kind"`
	AuthorID   string            `json:"author_id,omitempty"`
	Body       string            `json:"body"`
	CreatedAt  time.Time         `json:"created_at"`
}

// ----------------------------------------------------------------------
// Validation
// ----------------------------------------------------------------------

const (
	MaxEmailLen     = 254 // RFC 5321
	MaxNameLen      = 120
	MaxSubjectLen   = 200
	MaxBodyLen      = 8000
	MaxUserAgentLen = 512
	MinSubjectLen   = 3
	MinBodyLen      = 5
)

// Sentinel validation errors. Handlers map these to HTTP 400.
var (
	ErrInvalidEmail    = errors.New("support: invalid email")
	ErrInvalidName     = errors.New("support: invalid name")
	ErrInvalidSubject  = errors.New("support: invalid subject")
	ErrInvalidBody     = errors.New("support: invalid body")
	ErrInvalidCategory = errors.New("support: invalid category")
	ErrInvalidPriority = errors.New("support: invalid priority")
	ErrInvalidChannel  = errors.New("support: invalid channel")
	ErrInvalidStatus   = errors.New("support: invalid status")
)

// ValidateEmail enforces a pragmatic input contract for an email
// address (presence of @ and ., bounded length, no whitespace).
func ValidateEmail(s string) (string, error) {
	s = strings.ToLower(strings.TrimSpace(s))
	if s == "" || len(s) > MaxEmailLen {
		return "", ErrInvalidEmail
	}
	at := strings.IndexByte(s, '@')
	if at <= 0 || at == len(s)-1 {
		return "", ErrInvalidEmail
	}
	if !strings.Contains(s[at:], ".") {
		return "", ErrInvalidEmail
	}
	if strings.ContainsAny(s, " \t\r\n") {
		return "", ErrInvalidEmail
	}
	return s, nil
}

// ValidateName accepts an optional human name.
func ValidateName(s string) (string, error) {
	s = strings.TrimSpace(s)
	if len(s) > MaxNameLen {
		return "", ErrInvalidName
	}
	for _, r := range s {
		if r < 0x20 && r != '\t' {
			return "", ErrInvalidName
		}
	}
	return s, nil
}

// ValidateSubject enforces the input contract for a ticket subject.
func ValidateSubject(s string) (string, error) {
	s = strings.TrimSpace(s)
	if len(s) < MinSubjectLen || len(s) > MaxSubjectLen {
		return "", ErrInvalidSubject
	}
	return s, nil
}

// ValidateBody enforces the input contract for a ticket / message body.
func ValidateBody(s string) (string, error) {
	s = strings.TrimSpace(s)
	if len(s) < MinBodyLen || len(s) > MaxBodyLen {
		return "", ErrInvalidBody
	}
	return s, nil
}

// NormaliseCategory accepts empty (default 'general') or a known value.
func NormaliseCategory(s string) (TicketCategory, error) {
	s = strings.ToLower(strings.TrimSpace(s))
	if s == "" {
		return CategoryGeneral, nil
	}
	c := TicketCategory(s)
	if !c.IsValid() {
		return "", ErrInvalidCategory
	}
	return c, nil
}

// NormalisePriority accepts empty (default 'normal') or a known value.
func NormalisePriority(s string) (TicketPriority, error) {
	s = strings.ToLower(strings.TrimSpace(s))
	if s == "" {
		return PriorityNormal, nil
	}
	p := TicketPriority(s)
	if !p.IsValid() {
		return "", ErrInvalidPriority
	}
	return p, nil
}

// TruncateUserAgent caps the stored UA. Audit-only field; never parsed.
func TruncateUserAgent(ua string) string {
	if len(ua) <= MaxUserAgentLen {
		return ua
	}
	return ua[:MaxUserAgentLen]
}

// ----------------------------------------------------------------------
// Identifier generation
// ----------------------------------------------------------------------

// generateID returns a hex-encoded 16-byte (128-bit) identifier.
func generateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// generatePublicRef returns a short, URL-safe ticket reference shown
// to the user in emails and dashboard URLs (e.g. TKT-3F9A21B7).
func generatePublicRef() string {
	b := make([]byte, 4)
	_, _ = rand.Read(b)
	return "TKT-" + strings.ToUpper(hex.EncodeToString(b))
}
