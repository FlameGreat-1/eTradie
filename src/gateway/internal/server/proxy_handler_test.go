package server

// Tests for the browser-facing reverse proxy (Option B — single public
// entry point). These exercise the real ReverseProxyHandler against
// httptest upstreams and assert the four production-critical contracts:
//
//  1. Path-prefix rewrite per service (execution/management re-prefix,
//     engine identity).
//  2. Cookie jar + X-CSRF-Token are forwarded to the upstream unchanged
//     (so the upstream re-validates the same signed double-submit token).
//  3. Upstream status + body pass through verbatim (so the SPA still
//     sees tier_required 403 and llm_quota_exceeded 429 envelopes).
//  4. An unreachable upstream yields a 502 JSON error.
//
// The auth + CSRF middleware are represented here by pass-through stand-
// ins: this suite isolates the PROXY behaviour. The real auth/CSRF chain
// is the same middleware the gateway-native protected routes already use
// and is covered by src/auth's own tests; what is new and must be proven
// here is the rewrite + forwarding + status fidelity of the proxy.

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
)

// capturingUpstream records the path and selected headers of the last
// request it received, and replies with a configurable status + body.
type capturingUpstream struct {
	mu          sync.Mutex
	lastPath    string
	lastCookie  string
	lastCSRF    string
	status      int
	body        string
	contentType string
}

func (u *capturingUpstream) handler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		u.mu.Lock()
		u.lastPath = r.URL.Path
		u.lastCookie = r.Header.Get("Cookie")
		u.lastCSRF = r.Header.Get("X-CSRF-Token")
		status := u.status
		body := u.body
		ct := u.contentType
		u.mu.Unlock()

		if ct == "" {
			ct = "application/json"
		}
		w.Header().Set("Content-Type", ct)
		if status == 0 {
			status = http.StatusOK
		}
		w.WriteHeader(status)
		_, _ = io.WriteString(w, body)
	}
}

func (u *capturingUpstream) snapshot() (path, cookie, csrf string) {
	u.mu.Lock()
	defer u.mu.Unlock()
	return u.lastPath, u.lastCookie, u.lastCSRF
}

// passthrough is a no-op middleware standing in for auth / csrf so the
// test isolates the proxy. It mirrors the func(http.Handler) http.Handler
// signature RegisterRoutes expects.
func passthrough(next http.Handler) http.Handler { return next }

// newTestMux builds a ReverseProxyHandler pointed at the three given
// upstream base URLs and mounts it on a fresh mux with pass-through
// middleware.
func newTestMux(t *testing.T, engineURL, executionURL, managementURL string) *http.ServeMux {
	t.Helper()
	h, err := NewReverseProxyHandler(engineURL, executionURL, managementURL)
	if err != nil {
		t.Fatalf("NewReverseProxyHandler: %v", err)
	}
	mux := http.NewServeMux()
	h.RegisterRoutes(mux, passthrough, passthrough)
	return mux
}

func TestReverseProxy_PathRewrite(t *testing.T) {
	engine := &capturingUpstream{}
	execution := &capturingUpstream{}
	management := &capturingUpstream{}

	engineSrv := httptest.NewServer(engine.handler())
	defer engineSrv.Close()
	execSrv := httptest.NewServer(execution.handler())
	defer execSrv.Close()
	mgmtSrv := httptest.NewServer(management.handler())
	defer mgmtSrv.Close()

	mux := newTestMux(t, engineSrv.URL, execSrv.URL, mgmtSrv.URL)
	ts := httptest.NewServer(mux)
	defer ts.Close()

	cases := []struct {
		name         string
		browserPath  string
		wantUpstream *capturingUpstream
		wantPath     string
	}{
		// Execution: /api/execution/* -> /api/v1/*
		{"execution_state", "/api/execution/state", execution, "/api/v1/state"},
		{"execution_account", "/api/execution/account", execution, "/api/v1/account"},
		{"execution_settings", "/api/execution/settings", execution, "/api/v1/settings"},
		{"execution_orders_cancel", "/api/execution/orders/cancel", execution, "/api/v1/orders/cancel"},
		// Management: /api/management/* -> /api/v1/management/*
		{"management_trades", "/api/management/trades", management, "/api/v1/management/trades"},
		{"management_pnl", "/api/management/pnl-calendar", management, "/api/v1/management/pnl-calendar"},
		// Engine: identity rewrite.
		{"engine_broker", "/api/broker/connections", engine, "/api/broker/connections"},
		{"engine_analysis", "/api/analysis/latest", engine, "/api/analysis/latest"},
		{"engine_llm", "/api/llm/providers", engine, "/api/llm/providers"},
		{"engine_usage", "/api/usage/me", engine, "/api/usage/me"},
		{"engine_processor", "/api/processor/config", engine, "/api/processor/config"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, err := http.Get(ts.URL + tc.browserPath)
			if err != nil {
				t.Fatalf("GET %s: %v", tc.browserPath, err)
			}
			_ = resp.Body.Close()
			gotPath, _, _ := tc.wantUpstream.snapshot()
			if gotPath != tc.wantPath {
				t.Fatalf("browser %s: upstream got path %q, want %q", tc.browserPath, gotPath, tc.wantPath)
			}
		})
	}
}

func TestReverseProxy_RewriteWithQueryString(t *testing.T) {
	management := &capturingUpstream{}
	mgmtSrv := httptest.NewServer(management.handler())
	defer mgmtSrv.Close()

	mux := newTestMux(t, mgmtSrv.URL, mgmtSrv.URL, mgmtSrv.URL)
	ts := httptest.NewServer(mux)
	defer ts.Close()

	resp, err := http.Get(ts.URL + "/api/management/journal?limit=50&offset=0&symbol=EURUSD")
	if err != nil {
		t.Fatalf("GET: %v", err)
	}
	_ = resp.Body.Close()

	gotPath, _, _ := management.snapshot()
	if gotPath != "/api/v1/management/journal" {
		t.Fatalf("upstream path = %q, want /api/v1/management/journal", gotPath)
	}
}

func TestReverseProxy_ForwardsCookieAndCSRF(t *testing.T) {
	execution := &capturingUpstream{}
	execSrv := httptest.NewServer(execution.handler())
	defer execSrv.Close()

	mux := newTestMux(t, execSrv.URL, execSrv.URL, execSrv.URL)
	ts := httptest.NewServer(mux)
	defer ts.Close()

	req, err := http.NewRequest(http.MethodPost, ts.URL+"/api/execution/orders/cancel", strings.NewReader(`{"order_id":"O-1"}`))
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Cookie", "__Secure-access_token=abc; __Secure-csrf_token=rand.mac")
	req.Header.Set("X-CSRF-Token", "rand.mac")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("Do: %v", err)
	}
	_ = resp.Body.Close()

	_, gotCookie, gotCSRF := execution.snapshot()
	if !strings.Contains(gotCookie, "__Secure-access_token=abc") {
		t.Fatalf("upstream Cookie = %q, want it to contain the access-token cookie", gotCookie)
	}
	if !strings.Contains(gotCookie, "__Secure-csrf_token=rand.mac") {
		t.Fatalf("upstream Cookie = %q, want it to contain the csrf cookie", gotCookie)
	}
	if gotCSRF != "rand.mac" {
		t.Fatalf("upstream X-CSRF-Token = %q, want %q", gotCSRF, "rand.mac")
	}
}

func TestReverseProxy_StatusAndBodyPassthrough(t *testing.T) {
	cases := []struct {
		name   string
		status int
		body   string
	}{
		{
			name:   "tier_required_403",
			status: http.StatusForbidden,
			body:   `{"error":"upgrade","error_code":"tier_required","required_tier":"pro_byok","feature":"x"}`,
		},
		{
			name:   "llm_quota_429",
			status: http.StatusTooManyRequests,
			body:   `{"error_code":"llm_quota_exceeded","dimension":"daily_input"}`,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			engine := &capturingUpstream{status: tc.status, body: tc.body}
			engineSrv := httptest.NewServer(engine.handler())
			defer engineSrv.Close()

			mux := newTestMux(t, engineSrv.URL, engineSrv.URL, engineSrv.URL)
			ts := httptest.NewServer(mux)
			defer ts.Close()

			resp, err := http.Get(ts.URL + "/api/llm/providers")
			if err != nil {
				t.Fatalf("GET: %v", err)
			}
			defer resp.Body.Close()

			if resp.StatusCode != tc.status {
				t.Fatalf("status = %d, want %d", resp.StatusCode, tc.status)
			}
			got, _ := io.ReadAll(resp.Body)
			if strings.TrimSpace(string(got)) != tc.body {
				t.Fatalf("body = %q, want %q", string(got), tc.body)
			}
		})
	}
}

func TestReverseProxy_UnreachableUpstreamReturns502(t *testing.T) {
	// 127.0.0.1:1 is the well-known unused/privileged TCP port; a dial
	// there is refused deterministically, so the proxy must surface its
	// 502 JSON ErrorHandler. (Avoids the close-then-reuse race of
	// pointing at a just-closed httptest server.)
	deadURL := "http://127.0.0.1:1"

	mux := newTestMux(t, deadURL, deadURL, deadURL)
	ts := httptest.NewServer(mux)
	defer ts.Close()

	resp, err := http.Get(ts.URL + "/api/analysis/latest")
	if err != nil {
		t.Fatalf("GET: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("status = %d, want 502", resp.StatusCode)
	}
	var bodyObj map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&bodyObj); err != nil {
		t.Fatalf("decode 502 body: %v", err)
	}
	if bodyObj["error"] == "" {
		t.Fatalf("502 body should carry an error message, got %v", bodyObj)
	}
}

func TestNewReverseProxyHandler_RejectsBadUpstream(t *testing.T) {
	if _, err := NewReverseProxyHandler("://bad", "http://ok:8080", "http://ok:8083"); err == nil {
		t.Fatal("expected error for unparseable engine URL")
	}
	if _, err := NewReverseProxyHandler("http://ok:8000", "missing-scheme", "http://ok:8083"); err == nil {
		t.Fatal("expected error for scheme-less execution URL")
	}
	// Sanity: a fully valid trio constructs cleanly.
	if _, err := NewReverseProxyHandler("http://e:8000", "http://x:8080", "http://m:8083"); err != nil {
		t.Fatalf("valid trio should not error: %v", err)
	}
	_ = url.URL{} // keep net/url import meaningful if the build tags ever change
}
