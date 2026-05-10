// Package lemonsqueezy verifies and parses Lemon Squeezy webhook deliveries.
//
// Lemon Squeezy signs the raw body with HMAC-SHA256 and delivers the hex
// digest in the X-Signature header. Unlike Paddle, the signed payload does
// not include a timestamp, so timestamp-based replay defense is impossible
// at the verifier layer. We compensate by:
//
//   - rejecting bodies above the configured max size before any work
//   - hex-decoding both digests so hmac.Equal compares equal-length slices
//   - delegating replay defense to the (provider, event_id) idempotency
//     table, where event_id is the X-Event-Id header. A replay never
//     re-applies state because the second insert is a no-op.
package lemonsqueezy

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"net/http"
)

// Provider name used as the (provider, event_id) partition in the
// processed_webhook_events table and across logs/metrics.
const Provider = "lemonsqueezy"

// Headers Lemon Squeezy attaches to every webhook delivery.
const (
	SignatureHeader = "X-Signature"
	EventNameHeader = "X-Event-Name"
)

// Sentinel errors. Same mapping policy as the Paddle verifier.
var (
	ErrMissingSignature   = errors.New("lemonsqueezy: missing X-Signature header")
	ErrMalformedSignature = errors.New("lemonsqueezy: malformed X-Signature header")
	ErrSignatureMismatch  = errors.New("lemonsqueezy: signature mismatch")
	ErrBodyTooLarge       = errors.New("lemonsqueezy: webhook body exceeds configured max size")
)

// Verifier authenticates Lemon Squeezy webhook deliveries.
type Verifier struct {
	secret       []byte
	maxBodyBytes int64
}

// NewVerifier returns a Verifier ready for production use.
func NewVerifier(secret string, maxBodyBytes int64) (*Verifier, error) {
	if secret == "" {
		return nil, errors.New("lemonsqueezy: webhook secret is required")
	}
	if maxBodyBytes <= 0 {
		return nil, errors.New("lemonsqueezy: max body bytes must be positive")
	}
	return &Verifier{
		secret:       []byte(secret),
		maxBodyBytes: maxBodyBytes,
	}, nil
}

// MaxBodyBytes is exposed so the HTTP layer can apply http.MaxBytesReader
// with a matching limit before the body is even read.
func (v *Verifier) MaxBodyBytes() int64 { return v.maxBodyBytes }

// Verify checks the request signature against the supplied raw body.
//
// The body MUST be the exact bytes that arrived on the wire — no JSON
// re-marshal, no whitespace stripping.
func (v *Verifier) Verify(r *http.Request, body []byte) error {
	if int64(len(body)) > v.maxBodyBytes {
		return ErrBodyTooLarge
	}

	header := r.Header.Get(SignatureHeader)
	if header == "" {
		return ErrMissingSignature
	}

	received, err := hex.DecodeString(header)
	if err != nil {
		return ErrMalformedSignature
	}

	mac := hmac.New(sha256.New, v.secret)
	mac.Write(body)
	expected := mac.Sum(nil)

	if !hmac.Equal(received, expected) {
		return ErrSignatureMismatch
	}
	return nil
}
