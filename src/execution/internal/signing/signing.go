// Package signing implements HMAC request signing + anti-replay for the
// internal gateway -> execution ExecuteTrade gRPC call (CHECKLIST Tier 8
// "Order Integrity": signed internal execution requests + replay attack
// protection).
//
// Transport: the signature, timestamp, and nonce travel in gRPC
// metadata (the proto is not regenerated in this workflow). The
// canonical string is built identically on both sides so the same
// bytes are signed and verified.
//
// Key: the HMAC key is the shared ENGINE_INTERNAL_SHARED_SECRET that
// the gateway and execution already load from Vault (identical value,
// >=32 chars). No new secret is introduced.
//
// Retry-safety: the gateway adapter retries ExecuteTrade up to 3x. A
// retry resends the SAME metadata, so the NonceStore treats a repeat
// nonce carrying the SAME canonical hash within the freshness window as
// a legitimate retry (allowed) and rejects only a repeat carrying a
// DIFFERENT hash (true replay / tamper) or a stale timestamp.
package signing

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
)

// Version prefixes the canonical string so the scheme can evolve
// without ambiguity. Bump only with a coordinated gateway+execution
// release.
const Version = "v1"

// Metadata keys carried on the ExecuteTrade gRPC call. Lower-case per
// the gRPC metadata convention.
const (
	MetaSignature = "x-exec-signature"
	MetaTimestamp = "x-exec-timestamp"
	MetaNonce     = "x-exec-nonce"
)

// Fields are the request attributes bound by the signature. user_id is
// the authenticated principal (resolved from the JWT claims server-side
// on verify, supplied by the caller on sign) so the signature binds the
// request to who is making it, not just to its contents.
type Fields struct {
	Timestamp  time.Time // signer's clock, UTC
	Nonce      string    // the request idempotency key
	UserID     string
	Symbol     string
	Direction  string
	AnalysisID string
}

// Canonical builds the deterministic signing string. Field order is
// fixed and values are newline-joined; there is no map iteration so the
// output is byte-identical across processes and Go versions.
//
// Timestamp is encoded as RFC3339Nano in UTC so the signer and verifier
// agree to the nanosecond regardless of monotonic-clock stripping.
func (f Fields) Canonical() string {
	return strings.Join([]string{
		Version,
		f.Timestamp.UTC().Format(time.RFC3339Nano),
		f.Nonce,
		f.UserID,
		f.Symbol,
		f.Direction,
		f.AnalysisID,
	}, "\n")
}

// canonicalHash returns a stable hex digest of the canonical string,
// used as the NonceStore value to distinguish a legitimate retry (same
// hash) from a replay/tamper (different hash) for the same nonce.
func canonicalHash(canonical string) string {
	sum := sha256.Sum256([]byte(canonical))
	return hex.EncodeToString(sum[:])
}

// Sign returns the hex HMAC-SHA256 of the canonical string under key.
func Sign(key []byte, f Fields) string {
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(f.Canonical()))
	return hex.EncodeToString(mac.Sum(nil))
}

// verifySignature reports whether sigHex is a valid HMAC for f under
// key, using a constant-time comparison (hmac.Equal).
func verifySignature(key []byte, f Fields, sigHex string) bool {
	expected := Sign(key, f)
	// hex.DecodeString both sides and compare bytes in constant time.
	want, err1 := hex.DecodeString(expected)
	got, err2 := hex.DecodeString(strings.TrimSpace(sigHex))
	if err1 != nil || err2 != nil {
		return false
	}
	return hmac.Equal(want, got)
}

// Outcome is the typed result of a verification check. The interceptor
// maps each to a gRPC status code.
type Outcome int

const (
	// OutcomeOK — signature valid, fresh, not a replay (or a benign retry).
	OutcomeOK Outcome = iota
	// OutcomeBadSignature — missing/malformed/invalid HMAC.
	OutcomeBadSignature
	// OutcomeStale — timestamp outside the freshness window.
	OutcomeStale
	// OutcomeReplay — nonce reused with a DIFFERENT canonical hash.
	OutcomeReplay
)

func (o Outcome) String() string {
	switch o {
	case OutcomeOK:
		return "ok"
	case OutcomeBadSignature:
		return "bad_signature"
	case OutcomeStale:
		return "stale"
	case OutcomeReplay:
		return "replay"
	default:
		return "unknown"
	}
}

// ErrEmptyKey is returned by NewVerifier when key is empty.
var ErrEmptyKey = errors.New("signing: HMAC key must not be empty")

// Verifier validates inbound signed requests. Safe for concurrent use.
type Verifier struct {
	key    []byte
	window time.Duration
	nonces *NonceStore
}

// NewVerifier builds a Verifier. window is the max allowed clock skew
// (both directions) AND the nonce-retention TTL; they are intentionally
// the same value because a nonce can only be replayed usefully inside
// the freshness window. Returns ErrEmptyKey if key is empty so a
// mis-wired deploy fails loudly rather than verifying nothing.
func NewVerifier(key []byte, window time.Duration) (*Verifier, error) {
	if len(key) == 0 {
		return nil, ErrEmptyKey
	}
	if window <= 0 {
		window = 30 * time.Second
	}
	return &Verifier{
		key:    key,
		window: window,
		nonces: NewNonceStore(window),
	}, nil
}

// Check validates signature, freshness, and replay together. now is
// injectable for tests; pass time.Now() in production.
//
// Order matters: signature first (an unsigned/forged request must never
// influence the nonce store), then freshness, then replay. Only a
// fully-valid, fresh request is recorded in the nonce store.
func (v *Verifier) Check(f Fields, sigHex string, now time.Time) Outcome {
	if !verifySignature(v.key, f, sigHex) {
		return OutcomeBadSignature
	}

	delta := now.Sub(f.Timestamp)
	if delta < 0 {
		delta = -delta
	}
	if delta > v.window {
		return OutcomeStale
	}

	canonical := f.Canonical()
	if !v.nonces.SeenOrRecord(f.UserID, f.Nonce, canonicalHash(canonical), now) {
		return OutcomeReplay
	}
	return OutcomeOK
}

// Window returns the configured freshness window (used by callers that
// want to log/observe it). Read-only.
func (v *Verifier) Window() time.Duration { return v.window }

// NonceStore is an in-memory, TTL-bounded record of recently-seen
// (user_id, nonce) -> canonical-hash. Safe for concurrent use.
//
// In-memory is correct here: the freshness window is seconds, a gateway
// retry always lands on the same execution replica's connection path,
// and the AUTHORITATIVE no-double-fire guarantee is the durable
// Postgres idempotency table — this store only rejects fast in-window
// replay/tamper before the broker round-trip. It is a defense-in-depth
// optimisation, not the durable de-dup of record.
type NonceStore struct {
	ttl time.Duration
	mu  sync.Mutex
	m   map[string]nonceEntry
}

type nonceEntry struct {
	hash string
	at   time.Time
}

// NewNonceStore builds a store with the given TTL.
func NewNonceStore(ttl time.Duration) *NonceStore {
	if ttl <= 0 {
		ttl = 30 * time.Second
	}
	return &NonceStore{ttl: ttl, m: make(map[string]nonceEntry)}
}

func nonceKey(userID, nonce string) string {
	return userID + "|" + nonce
}

// SeenOrRecord records (userID, nonce)->hash and reports whether the
// request may proceed:
//   - first sight of the nonce in the window  -> record, return true.
//   - repeat with the SAME hash (a retry)      -> return true (allowed).
//   - repeat with a DIFFERENT hash (replay)    -> return false (rejected).
//
// Expired entries are treated as absent (and refreshed). The store is
// opportunistically pruned on each call so it stays bounded by the
// in-window request volume without a background goroutine.
func (s *NonceStore) SeenOrRecord(userID, nonce, hash string, now time.Time) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.pruneLocked(now)

	key := nonceKey(userID, nonce)
	if e, ok := s.m[key]; ok && now.Sub(e.at) <= s.ttl {
		if e.hash == hash {
			// Legitimate retry of the identical request: refresh the
			// timestamp so a slow retry chain stays recognised, and allow.
			s.m[key] = nonceEntry{hash: hash, at: now}
			return true
		}
		// Same nonce, different payload within the window => replay/tamper.
		return false
	}

	s.m[key] = nonceEntry{hash: hash, at: now}
	return true
}

// pruneLocked drops entries older than the TTL. Caller holds s.mu.
func (s *NonceStore) pruneLocked(now time.Time) {
	for k, e := range s.m {
		if now.Sub(e.at) > s.ttl {
			delete(s.m, k)
		}
	}
}

// Len returns the current number of tracked nonces (test/observability).
func (s *NonceStore) Len() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.m)
}

// FieldsError is returned when required metadata is missing/malformed,
// so the interceptor can distinguish "no signature presented" from
// "signature presented but invalid".
type FieldsError struct{ Reason string }

func (e *FieldsError) Error() string { return fmt.Sprintf("signing: %s", e.Reason) }
