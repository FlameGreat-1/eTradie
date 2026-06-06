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
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/flamegreat-1/etradie/src/pkg/execsigning"
)

// The pure signing primitives live in the shared src/pkg/execsigning
// package so the gateway (signer) and execution (verifier) share ONE
// canonical definition with no drift. This package re-exports them and
// adds the execution-side stateful verification (freshness + replay).

// Fields is the shared request-attribute struct bound by the signature.
type Fields = execsigning.Fields

// Metadata keys carried on the ExecuteTrade gRPC call (re-exported).
const (
	MetaSignature = execsigning.MetaSignature
	MetaTimestamp = execsigning.MetaTimestamp
	MetaNonce     = execsigning.MetaNonce
)

// Version is the canonical-string scheme version (re-exported).
const Version = execsigning.Version

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
	if !execsigning.Verify(v.key, f, sigHex) {
		return OutcomeBadSignature
	}

	delta := now.Sub(f.Timestamp)
	if delta < 0 {
		delta = -delta
	}
	if delta > v.window {
		return OutcomeStale
	}

	if !v.nonces.SeenOrRecord(f.UserID, f.Nonce, f.CanonicalHash(), now) {
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
