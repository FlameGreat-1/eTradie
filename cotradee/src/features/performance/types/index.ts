/**
 * Wire types for the Performance Review feature.
 *
 * These mirror src/performancereview/models.go field-for-field.
 * Adding a field on the Go side requires bumping the Go-side
 * CurrentSchemaVersion AND adding the same field here so the SPA
 * does not silently drop it.
 *
 * The 14 sections map 1:1 to the PLAN.md specification.
 */

export type PerformanceReviewPeriod = 'weekly' | 'monthly';

export type JournalMode = 'system' | 'manual';

export type PerformanceReviewStatus = 'generating' | 'ready' | 'failed' | 'none';

export type ConfidenceBand = 'high' | 'medium' | 'low' | 'insufficient';

export type WarningSeverity = 'info' | 'warning' | 'critical';

export type EvolutionDirection = 'improved' | 'declined' | 'stable';

// --- Section 1: Executive Summary -----------------------------------------

export interface ExecutiveSummary {
  headline: string;
  narrative: string;
}

// --- Section 2: Performance Metrics ---------------------------------------

export interface PerformanceMetrics {
  total_trades: string;
  win_rate: string;
  avg_rr: string;
  net_pnl: string;
  best_session: string;
  worst_session: string;
  most_profitable_setup: string;
  worst_behavior: string;
}

// --- Section 3: Behavioral Analysis ---------------------------------------

export interface BehavioralAnalysis {
  patterns: string[];
}

// --- Section 4: System Adherence ------------------------------------------

export interface AdherenceItem {
  rule: string;
  compliance: string;
}

export interface SystemAdherence {
  items: AdherenceItem[];
}

// --- Section 5: Emotional Intelligence ------------------------------------

export interface EmotionalIntelligence {
  narrative: string;
}

// --- Section 6: Setup Quality ---------------------------------------------

export interface SetupQualityItem {
  setup: string;
  win_rate: string;
  avg_rr: string;
}

export interface SetupQuality {
  items: SetupQualityItem[];
}

// --- Section 7: Session Analysis ------------------------------------------

export interface SessionItem {
  session: string;
  performance: string;
}

export interface SessionAnalysis {
  items: SessionItem[];
}

// --- Section 8: Risk Analysis ---------------------------------------------

export interface RiskAnalysis {
  narrative: string;
}

// --- Section 9: Improvement Recommendations -------------------------------

export interface ImprovementRecommendations {
  items: string[];
}

// --- Section 10: Next Period Focus ----------------------------------------

export interface NextFocus {
  items: string[];
}

// --- Section 11: Confidence Report ----------------------------------------

export interface ConfidenceReport {
  band: ConfidenceBand;
  sample_size: number;
  note: string;
}

// --- Section 12: Trader Evolution -----------------------------------------

export interface EvolutionDelta {
  metric: string;
  direction: EvolutionDirection;
  delta: string;
}

export interface TraderEvolution {
  items: EvolutionDelta[];
}

// --- Section 13: System Alignment -----------------------------------------

export interface SystemAlignment {
  narrative: string;
  gaps: string[];
}

// --- Section 14: Psychological Warnings -----------------------------------

export interface PsychologicalWarning {
  signal: string;
  severity: WarningSeverity;
  explanation: string;
}

export interface PsychologicalWarnings {
  items: PsychologicalWarning[];
}

// --- Full review payload --------------------------------------------------

export interface PerformanceReview {
  schema_version: number;
  executive_summary: ExecutiveSummary;
  performance_metrics: PerformanceMetrics;
  behavioral_analysis: BehavioralAnalysis;
  system_adherence: SystemAdherence;
  emotional_intelligence: EmotionalIntelligence;
  setup_quality: SetupQuality;
  session_analysis: SessionAnalysis;
  risk_analysis: RiskAnalysis;
  improvement_recommendations: ImprovementRecommendations;
  next_focus: NextFocus;
  confidence_report: ConfidenceReport;
  trader_evolution: TraderEvolution;
  system_alignment: SystemAlignment;
  psychological_warnings: PsychologicalWarnings;
  period: PerformanceReviewPeriod;
  period_start: string; // ISO 8601
  period_end: string;   // ISO 8601
  generated_at: string;
  generated_by: string;
  profile_version: number;
  generation_started_at?: string;
}

// --- Record / list shapes (what /latest, /:id, /history return) -----------

/**
 * Full record returned by GET /latest and GET /:id. status='none' is
 * a synthetic shape emitted by the gateway when the user has no row
 * at all yet; it has has_review=false and no period_start /
 * period_end / review fields.
 */
export interface PerformanceReviewRecord {
  id?: number;
  period?: PerformanceReviewPeriod;
  period_start?: string;
  period_end?: string;
  journal_mode?: JournalMode;
  status: PerformanceReviewStatus;
  has_review: boolean;
  review?: PerformanceReview | null;
  last_error?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * Lightweight row used in the history list. The review JSONB is NOT
 * hydrated by the gateway list endpoint to keep the payload small;
 * the SPA fetches the full review on click via GET /:id.
 */
export interface PerformanceReviewHistoryRow {
  id: number;
  period: PerformanceReviewPeriod;
  period_start: string;
  period_end: string;
  journal_mode: JournalMode;
  status: PerformanceReviewStatus;
  last_error?: string;
  created_at: string;
  updated_at: string;
}

export interface PerformanceReviewHistoryPage {
  items: PerformanceReviewHistoryRow[];
  total: number;
  offset: number;
  limit: number;
}

/**
 * Response shape of POST /generate. The status is always
 * 'generating' on a successful 202; the SPA flips to polling the
 * /latest endpoint until the row transitions to 'ready' or 'failed'.
 */
export interface PerformanceReviewGenerateResponse {
  status: PerformanceReviewStatus;
  period: PerformanceReviewPeriod;
  period_start: string;
  period_end: string;
  journal_mode: JournalMode;
  message: string;
}
