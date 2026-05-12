package support

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Store is the PostgreSQL-backed persistence layer for support
// tickets and messages.
type Store struct {
	pool *pgxpool.Pool
}

// NewStore creates a support store backed by the given pool.
func NewStore(pool *pgxpool.Pool) *Store {
	return &Store{pool: pool}
}

// ErrTicketNotFound is returned when a ticket lookup finds no row OR
// when the caller does not own the ticket. The handler maps this to
// HTTP 404 so a probing caller cannot distinguish the two states.
var ErrTicketNotFound = errors.New("support: ticket not found")

// ErrTicketClosed is returned when a caller tries to mutate a ticket
// that is already in the terminal closed state. Mapped to HTTP 409.
var ErrTicketClosed = errors.New("support: ticket already closed")

// publicRefCollisionRetries bounds the retry count for the
// vanishingly rare 32-bit ref collision.
const publicRefCollisionRetries = 5

// CreateParams is the input to Store.CreateTicket. UserID is optional
// because the public contact form is reachable by anonymous visitors.
type CreateParams struct {
	UserID    *string
	Email     string
	Name      string
	Subject   string
	Body      string
	Category  TicketCategory
	Priority  TicketPriority
	Channel   TicketChannel
	IPAddress string
	UserAgent string
}

// CreateTicket inserts a new ticket and its first message in a single
// transaction so an HTTP retry never produces a ticket without a body.
func (s *Store) CreateTicket(ctx context.Context, p CreateParams) (*Ticket, error) {
	if !p.Category.IsValid() {
		return nil, ErrInvalidCategory
	}
	if !p.Priority.IsValid() {
		return nil, ErrInvalidPriority
	}
	if !p.Channel.IsValid() {
		return nil, ErrInvalidChannel
	}

	now := time.Now().UTC()
	ticketID := generateID()
	msgID := generateID()
	ua := TruncateUserAgent(p.UserAgent)

	tx, err := s.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return nil, fmt.Errorf("support: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	var publicRef string
	for i := 0; i < publicRefCollisionRetries; i++ {
		publicRef = generatePublicRef()
		_, err = tx.Exec(ctx,
			`INSERT INTO support_tickets
			   (id, public_ref, user_id, email, name, subject, category,
			    priority, status, channel, ip_address, user_agent,
			    created_at, updated_at)
			 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $13)`,
			ticketID, publicRef, p.UserID, p.Email, p.Name, p.Subject,
			string(p.Category), string(p.Priority), string(StatusOpen),
			string(p.Channel), p.IPAddress, ua, now,
		)
		if err == nil {
			break
		}
		if !isUniqueViolation(err) || i == publicRefCollisionRetries-1 {
			return nil, fmt.Errorf("support: insert ticket: %w", err)
		}
	}

	authorID := ""
	if p.UserID != nil {
		authorID = *p.UserID
	}

	_, err = tx.Exec(ctx,
		`INSERT INTO support_ticket_messages
		   (id, ticket_id, author_kind, author_id, body, created_at)
		 VALUES ($1, $2, $3, $4, $5, $6)`,
		msgID, ticketID, string(AuthorKindUser), authorID, p.Body, now,
	)
	if err != nil {
		return nil, fmt.Errorf("support: insert seed message: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, fmt.Errorf("support: commit: %w", err)
	}

	return &Ticket{
		ID:        ticketID,
		PublicRef: publicRef,
		UserID:    p.UserID,
		Email:     p.Email,
		Name:      p.Name,
		Subject:   p.Subject,
		Category:  p.Category,
		Priority:  p.Priority,
		Status:    StatusOpen,
		Channel:   p.Channel,
		CreatedAt: now,
		UpdatedAt: now,
		Messages: []Message{{
			ID:         msgID,
			TicketID:   ticketID,
			AuthorKind: AuthorKindUser,
			AuthorID:   authorID,
			Body:       p.Body,
			CreatedAt:  now,
		}},
	}, nil
}

// AppendMessage appends a new reply to an existing ticket and bumps
// updated_at. Ownership is enforced inside the SQL.
func (s *Store) AppendMessage(
	ctx context.Context,
	ticketID string,
	userID string,
	authorKind MessageAuthorKind,
	body string,
) (*Message, *Ticket, error) {
	if !authorKind.IsValid() {
		return nil, nil, errors.New("support: invalid author_kind")
	}

	now := time.Now().UTC()
	msgID := generateID()

	tx, err := s.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return nil, nil, fmt.Errorf("support: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	var (
		ownerID *string
		status  string
	)
	err = tx.QueryRow(ctx,
		`SELECT user_id, status FROM support_tickets WHERE id = $1`,
		ticketID,
	).Scan(&ownerID, &status)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil, ErrTicketNotFound
		}
		return nil, nil, fmt.Errorf("support: lookup ticket: %w", err)
	}
	if authorKind == AuthorKindUser {
		if ownerID == nil || *ownerID != userID {
			return nil, nil, ErrTicketNotFound
		}
	}
	if TicketStatus(status) == StatusClosed {
		return nil, nil, ErrTicketClosed
	}

	_, err = tx.Exec(ctx,
		`INSERT INTO support_ticket_messages
		   (id, ticket_id, author_kind, author_id, body, created_at)
		 VALUES ($1, $2, $3, $4, $5, $6)`,
		msgID, ticketID, string(authorKind), userID, body, now,
	)
	if err != nil {
		return nil, nil, fmt.Errorf("support: insert message: %w", err)
	}

	// A user reply reopens a resolved ticket; otherwise leave status alone.
	newStatus := TicketStatus(status)
	if authorKind == AuthorKindUser && newStatus == StatusResolved {
		newStatus = StatusOpen
	}

	_, err = tx.Exec(ctx,
		`UPDATE support_tickets
		    SET updated_at = $1, status = $2
		  WHERE id = $3`,
		now, string(newStatus), ticketID,
	)
	if err != nil {
		return nil, nil, fmt.Errorf("support: update ticket: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, nil, fmt.Errorf("support: commit: %w", err)
	}

	t, err := s.getTicketCore(ctx, ticketID)
	if err != nil {
		return nil, nil, err
	}

	return &Message{
		ID:         msgID,
		TicketID:   ticketID,
		AuthorKind: authorKind,
		AuthorID:   userID,
		Body:       body,
		CreatedAt:  now,
	}, t, nil
}

// GetWithMessages returns a ticket and its full conversation log,
// scoped to the caller's user_id.
func (s *Store) GetWithMessages(
	ctx context.Context,
	ticketID string,
	userID string,
) (*Ticket, error) {
	t, err := s.getTicketCore(ctx, ticketID)
	if err != nil {
		return nil, err
	}
	if t.UserID == nil || *t.UserID != userID {
		return nil, ErrTicketNotFound
	}

	rows, err := s.pool.Query(ctx,
		`SELECT id, ticket_id, author_kind, author_id, body, created_at
		   FROM support_ticket_messages
		  WHERE ticket_id = $1
		  ORDER BY created_at ASC`,
		ticketID,
	)
	if err != nil {
		return nil, fmt.Errorf("support: messages query: %w", err)
	}
	defer rows.Close()

	t.Messages = make([]Message, 0, 4)
	for rows.Next() {
		var (
			m          Message
			authorKind string
		)
		if err := rows.Scan(&m.ID, &m.TicketID, &authorKind, &m.AuthorID, &m.Body, &m.CreatedAt); err != nil {
			return nil, fmt.Errorf("support: messages scan: %w", err)
		}
		m.AuthorKind = MessageAuthorKind(authorKind)
		t.Messages = append(t.Messages, m)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("support: messages iterate: %w", err)
	}
	return t, nil
}

// ListByUser returns a bounded, newest-first list of tickets owned by
// the given user.
func (s *Store) ListByUser(
	ctx context.Context,
	userID string,
	limit, offset int,
) ([]Ticket, error) {
	if userID == "" {
		return nil, errors.New("support: empty user_id")
	}
	if limit <= 0 {
		limit = 25
	}
	if limit > 100 {
		limit = 100
	}
	if offset < 0 {
		offset = 0
	}

	rows, err := s.pool.Query(ctx,
		`SELECT id, public_ref, user_id, email, name, subject, category,
		        priority, status, channel, created_at, updated_at, closed_at
		   FROM support_tickets
		  WHERE user_id = $1
		  ORDER BY updated_at DESC
		  LIMIT $2 OFFSET $3`,
		userID, limit, offset,
	)
	if err != nil {
		return nil, fmt.Errorf("support: list query: %w", err)
	}
	defer rows.Close()

	out := make([]Ticket, 0, limit)
	for rows.Next() {
		t, err := scanTicket(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, *t)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("support: list iterate: %w", err)
	}
	return out, nil
}

// CloseTicket transitions a ticket to the closed state.
func (s *Store) CloseTicket(ctx context.Context, ticketID, userID string) (*Ticket, error) {
	now := time.Now().UTC()

	tag, err := s.pool.Exec(ctx,
		`UPDATE support_tickets
		    SET status = $1, closed_at = $2, updated_at = $2
		  WHERE id = $3
		    AND user_id = $4
		    AND status <> $1`,
		string(StatusClosed), now, ticketID, userID,
	)
	if err != nil {
		return nil, fmt.Errorf("support: close ticket: %w", err)
	}
	if tag.RowsAffected() == 0 {
		t, err := s.getTicketCore(ctx, ticketID)
		if err != nil {
			return nil, ErrTicketNotFound
		}
		if t.UserID == nil || *t.UserID != userID {
			return nil, ErrTicketNotFound
		}
		if t.Status == StatusClosed {
			return nil, ErrTicketClosed
		}
		return nil, ErrTicketNotFound
	}
	return s.getTicketCore(ctx, ticketID)
}

// CountOpenByEmail returns how many non-closed tickets exist for the
// given email. Used by the public contact handler to throttle.
func (s *Store) CountOpenByEmail(ctx context.Context, email string) (int64, error) {
	var n int64
	err := s.pool.QueryRow(ctx,
		`SELECT COUNT(*)
		   FROM support_tickets
		  WHERE email = $1
		    AND status <> $2`,
		email, string(StatusClosed),
	).Scan(&n)
	if err != nil {
		return 0, fmt.Errorf("support: count open: %w", err)
	}
	return n, nil
}

// ----------------------------------------------------------------------
// Internal helpers
// ----------------------------------------------------------------------

func (s *Store) getTicketCore(ctx context.Context, id string) (*Ticket, error) {
	row := s.pool.QueryRow(ctx,
		`SELECT id, public_ref, user_id, email, name, subject, category,
		        priority, status, channel, created_at, updated_at, closed_at
		   FROM support_tickets
		  WHERE id = $1`,
		id,
	)
	t, err := scanTicket(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrTicketNotFound
		}
		return nil, err
	}
	return t, nil
}

type rowScanner interface {
	Scan(dest ...any) error
}

func scanTicket(r rowScanner) (*Ticket, error) {
	var (
		t        Ticket
		userID   *string
		category string
		priority string
		status   string
		channel  string
		closedAt *time.Time
	)
	err := r.Scan(
		&t.ID, &t.PublicRef, &userID, &t.Email, &t.Name, &t.Subject,
		&category, &priority, &status, &channel,
		&t.CreatedAt, &t.UpdatedAt, &closedAt,
	)
	if err != nil {
		return nil, err
	}
	t.UserID = userID
	t.Category = TicketCategory(category)
	t.Priority = TicketPriority(priority)
	t.Status = TicketStatus(status)
	t.Channel = TicketChannel(channel)
	t.ClosedAt = closedAt
	return &t, nil
}

// isUniqueViolation reports whether err is a PostgreSQL
// 23505 (unique_violation). The store retries public_ref generation on
// this signal exclusively; any other DB error fails fast.
func isUniqueViolation(err error) bool {
	var pgErr *pgconn.PgError
	return errors.As(err, &pgErr) && pgErr.Code == "23505"
}
