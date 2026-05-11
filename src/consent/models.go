// Package consent implements the GDPR / ePrivacy cookie-consent
// persistence and HTTP API for the Exoper gateway.
//
// Scope:
//
//   - Records every consent decision a visitor makes as an immutable
//     row in the consent_records table.
//   - Supports anonymous-then-attach-on-login: visitors choose their
//     categories before they have an account; on first successful
//     sign-in the prior anonymous_id rows are linked to the new
//     user_id without losing the original timestamps.
//   - Exposes a tiny REST surface mounted under /api/v1/consent.
//
// Out of scope (deliberately):
//
//   - Strictly-necessary cookies (auth / CSRF / session). Per ePrivacy
//     Directive Art. 5(3) these require no consent and are NOT stored
//     in the categories blob.
//   - Geo-IP gating. The banner is shown universally; the legal model
//     adopted is the strictest applicable regime (GDPR / UK GDPR /
//     LGPD / CCPA) for every visitor.
package consent

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"strings"
	"time"
)

// SchemaSQL returns idempotent DDL for the consent_records table. It
// is called once at gateway startup against the same pgxpool used by
// auth / billing / mails, matching the existing pattern.
func SchemaSQL() string {
	return `
CREATE TABLE IF NOT EXISTS consent_records (
    id             TEXT PRIMARY KEY,
    user_id        TEXT,
    anonymous_id   TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    categories     JSONB NOT NULL,
    ip_hash        TEXT NOT NULL DEFAULT '',
    user_agent     TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consent_anonymous_id
    ON consent_records (anonymous_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_consent_user_id
    ON consent_records (user_id, created_at DESC)
    WHERE user_id IS NOT NULL;
`
}

// Category names. These strings MUST match the labels rendered by
// cotradee/src/routes/pages/CookiePolicyPage.tsx exactly. PLAN.md
// section 7 explicitly forbids drift between the policy and the
// implementation; a mismatch here is a compliance defect.
const (
	CategoryFunctional = "functional"
	CategoryAnalytics  = "analytics"
)

// AllOptionalCategories lists every category the user can toggle. The
// strictly-necessary category is intentionally omitted: it is always
// on and is not stored on a record.
var AllOptionalCategories = []string{
	CategoryFunctional,
	CategoryAnalytics,
}

// Categories is the on-the-wire and on-disk shape of a consent
// decision. We use named fields rather than map[string]bool so a typo
// in a future call site is a compile error, not a silent miss.
type Categories struct {
	Functional bool `json:"functional"`
	Analytics  bool `json:"analytics"`
}

// AllRejected returns a Categories with every optional category set
// to false. Used as the deterministic default for a brand-new visitor
// and for the explicit "Reject all (non-essential)" banner button.
func AllRejected() Categories {
	return Categories{Functional: false, Analytics: false}
}

// AllAccepted returns a Categories with every optional category set
// to true. Used by the "Accept all" banner button.
func AllAccepted() Categories {
	return Categories{Functional: true, Analytics: true}
}

// Record is the canonical representation of a single consent decision
// as returned to API callers. The Source field is computed at write
// time and exists only for audit clarity ("banner_accept_all",
// "banner_reject_all", "preferences_modal"); it is NOT stored as a
// separate column because the categories already carry every piece of
// information needed to reconstruct it during a regulator review.
type Record struct {
	ID            string     `json:"id"`
	UserID        *string    `json:"user_id,omitempty"`
	AnonymousID   string     `json:"anonymous_id"`
	PolicyVersion string     `json:"policy_version"`
	Categories    Categories `json:"categories"`
	CreatedAt     time.Time  `json:"created_at"`
}

// ----------------------------------------------------------------------
// Validation
// ----------------------------------------------------------------------

// ErrInvalidAnonymousID is returned when a caller submits an empty or
// excessively long anonymous identifier. We do not enforce a UUID
// format because the client may use any opaque identifier the browser
// can generate (crypto.randomUUID is available in every supported
// browser, but mocking it in tests is easier with raw hex).
var ErrInvalidAnonymousID = errors.New("consent: invalid anonymous_id")

// ErrInvalidPolicyVersion is returned when a caller submits an empty
// or excessively long policy version string.
var ErrInvalidPolicyVersion = errors.New("consent: invalid policy_version")

// Hard limits chosen to be defensive against pathological client
// payloads without preventing any legitimate value. Both values are
// well above any realistic input.
const (
	maxAnonymousIDLen   = 128
	maxPolicyVersionLen = 32
	maxUserAgentLen     = 512
)

// ValidateAnonymousID enforces the input contract for an anonymous_id
// supplied by the SPA. Returns a wrapped sentinel error on rejection
// so handlers can map it to HTTP 400 without leaking internal detail.
func ValidateAnonymousID(s string) error {
	s = strings.TrimSpace(s)
	if s == "" || len(s) > maxAnonymousIDLen {
		return ErrInvalidAnonymousID
	}
	return nil
}

// ValidatePolicyVersion enforces the input contract for the
// policy_version field. The string is opaque to the server — it is
// stamped by the SPA at the time of consent and replayed back when
// the user reopens the preferences modal so the SPA can decide
// whether a re-prompt is required.
func ValidatePolicyVersion(s string) error {
	s = strings.TrimSpace(s)
	if s == "" || len(s) > maxPolicyVersionLen {
		return ErrInvalidPolicyVersion
	}
	return nil
}

// TruncateUserAgent shortens a UA string to the storage cap. Returns
// the original input when already within the cap. UA is purely audit
// metadata; we never parse it or branch on its contents.
func TruncateUserAgent(ua string) string {
	if len(ua) <= maxUserAgentLen {
		return ua
	}
	return ua[:maxUserAgentLen]
}

// ----------------------------------------------------------------------
// ID generation
// ----------------------------------------------------------------------

// generateID returns a fresh hex-encoded 16-byte (128-bit) identifier
// used as the consent_records primary key. 128 bits is identical to
// the strength used by the auth package for session ids; the same
// statistical collision guarantees apply.
func generateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
