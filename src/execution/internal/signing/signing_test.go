package signing

import (
	"testing"
	"time"

	"github.com/flamegreat-1/etradie/src/pkg/execsigning"
)

const testKeyStr = "this-is-a-32-byte-minimum-hmac-key!!"

func testKey() []byte { return []byte(testKeyStr) }

func fieldsAt(ts time.Time, nonce, symbol string) Fields {
	return Fields{
		Timestamp:  ts,
		Nonce:      nonce,
		UserID:     "user-abc",
		Symbol:     symbol,
		Direction:  "LONG",
		AnalysisID: nonce,
	}
}

func TestNewVerifierRejectsEmptyKey(t *testing.T) {
	if _, err := NewVerifier(nil, time.Second); err == nil {
		t.Fatal("expected ErrEmptyKey for an empty key")
	}
}

func TestCheckValidFresh(t *testing.T) {
	v, err := NewVerifier(testKey(), 30*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	now := time.Date(2026, 6, 6, 12, 0, 0, 0, time.UTC)
	f := fieldsAt(now, "nonce-1", "EURUSD")
	sig := execsigning.Sign(testKey(), f)
	if got := v.Check(f, sig, now); got != OutcomeOK {
		t.Fatalf("want OutcomeOK, got %s", got)
	}
}

func TestCheckBadSignature(t *testing.T) {
	v, _ := NewVerifier(testKey(), 30*time.Second)
	now := time.Now().UTC()
	f := fieldsAt(now, "nonce-1", "EURUSD")
	bad := execsigning.Sign([]byte("a-different-32-byte-minimum-key!!aa"), f)
	if got := v.Check(f, bad, now); got != OutcomeBadSignature {
		t.Fatalf("want OutcomeBadSignature, got %s", got)
	}
}

func TestCheckStaleBothDirections(t *testing.T) {
	v, _ := NewVerifier(testKey(), 30*time.Second)
	signedAt := time.Date(2026, 6, 6, 12, 0, 0, 0, time.UTC)
	f := fieldsAt(signedAt, "nonce-1", "EURUSD")
	sig := execsigning.Sign(testKey(), f)

	// now far in the future relative to the signed timestamp.
	if got := v.Check(f, sig, signedAt.Add(31*time.Second)); got != OutcomeStale {
		t.Fatalf("future-skew: want OutcomeStale, got %s", got)
	}
	// now far in the past relative to the signed timestamp.
	if got := v.Check(f, sig, signedAt.Add(-31*time.Second)); got != OutcomeStale {
		t.Fatalf("past-skew: want OutcomeStale, got %s", got)
	}
}

// TestCheckRetrySafety is the production-critical case: the gateway
// retries with byte-identical signed metadata, which must be ALLOWED on
// every repeat (same nonce, same canonical hash).
func TestCheckRetrySafety(t *testing.T) {
	v, _ := NewVerifier(testKey(), 30*time.Second)
	now := time.Date(2026, 6, 6, 12, 0, 0, 0, time.UTC)
	f := fieldsAt(now, "nonce-retry", "EURUSD")
	sig := execsigning.Sign(testKey(), f)

	for i := 0; i < 4; i++ { // initial + 3 retries (DefaultRetryConfig)
		if got := v.Check(f, sig, now.Add(time.Duration(i)*time.Second)); got != OutcomeOK {
			t.Fatalf("retry %d: want OutcomeOK, got %s", i, got)
		}
	}
}

// TestCheckReplayDifferentPayload: same nonce reused with a DIFFERENT
// request inside the window is a true replay/tamper and must be rejected.
func TestCheckReplayDifferentPayload(t *testing.T) {
	v, _ := NewVerifier(testKey(), 30*time.Second)
	now := time.Date(2026, 6, 6, 12, 0, 0, 0, time.UTC)

	f1 := fieldsAt(now, "nonce-shared", "EURUSD")
	if got := v.Check(f1, execsigning.Sign(testKey(), f1), now); got != OutcomeOK {
		t.Fatalf("first request: want OutcomeOK, got %s", got)
	}

	// Same nonce, different symbol -> different canonical hash.
	f2 := fieldsAt(now, "nonce-shared", "GBPUSD")
	if got := v.Check(f2, execsigning.Sign(testKey(), f2), now); got != OutcomeReplay {
		t.Fatalf("replay with different payload: want OutcomeReplay, got %s", got)
	}
}

// TestNonceExpiryAllowsReuse: after the window, the nonce entry is
// pruned, so the same nonce is accepted again (it is no longer a
// meaningful replay).
func TestNonceExpiryAllowsReuse(t *testing.T) {
	v, _ := NewVerifier(testKey(), 5*time.Second)
	t0 := time.Date(2026, 6, 6, 12, 0, 0, 0, time.UTC)
	f := fieldsAt(t0, "nonce-x", "EURUSD")
	sig := execsigning.Sign(testKey(), f)
	if got := v.Check(f, sig, t0); got != OutcomeOK {
		t.Fatalf("first: want OutcomeOK, got %s", got)
	}
	// Re-sign at a later time beyond the window so it is not stale AND
	// the prior nonce entry has expired.
	t1 := t0.Add(6 * time.Second)
	f2 := fieldsAt(t1, "nonce-x", "EURUSD")
	sig2 := execsigning.Sign(testKey(), f2)
	if got := v.Check(f2, sig2, t1); got != OutcomeOK {
		t.Fatalf("post-expiry reuse: want OutcomeOK, got %s", got)
	}
}

func TestNilVerifierGuardInStore(t *testing.T) {
	// NonceStore with same hash repeated allows; different rejects.
	s := NewNonceStore(10 * time.Second)
	now := time.Now()
	if !s.SeenOrRecord("u", "n", "hashA", now) {
		t.Fatal("first record should be allowed")
	}
	if !s.SeenOrRecord("u", "n", "hashA", now) {
		t.Fatal("same-hash repeat should be allowed (retry)")
	}
	if s.SeenOrRecord("u", "n", "hashB", now) {
		t.Fatal("different-hash repeat should be rejected (replay)")
	}
}
