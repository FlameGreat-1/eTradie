package consent

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/rs/zerolog"
)

// stubResolver is a deterministic IPResolver used by every handler
// test so the produced ip_hash is independent of the test runner's
// network configuration.
type stubResolver struct{ ip string }

func (s *stubResolver) Resolve(_ *http.Request) string { return s.ip }

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
