package auth

import (
	"context"
	"crypto/sha1" // #nosec G501 -- SHA-1 is the HIBP range-API wire format, NOT password storage (that is Argon2id).
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// BreachChecker reports whether a plaintext password appears in a known
// breach corpus. It is an ADVISORY hardening layer on top of the
// mandatory complexity policy, not an authentication gate, so callers
// treat an error as "could not check" (fail-open) and never block a
// user because the breach service is unavailable.
//
// The interface lives in the auth package so the dependency arrow
// points in; the gateway injects an implementation via
// Handler.WithBreachChecker. When none is injected the handlers skip
// the check entirely.
type BreachChecker interface {
	// IsBreached returns true when the password is known-breached.
	// On any error (timeout, transport, non-200) it returns
	// (false, err); the caller logs and proceeds (fail-open).
	IsBreached(ctx context.Context, plaintext string) (bool, error)
}

// ---------------------------------------------------------------------------
// HaveIBeenPwned (Pwned Passwords) k-anonymity implementation
// ---------------------------------------------------------------------------

const (
	// hibpRangeURL is the k-anonymity range endpoint. Only the first 5
	// hex chars of the SHA-1 are appended; the full hash never leaves
	// the process.
	hibpRangeURL = "https://api.pwnedpasswords.com/range/"

	// hibpTimeout bounds a single breach lookup so a slow HIBP never
	// stalls a registration / password change.
	hibpTimeout = 3 * time.Second
)

// HIBPBreachChecker queries the HaveIBeenPwned Pwned Passwords range
// API using k-anonymity.
type HIBPBreachChecker struct {
	client *http.Client
}

// NewHIBPBreachChecker builds a breach checker with a bounded HTTP
// client. The per-call context timeout (hibpTimeout) is the real guard;
// the client timeout is a backstop.
func NewHIBPBreachChecker() *HIBPBreachChecker {
	return &HIBPBreachChecker{
		client: &http.Client{Timeout: hibpTimeout + time.Second},
	}
}

// IsBreached implements BreachChecker using SHA-1 k-anonymity. SHA-1 is
// used ONLY because the HIBP protocol is defined over it; password
// storage on this platform is Argon2id (see password.go).
func (h *HIBPBreachChecker) IsBreached(ctx context.Context, plaintext string) (bool, error) {
	if plaintext == "" {
		return false, nil
	}

	sum := sha1.Sum([]byte(plaintext)) // #nosec G401 -- HIBP wire format only; not used for password storage.
	full := strings.ToUpper(hex.EncodeToString(sum[:]))
	prefix, suffix := full[:5], full[5:]

	callCtx, cancel := context.WithTimeout(ctx, hibpTimeout)
	defer cancel()

	req, err := http.NewRequestWithContext(callCtx, http.MethodGet, hibpRangeURL+prefix, nil)
	if err != nil {
		return false, fmt.Errorf("hibp: build request: %w", err)
	}
	// Add-Padding makes HIBP pad the response so its size does not leak
	// how many suffixes share the prefix.
	req.Header.Set("Add-Padding", "true")
	req.Header.Set("User-Agent", "etradie-auth")

	resp, err := h.client.Do(req)
	if err != nil {
		return false, fmt.Errorf("hibp: request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("hibp: unexpected status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(io.LimitReader(resp.Body, 2<<20)) // 2 MiB cap.
	if err != nil {
		return false, fmt.Errorf("hibp: read body: %w", err)
	}

	// Each line is "<35-hex-suffix>:<count>". A count of 0 is a padding
	// line (Add-Padding) and means not-breached for that suffix.
	for _, line := range strings.Split(string(body), "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) != 2 {
			continue
		}
		if strings.EqualFold(parts[0], suffix) {
			count := strings.TrimSpace(parts[1])
			if count != "" && count != "0" {
				return true, nil
			}
			return false, nil
		}
	}
	return false, nil
}

// ---------------------------------------------------------------------------
// No-op implementation
// ---------------------------------------------------------------------------

// NoopBreachChecker is an explicit disabled checker for dev/test or
// deployments that opt out of the external HIBP call. IsBreached always
// returns (false, nil).
type NoopBreachChecker struct{}

// IsBreached always reports not-breached.
func (NoopBreachChecker) IsBreached(_ context.Context, _ string) (bool, error) {
	return false, nil
}
