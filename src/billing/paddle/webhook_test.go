package paddle

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const testSecret = "test_secret_value_for_unit_tests_only"

// signedRequest builds an *http.Request whose Paddle-Signature header is the
// real HMAC-SHA256(secret, "<ts>:<body>") so the verifier accepts it.
func signedRequest(t *testing.T, body []byte, ts time.Time) *http.Request {
	t.Helper()
	mac := hmac.New(sha256.New, []byte(testSecret))
	mac.Write([]byte(fmt.Sprintf("%d", ts.Unix())))
	mac.Write([]byte{':'})
	mac.Write(body)
	digest := hex.EncodeToString(mac.Sum(nil))

	r := httptest.NewRequest(http.MethodPost, "/webhooks/paddle", strings.NewReader(string(body)))
	r.Header.Set(SignatureHeader, fmt.Sprintf("ts=%d;h1=%s", ts.Unix(), digest))
	return r
}

func fixedClock(t time.Time) func() time.Time { return func() time.Time { return t } }

func newTestVerifier(t *testing.T, now time.Time) *Verifier {
	t.Helper()
	v, err := NewVerifier(testSecret, 5*time.Minute, 1<<20)
	require.NoError(t, err)
	return v.WithClock(fixedClock(now))
}

func TestVerifier_ValidSignature(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	body := []byte(`{"event_type":"subscription.created"}`)

	v := newTestVerifier(t, now)
	assert.NoError(t, v.Verify(signedRequest(t, body, now), body))
}

func TestVerifier_MissingHeader(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v := newTestVerifier(t, now)
	r := httptest.NewRequest(http.MethodPost, "/webhooks/paddle", strings.NewReader("{}"))
	assert.ErrorIs(t, v.Verify(r, []byte("{}")), ErrMissingSignature)
}

func TestVerifier_MalformedHeader(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v := newTestVerifier(t, now)

	cases := []struct {
		name   string
		header string
	}{
		{"no h1", "ts=1700000000"},
		{"no ts", "h1=deadbeef"},
		{"non-numeric ts", "ts=notanumber;h1=deadbeef"},
		{"empty value", "ts=;h1="},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			r := httptest.NewRequest(http.MethodPost, "/webhooks/paddle", strings.NewReader("{}"))
			r.Header.Set(SignatureHeader, tc.header)
			assert.ErrorIs(t, v.Verify(r, []byte("{}")), ErrMalformedSignature)
		})
	}
}

func TestVerifier_NonHexH1(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v := newTestVerifier(t, now)
	r := httptest.NewRequest(http.MethodPost, "/webhooks/paddle", strings.NewReader("{}"))
	r.Header.Set(SignatureHeader, fmt.Sprintf("ts=%d;h1=ZZZZNOTHEX", now.Unix()))
	assert.ErrorIs(t, v.Verify(r, []byte("{}")), ErrMalformedSignature)
}

func TestVerifier_SignatureLengthMismatch(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v := newTestVerifier(t, now)
	body := []byte(`{"event_type":"subscription.created"}`)

	// Build a real signature, then truncate it. This is the case that was
	// non-constant-time before the fix; it must now resolve to a normal
	// signature mismatch.
	mac := hmac.New(sha256.New, []byte(testSecret))
	mac.Write([]byte(fmt.Sprintf("%d", now.Unix())))
	mac.Write([]byte{':'})
	mac.Write(body)
	digest := hex.EncodeToString(mac.Sum(nil))
	truncated := digest[:len(digest)-2]

	r := httptest.NewRequest(http.MethodPost, "/webhooks/paddle", strings.NewReader(string(body)))
	r.Header.Set(SignatureHeader, fmt.Sprintf("ts=%d;h1=%s", now.Unix(), truncated))

	err := v.Verify(r, body)
	require.Error(t, err)
	// truncated to odd length → hex.DecodeString fails → ErrMalformedSignature.
	// truncated to even length → ErrSignatureMismatch. Both are non-nil and
	// not panic; that's the contract we care about.
	assert.True(t,
		errors.Is(err, ErrSignatureMismatch) || errors.Is(err, ErrMalformedSignature),
		"expected signature-mismatch or malformed, got: %v", err)
}

func TestVerifier_BodyTamperedAfterSigning(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v := newTestVerifier(t, now)
	original := []byte(`{"event_type":"subscription.created"}`)
	tampered := []byte(`{"event_type":"subscription.canceled"}`)

	r := signedRequest(t, original, now)
	assert.ErrorIs(t, v.Verify(r, tampered), ErrSignatureMismatch)
}

func TestVerifier_ReplayTooOld(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v := newTestVerifier(t, now)
	old := now.Add(-10 * time.Minute) // outside the 5-minute window

	body := []byte(`{}`)
	err := v.Verify(signedRequest(t, body, old), body)
	assert.ErrorIs(t, err, ErrReplayWindow)
}

func TestVerifier_ReplayTooNew(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v := newTestVerifier(t, now)
	future := now.Add(10 * time.Minute) // also outside the window

	body := []byte(`{}`)
	err := v.Verify(signedRequest(t, body, future), body)
	assert.ErrorIs(t, err, ErrReplayWindow)
}

func TestVerifier_ReplayWithinWindow(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v := newTestVerifier(t, now)
	justOld := now.Add(-2 * time.Minute) // inside the 5-minute window

	body := []byte(`{}`)
	assert.NoError(t, v.Verify(signedRequest(t, body, justOld), body))
}

func TestVerifier_BodyTooLarge(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	v, err := NewVerifier(testSecret, 5*time.Minute, 64)
	require.NoError(t, err)
	v = v.WithClock(fixedClock(now))

	big := make([]byte, 65)
	assert.ErrorIs(t, v.Verify(signedRequest(t, big, now), big), ErrBodyTooLarge)
}