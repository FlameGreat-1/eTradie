// Package performancereview implements the Exoper AI Weekly / Monthly
// Performance Review feature.
//
// PLAN.md anchors every design decision here:
//
//   - A structured, calm, institutional review of the user's trading
//     history over a fixed window (weekly = trailing 7 days, monthly
//     = trailing calendar month).
//   - 14 sections (Executive Summary, Performance Metrics, Behavioral
//     Analysis, System Adherence, Emotional Intelligence, Setup
//     Quality, Session Analysis, Risk Analysis, Improvement
//     Recommendations, Next Period Focus, Confidence & Data Quality,
//     Trader Evolution, Performance vs System Alignment, AI
//     Psychological Warnings).
//   - History is always preserved: every successful run writes a new
//     row keyed on (user_id, period, period_start) so the SPA can
//     plot trader evolution (PLAN.md section 12).
//
// Authority separation (must remain true):
//
//   Layer A - Trading System   : governs AI execution.
//   Layer B - Trading Plan     : governs human discipline.
//   Layer C - Performance Rvw  : observes and analyses execution.  <- this pkg
//
// The performance review NEVER mutates the trading system, the
// trading plan, or the journal. It is a read-only intelligence
// surface; the engine consumes journal data, produces a review, and
// the gateway persists it. Nothing else changes.
package performancereview

import "time"

// CurrentSchemaVersion is bumped any time a backwards-incompatible
// field is added or removed from Review. The frontend persists
// schema_version so a future migration can upgrade older payloads
// without losing user-visible history.
const CurrentSchemaVersion = 1

// ---------------------------------------------------------------------------
// Period - weekly vs monthly
// ---------------------------------------------------------------------------

// Period identifies the review cadence.
//
//   PeriodWeekly  - last 7 days ending at PeriodEnd (inclusive). Cron
//                   fires every Monday 06:00 UTC for the prior week.
//   PeriodMonthly - last calendar month ending at PeriodEnd. Cron
//                   fires on the 1st of every month 06:00 UTC for the
//                   prior month.
type Period string

const (
	PeriodWeekly  Period = "weekly"
	PeriodMonthly Period = "monthly"
)

// IsValid reports whether the value is a recognised period.
func (p Period) IsValid() bool {
	switch p {
	case PeriodWeekly, PeriodMonthly:
		return true
	}
	return false
}

// ---------------------------------------------------------------------------
// Status - lifecycle of a single review row
// ---------------------------------------------------------------------------

// Status is the lifecycle state of a review row.
//
//   StatusGenerating - the LLM call is in flight. The SPA polls and
//                      renders a friendly progress state.
//   StatusReady      - the review has been generated and validated.
//   StatusFailed     - the most recent attempt failed; LastError
//                      carries a user-safe message. The previous
//                      successful review (a different row keyed on
//                      an earlier period_start) is preserved.
type Status string

const (
	StatusGenerating Status = "generating"
	StatusReady      Status = "ready"
	StatusFailed     Status = "failed"
)

// IsValid reports whether the value is one of the recognised states.
func (s Status) IsValid() bool {
	switch s {
	case StatusGenerating, StatusReady, StatusFailed:
		return true
	}
	return false
}

// ---------------------------------------------------------------------------
// Confidence band
// ---------------------------------------------------------------------------

// ConfidenceBand is the deterministic confidence label the aggregator
// stamps on the input bundle and the LLM is required to honour
// (PLAN.md section 11).
//
// Thresholds (closed in-system trades in the window):
//
//   high           >= 20
//   medium         8..19
//   low            3..7
//   insufficient    < 3   - the LLM refuses analytics and emits the
//                           canonical 'not enough data' executive
//                           summary; behavioural sections are empty.
type ConfidenceBand string

const (
	ConfidenceHigh         ConfidenceBand = "high"
	ConfidenceMedium       ConfidenceBand = "medium"
	ConfidenceLow          ConfidenceBand = "low"
	ConfidenceInsufficient ConfidenceBand = "insufficient"
)

// IsValid reports whether the value is one of the recognised bands.
func (c ConfidenceBand) IsValid() bool {
	switch c {
	case ConfidenceHigh, ConfidenceMedium, ConfidenceLow, ConfidenceInsufficient:
		return true
	}
	return false
}

// ---------------------------------------------------------------------------
// Section 1 - Executive Summary
// ---------------------------------------------------------------------------

// ExecutiveSummary is PLAN.md section 1 - a short, professional,
// objective paragraph (no motivational language).
type ExecutiveSummary struct {
	Headline string `json:"headline"`           // 1-line title
	Narrative string `json:"narrative"`         // 2..5 sentences
}

// ---------------------------------------------------------------------------
// Section 2 - Performance Metrics (deterministic + LLM commentary)
// ---------------------------------------------------------------------------

// PerformanceMetrics is PLAN.md section 2. Values are strings so the
// gateway renders the AI-formatted display verbatim ("+4.2%", "1:2.8",
// "London") without lossy float-to-string coercions.
//
// The aggregator computes the raw numbers deterministically; the LLM
// is only responsible for formatting and choosing which extras to
// surface. This guarantees the metrics card never lies.
type PerformanceMetrics struct {
	TotalTrades         string `json:"total_trades"`
	WinRate             string `json:"win_rate"`
	AvgRR               string `json:"avg_rr"`
	NetPnL              string `json:"net_pnl"`
	BestSession         string `json:"best_session"`
	WorstSession        string `json:"worst_session"`
	MostProfitableSetup string `json:"most_profitable_setup"`
	WorstBehavior       string `json:"worst_behavior"`
}

// ---------------------------------------------------------------------------
// Section 3 - Behavioral Analysis
// ---------------------------------------------------------------------------

// BehavioralAnalysis is PLAN.md section 3 - free-form bullets the LLM
// extracts from the trade-level data (revenge tendencies, premature
// exits, overtrading on Fridays, etc.).
type BehavioralAnalysis struct {
	Patterns []string `json:"patterns"` // 3..10 bullets
}

// ---------------------------------------------------------------------------
// Section 4 - System Adherence Score
// ---------------------------------------------------------------------------

// AdherenceItem is one row of the rule-compliance table.
type AdherenceItem struct {
	Rule       string `json:"rule"`
	Compliance string `json:"compliance"` // "92%", "100%", "n/a"
}

// SystemAdherence is PLAN.md section 4.
type SystemAdherence struct {
	Items []AdherenceItem `json:"items"`
}

// ---------------------------------------------------------------------------
// Section 5 - Emotional Intelligence Analysis
// ---------------------------------------------------------------------------

// EmotionalIntelligence is PLAN.md section 5. A short narrative
// referencing emotion tags surfaced by the journal.
type EmotionalIntelligence struct {
	Narrative string `json:"narrative"`
}

// ---------------------------------------------------------------------------
// Section 6 - Setup Quality Analysis
// ---------------------------------------------------------------------------

// SetupQualityItem is one row of the per-setup performance table.
type SetupQualityItem struct {
	Setup   string `json:"setup"`
	WinRate string `json:"win_rate"`
	AvgRR   string `json:"avg_rr"`
}

// SetupQuality is PLAN.md section 6.
type SetupQuality struct {
	Items []SetupQualityItem `json:"items"`
}

// ---------------------------------------------------------------------------
// Section 7 - Session Analysis
// ---------------------------------------------------------------------------

// SessionItem is one row of the per-session performance table.
type SessionItem struct {
	Session     string `json:"session"`
	Performance string `json:"performance"`
}

// SessionAnalysis is PLAN.md section 7.
type SessionAnalysis struct {
	Items []SessionItem `json:"items"`
}

// ---------------------------------------------------------------------------
// Section 8 - Risk Analysis
// ---------------------------------------------------------------------------

// RiskAnalysis is PLAN.md section 8 - a short narrative on the user's
// risk discipline.
type RiskAnalysis struct {
	Narrative string `json:"narrative"`
}

// ---------------------------------------------------------------------------
// Section 9 - Improvement Recommendations
// ---------------------------------------------------------------------------

// ImprovementRecommendations is PLAN.md section 9.
type ImprovementRecommendations struct {
	Items []string `json:"items"`
}

// ---------------------------------------------------------------------------
// Section 10 - Next Period Focus Areas
// ---------------------------------------------------------------------------

// NextFocus is PLAN.md section 10.
type NextFocus struct {
	Items []string `json:"items"`
}

// ---------------------------------------------------------------------------
// Section 11 - AI Confidence & Data Quality
// ---------------------------------------------------------------------------

// ConfidenceReport is PLAN.md section 11.
type ConfidenceReport struct {
	Band       ConfidenceBand `json:"band"`
	SampleSize int            `json:"sample_size"`
	Note       string         `json:"note"`
}

// ---------------------------------------------------------------------------
// Section 12 - Trader Evolution Tracking
// ---------------------------------------------------------------------------

// EvolutionDelta is one comparison row (e.g. "Risk discipline +18%").
type EvolutionDelta struct {
	Metric    string `json:"metric"`
	Direction string `json:"direction"` // "improved" | "declined" | "stable"
	Delta     string `json:"delta"`     // "+18%", "-0.3R", "flat"
}

// TraderEvolution is PLAN.md section 12. Items is empty on the user's
// very first review (nothing to compare against).
type TraderEvolution struct {
	Items []EvolutionDelta `json:"items"`
}

// ---------------------------------------------------------------------------
// Section 13 - Performance vs Trading System Alignment
// ---------------------------------------------------------------------------

// SystemAlignment is PLAN.md section 13 - the gap analysis between
// the user's defined operating framework and their observed
// behaviour.
type SystemAlignment struct {
	Narrative string   `json:"narrative"`
	Gaps      []string `json:"gaps"`
}

// ---------------------------------------------------------------------------
// Section 14 - AI Psychological Warnings
// ---------------------------------------------------------------------------

// PsychologicalWarning is one detected risk signal.
type PsychologicalWarning struct {
	Signal      string `json:"signal"`
	Severity    string `json:"severity"` // "info" | "warning" | "critical"
	Explanation string `json:"explanation"`
}

// PsychologicalWarnings is PLAN.md section 14.
type PsychologicalWarnings struct {
	Items []PsychologicalWarning `json:"items"`
}

// ---------------------------------------------------------------------------
// Review - the persisted 14-section payload
// ---------------------------------------------------------------------------

// Review is the canonical wire shape returned to the SPA and
// persisted as JSONB. Adding a field requires bumping
// CurrentSchemaVersion so older clients can warn or upgrade.
type Review struct {
	SchemaVersion int `json:"schema_version"`

	// The 14 PLAN.md sections in declaration order so the SPA can
	// iterate over them without a switch statement.
	ExecutiveSummary           ExecutiveSummary           `json:"executive_summary"`
	PerformanceMetrics         PerformanceMetrics         `json:"performance_metrics"`
	BehavioralAnalysis         BehavioralAnalysis         `json:"behavioral_analysis"`
	SystemAdherence            SystemAdherence            `json:"system_adherence"`
	EmotionalIntelligence      EmotionalIntelligence      `json:"emotional_intelligence"`
	SetupQuality               SetupQuality               `json:"setup_quality"`
	SessionAnalysis            SessionAnalysis            `json:"session_analysis"`
	RiskAnalysis               RiskAnalysis               `json:"risk_analysis"`
	ImprovementRecommendations ImprovementRecommendations `json:"improvement_recommendations"`
	NextFocus                  NextFocus                  `json:"next_focus"`
	ConfidenceReport           ConfidenceReport           `json:"confidence_report"`
	TraderEvolution            TraderEvolution            `json:"trader_evolution"`
	SystemAlignment            SystemAlignment            `json:"system_alignment"`
	PsychologicalWarnings      PsychologicalWarnings      `json:"psychological_warnings"`

	// Footer metadata. period_start and period_end are inclusive,
	// UTC. profile_version is the trading-system version the LLM
	// observed at generation time (so a future audit can correlate
	// the review to the framework it was scored against).
	Period         Period    `json:"period"`
	PeriodStart    time.Time `json:"period_start"`
	PeriodEnd      time.Time `json:"period_end"`
	GeneratedAt    time.Time `json:"generated_at"`
	GeneratedBy    string    `json:"generated_by"`    // "Exoper AI"
	ProfileVersion int       `json:"profile_version"`

	// GenerationStartedAt is stamped by the engine at the moment
	// the LLM call is dispatched. The gateway uses it on callback
	// to record PerformanceReviewLLMCallDuration accurately.
	// Optional on the wire; when zero the metric is skipped rather
	// than reporting an inaccurate value.
	GenerationStartedAt time.Time `json:"generation_started_at,omitempty"`
}

// ---------------------------------------------------------------------------
// Record - one row in user_performance_reviews
// ---------------------------------------------------------------------------

// JournalMode identifies whether the performance review was generated
// using the System Journal (objective trades from management_trades)
// or the Manual Journal (the 26-column Daily Execution Journal from
// the Trading Plan that includes both auto-filled objective data AND
// the trader's subjective annotations).
type JournalMode string

const (
	JournalModeSystem JournalMode = "system"
	JournalModeManual JournalMode = "manual"
)

// IsValidJournalMode reports whether the value is a recognised mode.
func (m JournalMode) IsValid() bool {
	switch m {
	case JournalModeSystem, JournalModeManual:
		return true
	}
	return false
}

// Record is the gateway-side representation of one row. The primary
// key is (user_id, period, period_start) so every successful run is
// preserved; the SPA's history view paginates over them.
type Record struct {
	ID          int64       `json:"id"`
	UserID      string      `json:"user_id"`
	Period      Period      `json:"period"`
	PeriodStart time.Time   `json:"period_start"`
	PeriodEnd   time.Time   `json:"period_end"`
	Status      Status      `json:"status"`
	JournalMode JournalMode `json:"journal_mode"`
	Review      *Review     `json:"review,omitempty"`
	LastError   string      `json:"last_error,omitempty"`
	CreatedAt   time.Time   `json:"created_at"`
	UpdatedAt   time.Time   `json:"updated_at"`
}

// StatusView is the lightweight projection returned by the GET status
// endpoint. Same shape philosophy as tradingplan.StatusView.
type StatusView struct {
	Period      Period      `json:"period"`
	Status      Status      `json:"status"`
	JournalMode JournalMode `json:"journal_mode"`
	HasReview   bool        `json:"has_review"`
	PeriodStart *time.Time  `json:"period_start,omitempty"`
	PeriodEnd   *time.Time  `json:"period_end,omitempty"`
	LastError   string      `json:"last_error,omitempty"`
	UpdatedAt   *time.Time  `json:"updated_at,omitempty"`
}

// ---------------------------------------------------------------------------
// Generation inputs
// ---------------------------------------------------------------------------

// GenerationRequest is the typed input to the engine generator. The
// gateway marshals this once and posts it to the engine's internal
// dispatch endpoint. We deliberately pass profile_json and trades_json
// as raw bytes so the gateway does not need to import the journal or
// tradingsystem types here.
type GenerationRequest struct {
	UserID         string      `json:"user_id"`
	Period         Period      `json:"period"`
	PeriodStart    time.Time   `json:"period_start"`
	PeriodEnd      time.Time   `json:"period_end"`
	ProfileVersion int         `json:"profile_version"`
	JournalMode    JournalMode `json:"journal_mode"`
}

// History page caps. Performance reviews are small (~10-30 KB JSONB);
// 50 rows per page keeps the response under 1.5 MB on the worst-case
// path and is plenty for the SPA's infinite-scroll history view.
const (
	HistoryMaxLimit     = 50
	HistoryDefaultLimit = 20
)
