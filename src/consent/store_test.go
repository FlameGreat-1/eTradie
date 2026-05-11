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

// --- Retention tests (audit finding H) ---------------------------------

// insertAt inserts a row and back-dates its created_at directly via
// SQL UPDATE so the test can produce a row whose timestamp is older
// than the in-process clock allows. The Store.Insert path always
// stamps time.Now().UTC(), which is the right production behaviour,
// so we reach behind it for the test-only back-date.
func insertAt(t *testing.T, s *Store, anon string, userID *string, when time.Time) {
	t.Helper()
	ctx := context.Background()
	rec, err := s.Insert(ctx, InsertParams{
		UserID:        userID,
		AnonymousID:   anon,
		PolicyVersion: "v1",
		Categories:    AllRejected(),
	})
	if err != nil {
		t.Fatalf("insert: %v", err)
	}
	if _, err := s.pool.Exec(ctx,
		`UPDATE consent_records SET created_at = $1 WHERE id = $2`,
		when.UTC(), rec.ID,
	); err != nil {
		t.Fatalf("back-date update: %v", err)
	}
}

func countRows(t *testing.T, s *Store) int {
	t.Helper()
	var n int
	if err := s.pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM consent_records`,
	).Scan(&n); err != nil {
		t.Fatalf("count: %v", err)
	}
	return n
}

func TestStore_DeleteExpired_PreservesLatestPerAnonymousID(t *testing.T) {
	s, close := newTestStore(t)
	defer close()

	now := time.Now().UTC()
	insertAt(t, s, "anon-rt-1", nil, now.AddDate(-3, 0, 0)) // 3y old
	insertAt(t, s, "anon-rt-1", nil, now.AddDate(-2, -6, 0)) // 2.5y old
	insertAt(t, s, "anon-rt-1", nil, now.AddDate(0, -1, 0)) // 1 month old (KEEP)

	cutoff := now.AddDate(-2, 0, 0)
	deleted, err := s.DeleteExpired(context.Background(), cutoff)
	if err != nil {
		t.Fatalf("DeleteExpired: %v", err)
	}
	// Both rows older than the cutoff are also older than the
	// 1-month-old latest, so they should both be deleted.
	if deleted != 2 {
		t.Fatalf("want 2 deleted, got %d", deleted)
	}
	if got := countRows(t, s); got != 1 {
		t.Fatalf("want 1 row remaining (the latest), got %d", got)
	}
	latest, err := s.LatestForAnonymousID(context.Background(), "anon-rt-1")
	if err != nil || latest == nil {
		t.Fatalf("latest after retention: %v %+v", err, latest)
	}
	if latest.CreatedAt.Before(now.AddDate(0, -2, 0)) {
		t.Fatalf("surviving row is not the newest: %+v", latest)
	}
}

func TestStore_DeleteExpired_PreservesLatestPerUserID(t *testing.T) {
	s, close := newTestStore(t)
	defer close()

	uid := "user-rt-1"
	now := time.Now().UTC()
	// Three rows for the same user across different anonymous_ids,
	// all older than the cutoff EXCEPT we want the latest one to be
	// preserved by the per-user-id rule.
	insertAt(t, s, "anon-A", &uid, now.AddDate(-5, 0, 0))
	insertAt(t, s, "anon-B", &uid, now.AddDate(-4, 0, 0))
	insertAt(t, s, "anon-C", &uid, now.AddDate(-3, 0, 0)) // latest among these, still older than cutoff

	cutoff := now.AddDate(-2, 0, 0)
	deleted, err := s.DeleteExpired(context.Background(), cutoff)
	if err != nil {
		t.Fatalf("DeleteExpired: %v", err)
	}
	// Two should be deleted; the latest per user_id is preserved
	// even though it is older than the cutoff.
	if deleted != 2 {
		t.Fatalf("want 2 deleted, got %d", deleted)
	}
	latest, err := s.LatestForUserID(context.Background(), uid)
	if err != nil || latest == nil {
		t.Fatalf("latest for user after retention: %v %+v", err, latest)
	}
	if latest.AnonymousID != "anon-C" {
		t.Fatalf("surviving row is not the newest per user_id: %+v", latest)
	}
}

func TestStore_DeleteExpired_DeletesOldOnlyOnceLatestPreserved(t *testing.T) {
	s, close := newTestStore(t)
	defer close()

	now := time.Now().UTC()
	uid := "user-mixed-1"

	// Mixed: one ancient anonymous-only row, one ancient user row,
	// one recent user row. The recent row protects both the user_id
	// latest AND the anonymous_id latest because it shares the
	// anonymous_id with the ancient anonymous row.
	insertAt(t, s, "anon-mixed", nil, now.AddDate(-5, 0, 0)) // ancient, anon only
	insertAt(t, s, "anon-mixed", &uid, now.AddDate(-4, 0, 0)) // ancient, user too
	insertAt(t, s, "anon-mixed", &uid, now.AddDate(0, -1, 0)) // recent (KEEP)

	cutoff := now.AddDate(-2, 0, 0)
	deleted, err := s.DeleteExpired(context.Background(), cutoff)
	if err != nil {
		t.Fatalf("DeleteExpired: %v", err)
	}
	if deleted != 2 {
		t.Fatalf("want 2 deleted, got %d", deleted)
	}
	if got := countRows(t, s); got != 1 {
		t.Fatalf("want 1 row remaining, got %d", got)
	}
}

func TestStore_CutoffFromNow_IsCalendarAware(t *testing.T) {
	now := time.Date(2026, 5, 11, 12, 0, 0, 0, time.UTC)
	cutoff := CutoffFromNow(now)
	want := time.Date(2024, 5, 11, 12, 0, 0, 0, time.UTC)
	if !cutoff.Equal(want) {
		t.Fatalf("CutoffFromNow: want %s, got %s", want, cutoff)
	}

	// Month-end safety: AddDate handles month rollovers correctly.
	// Going back 24 months from 2026-03-31 gives 2024-03-31, not
	// 2024-04-01 (Go's AddDate normalises that path).
	now2 := time.Date(2026, 3, 31, 0, 0, 0, 0, time.UTC)
	got2 := CutoffFromNow(now2)
	want2 := time.Date(2024, 3, 31, 0, 0, 0, 0, time.UTC)
	if !got2.Equal(want2) {
		t.Fatalf("CutoffFromNow month-end: want %s, got %s", want2, got2)
	}
}
