package support

import (
	"context"
	"errors"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Integration tests for the support store run only when
// POSTGRES_TEST_URL is set. This matches the convention used by
// src/consent/store_test.go and src/auth/store integration suites:
// CI provisions a throwaway Postgres; local devs opt-in.
func newTestStore(t *testing.T) (*Store, *pgxpool.Pool, func()) {
	t.Helper()
	url := os.Getenv("POSTGRES_TEST_URL")
	if strings.TrimSpace(url) == "" {
		t.Skip("POSTGRES_TEST_URL not set; skipping support store integration tests")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := pgxpool.New(ctx, url)
	if err != nil {
		t.Fatalf("pgxpool.New: %v", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		t.Fatalf("pgxpool.Ping: %v", err)
	}
	if _, err := pool.Exec(ctx, SchemaSQL()); err != nil {
		pool.Close()
		t.Fatalf("schema: %v", err)
	}
	// Wipe both tables in the correct order (messages references
	// tickets via FK ON DELETE CASCADE, so deleting tickets is
	// enough, but be explicit so re-runs are deterministic even if
	// the schema is altered later).
	if _, err := pool.Exec(ctx, `DELETE FROM support_ticket_messages`); err != nil {
		pool.Close()
		t.Fatalf("wipe messages: %v", err)
	}
	if _, err := pool.Exec(ctx, `DELETE FROM support_tickets`); err != nil {
		pool.Close()
		t.Fatalf("wipe tickets: %v", err)
	}
	return NewStore(pool), pool, func() { pool.Close() }
}

func seedTicket(t *testing.T, s *Store, userID *string, email string) *Ticket {
	t.Helper()
	t2, err := s.CreateTicket(context.Background(), CreateParams{
		UserID:    userID,
		Email:     email,
		Name:      "Test User",
		Subject:   "Initial subject",
		Body:      "Initial body content",
		Category:  CategoryGeneral,
		Priority:  PriorityNormal,
		Channel:   ChannelContact,
		IPAddress: "127.0.0.1",
		UserAgent: "go-test",
	})
	if err != nil {
		t.Fatalf("seed CreateTicket: %v", err)
	}
	return t2
}

func TestStore_CreateTicket_PersistsTicketAndFirstMessage(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	uid := "user-1"
	tk := seedTicket(t, s, &uid, "user@example.com")
	if tk.ID == "" || tk.PublicRef == "" {
		t.Fatalf("missing ids: %+v", tk)
	}
	if len(tk.Messages) != 1 {
		t.Fatalf("want 1 seed message, got %d", len(tk.Messages))
	}
	if tk.Status != StatusOpen {
		t.Fatalf("want status=open, got %q", tk.Status)
	}

	// Re-read via GetWithMessages to confirm round-trip.
	got, err := s.GetWithMessages(context.Background(), tk.ID, uid)
	if err != nil {
		t.Fatalf("GetWithMessages: %v", err)
	}
	if got.PublicRef != tk.PublicRef || len(got.Messages) != 1 {
		t.Fatalf("round-trip mismatch: %+v vs %+v", got, tk)
	}
}

func TestStore_GetWithMessages_OwnershipEnforced(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	uid := "owner-1"
	tk := seedTicket(t, s, &uid, "owner@example.com")

	_, err := s.GetWithMessages(context.Background(), tk.ID, "stranger-2")
	if !errors.Is(err, ErrTicketNotFound) {
		t.Fatalf("want ErrTicketNotFound for non-owner, got %v", err)
	}
}

func TestStore_AppendMessage_UserReplyReopensResolved(t *testing.T) {
	s, pool, close := newTestStore(t)
	defer close()

	uid := "owner-2"
	tk := seedTicket(t, s, &uid, "r@example.com")

	// Move directly to 'resolved' via an out-of-band UPDATE so we do
	// not couple this test to staff-side logic that does not exist
	// in the store yet.
	if _, err := pool.Exec(context.Background(),
		`UPDATE support_tickets SET status='resolved' WHERE id=$1`, tk.ID,
	); err != nil {
		t.Fatalf("force resolved: %v", err)
	}

	msg, updated, err := s.AppendMessage(context.Background(), tk.ID, uid, AuthorKindUser, "please reopen")
	if err != nil {
		t.Fatalf("AppendMessage: %v", err)
	}
	if msg.AuthorKind != AuthorKindUser {
		t.Fatalf("author=%q", msg.AuthorKind)
	}
	if updated.Status != StatusOpen {
		t.Fatalf("want status=open after user reply, got %q", updated.Status)
	}
}

func TestStore_AppendMessage_ClosedTicketRejected(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	uid := "owner-3"
	tk := seedTicket(t, s, &uid, "c@example.com")
	if _, err := s.CloseTicket(context.Background(), tk.ID, uid); err != nil {
		t.Fatalf("CloseTicket: %v", err)
	}

	_, _, err := s.AppendMessage(context.Background(), tk.ID, uid, AuthorKindUser, "too late")
	if !errors.Is(err, ErrTicketClosed) {
		t.Fatalf("want ErrTicketClosed, got %v", err)
	}
}

func TestStore_AppendMessage_OwnershipEnforced_UserKind(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	uid := "owner-4"
	tk := seedTicket(t, s, &uid, "o4@example.com")

	_, _, err := s.AppendMessage(context.Background(), tk.ID, "stranger", AuthorKindUser, "hi")
	if !errors.Is(err, ErrTicketNotFound) {
		t.Fatalf("want ErrTicketNotFound for non-owner user reply, got %v", err)
	}
}

func TestStore_CloseTicket_Idempotent(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	uid := "owner-5"
	tk := seedTicket(t, s, &uid, "o5@example.com")

	if _, err := s.CloseTicket(context.Background(), tk.ID, uid); err != nil {
		t.Fatalf("first close: %v", err)
	}
	// Second close: must be ErrTicketClosed (the surface the handler
	// maps to HTTP 409), not a successful re-close.
	if _, err := s.CloseTicket(context.Background(), tk.ID, uid); !errors.Is(err, ErrTicketClosed) {
		t.Fatalf("want ErrTicketClosed on second close, got %v", err)
	}
}

func TestStore_CloseTicket_OwnershipEnforced(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	uid := "owner-6"
	tk := seedTicket(t, s, &uid, "o6@example.com")

	if _, err := s.CloseTicket(context.Background(), tk.ID, "stranger"); !errors.Is(err, ErrTicketNotFound) {
		t.Fatalf("want ErrTicketNotFound for non-owner close, got %v", err)
	}
}

func TestStore_CountOpenByEmail_IgnoresClosed(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	email := "counted@example.com"
	uid := "counted-uid"

	// Three open + one closed.
	seedTicket(t, s, &uid, email)
	seedTicket(t, s, &uid, email)
	seedTicket(t, s, &uid, email)
	doomed := seedTicket(t, s, &uid, email)
	if _, err := s.CloseTicket(context.Background(), doomed.ID, uid); err != nil {
		t.Fatalf("close doomed: %v", err)
	}

	n, err := s.CountOpenByEmail(context.Background(), email)
	if err != nil {
		t.Fatalf("CountOpenByEmail: %v", err)
	}
	if n != 3 {
		t.Fatalf("want 3 open, got %d", n)
	}
}

func TestStore_ListByUser_BoundsLimitAndOffset(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	uid := "lister"
	for i := 0; i < 5; i++ {
		seedTicket(t, s, &uid, "l@example.com")
	}

	out, err := s.ListByUser(context.Background(), uid, 2, 0)
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(out) != 2 {
		t.Fatalf("want 2, got %d", len(out))
	}

	// limit <= 0 -> default 25, limit > 100 -> capped at 100.
	out, err = s.ListByUser(context.Background(), uid, 0, 0)
	if err != nil {
		t.Fatalf("list default: %v", err)
	}
	if len(out) != 5 {
		t.Fatalf("want 5 with default limit, got %d", len(out))
	}
	out, err = s.ListByUser(context.Background(), uid, 9999, 0)
	if err != nil {
		t.Fatalf("list capped: %v", err)
	}
	if len(out) != 5 {
		t.Fatalf("want 5 with cap, got %d", len(out))
	}

	// Empty userID is rejected without touching the DB.
	if _, err := s.ListByUser(context.Background(), "", 10, 0); err == nil {
		t.Fatal("want err for empty user_id")
	}
}

func TestStore_ListByUser_OrderingNewestFirst(t *testing.T) {
	s, _, close := newTestStore(t)
	defer close()

	uid := "orderer"
	first := seedTicket(t, s, &uid, "o@example.com")
	// Sleep so the second ticket's updated_at differs by at least 1
	// microsecond; Postgres TIMESTAMPTZ has microsecond resolution
	// so a sub-microsecond sleep can collide on fast hardware.
	time.Sleep(2 * time.Millisecond)
	second := seedTicket(t, s, &uid, "o@example.com")

	out, err := s.ListByUser(context.Background(), uid, 10, 0)
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(out) != 2 || out[0].ID != second.ID || out[1].ID != first.ID {
		t.Fatalf("want newest-first ordering, got %+v", out)
	}
}
