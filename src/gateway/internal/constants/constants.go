package constants

// CyclePhase represents discrete phases within a single analysis cycle.
type CyclePhase string

const (
	PhaseInitializing     CyclePhase = "INITIALIZING"
	PhaseCollectingTA     CyclePhase = "COLLECTING_TA"
	PhaseCollectingMacro  CyclePhase = "COLLECTING_MACRO"
	PhaseCollectParallel  CyclePhase = "COLLECTING_PARALLEL"
	PhaseBuildingQuery    CyclePhase = "BUILDING_QUERY"
	PhaseRetrievingRAG    CyclePhase = "RETRIEVING_RAG"
	PhaseAssemblingCtx    CyclePhase = "ASSEMBLING_CONTEXT"
	PhaseProcessingLLM    CyclePhase = "PROCESSING_LLM"
	PhaseEvaluatingGuards CyclePhase = "EVALUATING_GUARDS"
	PhaseRoutingDecision  CyclePhase = "ROUTING_DECISION"
	PhaseCompleted        CyclePhase = "COMPLETED"
	PhaseFailed           CyclePhase = "FAILED"
)

func (p CyclePhase) String() string { return string(p) }

// CycleStatus represents the overall status of an analysis cycle.
type CycleStatus string

const (
	StatusRunning   CycleStatus = "RUNNING"
	StatusCompleted CycleStatus = "COMPLETED"
	StatusFailed    CycleStatus = "FAILED"
	StatusTimedOut  CycleStatus = "TIMED_OUT"
	StatusSkipped   CycleStatus = "SKIPPED"
)

func (s CycleStatus) String() string { return string(s) }

// CycleOutcome represents the final outcome after the processor LLM decision.
type CycleOutcome string

const (
	OutcomeTradeApproved    CycleOutcome = "TRADE_APPROVED"
	OutcomeNoSetup          CycleOutcome = "NO_SETUP"
	OutcomeRejectedByGuard  CycleOutcome = "REJECTED_BY_GUARD"
	OutcomeInsufficientData CycleOutcome = "INSUFFICIENT_DATA"
	OutcomeProcessorError   CycleOutcome = "PROCESSOR_ERROR"
	OutcomePipelineError    CycleOutcome = "PIPELINE_ERROR"
)

func (o CycleOutcome) String() string { return string(o) }

// PipelineStage identifies which service produced an error or metric.
type PipelineStage string

const (
	StageTACollector     PipelineStage = "ta_collector"
	StageMacroCollector  PipelineStage = "macro_collector"
	StageQueryBuilder    PipelineStage = "query_builder"
	StageRAGRetrieval    PipelineStage = "rag_retrieval"
	StageContextAssembly PipelineStage = "context_assembly"
	StageProcessorLLM    PipelineStage = "processor_llm"
	StageGuardEvaluation PipelineStage = "guard_evaluation"
	StageDecisionRouting PipelineStage = "decision_routing"
)

func (s PipelineStage) String() string { return string(s) }

// GuardVerdict represents the result of a single guard check.
type GuardVerdict string

const (
	VerdictPass   GuardVerdict = "PASS"
	VerdictReject GuardVerdict = "REJECT"
	VerdictWarn   GuardVerdict = "WARN"
)

func (v GuardVerdict) String() string { return string(v) }

// GuardRule identifies hard rejection rules evaluated after the processor.
type GuardRule string

const (
	RuleNewsProximity        GuardRule = "MR-REJECT-001"
	RuleSessionRestriction   GuardRule = "MR-REJECT-002"
	RuleDailyLossLimit       GuardRule = "MR-REJECT-003"
	RuleSpreadTooWide        GuardRule = "MR-REJECT-004"
	RuleCorrelationLimit     GuardRule = "MR-REJECT-005"
	RuleCounterTrendNoChoch  GuardRule = "MR-REJECT-006"
	RuleMaxConcurrentTrades  GuardRule = "MR-REJECT-007"
	RuleWeekendGapRisk       GuardRule = "MR-REJECT-008"
	RuleLowLiquidityHours    GuardRule = "MR-REJECT-009"
	RuleDrawdownCircuitBreak GuardRule = "MR-REJECT-010"
)

func (r GuardRule) String() string { return string(r) }

// Scheduler job identifiers.
const (
	GatewayCycleJobID  = "gateway_analysis_cycle"
	GatewayHealthJobID = "gateway_health_check"
)

// Cache namespaces and key prefixes.
const (
	GatewayCacheNamespace    = "gateway"
	TAResultCacheKeyPrefix   = "ta_result"
	MacroResultCacheKeyPrefix = "macro_result"
)

// NewsLockoutMinutes is the lockout window before high-impact news events.
// Matches engine.shared.models.events.NEWS_LOCKOUT_MINUTES.
const NewsLockoutMinutes = 30
