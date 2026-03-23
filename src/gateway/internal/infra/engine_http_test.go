package infra_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
)

func TestEngineHTTPClient_PostJSON_Success(t *testing.T) {
	// Setup a mock server that expects an idempotency key and returns 200 OK.
	var idempotencyKey string
	var callCount int32

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&callCount, 1)

		idempotencyKey = r.Header.Get("X-Idempotency-Key")
		if idempotencyKey == "" {
			t.Errorf("expected X-Idempotency-Key header to be set")
		}

		w.WriteHeader(http.StatusOK)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{"status": "success", "trade_id": "123"})
	}))
	defer server.Close()

	client := infra.NewEngineHTTPClient(server.URL, 5)
	defer client.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	payload := map[string]interface{}{"symbol": "EURUSD"}
	resp, err := client.PostJSON(ctx, "/internal/broker/place_order", payload)

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if resp["status"] != "success" {
		t.Errorf("expected status 'success', got %v", resp["status"])
	}
	if atomic.LoadInt32(&callCount) != 1 {
		t.Errorf("expected exactly 1 call, got %d", atomic.LoadInt32(&callCount))
	}
}

func TestEngineHTTPClient_PostJSON_RetryOn503(t *testing.T) {
	var callCount int32
	var idempotencyKeys []string

	// Mock server returns 503 on first call, 200 on second call.
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count := atomic.AddInt32(&callCount, 1)
		idempotencyKeys = append(idempotencyKeys, r.Header.Get("X-Idempotency-Key"))

		if count == 1 {
			w.WriteHeader(http.StatusServiceUnavailable)
			w.Write([]byte(`{"error": "service down"}`))
			return
		}

		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{"status": "recovered"})
	}))
	defer server.Close()

	client := infra.NewEngineHTTPClient(server.URL, 5)
	defer client.Close()

	ctx := context.Background()
	payload := map[string]interface{}{"symbol": "GBPUSD"}

	resp, err := client.PostJSON(ctx, "/test", payload)

	if err != nil {
		t.Fatalf("expected retry to succeed, got error: %v", err)
	}
	if resp["status"] != "recovered" {
		t.Errorf("expected status 'recovered', got %v", resp["status"])
	}
	if atomic.LoadInt32(&callCount) != 2 {
		t.Errorf("expected exactly 2 calls, got %d", atomic.LoadInt32(&callCount))
	}
	if len(idempotencyKeys) == 2 && idempotencyKeys[0] != idempotencyKeys[1] {
		t.Errorf("expected the same idempotency key across retries, got %v and %v", idempotencyKeys[0], idempotencyKeys[1])
	}
}

func TestEngineHTTPClient_PostJSON_NoRetryOn400(t *testing.T) {
	var callCount int32

	// Mock server always returns 400 Bad Request
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&callCount, 1)
		w.WriteHeader(http.StatusBadRequest)
		w.Write([]byte(`{"error": "invalid payload"}`))
	}))
	defer server.Close()

	client := infra.NewEngineHTTPClient(server.URL, 5)
	defer client.Close()

	ctx := context.Background()
	payload := map[string]interface{}{"symbol": "INVALID"}

	_, err := client.PostJSON(ctx, "/test", payload)

	if err == nil {
		t.Fatalf("expected error on 400 response, got nil")
	}
	if !strings.Contains(err.Error(), "400") {
		t.Errorf("expected error to contain status 400, got %v", err)
	}
	if atomic.LoadInt32(&callCount) != 1 {
		t.Errorf("expected exactly 1 call (no retries for 4xx), got %d", atomic.LoadInt32(&callCount))
	}
}
