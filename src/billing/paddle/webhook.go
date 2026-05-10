// Package paddle verifies and parses Paddle Billing v1 webhook deliveries.
//
// The verifier enforces:
//   - HMAC-SHA256 over "<ts>:<raw_body>" with the dashboard-provided secret
//   - constant-time digest comparison after hex-decode of both sides
//   - replay-window check on the signed ts (default 300s, configurable)
//   - body-size guard before any HMAC work
//
// Replay defense at the network layer is paired with idempotency at the DB
// layer (processed_webhook_events) so a captured webhook cannot be replayed
// during the window OR processed twice if it slips through.
package paddle

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// Provider name used as the (provider, event_id) partition in the
// processed_webhook_events table and across logs/metrics.
const Provider = "paddle"

// SignatureHeader is the request header Paddle uses to deliver the signature.
const SignatureHeader = "Paddle-Signature"

// Sentinel errors. Callers map these to a 400/401 response so the provider
// stops retrying on permanent failures, while infrastructure failures are
// surfaced as 5xx so the provider DOES retry.
var (
	ErrMissingSignature   = errors.New("paddle: missing Paddle-Signature header")
	ErrMalformedSignature = errors.New("paddle: malformed Paddle-Signature header")
	ErrSignatureMismatch  = errors.New("paddle: signature mismatch")
	ErrReplayWindow       = errors.New("paddle: signature timestamp outside replay window")
	ErrBodyTooLarge       = errors.New("paddle: webhook body exceeds configured max size")
)

// Verifier authenticates Paddle webhook deliveries.
//
// Construct via NewVerifier. The struct is safe for concurrent use; all fields
// are read-only after construction.
type Verifier struct {
	secret       []byte
	replayWindow time.Duration
	maxBodyBytes int64
	now          func() time.Time
}

// NewVerifier returns a Verifier ready for production use.
//
//	secret       — the dashboard-issued webhook signing secret (PADDLE_WEBHOOK_SECRET).
//	replayWindow — reject webhooks whose signed ts is older or further-future than this.
//	maxBodyBytes — hard cap on the body the verifier will inspect.
func NewVerifier(secret string, replayWindow time.Duration, maxBodyBytes int64) (*Verifier, error) {
	if secret == "" {
		return nil, errors.New("paddle: webhook secret is required")
	}
	if replayWindow <= 0 {
		return nil, errors.New("paddle: replay window must be positive")
	}
	if maxBodyBytes <= 0 {
		return nil, errors.New("paddle: max body bytes must be positive")
	}
	return &Verifier{
		secret:       []byte(secret),
		replayWindow: replayWindow,
		maxBodyBytes: maxBodyBytes,
		now:          time.Now,
	}, nil
}

// WithClock overrides the clock used for replay-window checks. Test-only.
func (v *Verifier) WithClock(now func() time.Time) *Verifier {
	copy := *v
	copy.now = now
	return &copy
}

// MaxBodyBytes is exposed so the HTTP layer can apply http.MaxBytesReader
// with a matching limit before the body is even read.
func (v *Verifier) MaxBodyBytes() int64 { return v.maxBodyBytes }

// Verify checks the request signature against the supplied raw body.
//
// The body MUST be the exact bytes that arrived on the wire — no JSON
// re-marshal, no whitespace stripping. Callers are expected to read the body
// once into a []byte (under MaxBodyBytes) and pass both the *http.Request
// (for the header) and the captured bytes here.
func (v *Verifier) Verify(r *http.Request, body []byte) error {
	if int64(len(body)) > v.maxBodyBytes {
		return ErrBodyTooLarge
	}

	header := r.Header.Get(SignatureHeader)
	if header == "" {
		return ErrMissingSignature
	}

	ts, h1, err := parseSignatureHeader(header)
	if err != nil {
		return err
	}

	// Replay window. Reject if the signed timestamp is too old OR too far in
	// the future (clock skew on either side, or a malicious replay).
	delta := v.now().Sub(ts)
	if delta < 0 {
		delta = -delta
	}
	if delta > v.replayWindow {
		return fmt.Errorf("%w (delta=%s)", ErrReplayWindow, delta)
	}

	// Compute expected digest = HMAC-SHA256(secret, "<ts>:<body>").
	mac := hmac.New(sha256.New, v.secret)
	// Paddle signs the raw timestamp (seconds since epoch) as a string,
	// followed by ':' and the raw body. Reuse the original ts string to
	// avoid any reformatting drift.
	mac.Write([]byte(strconv.FormatInt(ts.Unix(), 10)))
	mac.Write([]byte{':'})
	mac.Write(body)
	expected := mac.Sum(nil)

	received, err := hex.DecodeString(h1)
	if err != nil {
		return ErrMalformedSignature
	}
	if !hmac.Equal(received, expected) {
		return ErrSignatureMismatch
	}
	return nil
}

// parseSignatureHeader splits the "ts=...;h1=..." header into its components
// and returns (timestamp, hex-digest). Unknown fields are ignored to remain
// compatible with future Paddle additions.
func parseSignatureHeader(header string) (time.Time, string, error) {
	var (
		tsRaw string
		h1    string
	)
	for _, part := range strings.Split(header, ";") {
		kv := strings.SplitN(strings.TrimSpace(part), "=", 2)
		if len(kv) != 2 {
			continue
		}
		switch kv[0] {
		case "ts":
			tsRaw = kv[1]
		case "h1":
			h1 = kv[1]
		}
	}
	if tsRaw == "" || h1 == "" {
		return time.Time{}, "", ErrMalformedSignature
	}
	tsInt, err := strconv.ParseInt(tsRaw, 10, 64)
	if err != nil {
		return time.Time{}, "", ErrMalformedSignature
	}
	return time.Unix(tsInt, 0), h1, nil
}
