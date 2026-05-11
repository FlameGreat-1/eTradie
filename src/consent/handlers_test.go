package consent

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"github.com/rs/zerolog"
)

// stubResolver is a deterministic IPResolver used by every handler
// test so the produced ip_hash is independent of the test runner's
// network configuration.
type stubResolver struct{ ip string }

func (s *stubResolver) Resolve(_ *http.Request) string { return s.ip }

// fakeLimiter is a deterministic in-memory limiter for tests. It
// permits `cap` Allow() calls per distinct key; subsequent calls
// return false. Safe for concurrent use because the handler may be
// hit from multiple goroutines in t.Parallel scenarios.
type fakeLimiter struct {
	mu     sync.Mutex
	cap    int
	counts map[string]int
}

func newFakeLimiter(cap int) *fakeLimiter {
	return &fakeLimiter{cap: cap, counts: map[string]int{}}
}

func (f *fakeLimiter) Allow(key string) bool {
	f.mu.Lock()
	defer f.mu.Unlock()
	if f.counts[key] >= f.cap {
		return false
	}
	f.counts[key]++
	return true
}

func newTestHandler(t *testing.T) (*Handler, *Store, func()) {
	t.Helper()
	// newTestStore already runs SchemaSQL, wipes the table, and
	// calls t.Skip when POSTGRES_TEST_URL is unset.
	store, dbClose := newTestStore(t)
	h := NewHandler(
		store,
		&stubResolver{ip: "127.0.0.1"},
		[]byte("unit-test-salt"),
		zerolog.Nop(),
	)
	return h, store, dbClose
}

// newTestHandlerWithLimiters wires deterministic limiters for tests
// that exercise the 429 paths. Both limiters are returned so the
// test can inspect their state.
func newTestHandlerWithLimiters(t *testing.T, ipCap, anonCap int) (*Handler, *Store, *fakeLimiter, *fakeLimiter, func()) {
	t.Helper()
	store, dbClose := newTestStore(t)
	ipL := newFakeLimiter(ipCap)
	anonL := newFakeLimiter(anonCap)
	h := NewHandlerWithLimiters(
		store,
		&stubResolver{ip: "127.0.0.1"},
		[]byte("unit-test-salt"),
		ipL,
		anonL,
		zerolog.Nop(),
	)
	return h, store, ipL, anonL, dbClose
}

// Many test environments do not have Postgres available; in that
// case newTestStore calls t.Skip and the assertion below short-
// circuits, mirroring the convention used by store_test.go.
func TestHandler_PostConsentAnonymous(t *testing.T) {
	h, store, close := newTestHandler(t)
	defer close()

	body := strings.NewReader(`{
		"anonymous_id": "anon-handler-1",
		"policy_version": "v1",
		"categories": {"functional": true, "analytics": false}
	}`)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/consent", body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	h.handleConsent(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("want 201, got %d body=%s", rec.Code, rec.Body.String())
	}

	var resp consentResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp.Record == nil || resp.Record.AnonymousID != "anon-handler-1" {
		t.Fatalf("bad record: %+v", resp.Record)
	}

	// Verify the row landed in the store.
	latest, err := store.LatestForAnonymousID(context.Background(), "anon-handler-1")
	if err != nil {
		t.Fatalf("latest: %v", err)
	}
	if latest == nil || !latest.Categories.Functional || latest.Categories.Analytics {
		t.Fatalf("bad stored row: %+v", latest)
	}
}

func TestHandler_PostConsent_RejectsInvalidJSON(t *testing.T) {
	h, _, close := newTestHandler(t)
	defer close()

	req := httptest.NewRequest(http.MethodPost, "/api/v1/consent", bytes.NewReader([]byte(`not-json`)))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	h.handleConsent(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("want 400, got %d", rec.Code)
	}
}

func TestHandler_PostConsent_RejectsMissingFields(t *testing.T) {
	h, _, close := newTestHandler(t)
	defer close()

	cases := []string{
		`{"policy_version":"v1"}`,
		`{"anonymous_id":"a"}`,
	}
	for _, body := range cases {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/consent", strings.NewReader(body))
		rec := httptest.NewRecorder()
		h.handleConsent(rec, req)
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("want 400 for body %q, got %d", body, rec.Code)
		}
	}
}

func TestHandler_GetLatest_AnonymousRequiresQueryParam(t *testing.T) {
	h, _, close := newTestHandler(t)
	defer close()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/consent", nil)
	rec := httptest.NewRecorder()
	h.handleConsent(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("want 400 when anonymous_id missing, got %d", rec.Code)
	}
}

func TestHandler_GetLatest_AnonymousReturnsNullWhenAbsent(t *testing.T) {
	h, _, close := newTestHandler(t)
	defer close()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/consent?anonymous_id=never-set", nil)
	rec := httptest.NewRecorder()
	h.handleConsent(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", rec.Code)
	}
	var resp consentResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp.Record != nil {
		t.Fatalf("expected nil record, got %+v", resp.Record)
	}
}

func TestHandler_RejectsUnknownMethod(t *testing.T) {
	h, _, close := newTestHandler(t)
	defer close()

	req := httptest.NewRequest(http.MethodDelete, "/api/v1/consent", nil)
	rec := httptest.NewRecorder()
	h.handleConsent(rec, req)

	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("want 405, got %d", rec.Code)
	}
}

// --- Rate-limit tests (audit finding F) ---------------------------------

func TestHandler_PostConsent_IPRateLimited(t *testing.T) {
	// ipCap=1 lets exactly one POST through; the second must be 429
	// from the IP branch (which fires before JSON decode).
	h, _, _, _, close := newTestHandlerWithLimiters(t, 1, 100)
	defer close()

	newReq := func(anon string) *http.Request {
		body := strings.NewReader(`{"anonymous_id":"` + anon + `","policy_version":"v1","categories":{"functional":true,"analytics":false}}`)
		return httptest.NewRequest(http.MethodPost, "/api/v1/consent", body)
	}

	rec1 := httptest.NewRecorder()
	h.handleConsent(rec1, newReq("anon-rl-1"))
	if rec1.Code != http.StatusCreated {
		t.Fatalf("first POST: want 201, got %d body=%s", rec1.Code, rec1.Body.String())
	}

	rec2 := httptest.NewRecorder()
	h.handleConsent(rec2, newReq("anon-rl-2"))
	if rec2.Code != http.StatusTooManyRequests {
		t.Fatalf("second POST: want 429, got %d", rec2.Code)
	}
	if got := rec2.Header().Get("Retry-After"); got != "60" {
		t.Fatalf("want Retry-After=60, got %q", got)
	}
}

func TestHandler_PostConsent_AnonymousIDRateLimited(t *testing.T) {
	// ipCap big, anonCap=1: same anonymous_id used twice must trip
	// the second-tier limiter even though the IP limiter has room.
	h, _, _, _, close := newTestHandlerWithLimiters(t, 100, 1)
	defer close()

	newReq := func() *http.Request {
		body := strings.NewReader(`{"anonymous_id":"anon-same","policy_version":"v1","categories":{"functional":false,"analytics":false}}`)
		return httptest.NewRequest(http.MethodPost, "/api/v1/consent", body)
	}

	rec1 := httptest.NewRecorder()
	h.handleConsent(rec1, newReq())
	if rec1.Code != http.StatusCreated {
		t.Fatalf("first POST: want 201, got %d", rec1.Code)
	}

	rec2 := httptest.NewRecorder()
	h.handleConsent(rec2, newReq())
	if rec2.Code != http.StatusTooManyRequests {
		t.Fatalf("second POST same anonymous_id: want 429, got %d", rec2.Code)
	}
}

func TestHandler_PostConsent_DifferentAnonymousIDsBypassAnonLimiter(t *testing.T) {
	// anonCap=1 per key: two requests with DIFFERENT anonymous_ids
	// must both succeed because the per-key counter is independent.
	h, _, _, _, close := newTestHandlerWithLimiters(t, 100, 1)
	defer close()

	newReq := func(anon string) *http.Request {
		body := strings.NewReader(`{"anonymous_id":"` + anon + `","policy_version":"v1","categories":{"functional":false,"analytics":false}}`)
		return httptest.NewRequest(http.MethodPost, "/api/v1/consent", body)
	}

	rec1 := httptest.NewRecorder()
	h.handleConsent(rec1, newReq("anon-A"))
	if rec1.Code != http.StatusCreated {
		t.Fatalf("first POST: want 201, got %d", rec1.Code)
	}

	rec2 := httptest.NewRecorder()
	h.handleConsent(rec2, newReq("anon-B"))
	if rec2.Code != http.StatusCreated {
		t.Fatalf("second POST (different anonymous_id): want 201, got %d body=%s", rec2.Code, rec2.Body.String())
	}
}
