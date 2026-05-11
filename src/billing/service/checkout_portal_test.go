package service

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/rs/zerolog"
)

func newTestCheckoutService(t *testing.T, paddleBase, lsBase string) *CheckoutService {
	t.Helper()
	svc, err := NewCheckoutService(CheckoutConfig{
		PaddleAPIBaseURL:      paddleBase,
		PaddleAPIKey:          "test-paddle-key",
		PaddlePriceProBYOK:    "pri_test_byok",
		PaddlePriceProManaged: "pri_test_managed",
		LSAPIBaseURL:          lsBase,
		LSAPIKey:              "test-ls-key",
		LSStoreID:             "1",
		LSVariantProBYOK:      "1",
		LSVariantProManaged:   "2",
		SuccessURL:            "https://app.test/success",
		CancelURL:             "https://app.test/cancel",
		HTTPTimeout:           2 * time.Second,
	}, zerolog.Nop())
	if err != nil {
		t.Fatalf("NewCheckoutService: %v", err)
	}
	return svc
}

func TestPortal_PaddleHappyPath(t *testing.T) {
	paddle := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("want POST, got %s", r.Method)
		}
		if !strings.HasSuffix(r.URL.Path, "/customers/cus_test/portal-sessions") {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		if r.Header.Get("Authorization") != "Bearer test-paddle-key" {
			t.Errorf("missing bearer")
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":{"id":"prt_1","urls":{"general":"https://paddle.test/portal/abc"}}}`))
	}))
	t.Cleanup(paddle.Close)

	svc := newTestCheckoutService(t, paddle.URL, "https://lsapi.test")
	resp, err := svc.CreatePortalSession(context.Background(), PortalRequest{
		Provider:           "paddle",
		ProviderCustomerID: "cus_test",
		UserID:             "u1",
	})
	if err != nil {
		t.Fatalf("CreatePortalSession: %v", err)
	}
	if resp.PortalURL != "https://paddle.test/portal/abc" {
		t.Fatalf("unexpected portal URL: %s", resp.PortalURL)
	}
}

func TestPortal_LemonSqueezyHappyPath(t *testing.T) {
	ls := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			t.Errorf("want GET, got %s", r.Method)
		}
		if !strings.HasSuffix(r.URL.Path, "/v1/customers/123") {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/vnd.api+json")
		_, _ = w.Write([]byte(`{"data":{"id":"123","attributes":{"urls":{"customer_portal":"https://ls.test/portal/xyz"}}}}`))
	}))
	t.Cleanup(ls.Close)

	svc := newTestCheckoutService(t, "https://paddle.test", ls.URL)
	resp, err := svc.CreatePortalSession(context.Background(), PortalRequest{
		Provider:           "lemonsqueezy",
		ProviderCustomerID: "123",
		UserID:             "u1",
	})
	if err != nil {
		t.Fatalf("CreatePortalSession: %v", err)
	}
	if resp.PortalURL != "https://ls.test/portal/xyz" {
		t.Fatalf("unexpected portal URL: %s", resp.PortalURL)
	}
}

func TestPortal_LemonSqueezyEmptyURLNotSupported(t *testing.T) {
	ls := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/vnd.api+json")
		_, _ = w.Write([]byte(`{"data":{"id":"123","attributes":{"urls":{}}}}`))
	}))
	t.Cleanup(ls.Close)

	svc := newTestCheckoutService(t, "https://paddle.test", ls.URL)
	_, err := svc.CreatePortalSession(context.Background(), PortalRequest{
		Provider:           "lemonsqueezy",
		ProviderCustomerID: "123",
		UserID:             "u1",
	})
	if err == nil {
		t.Fatalf("expected ErrPortalNotSupported, got nil")
	}
	if !strings.Contains(err.Error(), "portal not supported") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestPortal_PaddleFiveHundredTripsBreaker(t *testing.T) {
	var hits atomic.Int32
	paddle := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		hits.Add(1)
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"error":"upstream broken"}`))
	}))
	t.Cleanup(paddle.Close)

	svc := newTestCheckoutService(t, paddle.URL, "https://lsapi.test")

	// Force a low breaker threshold so 5 calls trip it (default is 5).
	for i := 0; i < 5; i++ {
		_, err := svc.CreatePortalSession(context.Background(), PortalRequest{
			Provider:           "paddle",
			ProviderCustomerID: "cus_test",
			UserID:             "u1",
		})
		if err == nil {
			t.Fatalf("call #%d: expected error from 500, got nil", i)
		}
	}

	hitsBeforeBreaker := hits.Load()

	// Next call should fast-fail via the breaker WITHOUT touching the
	// server (or at most touching it once for an in-flight retry).
	_, err := svc.CreatePortalSession(context.Background(), PortalRequest{
		Provider:           "paddle",
		ProviderCustomerID: "cus_test",
		UserID:             "u1",
	})
	if err == nil {
		t.Fatalf("want fast-fail with breaker open")
	}
	hitsAfterBreaker := hits.Load()
	if hitsAfterBreaker > hitsBeforeBreaker {
		t.Fatalf("breaker did not short-circuit: server hits before=%d after=%d", hitsBeforeBreaker, hitsAfterBreaker)
	}
}

func TestPortal_PaddleUnauthorizedNoBreakerTrip(t *testing.T) {
	var hits atomic.Int32
	paddle := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		hits.Add(1)
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = w.Write([]byte(`{"error":"bad key"}`))
	}))
	t.Cleanup(paddle.Close)

	svc := newTestCheckoutService(t, paddle.URL, "https://lsapi.test")

	// 4xx must NOT trip the breaker; 10 calls hit the server 10 times.
	for i := 0; i < 10; i++ {
		_, _ = svc.CreatePortalSession(context.Background(), PortalRequest{
			Provider:           "paddle",
			ProviderCustomerID: "cus_test",
			UserID:             "u1",
		})
	}
	if hits.Load() != 10 {
		t.Fatalf("want all 10 requests to hit the server (4xx does not trip breaker), got %d", hits.Load())
	}
}
