package lemonsqueezy

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const testSecret = "ls_test_secret_for_unit_tests_only"

func signedReq(t *testing.T, body []byte) *http.Request {
	t.Helper()
	mac := hmac.New(sha256.New, []byte(testSecret))
	mac.Write(body)
	digest := hex.EncodeToString(mac.Sum(nil))

	r := httptest.NewRequest(http.MethodPost, "/webhooks/lemonsqueezy", strings.NewReader(string(body)))
	r.Header.Set(SignatureHeader, digest)
	return r
}

func newTestVerifier(t *testing.T) *Verifier {
	t.Helper()
	v, err := NewVerifier(testSecret, 1<<20)
	require.NoError(t, err)
	return v
}

func TestLSVerifier_ValidSignature(t *testing.T) {
	v := newTestVerifier(t)
	body := []byte(`{"meta":{"event_name":"subscription_created"}}`)
	assert.NoError(t, v.Verify(signedReq(t, body), body))
}

func TestLSVerifier_MissingSignature(t *testing.T) {
	v := newTestVerifier(t)
	r := httptest.NewRequest(http.MethodPost, "/webhooks/lemonsqueezy", strings.NewReader("{}"))
	assert.ErrorIs(t, v.Verify(r, []byte("{}")), ErrMissingSignature)
}

func TestLSVerifier_NonHex(t *testing.T) {
	v := newTestVerifier(t)
	r := httptest.NewRequest(http.MethodPost, "/webhooks/lemonsqueezy", strings.NewReader("{}"))
	r.Header.Set(SignatureHeader, "ZZZZNOTHEX")
	assert.ErrorIs(t, v.Verify(r, []byte("{}")), ErrMalformedSignature)
}

func TestLSVerifier_LengthMismatch(t *testing.T) {
	v := newTestVerifier(t)
	body := []byte(`{"meta":{"event_name":"subscription_created"}}`)

	// Real digest, then truncated. The pre-fix code had non-constant-time
	// behaviour on this exact case.
	mac := hmac.New(sha256.New, []byte(testSecret))
	mac.Write(body)
	digest := hex.EncodeToString(mac.Sum(nil))
	truncated := digest[:len(digest)-2]

	r := httptest.NewRequest(http.MethodPost, "/webhooks/lemonsqueezy", strings.NewReader(string(body)))
	r.Header.Set(SignatureHeader, truncated)

	err := v.Verify(r, body)
	require.Error(t, err)
	assert.True(t,
		errors.Is(err, ErrSignatureMismatch) || errors.Is(err, ErrMalformedSignature),
		"got %v", err)
}

func TestLSVerifier_Tampered(t *testing.T) {
	v := newTestVerifier(t)
	original := []byte(`{"meta":{"event_name":"subscription_created"}}`)
	tampered := []byte(`{"meta":{"event_name":"subscription_cancelled"}}`)
	r := signedReq(t, original)
	assert.ErrorIs(t, v.Verify(r, tampered), ErrSignatureMismatch)
}

func TestLSVerifier_BodyTooLarge(t *testing.T) {
	v, err := NewVerifier(testSecret, 64)
	require.NoError(t, err)
	big := make([]byte, 65)
	assert.ErrorIs(t, v.Verify(signedReq(t, big), big), ErrBodyTooLarge)
}