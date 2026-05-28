package store

import (
	"context"
	"errors"
	"strings"
	"time"
)

// QuotaPreflightOutcome is the consolidated result of the pre-flight
// check shared between the manual-cycle path (api_handlers.go) and the
// auto-cycle path (scheduler.go). It carries every field both call
// sites need so they can emit byte-identical alert events and 429
// bodies without duplicating any logic. Audit ref: ADMIN-QUOTA-AUDIT-11.
type QuotaPreflightOutcome struct {
	// Blocked is true when the caller MUST short-circuit the cycle.
	// When false, every other field is unset and the caller proceeds
	// normally.
	Blocked bool

	// Tier is the canonical tier string used for policy lookup. Always
	// populated (even when Blocked=false) so callers can log it.
	Tier string

	// IsAdmin echoes whether the caller is an admin. Used by the SPA
	// modal to pick the right CTA (Adjust Limits vs Use Your Own Key).
	IsAdmin bool

	// PolicyEnforced reflects the row.Enforced field. When false the
	// caller can skip the rest of the pre-flight (BYOK / free tier).
	PolicyEnforced bool

	// Result mirrors the breached dimension. Empty when Blocked=false.
	Dimension string
	Limit     int64
	Used      int64
	Requested int64
	ResetsAt  time.Time
	RetryAfter int
}

// LLMQuotaPreflightCaller is the minimal identity carried by both the
// authenticated request (auth.Claims) and the scheduler tick
// (auth.User). The helper consumes just the three fields it needs.
type LLMQuotaPreflightCaller struct {
	UserID string
	Role   string // "admin" or "etradie" (raw role string)
	Tier   string // raw tier string from the JWT / user record
}

// LLMQuotaPreflight is the single source of truth for the pre-flight
// check shared by every site that wants to short-circuit before the
// orchestrator burns TA + Macro + RAG. It:
//
//   1. Resolves the canonical tier string (admin -> "admin").
//   2. Loads the policy row via QuotaPolicyStore.GetPolicy.
//   3. Short-circuits to Blocked=false when the tier is not enforced
//      (BYOK / free) so the caller can skip the rest cleanly.
//   4. Runs UsageStore.PreflightLLMQuota with estimatedInput=0,
//      maxOutput=0 (the conservative pre-prompt check).
//   5. Returns a QuotaPreflightOutcome the caller can use to emit the
//      alert event AND the 429 body without further branching.
//
// Failure posture (matches the audit-ref ADMIN-QUOTA-7 commits):
//   - Policy lookup error -> Blocked=false, log left to the caller
//     (so per-site tagging can still happen). The deep Reserve path
//     stays as the correctness boundary.
//   - Usage lookup error  -> same.
//   - ErrPolicyNotFound   -> Blocked=false (no row means the seed
//     never ran; the deep Reserve will tier_not_eligible the call).
//
// The returned outcome's RetryAfter is at least 1 second.
func LLMQuotaPreflight(
	ctx context.Context,
	policyStore *QuotaPolicyStore,
	usageStore *UsageStore,
	caller LLMQuotaPreflightCaller,
) (QuotaPreflightOutcome, error) {
	tier := strings.ToLower(strings.TrimSpace(caller.Tier))
	isAdmin := strings.EqualFold(strings.TrimSpace(caller.Role), "admin")
	if isAdmin {
		tier = "admin"
	}

	outcome := QuotaPreflightOutcome{Tier: tier, IsAdmin: isAdmin}

	row, err := policyStore.GetPolicy(ctx, tier)
	if err != nil {
		if errors.Is(err, ErrPolicyNotFound) {
			return outcome, nil
		}
		return outcome, err
	}
	outcome.PolicyEnforced = row.Enforced
	if !row.Enforced {
		return outcome, nil
	}

	policy := row.ToLLMQuotaPolicy()
	res, err := usageStore.PreflightLLMQuota(ctx, caller.UserID, 0, 0, policy)
	if err != nil {
		return outcome, err
	}
	if res.Allowed {
		return outcome, nil
	}

	retryAfter := int(time.Until(res.ResetsAt).Seconds())
	if retryAfter < 1 {
		retryAfter = 1
	}

	outcome.Blocked = true
	outcome.Dimension = res.Dimension
	outcome.Limit = res.Limit
	outcome.Used = res.Used
	outcome.Requested = res.Requested
	outcome.ResetsAt = res.ResetsAt
	outcome.RetryAfter = retryAfter
	return outcome, nil
}
