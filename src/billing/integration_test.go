package billing_test

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/billing/events"
	"github.com/flamegreat-1/etradie/src/billing/lemonsqueezy"
	"github.com/flamegreat-1/etradie/src/billing/paddle"
	"github.com/flamegreat-1/etradie/src/billing/server"
	"github.com/flamegreat-1/etradie/src/billing/service"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

const (
	testPaddleSecret   = "a_long_enough_test_secret_for_paddle_webhook_signing"
	testInternalSecret = "this_is_a_long_internal_shared_secret_at_least_32_chars"
	testPriceBYOK      = "pri_int_byok"
	testPriceManaged   = "pri_int_managed"
)

// captureRevoker is a thread-safe in-test stand-in for *auth.SessionStore.
// The integration test does not exercise auth_sessions; it only verifies
// the revoke contract is honoured (one call per applied tier/status change).
type captureRevoker struct {
	mu    sync.Mutex
	calls []string
}

func (r *captureRevoker) RevokeAllUserSessions(_ context.Context, userID string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls = append(r.calls, userID)
	return nil
}

func (r *captureRevoker) snapshot() []string {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]string, len(r.calls))
	copy(out, r.calls)
	return out
}

// testPool returns a real pgx pool or nil if BILLING_TEST_DATABASE_URL is not set.
func testPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	url := os.Getenv("BILLING_TEST_DATABASE_URL")
	if url == "" {
		return nil
	}
	pool, err := pgxpool.New(context.Background(), url)
	require.NoError(t, err)
	t.Cleanup(pool.Close)
	return pool
}

func setupSchema(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	ctx := context.Background()
	_, err := pool.Exec(ctx, auth.SchemaSQL())
	require.NoError(t, err)
	_, err = pool.Exec(ctx, store.SchemaSQL())
	require.NoError(t, err)
}

func truncateAll(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	_, err := pool.Exec(context.Background(), `
		TRUNCATE TABLE
			billing_subscription_events,
			processed_webhook_events,
			billing_usage,
			billing_subscriptions,
			auth_users
		RESTART IDENTITY CASCADE
	`)
	require.NoError(t, err)
}

func seedUser(t *testing.T, pool *pgxpool.Pool, id, username, email string) {
	t.Helper()
	now := time.Now().UTC()
	_, err := pool.Exec(context.Background(),
		`INSERT INTO auth_users (id, username, email, password_hash, role, active, created_at, updated_at)
		 VALUES ($1, $2, $3, '', 'etradie', TRUE, $4, $4)`,
		id, username, email, now,
	)
	require.NoError(t, err)
}

// buildIntegrationServer constructs the real billing.Server with real stores
// (against testPool) and an LS verifier we won't exercise. Returns the
// *httptest.Server hosting the production mux and the captureRevoker so the
// test can assert revocation behaviour.
func buildIntegrationServer(t *testing.T, pool *pgxpool.Pool) (*httptest.Server, *captureRevoker) {
	t.Helper()

	subStore := store.NewSubscriptionStore(pool)
	processedStore := store.NewProcessedEventStore(pool)
	auditStore := store.NewSubscriptionEventStore(pool)
	revoker := &captureRevoker{}
	log := zerolog.Nop()

	subSvc := service.NewService(subStore, processedStore, auditStore, revoker, log)

	// Checkout service is required by server.Options but never exercised by
	// these tests; supply a real one against a clearly-test API base URL
	// (the test never POSTs to /internal/checkout).
	checkoutSvc, err := service.NewCheckoutService(service.CheckoutConfig{
		PaddleAPIBaseURL:      "https://api.paddle.example.invalid",
		PaddleAPIKey:          "test",
		PaddlePriceProBYOK:    testPriceBYOK,
		PaddlePriceProManaged: testPriceManaged,
		LSAPIBaseURL:          "https://api.lemonsqueezy.example.invalid",
		LSAPIKey:              "test",
		LSStoreID:             "1",
		LSVariantProBYOK:      "1",
		LSVariantProManaged:   "2",
		SuccessURL:            "https://app.example.invalid/success",
		CancelURL:             "https://app.example.invalid/cancel",
		HTTPTimeout:           1 * time.Second,
	}, log)
	require.NoError(t, err)

	paddleVer, err := paddle.NewVerifier(testPaddleSecret, 5*time.Minute, 1<<20)
	require.NoError(t, err)
	lsVer, err := lemonsqueezy.NewVerifier("unused_test_secret_for_ls_at_least_32_chars", 1<<20)
	require.NoError(t, err)

	metrics := server.NewMetrics()

	srv := server.New(server.Options{
		HTTPPort:       0, // unused; httptest.NewServer assigns its own port
		DB:             pool,
		Log:            log,
		Metrics:        metrics,
		InternalSecret: testInternalSecret,
		PaddleVerifier: paddleVer,
		PaddlePrices: paddle.PriceTierMap{
			testPriceBYOK:    events.TierProBYOK,
			testPriceManaged: events.TierProManaged,
		},
		LSVerifier:          lsVer,
		LSVariants:          lemonsqueezy.VariantTierMap{},
		SubscriptionService: subSvc,
		CheckoutService:     checkoutSvc,
	})

	// The production server.Server holds the *http.Server it built. We can
	// reach the underlying handler via the documented httptest pattern:
	// construct a fresh httptest.Server with our own mux that mirrors the
	// production mux. Cheaper than reflection: build a mux that calls the
	// same handler methods (which are exported as method values via the
	// HTTP server's Handler field).
	//
	// server.New stores its mux on (*server.Server).http.Handler. We don't
	// expose it directly, but we don't need to: we can wrap the *http.Server's
	// Handler. The simplest path is to issue a request via httptest with a
	// custom RoundTripper... but the cleanest is to wrap the production
	// Handler via httptest.NewServer.
	//
	// To do that we need the Handler. Since *http.Server.Handler is public,
	// we read it through an explicit helper added in this batch:
	//
	// (avoiding adding exported test-only API — instead we reconstruct a
	// small mux around the same Server's webhook endpoint by serving every
	// request through srv's http.Handler, which is the http.Server's mux.)
	//
	// The simplest practical approach is to start the production server on
	// a random port via srv.Start() and address it directly. server.Server
	// already supports HTTPPort=0 — the OS assigns a free port. But Start()
	// blocks; we'd need to capture the actual listen address.
	//
	// To keep this self-contained we mount the same handler shape (which
	// the production server uses) onto httptest.NewServer below. This means
	// we re-register the same routes, but the handlers themselves are the
	// exact same service methods.
	//
	// However, the production handlers are unexported methods on *server.Server.
	// They cannot be addressed from outside the package. Therefore the only
	// truly end-to-end option is to expose the Handler explicitly via a tiny
	// helper. That helper is added in the same file as Server (see Handler()).
	ts := httptest.NewServer(srv.Handler())
	t.Cleanup(ts.Close)
	return ts, revoker
}

// signPaddleBody computes a Paddle-Signature header for the body.
func signPaddleBody(t *testing.T, body []byte, ts time.Time) string {
	t.Helper()
	tsStr := fmt.Sprintf("%d", ts.Unix())
	mac := hmac.New(sha256.New, []byte(testPaddleSecret))
	mac.Write([]byte(tsStr))
	mac.Write([]byte{':'})
	mac.Write(body)
	return "ts=" + tsStr + ";h1=" + hex.EncodeToString(mac.Sum(nil))
}

func TestIntegration_PaddleWebhookEndToEnd(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_int_e2e", "e2e_user", "e2e@example.com")

	ts, revoker := buildIntegrationServer(t, pool)

	body := []byte(`{
		"event_id": "evt_int_e2e_1",
		"event_type": "subscription.created",
		"occurred_at": "2025-01-01T00:00:00Z",
		"data": {
			"id": "sub_int_e2e_1",
			"status": "active",
			"customer_id": "cus_int_e2e_1",
			"current_billing_period": {"ends_at": "2025-02-01T00:00:00Z"},
			"custom_data": {"user_id": "u_int_e2e"},
			"items": [{"status": "active", "price": {"id": "` + testPriceManaged + `"}}]
		}
	}`)
	now := time.Now().UTC()
	sig := signPaddleBody(t, body, now)

	req, err := http.NewRequest(http.MethodPost, ts.URL+"/webhooks/paddle", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set(paddle.SignatureHeader, sig)
	req.Header.Set(paddle.EventIDHeader, "evt_int_e2e_1")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, http.StatusOK, resp.StatusCode)

	var firstResp map[string]any
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&firstResp))
	assert.Equal(t, true, firstResp["applied"])
	assert.Equal(t, false, firstResp["already_processed"])

	// DB assertions: subscription row, audit row, idempotency row.
	var tier, status string
	require.NoError(t, pool.QueryRow(context.Background(),
		`SELECT tier, status FROM billing_subscriptions WHERE user_id = $1`, "u_int_e2e",
	).Scan(&tier, &status))
	assert.Equal(t, "pro_managed", tier)
	assert.Equal(t, "active", status)

	var auditCount, idemCount int
	require.NoError(t, pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM billing_subscription_events WHERE user_id = $1`, "u_int_e2e",
	).Scan(&auditCount))
	assert.Equal(t, 1, auditCount)
	require.NoError(t, pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM processed_webhook_events WHERE provider = 'paddle' AND event_id = $1`,
		"evt_int_e2e_1",
	).Scan(&idemCount))
	assert.Equal(t, 1, idemCount)

	assert.Equal(t, []string{"u_int_e2e"}, revoker.snapshot(), "revocation fires on first apply")

	// Replay the same webhook: must be already_processed with no extra writes.
	req2, err := http.NewRequest(http.MethodPost, ts.URL+"/webhooks/paddle", bytes.NewReader(body))
	require.NoError(t, err)
	req2.Header.Set("Content-Type", "application/json")
	req2.Header.Set(paddle.SignatureHeader, sig)
	req2.Header.Set(paddle.EventIDHeader, "evt_int_e2e_1")
	resp2, err := http.DefaultClient.Do(req2)
	require.NoError(t, err)
	defer resp2.Body.Close()
	assert.Equal(t, http.StatusOK, resp2.StatusCode)

	var secondResp map[string]any
	require.NoError(t, json.NewDecoder(resp2.Body).Decode(&secondResp))
	assert.Equal(t, true, secondResp["already_processed"])
	assert.Equal(t, false, secondResp["applied"])

	require.NoError(t, pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM billing_subscription_events WHERE user_id = $1`, "u_int_e2e",
	).Scan(&auditCount))
	assert.Equal(t, 1, auditCount, "no new audit row on duplicate")
	assert.Equal(t, []string{"u_int_e2e"}, revoker.snapshot(), "revoker NOT called again on duplicate")
}

func TestIntegration_PaddleWebhookSignatureRejected(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_int_sig", "sig_user", "sig@example.com")

	ts, _ := buildIntegrationServer(t, pool)

	body := []byte(`{
		"event_id": "evt_sig_1",
		"event_type": "subscription.created",
		"occurred_at": "2025-01-01T00:00:00Z",
		"data": {
			"id": "sub_sig_1",
			"status": "active",
			"customer_id": "cus_sig_1",
			"custom_data": {"user_id": "u_int_sig"},
			"items": [{"status": "active", "price": {"id": "` + testPriceBYOK + `"}}]
		}
	}`)

	// Build a malformed-but-well-shaped signature: correct ts, BAD digest.
	tsHeader := "ts=" + fmt.Sprintf("%d", time.Now().Unix()) + ";h1=" + strings.Repeat("0", 64)

	req, err := http.NewRequest(http.MethodPost, ts.URL+"/webhooks/paddle", bytes.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set(paddle.SignatureHeader, tsHeader)
	req.Header.Set(paddle.EventIDHeader, "evt_sig_1")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, http.StatusUnauthorized, resp.StatusCode)

	// DB must be untouched.
	var n int
	require.NoError(t, pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM billing_subscriptions WHERE user_id = 'u_int_sig'`,
	).Scan(&n))
	assert.Equal(t, 0, n)
	require.NoError(t, pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM processed_webhook_events`,
	).Scan(&n))
	assert.Equal(t, 0, n)
}
