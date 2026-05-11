package consent

import (
	"context"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Integration tests for the consent store run only when POSTGRES_TEST_URL
// is set, matching the convention used by every other store_test.go in
// this repo. CI provides a Postgres instance; local devs can opt in by
// pointing at a throwaway DB.
func newTestStore(t *testing.T) (*Store, func()) {
	t.Helper()
	url := os.Getenv("POSTGRES_TEST_URL")
	if strings.TrimSpace(url) == "" {
		t.Skip("POSTGRES_TEST_URL not set; skipping consent store integration tests")
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
	// Isolate this test run by wiping the table. The table is
	// idempotently-created above so this is safe to repeat.
	if _, err := pool.Exec(ctx, `DELETE FROM consent_records`); err != nil {
		pool.Close()
		t.Fatalf("wipe: %v", err)
	}

	return NewStore(pool), func() { pool.Close() }
}

func TestStore_InsertAndLatestForAnonymous(t *testing.T) {
	s, close := newTestStore(t)
	defer close()
	ctx := context.Background()

	rec, err := s.Insert(ctx, InsertParams{
		AnonymousID:   "anon-1",
		PolicyVersion: "v1",
		Categories:    Categories{Functional: true, Analytics: false},
		UserAgent:     "go-test",
	})
	if err != nil {
		t.Fatalf("insert: %v", err)
	}
	if rec.ID == "" || rec.CreatedAt.IsZero() {
		t.Fatalf("insert returned empty id or zero time: %+v", rec)
	}

	got, err := s.LatestForAnonymousID(ctx, "anon-1")
	if err != nil {
		t.Fatalf("latest: %v", err)
	}
	if got == nil {
		t.Fatal("latest returned nil for known anonymous_id")
	}
	if got.PolicyVersion != "v1" || !got.Categories.Functional || got.Categories.Analytics {
		t.Fatalf("latest mismatch: %+v", got)
	}
}

func TestStore_LatestForAnonymous_NotFound(t *testing.T) {
	s, close := newTestStore(t)
	defer close()
	ctx := context.Background()

	got, err := s.LatestForAnonymousID(ctx, "never-recorded")
	if err != nil {
		t.Fatalf("latest: %v", err)
	}
	if got != nil {
		t.Fatalf("expected nil, got %+v", got)
	}
}

func TestStore_HistoryOrderedNewestFirst(t *testing.T) {
	s, close := newTestStore(t)
	defer close()
	ctx := context.Background()

	userID := "user-1"
	for i := 0; i < 3; i++ {
		_, err := s.Insert(ctx, InsertParams{
			UserID:        &userID,
			AnonymousID:   "anon-x",
			PolicyVersion: "v1",
			Categories:    AllRejected(),
		})
		if err != nil {
			t.Fatalf("insert %d: %v", i, err)
		}
		time.Sleep(5 * time.Millisecond)
	}

	hist, err := s.HistoryForUserID(ctx, userID, 10)
	if err != nil {
		t.Fatalf("history: %v", err)
	}
	if len(hist) != 3 {
		t.Fatalf("want 3 rows, got %d", len(hist))
	}
	for i := 1; i < len(hist); i++ {
		if !hist[i-1].CreatedAt.After(hist[i].CreatedAt) {
			t.Fatalf("history not newest-first at index %d", i)
		}
	}
}

func TestStore_AttachAnonymousToUser(t *testing.T) {
	s, close := newTestStore(t)
	defer close()
	ctx := context.Background()

	// Two anonymous rows, then attach to a user.
	for i := 0; i < 2; i++ {
		_, err := s.Insert(ctx, InsertParams{
			AnonymousID:   "anon-z",
			PolicyVersion: "v1",
			Categories:    AllAccepted(),
		})
		if err != nil {
			t.Fatalf("insert %d: %v", i, err)
		}
	}

	n, err := s.AttachAnonymousToUser(ctx, "anon-z", "user-99")
	if err != nil {
		t.Fatalf("attach: %v", err)
	}
	if n != 2 {
		t.Fatalf("want 2 rows attached, got %d", n)
	}

	// Re-running the attach must be a no-op (idempotency safety).
	n, err = s.AttachAnonymousToUser(ctx, "anon-z", "user-99")
	if err != nil {
		t.Fatalf("re-attach: %v", err)
	}
	if n != 0 {
		t.Fatalf("want 0 rows on re-attach, got %d", n)
	}

	latest, err := s.LatestForUserID(ctx, "user-99")
	if err != nil {
		t.Fatalf("latest: %v", err)
	}
	if latest == nil || latest.UserID == nil || *latest.UserID != "user-99" {
		t.Fatalf("latest after attach: %+v", latest)
	}
}

func TestStore_InsertRejectsInvalidInput(t *testing.T) {
	s, close := newTestStore(t)
	defer close()
	ctx := context.Background()

	cases := []struct {
		name   string
		params InsertParams
	}{
		{"empty anonymous_id", InsertParams{PolicyVersion: "v1"}},
		{"empty policy_version", InsertParams{AnonymousID: "a"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := s.Insert(ctx, tc.params); err == nil {
				t.Fatalf("expected error")
			}
		})
	}
}
