package store

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// ---------------------------------------------------------------------------
// AdminQueries — read-only admin-facing query surface for the billing
// database. The five query methods all join billing_* tables with
// auth_users so the admin SPA gets a user-friendly row shape
// (username/email next to tier/status/tokens) in a single round-trip.
//
// NONE of the methods on this type mutate state. They are deliberately
// separated from SubscriptionStore / UsageStore so the user-facing fast
// path is not polluted with admin-only joins and pagination logic.
// ---------------------------------------------------------------------------

type AdminQueries struct {
	db *pgxpool.Pool
}

func NewAdminQueries(db *pgxpool.Pool) *AdminQueries {
	return &AdminQueries{db: db}
}

// ---------------------------------------------------------------------------
// Pagination + filter primitives
// ---------------------------------------------------------------------------

// Page is a 1-indexed pagination request. Zero values default to
// (page=1, size=50). Max size is hard-capped at 200 so a runaway admin
// query cannot scan the whole table in one shot.
type Page struct {
	Page int
	Size int
}

func (p Page) normalize() (limit, offset int) {
	size := p.Size
	if size <= 0 {
		size = 50
	}
	if size > 200 {
		size = 200
	}
	page := p.Page
	if page <= 0 {
		page = 1
	}
	return size, (page - 1) * size
}

// SubscriptionFilter narrows ListSubscriptions. All fields are optional;
// empty values disable that predicate.
type SubscriptionFilter struct {
	Tier     string
	Status   string
	Provider string
	Search   string // ILIKE on username/email
}

// AdminSubscriptionRow is the admin-facing shape: subscription columns
// plus the joined user identity. Pointers mirror the underlying
// nullable columns so the JSON encoder emits `null` rather than
// silently coercing missing data to empty strings.
type AdminSubscriptionRow struct {
	UserID                 string     `json:"user_id"`
	Username               string     `json:"username"`
	Email                  string     `json:"email"`
	Tier                   string     `json:"tier"`
	Status                 string     `json:"status"`
	PaymentProvider        *string    `json:"payment_provider"`
	ProviderCustomerID     *string    `json:"provider_customer_id"`
	ProviderSubscriptionID *string    `json:"provider_subscription_id"`
	CurrentPeriodEnd       *time.Time `json:"current_period_end"`
	EventTimestamp         time.Time  `json:"event_timestamp"`
	CreatedAt              time.Time  `json:"created_at"`
	UpdatedAt              time.Time  `json:"updated_at"`
}

// ListSubscriptions returns a paginated admin view of every
// subscription row joined with the owning user's identity. The result
// is ordered by updated_at DESC so the most-recently-changed
// subscriptions appear first (operationally the most useful order for
// support triage).
func (q *AdminQueries) ListSubscriptions(
	ctx context.Context, f SubscriptionFilter, p Page,
) (rows []AdminSubscriptionRow, total int64, err error) {
	limit, offset := p.normalize()

	where := []string{}
	args := []any{}
	next := func() string { return fmt.Sprintf("$%d", len(args)+1) }

	if s := strings.TrimSpace(f.Tier); s != "" {
		args = append(args, s)
		where = append(where, "bs.tier = "+next())
	}
	if s := strings.TrimSpace(f.Status); s != "" {
		args = append(args, s)
		where = append(where, "bs.status = "+next())
	}
	if s := strings.TrimSpace(f.Provider); s != "" {
		args = append(args, s)
		where = append(where, "bs.payment_provider = "+next())
	}
	if s := strings.TrimSpace(f.Search); s != "" {
		args = append(args, "%"+s+"%")
		p1 := next()
		args = append(args, "%"+s+"%")
		p2 := next()
		where = append(where, "(au.username ILIKE "+p1+" OR au.email ILIKE "+p2+")")
	}
	whereSQL := ""
	if len(where) > 0 {
		whereSQL = "WHERE " + strings.Join(where, " AND ")
	}

	countSQL := `
		SELECT COUNT(*)
		FROM billing_subscriptions bs
		JOIN auth_users au ON au.id = bs.user_id
		` + whereSQL
	if err := q.db.QueryRow(ctx, countSQL, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("admin_list_subscriptions: count: %w", err)
	}

	listSQL := `
		SELECT bs.user_id, au.username, au.email,
		       bs.tier, bs.status,
		       bs.payment_provider, bs.provider_customer_id, bs.provider_subscription_id,
		       bs.current_period_end, bs.event_timestamp, bs.created_at, bs.updated_at
		FROM billing_subscriptions bs
		JOIN auth_users au ON au.id = bs.user_id
		` + whereSQL + `
		ORDER BY bs.updated_at DESC
		LIMIT $` + fmt.Sprintf("%d", len(args)+1) +
		` OFFSET $` + fmt.Sprintf("%d", len(args)+2)
	args = append(args, limit, offset)

	dbRows, err := q.db.Query(ctx, listSQL, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("admin_list_subscriptions: query: %w", err)
	}
	defer dbRows.Close()

	rows = make([]AdminSubscriptionRow, 0, limit)
	for dbRows.Next() {
		var r AdminSubscriptionRow
		if err := dbRows.Scan(
			&r.UserID, &r.Username, &r.Email,
			&r.Tier, &r.Status,
			&r.PaymentProvider, &r.ProviderCustomerID, &r.ProviderSubscriptionID,
			&r.CurrentPeriodEnd, &r.EventTimestamp, &r.CreatedAt, &r.UpdatedAt,
		); err != nil {
			return nil, 0, fmt.Errorf("admin_list_subscriptions: scan: %w", err)
		}
		rows = append(rows, r)
	}
	if err := dbRows.Err(); err != nil {
		return nil, 0, fmt.Errorf("admin_list_subscriptions: rows: %w", err)
	}
	return rows, total, nil
}

// ---------------------------------------------------------------------------
// Subscription events (the canonical "payment transactions" feed)
// ---------------------------------------------------------------------------

// EventFilter narrows ListSubscriptionEvents. All fields are optional.
type EventFilter struct {
	Provider  string
	EventName string
	UserID    string
	Search    string // ILIKE on username/email
}

// AdminSubscriptionEventRow is one row of the audit feed. previous_*
// columns are NULL on first-insert (the very first tier the user ever
// landed on); we surface them as empty strings so the JSON shape is
// stable for the SPA.
type AdminSubscriptionEventRow struct {
	ID             int64     `json:"id"`
	UserID         string    `json:"user_id"`
	Username       string    `json:"username"`
	Email          string    `json:"email"`
	Provider       string    `json:"provider"`
	EventName      string    `json:"event_name"`
	EventID        string    `json:"event_id"`
	PreviousTier   string    `json:"previous_tier"`
	NewTier        string    `json:"new_tier"`
	PreviousStatus string    `json:"previous_status"`
	NewStatus      string    `json:"new_status"`
	EventTimestamp time.Time `json:"event_timestamp"`
	CreatedAt      time.Time `json:"created_at"`
}

func (q *AdminQueries) ListSubscriptionEvents(
	ctx context.Context, f EventFilter, p Page,
) (rows []AdminSubscriptionEventRow, total int64, err error) {
	limit, offset := p.normalize()

	where := []string{}
	args := []any{}
	next := func() string { return fmt.Sprintf("$%d", len(args)+1) }

	if s := strings.TrimSpace(f.Provider); s != "" {
		args = append(args, s)
		where = append(where, "e.provider = "+next())
	}
	if s := strings.TrimSpace(f.EventName); s != "" {
		args = append(args, s)
		where = append(where, "e.event_name = "+next())
	}
	if s := strings.TrimSpace(f.UserID); s != "" {
		args = append(args, s)
		where = append(where, "e.user_id = "+next())
	}
	if s := strings.TrimSpace(f.Search); s != "" {
		args = append(args, "%"+s+"%")
		p1 := next()
		args = append(args, "%"+s+"%")
		p2 := next()
		where = append(where, "(au.username ILIKE "+p1+" OR au.email ILIKE "+p2+")")
	}
	whereSQL := ""
	if len(where) > 0 {
		whereSQL = "WHERE " + strings.Join(where, " AND ")
	}

	countSQL := `
		SELECT COUNT(*)
		FROM billing_subscription_events e
		JOIN auth_users au ON au.id = e.user_id
		` + whereSQL
	if err := q.db.QueryRow(ctx, countSQL, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("admin_list_subscription_events: count: %w", err)
	}

	listSQL := `
		SELECT e.id, e.user_id, au.username, au.email,
		       e.provider, e.event_name, e.event_id,
		       COALESCE(e.previous_tier, ''),
		       e.new_tier,
		       COALESCE(e.previous_status, ''),
		       e.new_status,
		       e.event_timestamp, e.created_at
		FROM billing_subscription_events e
		JOIN auth_users au ON au.id = e.user_id
		` + whereSQL + `
		ORDER BY e.created_at DESC, e.id DESC
		LIMIT $` + fmt.Sprintf("%d", len(args)+1) +
		` OFFSET $` + fmt.Sprintf("%d", len(args)+2)
	args = append(args, limit, offset)

	dbRows, err := q.db.Query(ctx, listSQL, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("admin_list_subscription_events: query: %w", err)
	}
	defer dbRows.Close()

	rows = make([]AdminSubscriptionEventRow, 0, limit)
	for dbRows.Next() {
		var r AdminSubscriptionEventRow
		if err := dbRows.Scan(
			&r.ID, &r.UserID, &r.Username, &r.Email,
			&r.Provider, &r.EventName, &r.EventID,
			&r.PreviousTier, &r.NewTier, &r.PreviousStatus, &r.NewStatus,
			&r.EventTimestamp, &r.CreatedAt,
		); err != nil {
			return nil, 0, fmt.Errorf("admin_list_subscription_events: scan: %w", err)
		}
		rows = append(rows, r)
	}
	if err := dbRows.Err(); err != nil {
		return nil, 0, fmt.Errorf("admin_list_subscription_events: rows: %w", err)
	}
	return rows, total, nil
}

// GetUserSubscriptionEvents returns the most recent N audit rows for
// one user. Used by the per-user drill-down page on the admin
// dashboard. limit is hard-capped at 500 — admin support workflows
// never need the full history in one shot.
func (q *AdminQueries) GetUserSubscriptionEvents(
	ctx context.Context, userID string, limit int,
) ([]AdminSubscriptionEventRow, error) {
	if strings.TrimSpace(userID) == "" {
		return nil, fmt.Errorf("admin_get_user_subscription_events: user_id is required")
	}
	if limit <= 0 || limit > 500 {
		limit = 100
	}
	const sqlStmt = `
		SELECT e.id, e.user_id, au.username, au.email,
		       e.provider, e.event_name, e.event_id,
		       COALESCE(e.previous_tier, ''),
		       e.new_tier,
		       COALESCE(e.previous_status, ''),
		       e.new_status,
		       e.event_timestamp, e.created_at
		FROM billing_subscription_events e
		JOIN auth_users au ON au.id = e.user_id
		WHERE e.user_id = $1
		ORDER BY e.created_at DESC, e.id DESC
		LIMIT $2
	`
	dbRows, err := q.db.Query(ctx, sqlStmt, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("admin_get_user_subscription_events: %w", err)
	}
	defer dbRows.Close()

	out := make([]AdminSubscriptionEventRow, 0, limit)
	for dbRows.Next() {
		var r AdminSubscriptionEventRow
		if err := dbRows.Scan(
			&r.ID, &r.UserID, &r.Username, &r.Email,
			&r.Provider, &r.EventName, &r.EventID,
			&r.PreviousTier, &r.NewTier, &r.PreviousStatus, &r.NewStatus,
			&r.EventTimestamp, &r.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("admin_get_user_subscription_events: scan: %w", err)
		}
		out = append(out, r)
	}
	return out, dbRows.Err()
}

// ---------------------------------------------------------------------------
// LLM usage — per-user list + system-wide aggregate
// ---------------------------------------------------------------------------

// AdminLLMUsageRow is one row of the per-user LLM usage list. Tier is
// pulled from billing_subscriptions (LEFT JOIN so users without a row
// still appear as the implicit 'free' tier — same default the
// SubscriptionStore.GetSubscription path uses).
type AdminLLMUsageRow struct {
	UserID             string     `json:"user_id"`
	Username           string     `json:"username"`
	Email              string     `json:"email"`
	Tier               string     `json:"tier"`
	Status             string     `json:"status"`
	InputTokensToday   int64      `json:"input_tokens_today"`
	OutputTokensToday  int64      `json:"output_tokens_today"`
	InputTokensMonth   int64      `json:"input_tokens_month"`
	OutputTokensMonth  int64      `json:"output_tokens_month"`
	BlockedToday       int        `json:"blocked_today"`
	BlockedMonth       int        `json:"blocked_month"`
	MonthlyWindowStart time.Time  `json:"monthly_window_start"`
	LastMeteredAt      *time.Time `json:"last_metered_at"`
	LLMTokensUsedTotal int64      `json:"llm_tokens_used_total"`
}

// ListLLMUsage paginates per-user LLM usage with optional search on
// username/email. The admin SPA renders this as a sortable table.
func (q *AdminQueries) ListLLMUsage(
	ctx context.Context, search string, p Page,
) (rows []AdminLLMUsageRow, total int64, err error) {
	limit, offset := p.normalize()

	where := []string{}
	args := []any{}
	next := func() string { return fmt.Sprintf("$%d", len(args)+1) }

	if s := strings.TrimSpace(search); s != "" {
		args = append(args, "%"+s+"%")
		p1 := next()
		args = append(args, "%"+s+"%")
		p2 := next()
		where = append(where, "(au.username ILIKE "+p1+" OR au.email ILIKE "+p2+")")
	}
	whereSQL := ""
	if len(where) > 0 {
		whereSQL = "WHERE " + strings.Join(where, " AND ")
	}

	// The auth_users base table is the truth: we want every active
	// user in the result set, even if they have not yet produced any
	// LLM usage rows (zeros are valid signal for admin triage).
	countSQL := `
		SELECT COUNT(*)
		FROM auth_users au
		LEFT JOIN billing_usage bu ON bu.user_id = au.id
		LEFT JOIN billing_subscriptions bs ON bs.user_id = au.id
		` + whereSQL
	if err := q.db.QueryRow(ctx, countSQL, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("admin_list_llm_usage: count: %w", err)
	}

	listSQL := `
		SELECT au.id, au.username, au.email,
		       COALESCE(bs.tier, 'free'),
		       COALESCE(bs.status, 'active'),
		       COALESCE(bu.llm_input_tokens_today, 0),
		       COALESCE(bu.llm_output_tokens_today, 0),
		       COALESCE(bu.llm_input_tokens_month, 0),
		       COALESCE(bu.llm_output_tokens_month, 0),
		       COALESCE(bu.llm_quota_blocked_count_today, 0),
		       COALESCE(bu.llm_quota_blocked_count_month, 0),
		       COALESCE(bu.monthly_window_start, NOW()),
		       bu.llm_last_metered_at,
		       COALESCE(bu.llm_tokens_used, 0)
		FROM auth_users au
		LEFT JOIN billing_usage bu ON bu.user_id = au.id
		LEFT JOIN billing_subscriptions bs ON bs.user_id = au.id
		` + whereSQL + `
		ORDER BY COALESCE(bu.llm_input_tokens_month, 0)
		       + COALESCE(bu.llm_output_tokens_month, 0) DESC,
		       au.username ASC
		LIMIT $` + fmt.Sprintf("%d", len(args)+1) +
		` OFFSET $` + fmt.Sprintf("%d", len(args)+2)
	args = append(args, limit, offset)

	dbRows, err := q.db.Query(ctx, listSQL, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("admin_list_llm_usage: query: %w", err)
	}
	defer dbRows.Close()

	rows = make([]AdminLLMUsageRow, 0, limit)
	for dbRows.Next() {
		var r AdminLLMUsageRow
		if err := dbRows.Scan(
			&r.UserID, &r.Username, &r.Email,
			&r.Tier, &r.Status,
			&r.InputTokensToday, &r.OutputTokensToday,
			&r.InputTokensMonth, &r.OutputTokensMonth,
			&r.BlockedToday, &r.BlockedMonth,
			&r.MonthlyWindowStart, &r.LastMeteredAt,
			&r.LLMTokensUsedTotal,
		); err != nil {
			return nil, 0, fmt.Errorf("admin_list_llm_usage: scan: %w", err)
		}
		rows = append(rows, r)
	}
	return rows, total, dbRows.Err()
}

// AdminLLMAggregate is the system-wide LLM rollup. Used by the admin
// dashboard's headline tiles.
type AdminLLMAggregate struct {
	InputTokensToday  int64 `json:"input_tokens_today"`
	OutputTokensToday int64 `json:"output_tokens_today"`
	InputTokensMonth  int64 `json:"input_tokens_month"`
	OutputTokensMonth int64 `json:"output_tokens_month"`
	BlockedMonth      int64 `json:"blocked_month"`
	ActiveUsersMonth  int64 `json:"active_users_month"`
	HeldReservations  int64 `json:"held_reservations"`
	TotalReservations int64 `json:"total_reservations"`
}

// AggregateLLMUsage returns the system-wide totals. Active users this
// month = anyone whose monthly counters are non-zero.
func (q *AdminQueries) AggregateLLMUsage(ctx context.Context) (*AdminLLMAggregate, error) {
	var agg AdminLLMAggregate
	err := q.db.QueryRow(ctx, `
		SELECT
		  COALESCE(SUM(llm_input_tokens_today), 0),
		  COALESCE(SUM(llm_output_tokens_today), 0),
		  COALESCE(SUM(llm_input_tokens_month), 0),
		  COALESCE(SUM(llm_output_tokens_month), 0),
		  COALESCE(SUM(llm_quota_blocked_count_month), 0),
		  COUNT(*) FILTER (
		    WHERE llm_input_tokens_month > 0
		       OR llm_output_tokens_month > 0
		  )
		FROM billing_usage
	`).Scan(
		&agg.InputTokensToday, &agg.OutputTokensToday,
		&agg.InputTokensMonth, &agg.OutputTokensMonth,
		&agg.BlockedMonth, &agg.ActiveUsersMonth,
	)
	if err != nil {
		return nil, fmt.Errorf("admin_aggregate_llm_usage: usage: %w", err)
	}

	err = q.db.QueryRow(ctx, `
		SELECT
		  COUNT(*) FILTER (WHERE status = 'held'),
		  COUNT(*)
		FROM billing_llm_reservations
	`).Scan(&agg.HeldReservations, &agg.TotalReservations)
	if err != nil {
		return nil, fmt.Errorf("admin_aggregate_llm_usage: reservations: %w", err)
	}
	return &agg, nil
}
