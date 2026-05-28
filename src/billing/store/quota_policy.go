package store

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

// QuotaPolicyRow is the SPA-/admin-facing shape of one tier_quota_policies
// row. Distinct from LLMQuotaPolicy (defined in usage.go) which is the
// store-internal shape consumed by Reserve. The conversion lives in
// ToLLMQuotaPolicy below so neither shape contaminates the other.
type QuotaPolicyRow struct {
	Tier                  string    `json:"tier"`
	DailyInputTokens      int64     `json:"daily_input_tokens"`
	DailyOutputTokens     int64     `json:"daily_output_tokens"`
	MonthlyInputTokens    int64     `json:"monthly_input_tokens"`
	MonthlyOutputTokens   int64     `json:"monthly_output_tokens"`
	MaxInputTokensPerCall int64     `json:"max_input_tokens_per_call"`
	SoftCapPercent        int       `json:"soft_cap_percent"`
	ReservationTTLSeconds int       `json:"reservation_ttl_seconds"`
	AllowedModels         []string  `json:"allowed_models"`
	Enforced              bool      `json:"enforced"`
	UpdatedAt             time.Time `json:"updated_at"`
	UpdatedBy             *string   `json:"updated_by,omitempty"`
}

// ToLLMQuotaPolicy converts a row into the shape Reserve consumes.
// Distinct allocations for AllowedModels so a cache reader cannot mutate
// the store-cached row's slice.
func (r *QuotaPolicyRow) ToLLMQuotaPolicy() LLMQuotaPolicy {
	allowed := make(map[string]bool, len(r.AllowedModels))
	for _, m := range r.AllowedModels {
		m = strings.ToLower(strings.TrimSpace(m))
		if m != "" {
			allowed[m] = true
		}
	}
	return LLMQuotaPolicy{
		DailyInputTokens:      r.DailyInputTokens,
		DailyOutputTokens:     r.DailyOutputTokens,
		MonthlyInputTokens:    r.MonthlyInputTokens,
		MonthlyOutputTokens:   r.MonthlyOutputTokens,
		MaxInputTokensPerCall: r.MaxInputTokensPerCall,
		SoftCapPercent:        r.SoftCapPercent,
		AllowedModels:         allowed,
		ReservationTTL:        time.Duration(r.ReservationTTLSeconds) * time.Second,
	}
}

// ErrPolicyNotFound is returned when GetPolicy finds no row for the tier.
// Callers MUST treat this as a hard failure (tier_not_eligible at the
// metering pre-flight) rather than silently substituting an empty policy:
// a missing row indicates a bad deploy (seed migration did not run).
var ErrPolicyNotFound = errors.New("quota policy: tier not found")

// CanonicalTiers is the stable display order used by ListPolicies and the
// admin SPA. Most-edited tiers first.
var CanonicalTiers = []string{"pro_managed", "admin", "pro_byok", "free"}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

// ValidatePolicy enforces the SAME bounds as the migration's CHECK
// constraints. Called by Upsert before the DB write AND by the gateway
// admin handler before the call, so a client-side bypass cannot reach
// the DB with out-of-range values.
//
// Returns nil on success; otherwise returns a single error describing the
// first failing field. The admin SPA surfaces the message verbatim.
func ValidatePolicy(p *QuotaPolicyRow) error {
	if p == nil {
		return fmt.Errorf("policy is nil")
	}
	tier := strings.ToLower(strings.TrimSpace(p.Tier))
	switch tier {
	case "free", "pro_byok", "pro_managed", "admin":
		// ok
	default:
		return fmt.Errorf("tier must be one of free, pro_byok, pro_managed, admin; got %q", p.Tier)
	}
	p.Tier = tier

	if p.DailyInputTokens < 0 {
		return fmt.Errorf("daily_input_tokens must be >= 0")
	}
	if p.DailyOutputTokens < 0 {
		return fmt.Errorf("daily_output_tokens must be >= 0")
	}
	if p.MonthlyInputTokens < 0 {
		return fmt.Errorf("monthly_input_tokens must be >= 0")
	}
	if p.MonthlyOutputTokens < 0 {
		return fmt.Errorf("monthly_output_tokens must be >= 0")
	}
	if p.MaxInputTokensPerCall < 0 {
		return fmt.Errorf("max_input_tokens_per_call must be >= 0")
	}
	if p.SoftCapPercent < 0 || p.SoftCapPercent > 100 {
		return fmt.Errorf("soft_cap_percent must be 0..100; got %d", p.SoftCapPercent)
	}
	if p.ReservationTTLSeconds < 30 || p.ReservationTTLSeconds > 3600 {
		return fmt.Errorf("reservation_ttl_seconds must be 30..3600; got %d", p.ReservationTTLSeconds)
	}

	// Enforced=true requires non-zero caps on every dimension that
	// will actually be enforced; allowing all zeros with enforced=true
	// would silently block 100% of reservations and look like a bug.
	if p.Enforced {
		if p.DailyInputTokens == 0 || p.DailyOutputTokens == 0 ||
			p.MonthlyInputTokens == 0 || p.MonthlyOutputTokens == 0 ||
			p.MaxInputTokensPerCall == 0 {
			return fmt.Errorf("enforced policy requires all four token caps and max_input_tokens_per_call to be > 0")
		}
	}

	// Normalise the allow-list to lowercase trimmed unique entries.
	if len(p.AllowedModels) > 0 {
		seen := make(map[string]struct{}, len(p.AllowedModels))
		normalised := make([]string, 0, len(p.AllowedModels))
		for _, m := range p.AllowedModels {
			m = strings.ToLower(strings.TrimSpace(m))
			if m == "" {
				continue
			}
			if _, dup := seen[m]; dup {
				continue
			}
			seen[m] = struct{}{}
			normalised = append(normalised, m)
		}
		p.AllowedModels = normalised
	}
	return nil
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

// cachedPolicy holds one cache entry. expiresAt is the wall-clock time at
// which a re-read must occur even without explicit invalidation; it is a
// safety net for the unlikely case of a manual DB UPDATE that bypassed
// Upsert (the cache would otherwise stay stale forever).
type cachedPolicy struct {
	row       *QuotaPolicyRow
	expiresAt time.Time
}

// QuotaPolicyStore reads and writes tier_quota_policies with a tiny
// in-memory cache. Safe for concurrent use.
type QuotaPolicyStore struct {
	db       *pgxpool.Pool
	cache    sync.Map // tier(string) -> *cachedPolicy
	cacheTTL time.Duration

	// hitCount / missCount are exposed via Stats() for the future
	// /metrics surface. atomic counters so the read path stays
	// allocation-free.
	hitCount  atomic.Uint64
	missCount atomic.Uint64
}

// NewQuotaPolicyStore returns a store with a 30 s cache TTL.
func NewQuotaPolicyStore(db *pgxpool.Pool) *QuotaPolicyStore {
	return &QuotaPolicyStore{
		db:       db,
		cacheTTL: 30 * time.Second,
	}
}

// Stats reports cache hit / miss counts. Exposed for the future Prometheus
// gauge in the gateway's metering observability bundle.
func (s *QuotaPolicyStore) Stats() (hits, misses uint64) {
	return s.hitCount.Load(), s.missCount.Load()
}

// InvalidateCache drops the per-tier cache entry. Called by Upsert.
// Public so a future admin-side "force refresh" tool can call it directly
// without going through an UPDATE.
func (s *QuotaPolicyStore) InvalidateCache(tier string) {
	s.cache.Delete(strings.ToLower(strings.TrimSpace(tier)))
}

// InvalidateAll drops every cache entry. Used by tests and by the
// service's hot-reload path if the operator ever resets the table.
func (s *QuotaPolicyStore) InvalidateAll() {
	s.cache.Range(func(k, _ any) bool {
		s.cache.Delete(k)
		return true
	})
}

// ---------------------------------------------------------------------------
// Read
// ---------------------------------------------------------------------------

const quotaPolicyColumns = `
	tier,
	daily_input_tokens,
	daily_output_tokens,
	monthly_input_tokens,
	monthly_output_tokens,
	max_input_tokens_per_call,
	soft_cap_percent,
	reservation_ttl_seconds,
	allowed_models,
	enforced,
	updated_at,
	updated_by
`

func scanQuotaPolicyRow(row pgx.Row) (*QuotaPolicyRow, error) {
	var (
		out       QuotaPolicyRow
		rawModels []byte
	)
	err := row.Scan(
		&out.Tier,
		&out.DailyInputTokens,
		&out.DailyOutputTokens,
		&out.MonthlyInputTokens,
		&out.MonthlyOutputTokens,
		&out.MaxInputTokensPerCall,
		&out.SoftCapPercent,
		&out.ReservationTTLSeconds,
		&rawModels,
		&out.Enforced,
		&out.UpdatedAt,
		&out.UpdatedBy,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrPolicyNotFound
		}
		return nil, fmt.Errorf("quota_policy: scan: %w", err)
	}
	if len(rawModels) > 0 {
		if err := json.Unmarshal(rawModels, &out.AllowedModels); err != nil {
			return nil, fmt.Errorf("quota_policy: parse allowed_models: %w", err)
		}
	}
	if out.AllowedModels == nil {
		out.AllowedModels = []string{}
	}
	return &out, nil
}

// GetPolicy returns the policy row for the given tier, using the cache
// when fresh. tier is normalised to lowercase trimmed.
func (s *QuotaPolicyStore) GetPolicy(ctx context.Context, tier string) (*QuotaPolicyRow, error) {
	tier = strings.ToLower(strings.TrimSpace(tier))
	if tier == "" {
		return nil, fmt.Errorf("quota_policy: tier is required")
	}

	// Cache fast-path.
	if raw, ok := s.cache.Load(tier); ok {
		entry := raw.(*cachedPolicy)
		if time.Now().Before(entry.expiresAt) {
			s.hitCount.Add(1)
			// Return a defensive copy of AllowedModels so a caller that
			// happens to append to the slice cannot mutate the cached row.
			row := *entry.row
			row.AllowedModels = append([]string(nil), entry.row.AllowedModels...)
			return &row, nil
		}
		s.cache.Delete(tier)
	}

	s.missCount.Add(1)

	query := `SELECT ` + quotaPolicyColumns + ` FROM tier_quota_policies WHERE tier = $1`
	row, err := scanQuotaPolicyRow(s.db.QueryRow(ctx, query, tier))
	if err != nil {
		return nil, err
	}

	s.cache.Store(tier, &cachedPolicy{
		row:       row,
		expiresAt: time.Now().Add(s.cacheTTL),
	})
	// Defensive copy on the way out, same reason as the cache-hit branch.
	copy := *row
	copy.AllowedModels = append([]string(nil), row.AllowedModels...)
	return &copy, nil
}

// ListPolicies returns every row in CanonicalTiers order. Unknown tiers
// found in the DB (should never happen because of the CHECK constraint)
// are appended after the canonical set so the admin can still see and
// edit them.
func (s *QuotaPolicyStore) ListPolicies(ctx context.Context) ([]*QuotaPolicyRow, error) {
	query := `SELECT ` + quotaPolicyColumns + ` FROM tier_quota_policies`
	rows, err := s.db.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("quota_policy: list: %w", err)
	}
	defer rows.Close()

	byTier := make(map[string]*QuotaPolicyRow, 4)
	for rows.Next() {
		r, err := scanQuotaPolicyRow(rows)
		if err != nil {
			return nil, err
		}
		byTier[r.Tier] = r
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("quota_policy: list iter: %w", err)
	}

	out := make([]*QuotaPolicyRow, 0, len(byTier))
	for _, t := range CanonicalTiers {
		if row, ok := byTier[t]; ok {
			out = append(out, row)
			delete(byTier, t)
		}
	}
	// Append any extras (defensive: CHECK constraint forbids this in
	// the DB, but a future schema change might widen the allow-list).
	for _, row := range byTier {
		out = append(out, row)
	}
	return out, nil
}

// ---------------------------------------------------------------------------
// Write
// ---------------------------------------------------------------------------

// UpsertPolicy persists the row and invalidates the per-tier cache entry
// so the next read sees the new value immediately. updatedBy must be the
// admin's user_id (taken from the JWT in the gateway handler); empty
// updatedBy is rejected so the audit trail stays complete.
func (s *QuotaPolicyStore) UpsertPolicy(
	ctx context.Context,
	row *QuotaPolicyRow,
	updatedBy string,
) error {
	if strings.TrimSpace(updatedBy) == "" {
		return fmt.Errorf("quota_policy: updated_by is required")
	}
	if err := ValidatePolicy(row); err != nil {
		return fmt.Errorf("quota_policy: validate: %w", err)
	}

	allowedJSON, err := json.Marshal(row.AllowedModels)
	if err != nil {
		return fmt.Errorf("quota_policy: marshal allowed_models: %w", err)
	}

	// INSERT ... ON CONFLICT DO UPDATE so the migration's seed row is
	// updated in place on the first edit, and a hypothetical tier row
	// that did NOT exist (e.g. a future tier added before its seed
	// migration) is created cleanly. The seed migration already covers
	// every canonical tier so the INSERT branch is unreachable in
	// normal operation; keep the ON CONFLICT path as defense-in-depth.
	_, err = s.db.Exec(ctx, `
		INSERT INTO tier_quota_policies (
			tier,
			daily_input_tokens,
			daily_output_tokens,
			monthly_input_tokens,
			monthly_output_tokens,
			max_input_tokens_per_call,
			soft_cap_percent,
			reservation_ttl_seconds,
			allowed_models,
			enforced,
			updated_at,
			updated_by
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, NOW(), $11)
		ON CONFLICT (tier) DO UPDATE SET
			daily_input_tokens         = EXCLUDED.daily_input_tokens,
			daily_output_tokens        = EXCLUDED.daily_output_tokens,
			monthly_input_tokens       = EXCLUDED.monthly_input_tokens,
			monthly_output_tokens      = EXCLUDED.monthly_output_tokens,
			max_input_tokens_per_call  = EXCLUDED.max_input_tokens_per_call,
			soft_cap_percent           = EXCLUDED.soft_cap_percent,
			reservation_ttl_seconds    = EXCLUDED.reservation_ttl_seconds,
			allowed_models             = EXCLUDED.allowed_models,
			enforced                   = EXCLUDED.enforced,
			updated_at                 = NOW(),
			updated_by                 = EXCLUDED.updated_by
	`,
		row.Tier,
		row.DailyInputTokens,
		row.DailyOutputTokens,
		row.MonthlyInputTokens,
		row.MonthlyOutputTokens,
		row.MaxInputTokensPerCall,
		row.SoftCapPercent,
		row.ReservationTTLSeconds,
		allowedJSON,
		row.Enforced,
		updatedBy,
	)
	if err != nil {
		return fmt.Errorf("quota_policy: upsert: %w", err)
	}

	// Explicit invalidation: the next GetPolicy(tier) call rebuilds
	// from the row that was just committed. An admin watching the
	// dashboard's usage panel sees the new caps within one polling
	// cycle (UsagePanel polls on mount + manual refresh).
	s.InvalidateCache(row.Tier)
	return nil
}
