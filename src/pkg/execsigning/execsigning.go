// Package execsigning holds the PURE, dependency-free primitives for
// signing the internal gateway -> execution ExecuteTrade gRPC call
// (CHECKLIST Tier 8: signed internal execution requests + replay
// protection).
//
// It lives under src/pkg (like src/pkg/resilience) so BOTH the gateway
// (signer) and the execution service (verifier) can import it; the
// execution-only stateful pieces (Verifier, NonceStore, the gRPC
// interceptor) live in src/execution/internal/signing and build on
// these primitives.
//
// Pure stdlib only (crypto/hmac, crypto/sha256, encoding/hex, strings,
// time). No grpc, no auth, no observability imports — deliberately, so
// it is safe to import from any layer with zero cycle risk.
package execsigning

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"strings"
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

// Fields are the request attributes bound by the signature. UserID is
// the authenticated principal (supplied by the signer from its verified
// claims; re-derived by the verifier from the JWT in context) so the
// signature binds the request to who is making it, not just to its
// contents.
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
// output is byte-identical across processes and Go versions. Timestamp
// is RFC3339Nano in UTC so signer and verifier agree to the nanosecond.
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

// CanonicalHash returns a stable hex SHA-256 digest of the canonical
// string, used by the verifier's nonce store to distinguish a
// legitimate retry (same hash) from a replay/tamper (different hash).
func (f Fields) CanonicalHash() string {
	sum := sha256.Sum256([]byte(f.Canonical()))
	return hex.EncodeToString(sum[:])
}

// Sign returns the hex HMAC-SHA256 of the canonical string under key.
func Sign(key []byte, f Fields) string {
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(f.Canonical()))
	return hex.EncodeToString(mac.Sum(nil))
}

// Verify reports whether sigHex is a valid HMAC for f under key, using a
// constant-time comparison (hmac.Equal over the decoded bytes).
func Verify(key []byte, f Fields, sigHex string) bool {
	want, err1 := hex.DecodeString(Sign(key, f))
	got, err2 := hex.DecodeString(strings.TrimSpace(sigHex))
	if err1 != nil || err2 != nil {
		return false
	}
	return hmac.Equal(want, got)
}
