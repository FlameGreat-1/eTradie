package support

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
)

// fakeLimiter is a deterministic in-memory rate limiter for the
// handler tests. Mirrors the pattern used by consent's test suite.
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

// stubResolver returns a fixed IP regardless of the request, so the
// produced ip_address column is independent of the test runner.
type stubResolver struct{ ip string }

func (s *stubResolver) Resolve(_ *http.Request) string { return s.ip }

// stubUserLookup is a deterministic UserLookup used by the handler's
// authenticated-create-ticket path so the test does not need a real
// auth_users row.
type stubUserLookup struct {
	users map[string]*auth.User
}

func (s *stubUserLookup) GetUserByID(_ context.Context, id string) (*auth.User, error) {
	u, ok := s.users[id]
	if !ok {
		return nil, nil
	}
	return u, nil
}

func newHandlerForTest(t *testing.T, ipCap, emailCap int) (*Handler, *Store, *fakeLimiter, *fakeLimiter, func()) {
	t.Helper()
	store, _, dbClose := newTestStore(t)
	ipL := newFakeLimiter(ipCap)
	emL := newFakeLimiter(emailCap)
	cfg := &Config{
		InboxEmail:           "staff@example.com",
		CommunityFacebookURL: "https://facebook.example/exoper",
		CommunityDiscordURL:  "https://discord.example/exoper",
		PublicSiteURL:        "https://exoper.test",
	}
	lookup := &stubUserLookup{users: map[string]*auth.User{
		"u1": {ID: "u1", Username: "alice", Email: "alice@example.com"},
		"u2": {ID: "u2", Username: "bob", Email: "bob@example.com"},
	}}
	h := NewHandlerWithLimiters(
		store, nil, cfg, lookup, &stubResolver{ip: "127.0.0.1"},
		ipL, emL, zerolog.Nop(),
	)
	return h, store, ipL, emL, dbClose
}

// ---------------------------------------------------------------------------
// GET /api/support/community-links
// ---------------------------------------------------------------------------

func TestHandler_CommunityLinks_OnlyConfiguredArePublished(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	req := httptest.NewRequest(http.MethodGet, "/api/support/community-links", nil)
	rec := httptest.NewRecorder()
	h.handleCommunityLinks(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", rec.Code)
	}
	var resp communityResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(resp.Links) != 2 {
		t.Fatalf("want 2 links (fb+discord), got %d: %+v", len(resp.Links), resp.Links)
	}
}

func TestHandler_CommunityLinks_RejectsPOST(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	req := httptest.NewRequest(http.MethodPost, "/api/support/community-links", nil)
	rec := httptest.NewRecorder()
	h.handleCommunityLinks(rec, req)

	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("want 405, got %d", rec.Code)
	}
}

// ---------------------------------------------------------------------------
// POST /api/support/contact (public)
// ---------------------------------------------------------------------------

func TestHandler_PublicContact_HappyPath(t *testing.T) {
	h, store, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	body := strings.NewReader(`{
		"email": "contact@example.com",
		"name": "Jane",
		"subject": "Cannot place order",
		"message": "My broker connection keeps disconnecting today.",
		"category": "technical",
		"priority": "high"
	}`)
	req := httptest.NewRequest(http.MethodPost, "/api/support/contact", body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.handlePublicContact(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("want 201, got %d body=%s", rec.Code, rec.Body.String())
	}
	var resp publicContactResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp.Ticket == nil || resp.Ticket.PublicRef == "" {
		t.Fatalf("missing ticket / public_ref: %+v", resp.Ticket)
	}

	n, _ := store.CountOpenByEmail(context.Background(), "contact@example.com")
	if n != 1 {
		t.Fatalf("want 1 stored open ticket, got %d", n)
	}
}

func TestHandler_PublicContact_RejectsInvalidBody(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	cases := []struct {
		name string
		json string
	}{
		{"malformed-json", `not-json`},
		{"missing-email", `{"subject":"abc","message":"hello world"}`},
		{"bad-email", `{"email":"no-at","subject":"abc","message":"hello world"}`},
		{"short-subject", `{"email":"a@b.co","subject":"a","message":"hello world"}`},
		{"short-message", `{"email":"a@b.co","subject":"abc","message":"hi"}`},
		{"unknown-category", `{"email":"a@b.co","subject":"abc","message":"hello world","category":"weird"}`},
		{"unknown-priority", `{"email":"a@b.co","subject":"abc","message":"hello world","priority":"weird"}`},
		{"unknown-field", `{"email":"a@b.co","subject":"abc","message":"hello world","surprise":true}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/api/support/contact", strings.NewReader(tc.json))
			req.Header.Set("Content-Type", "application/json")
			rec := httptest.NewRecorder()
			h.handlePublicContact(rec, req)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("want 400 for %s, got %d body=%s", tc.name, rec.Code, rec.Body.String())
			}
		})
	}
}

func TestHandler_PublicContact_RateLimitsPerIP(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 0, 100) // 0 IP cap -> instant 429
	defer close()

	body := strings.NewReader(`{"email":"a@b.co","subject":"abc","message":"hello world"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/support/contact", body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.handlePublicContact(rec, req)

	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("want 429 from IP limiter, got %d", rec.Code)
	}
}

func TestHandler_PublicContact_RateLimitsPerEmail(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 0) // 0 email cap -> 429 AFTER validation
	defer close()

	body := strings.NewReader(`{"email":"a@b.co","subject":"abc","message":"hello world"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/support/contact", body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.handlePublicContact(rec, req)

	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("want 429 from email limiter, got %d", rec.Code)
	}
}

func TestHandler_PublicContact_RejectsSixthOpenTicketPerEmail(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	bodyTemplate := `{"email":"flooder@example.com","subject":"abc %d","message":"hello world flood"}`
	for i := 0; i < maxOpenTicketsPerEmail; i++ {
		req := httptest.NewRequest(http.MethodPost, "/api/support/contact",
			strings.NewReader(strings.Replace(bodyTemplate, "%d", string(rune('a'+i)), 1)))
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()
		h.handlePublicContact(rec, req)
		if rec.Code != http.StatusCreated {
			t.Fatalf("iter %d: want 201, got %d body=%s", i, rec.Code, rec.Body.String())
		}
	}

	// 6th attempt must be 429 with the per-email ceiling message.
	req := httptest.NewRequest(http.MethodPost, "/api/support/contact",
		strings.NewReader(strings.Replace(bodyTemplate, "%d", "z", 1)))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.handlePublicContact(rec, req)
	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("6th attempt: want 429, got %d", rec.Code)
	}
}

// ---------------------------------------------------------------------------
// Authenticated routes via the full RequireAuth middleware chain.
// Mints a real JWT against a real TokenService so the test exercises
// the exact code path production traffic does.
// ---------------------------------------------------------------------------

func mintAuthBearer(t *testing.T, uid, username string) (string, *auth.TokenService) {
	t.Helper()
	cfg := &auth.Config{
		JWTSecret:             "unit-test-secret-which-is-at-least-32-bytes-long",
		AccessTokenTTLSeconds: 60,
		Issuer:                "unit-test",
	}
	ts := auth.NewTokenService(cfg)
	pair, _, err := ts.IssueTokenPair(&auth.User{
		ID: uid, Username: username, Email: username + "@example.com",
		Role: auth.RoleEtradie, Tier: "free", Status: "active",
	})
	if err != nil {
		t.Fatalf("IssueTokenPair: %v", err)
	}
	return pair.AccessToken, ts
}

func authedRequest(t *testing.T, method, path, body, bearer string) *http.Request {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, strings.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
	}
	r.Header.Set("Authorization", "Bearer "+bearer)
	return r
}

func TestHandler_AuthedListTickets_ReturnsOnlyCallerTickets(t *testing.T) {
	h, store, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	u1 := "u1"
	u2 := "u2"
	_ = seedTicket(t, store, &u1, "alice@example.com")
	_ = seedTicket(t, store, &u2, "bob@example.com")

	bearer, ts := mintAuthBearer(t, u1, "alice")
	httpHandler := auth.RequireAuth(ts)(http.HandlerFunc(h.handleTicketsCollection))

	req := authedRequest(t, http.MethodGet, "/api/support/tickets", "", bearer)
	rec := httptest.NewRecorder()
	httpHandler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d body=%s", rec.Code, rec.Body.String())
	}
	var resp listTicketsResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(resp.Tickets) != 1 || resp.Tickets[0].Email != "alice@example.com" {
		t.Fatalf("want only alice's ticket, got %+v", resp.Tickets)
	}
}

func TestHandler_AuthedGetTicket_OwnershipReturns404(t *testing.T) {
	h, store, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	u1 := "u1"
	tk := seedTicket(t, store, &u1, "alice@example.com")

	bearer, ts := mintAuthBearer(t, "u2", "bob") // wrong owner
	httpHandler := auth.RequireAuth(ts)(http.HandlerFunc(h.handleTicketsItem))

	req := authedRequest(t, http.MethodGet, "/api/support/tickets/"+tk.ID, "", bearer)
	rec := httptest.NewRecorder()
	httpHandler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("want 404 for non-owner (must not be 403), got %d", rec.Code)
	}
}

func TestHandler_AuthedItem_RejectsMalformedID(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	bearer, ts := mintAuthBearer(t, "u1", "alice")
	httpHandler := auth.RequireAuth(ts)(http.HandlerFunc(h.handleTicketsItem))

	// Anything not 32 lowercase hex is rejected before touching the DB.
	for _, bogus := range []string{"xx", "deadbeef", strings.Repeat("z", 32), strings.Repeat("a", 31)} {
		req := authedRequest(t, http.MethodGet, "/api/support/tickets/"+bogus, "", bearer)
		rec := httptest.NewRecorder()
		httpHandler.ServeHTTP(rec, req)
		if rec.Code != http.StatusNotFound {
			t.Fatalf("want 404 for bogus id %q, got %d", bogus, rec.Code)
		}
	}
}

func TestHandler_AuthedReply_ClosedTicketReturns409(t *testing.T) {
	h, store, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	u1 := "u1"
	tk := seedTicket(t, store, &u1, "alice@example.com")
	if _, err := store.CloseTicket(context.Background(), tk.ID, u1); err != nil {
		t.Fatalf("close: %v", err)
	}

	bearer, ts := mintAuthBearer(t, u1, "alice")
	httpHandler := auth.RequireAuth(ts)(http.HandlerFunc(h.handleTicketsItem))

	req := authedRequest(t, http.MethodPost, "/api/support/tickets/"+tk.ID+"/messages",
		`{"message":"please reopen"}`, bearer)
	rec := httptest.NewRecorder()
	httpHandler.ServeHTTP(rec, req)

	if rec.Code != http.StatusConflict {
		t.Fatalf("want 409 for reply-on-closed, got %d", rec.Code)
	}
}

func TestHandler_AuthedClose_AlreadyClosedReturns409(t *testing.T) {
	h, store, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	u1 := "u1"
	tk := seedTicket(t, store, &u1, "alice@example.com")
	if _, err := store.CloseTicket(context.Background(), tk.ID, u1); err != nil {
		t.Fatalf("first close: %v", err)
	}

	bearer, ts := mintAuthBearer(t, u1, "alice")
	httpHandler := auth.RequireAuth(ts)(http.HandlerFunc(h.handleTicketsItem))

	req := authedRequest(t, http.MethodPost, "/api/support/tickets/"+tk.ID+"/close", "", bearer)
	rec := httptest.NewRecorder()
	httpHandler.ServeHTTP(rec, req)

	if rec.Code != http.StatusConflict {
		t.Fatalf("want 409 for already-closed, got %d", rec.Code)
	}
}

func TestHandler_AuthedCreateTicket_Persists(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	bearer, ts := mintAuthBearer(t, "u1", "alice")
	httpHandler := auth.RequireAuth(ts)(http.HandlerFunc(h.handleTicketsCollection))

	body := `{"subject":"upgrade query","message":"how do i upgrade my plan","category":"billing","priority":"normal"}`
	req := authedRequest(t, http.MethodPost, "/api/support/tickets", body, bearer)
	rec := httptest.NewRecorder()
	httpHandler.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("want 201, got %d body=%s", rec.Code, rec.Body.String())
	}
	var resp ticketResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp.Ticket == nil || resp.Ticket.Email != "alice@example.com" {
		t.Fatalf("bad ticket: %+v", resp.Ticket)
	}
	if resp.Ticket.Channel != ChannelWeb {
		t.Fatalf("want channel=web for authed-create, got %q", resp.Ticket.Channel)
	}
}

func TestHandler_AuthedRoutes_RejectMissingBearer(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	_, ts := mintAuthBearer(t, "u1", "alice")
	httpHandler := auth.RequireAuth(ts)(http.HandlerFunc(h.handleTicketsCollection))

	req := httptest.NewRequest(http.MethodGet, "/api/support/tickets", nil)
	rec := httptest.NewRecorder()
	httpHandler.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("want 401, got %d", rec.Code)
	}
}

func TestIsValidIDFormat(t *testing.T) {
	if !isValidIDFormat("0123456789abcdef0123456789abcdef") {
		t.Fatal("want valid for 32-char lowercase hex")
	}
	for _, bad := range []string{
		"",
		"0123456789abcdef0123456789abcde", // 31 chars
		"0123456789ABCDEF0123456789abcdef", // uppercase
		"0123456789abcdef0123456789abcdez", // non-hex
	} {
		if isValidIDFormat(bad) {
			t.Fatalf("want invalid for %q", bad)
		}
	}
}

// Sanity: the contact-form 64 KiB body cap is enforced. We send a
// 200 KiB payload and expect 400 (the decoder errors out reading past
// MaxBytesReader before unmarshalling).
func TestHandler_PublicContact_BodyCap(t *testing.T) {
	h, _, _, _, close := newHandlerForTest(t, 100, 100)
	defer close()

	large := bytes.NewBuffer(nil)
	large.WriteString(`{"email":"a@b.co","subject":"abc","message":"`)
	for i := 0; i < 200_000; i++ {
		large.WriteByte('x')
	}
	large.WriteString(`"}`)

	req := httptest.NewRequest(http.MethodPost, "/api/support/contact", large)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.handlePublicContact(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("want 400 for over-size body, got %d", rec.Code)
	}
}

// Compile-time check that the handler's internal types stay in sync
// with the package's exported wire types.
var _ = func() time.Time { return time.Time{} }
