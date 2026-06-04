package server

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/rs/zerolog"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/analytics"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/monitoring"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// JournalStore defines the database operations required by the gRPC server.
// All query methods are scoped by userID for multi-tenant data isolation.
type JournalStore interface {
	InsertTrade(ctx context.Context, t *journal.TradeRecord) error
	GetTradeByBrokerOrderID(ctx context.Context, userID, brokerOrderID string) (*journal.TradeRecord, error)
	GetClosedTrades(ctx context.Context, userID string, limit, offset int, symbolFilter, styleFilter string) ([]*journal.TradeRecord, int, error)
	GetManualClosedTrades(ctx context.Context, userID string, since, until time.Time, limit, offset int) ([]*journal.TradeRecord, int, error)
}

// TradeMonitor defines the active trade tracking operations required by the gRPC server.
//
// Two refresh entry points exist on purpose:
//   - RefreshUserTradeIdentity is the canonical path used when *auth.Claims
//     is already in scope (e.g. RegisterFilledTrade): it overwrites the
//     full identity (UserID match, plus Username/Role/Tier/StatusJWT/AuthToken)
//     atomically under each Trade's write lock.
//   - RefreshUserTradeTokens is the lighter path used when only the raw
//     bearer token is available (e.g. GetManagedTrades pulling the token
//     out of auth.RawTokenFromContext). It internally parses the local-mint
//     JWT to recover the claims and delegates to RefreshUserTradeIdentity.
//
// Implementations MUST keep the two methods consistent: a call to either
// must converge on the same in-memory state for the matching trades.
type TradeMonitor interface {
	RegisterTrade(t *types.Trade)
	GetAllTrades() []*types.Trade
	TradeCount() int
	RefreshUserTradeIdentity(claims *auth.Claims, newToken string) int
	RefreshUserTradeTokens(userID, newToken string) int
}

// MetricsCalculator defines the performance analytics operations required by the gRPC server.
// Calculate is scoped by userID for multi-tenant data isolation.
type MetricsCalculator interface {
	Calculate(ctx context.Context, userID, period string) (*analytics.PerformanceSummary, error)
}

// ManagementServer implements the ManagementService gRPC contract.
type ManagementServer struct {
	managementv1.UnimplementedManagementServiceServer
	monitor TradeMonitor
	journal JournalStore
	metrics MetricsCalculator
	log     zerolog.Logger
}

// NewManagementServer creates the gRPC server implementation.
func NewManagementServer(
	monitor TradeMonitor,
	journal JournalStore,
	metrics MetricsCalculator,
) *ManagementServer {
	return &ManagementServer{
		monitor: monitor,
		journal: journal,
		metrics: metrics,
		log:     observability.Logger("grpc_server"),
	}
}

// RegisterFilledTrade is called by the Gateway when a trade is filled.
// This is Step 7 of the architecture \u2014 full ownership transfer.
func (s *ManagementServer) RegisterFilledTrade(ctx context.Context, req *managementv1.RegisterFilledTradeRequest) (*managementv1.RegisterFilledTradeResponse, error) {
	// Defense-in-depth tier check: trade management (watchers, trailing stops,
	// breakeven moves) is a Pro feature. Free-tier callers are rejected here
	// even if they somehow bypass the gateway perimeter.
	claims := auth.ClaimsFromContext(ctx)
	if claims == nil {
		return nil, status.Errorf(codes.Unauthenticated, "missing claims in context")
	}
	userID := claims.UserID
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}
	if claims.Role != auth.RoleAdmin && claims.Tier == "free" {
		return nil, status.Errorf(codes.PermissionDenied,
			"trade management is restricted to Pro users")
	}

	// Validate required fields.
	if req.GetSymbol() == "" || req.GetBrokerOrderId() == "" {
		return nil, status.Errorf(codes.InvalidArgument, "symbol and broker_order_id are required")
	}
	if req.GetFillPrice() <= 0 {
		return nil, status.Errorf(codes.InvalidArgument, "fill_price must be positive")
	}
	if req.GetStopLoss() <= 0 {
		return nil, status.Errorf(codes.InvalidArgument, "stop_loss must be positive")
	}
	if req.GetLotSize() <= 0 {
		return nil, status.Errorf(codes.InvalidArgument, "lot_size must be positive")
	}

	// Idempotency check: see if we already registered this MT5 ticket for this user.
	existingTrade, err := s.journal.GetTradeByBrokerOrderID(ctx, userID, req.GetBrokerOrderId())
	if err == nil && existingTrade != nil {
		s.log.Info().
			Str("broker_order_id", req.GetBrokerOrderId()).
			Str("trade_id", existingTrade.TradeID).
			Str("user_id", userID).
			Msg("trade_already_registered_idempotent_return")

		return &managementv1.RegisterFilledTradeResponse{
			Success: true,
			TradeId: existingTrade.TradeID,
			Message: "Trade already registered (idempotent). Monitoring active.",
		}, nil
	}

	tradeID := monitoring.GenerateTradeID()

	// Capture the raw JWT token from the request context so the monitoring
	// worker goroutine can make authenticated downstream calls.
	authToken := auth.RawTokenFromContext(ctx)

	s.log.Info().
		Str("trade_id", tradeID).
		Str("user_id", userID).
		Str("symbol", req.GetSymbol()).
		Str("direction", req.GetDirection()).
		Str("broker_order_id", req.GetBrokerOrderId()).
		Float64("fill_price", req.GetFillPrice()).
		Float64("stop_loss", req.GetStopLoss()).
		Float64("lot_size", req.GetLotSize()).
		Str("style", req.GetTradingStyle()).
		Str("analysis_id", req.GetAnalysisId()).
		Str("trace_id", req.GetTraceId()).
		Msg("register_filled_trade_received")

	// Build the in-memory trade object.
	// Identity fields are stamped here, at the trust boundary; the
	// monitoring worker reads them via Trade.IdentityCtx and never
	// re-parses the JWT.
	trade := &types.Trade{
		TradeID:          tradeID,
		Symbol:           req.GetSymbol(),
		Point:            req.GetPoint(),
		Digits:           int(req.GetDigits()),
		Direction:        constants.Direction(req.GetDirection()),
		BrokerOrderID:    req.GetBrokerOrderId(),
		AnalysisID:       req.GetAnalysisId(),
		TraceID:          req.GetTraceId(),
		UserID:           userID,
		Username:         claims.Username,
		Role:             string(claims.Role),
		Tier:             claims.Tier,
		StatusJWT:        claims.Status,
		AuthToken:        authToken,
		TradingStyle:     constants.TradingStyle(req.GetTradingStyle()),
		Grade:            req.GetGrade(),
		Session:          req.GetSession(),
		SetupType:        req.GetSetupType(),
		ExecutionMode:    req.GetExecutionMode(),
		ConfluenceScore:  req.GetConfluenceScore(),
		// System-executed trade (gateway -> execution -> here).
		Origin:           journal.OriginSystem,
		EntryPrice:       req.GetFillPrice(),
		StopLoss:         req.GetStopLoss(),
		InitialSL:        req.GetStopLoss(),
		TP1Price:         req.GetTp1Price(),
		TP1Pct:           req.GetTp1Pct(),
		TP2Price:         req.GetTp2Price(),
		TP2Pct:           req.GetTp2Pct(),
		TP3Price:         req.GetTp3Price(),
		TP3Pct:           req.GetTp3Pct(),
		TotalLotSize:     req.GetLotSize(),
		RemainingLotSize: req.GetLotSize(),
		RiskAmount:       req.GetRiskAmount(),
		RiskPercent:      req.GetRiskPercent(),
		RRRatio:          req.GetRrRatio(),
		Slippage:         req.GetSlippage(),
		Status:           constants.StatusActive,
		OpenedAt:         time.Now().UTC(),
	}

	// Persist to journal.
	if err := s.journal.InsertTrade(ctx, &journal.TradeRecord{
		UserID:          userID,
		TradeID:         tradeID,
		Symbol:          trade.Symbol,
		Direction:       string(trade.Direction),
		EntryPrice:      trade.EntryPrice,
		StopLoss:        trade.StopLoss,
		InitialSL:       trade.InitialSL,
		TP1Price:        trade.TP1Price,
		TP1Pct:          trade.TP1Pct,
		TP2Price:        trade.TP2Price,
		TP2Pct:          trade.TP2Pct,
		TP3Price:        trade.TP3Price,
		TP3Pct:          trade.TP3Pct,
		TotalLotSize:     trade.TotalLotSize,
		RemainingLotSize: trade.RemainingLotSize,
		Point:           trade.Point,
		Digits:          trade.Digits,
		RRRatio:         trade.RRRatio,
		RiskAmount:      trade.RiskAmount,
		RiskPercent:     trade.RiskPercent,
		ConfluenceScore: trade.ConfluenceScore,
		Grade:           trade.Grade,
		SetupType:       trade.SetupType,
		TradingStyle:    string(trade.TradingStyle),
		Session:         trade.Session,
		ExecutionMode:   trade.ExecutionMode,
		Slippage:        trade.Slippage,
		Origin:          trade.Origin,
		Status:          string(trade.Status),
		AnalysisID:      trade.AnalysisID,
		BrokerOrderID:   trade.BrokerOrderID,
		OpenedAt:        trade.OpenedAt,
	}); err != nil {
		s.log.Error().Err(err).Str("trade_id", tradeID).Str("user_id", userID).Msg("journal_insert_failed")
		return nil, status.Errorf(codes.Internal, "journal insert failed: %v", err)
	}

	// Register with monitoring manager \u2014 spawns the worker goroutine.
	s.monitor.RegisterTrade(trade)

	// Refresh identity (tier, status, username) AND token on every
	// active trade owned by this user. Critical for the post-restart
	// path (restored trades have empty AuthTokens) and after a tier
	// change mid-session so that in-memory claims track the JWT.
	s.monitor.RefreshUserTradeIdentity(claims, authToken)

	observability.TradeRegisteredTotal.WithLabelValues(trade.Symbol, string(trade.TradingStyle)).Inc()

	s.log.Info().
		Str("trade_id", tradeID).
		Str("user_id", userID).
		Str("symbol", trade.Symbol).
		Msg("trade_registered_and_monitoring_started")

	return &managementv1.RegisterFilledTradeResponse{
		Success: true,
		TradeId: tradeID,
		Message: fmt.Sprintf("Trade %s registered. Monitoring active.", tradeID),
	}, nil
}

// UpdateTradeStatus receives trade event updates.
func (s *ManagementServer) UpdateTradeStatus(ctx context.Context, req *managementv1.UpdateTradeStatusRequest) (*managementv1.UpdateTradeStatusResponse, error) {
	claims := auth.ClaimsFromContext(ctx)
	if claims == nil {
		return nil, status.Errorf(codes.Unauthenticated, "missing claims in context")
	}
	userID := claims.UserID
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}
	if claims.Role != auth.RoleAdmin && claims.Tier == "free" {
		return nil, status.Errorf(codes.PermissionDenied,
			"trade management is restricted to Pro users")
	}

	s.log.Info().
		Str("trade_id", req.GetTradeId()).
		Str("event", req.GetEventType()).
		Str("user_id", userID).
		Msg("trade_status_update_received")

	return &managementv1.UpdateTradeStatusResponse{Success: true}, nil
}

// GetManagedTrades returns all actively managed trades for the authenticated user.
func (s *ManagementServer) GetManagedTrades(ctx context.Context, _ *managementv1.GetManagedTradesRequest) (*managementv1.GetManagedTradesResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}

	// Refresh auth tokens on all of this user's trades. This is critical
	// after a service restart: restored trades have empty AuthTokens and
	// the user's first authenticated call refreshes them all.
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		s.monitor.RefreshUserTradeTokens(userID, rawToken)
	}

	trades := s.monitor.GetAllTrades()

	pbTrades := make([]*managementv1.ManagedTrade, 0, len(trades))
	for _, t := range trades {
		t.RLock()
		// Only return trades owned by the authenticated user.
		if t.UserID != userID {
			t.RUnlock()
			continue
		}
		pbTrades = append(pbTrades, &managementv1.ManagedTrade{
			TradeId:          t.TradeID,
			Symbol:           t.Symbol,
			Direction:        string(t.Direction),
			EntryPrice:       t.EntryPrice,
			CurrentPrice:     t.CurrentPrice,
			StopLoss:         t.StopLoss,
			Tp1Price:         t.TP1Price,
			Tp2Price:         t.TP2Price,
			Tp3Price:         t.TP3Price,
			TotalLotSize:     t.TotalLotSize,
			RemainingLotSize: t.RemainingLotSize,
			UnrealizedPnl:    t.UnrealizedPnL,
			RealizedPnl:      t.RealizedPnL,
			TradingStyle:     string(t.TradingStyle),
			Status:           string(t.Status),
			BreakevenSet:     t.BreakevenSet,
			Tp1Hit:           t.TP1Hit,
			Tp2Hit:           t.TP2Hit,
			BrokerOrderId:    t.BrokerOrderID,
			AnalysisId:       t.AnalysisID,
			OpenedAt:         t.OpenedAt.Format(time.RFC3339),
		})
		t.RUnlock()
	}

	return &managementv1.GetManagedTradesResponse{Trades: pbTrades}, nil
}

// GetTradeJournal returns closed trade journal entries for the authenticated user.
func (s *ManagementServer) GetTradeJournal(ctx context.Context, req *managementv1.GetTradeJournalRequest) (*managementv1.GetTradeJournalResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}

	limit := int(req.GetLimit())
	if limit <= 0 {
		limit = 50
	}
	offset := int(req.GetOffset())

	trades, total, err := s.journal.GetClosedTrades(ctx, userID, limit, offset, req.GetSymbolFilter(), req.GetStyleFilter())
	if err != nil {
		return nil, status.Errorf(codes.Internal, "get closed trades: %v", err)
	}

	entries := make([]*managementv1.JournalEntry, 0, len(trades))
	for _, t := range trades {
		entry := &managementv1.JournalEntry{
			TradeId:           t.TradeID,
			Symbol:            t.Symbol,
			Direction:         t.Direction,
			EntryPrice:        t.EntryPrice,
			ExitPrice:         t.ExitPrice,
			StopLoss:          t.StopLoss,
			LotSize:           t.TotalLotSize,
			GrossPnl:          t.GrossPnL,
			RMultiple:         t.RMultiple,
			ConfluenceScore:   t.ConfluenceScore,
			Grade:             t.Grade,
			SetupType:         t.SetupType,
			TradingStyle:      t.TradingStyle,
			Outcome:           t.Outcome,
			OpenedAt:          t.OpenedAt.Format(time.RFC3339),
			DurationMinutes:   int32(t.DurationMinutes),
			SlAdjustmentCount: int32(t.SLAdjustments),
			PartialCloseCount: int32(t.PartialCloses),
			AnalysisId:        t.AnalysisID,
		}
		if t.ClosedAt != nil {
			entry.ClosedAt = t.ClosedAt.Format(time.RFC3339)
		}
		entries = append(entries, entry)
	}

	return &managementv1.GetTradeJournalResponse{
		Entries:    entries,
		TotalCount: int32(total),
	}, nil
}

// GetPerformanceMetrics returns real-time analytics for the authenticated user.
func (s *ManagementServer) GetPerformanceMetrics(ctx context.Context, req *managementv1.GetPerformanceMetricsRequest) (*managementv1.GetPerformanceMetricsResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}

	period := req.GetPeriod()
	if period == "" {
		period = "ALL_TIME"
	}

	summary, err := s.metrics.Calculate(ctx, userID, period)
	if err != nil {
		return nil, status.Errorf(codes.Internal, "calculate metrics: %v", err)
	}

	return &managementv1.GetPerformanceMetricsResponse{
		WinRate:              summary.WinRate,
		AvgRMultiple:         summary.AvgRMultiple,
		Expectancy:           summary.Expectancy,
		TotalTrades:          int32(summary.TotalTrades),
		Wins:                 int32(summary.Wins),
		Losses:               int32(summary.Losses),
		Breakevens:           int32(summary.Breakevens),
		TotalPnl:             summary.TotalPnL,
		MaxConsecutiveWins:   int32(summary.MaxConsecutiveWins),
		MaxConsecutiveLosses: int32(summary.MaxConsecutiveLosses),
		MaxDrawdownPct:       summary.MaxDrawdownPct,
		BestTradeR:           summary.BestTradeR,
		WorstTradeR:          summary.WorstTradeR,
		WinRateBySymbol:      summary.WinRateBySymbol,
		WinRateByStyle:       summary.WinRateByStyle,
		WinRateBySetup:       summary.WinRateBySetup,
		WinRateBySession:     summary.WinRateBySession,
	}, nil
}

// GetManualJournal returns the user's manually-executed / reconciled
// trades (origin = MANUAL_RECONCILED) within a time window, both open
// and closed, for the 90-Day Trading Plan's Daily Execution Journal
// auto-populate. System trades and MANUAL_RESTORED history rows are
// excluded. Open trades carry is_open=true with blank close cells.
func (s *ManagementServer) GetManualJournal(ctx context.Context, req *managementv1.GetManualJournalRequest) (*managementv1.GetManualJournalResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}

	// Parse optional RFC3339 window bounds; empty = unbounded.
	var since, until time.Time
	if s := strings.TrimSpace(req.GetSinceRfc3339()); s != "" {
		t, err := time.Parse(time.RFC3339, s)
		if err != nil {
			return nil, status.Errorf(codes.InvalidArgument, "since_rfc3339 must be RFC3339: %v", err)
		}
		since = t
	}
	if u := strings.TrimSpace(req.GetUntilRfc3339()); u != "" {
		t, err := time.Parse(time.RFC3339, u)
		if err != nil {
			return nil, status.Errorf(codes.InvalidArgument, "until_rfc3339 must be RFC3339: %v", err)
		}
		until = t
	}

	entries := make([]*managementv1.ManualJournalEntry, 0)

	// OPEN manual trades from the live monitor (always returned in full).
	for _, t := range s.monitor.GetAllTrades() {
		t.RLock()
		if t.UserID != userID || t.Origin != journal.OriginManualReconciled || t.Status == constants.StatusClosed {
			t.RUnlock()
			continue
		}
		openedAt := t.OpenedAt
		// Apply the same window filter to open trades as the closed query.
		if (!since.IsZero() && openedAt.Before(since)) || (!until.IsZero() && openedAt.After(until)) {
			t.RUnlock()
			continue
		}
		entries = append(entries, &managementv1.ManualJournalEntry{
			TradeId:       t.TradeID,
			Symbol:        t.Symbol,
			Direction:     string(t.Direction),
			TradingStyle:  string(t.TradingStyle),
			SetupType:     t.SetupType,
			EntryPrice:    t.EntryPrice,
			StopLoss:      t.StopLoss,
			Tp1Price:      t.TP1Price,
			Tp2Price:      t.TP2Price,
			Tp3Price:      t.TP3Price,
			ExitPrice:     0,
			RiskPercent:   t.RiskPercent,
			TotalLotSize:  t.TotalLotSize,
			RrRatio:       t.RRRatio,
			RMultiple:     0,
			GrossPnl:      0,
			Outcome:       "",
			Session:       t.Session,
			IsOpen:        true,
			OpenedAt:      openedAt.Format(time.RFC3339),
			ClosedAt:      "",
			BrokerOrderId: t.BrokerOrderID,
		})
		t.RUnlock()
	}

	// CLOSED manual trades from the journal store (paginated window).
	closed, totalClosed, err := s.journal.GetManualClosedTrades(ctx, userID, since, until, int(req.GetLimit()), int(req.GetOffset()))
	if err != nil {
		return nil, status.Errorf(codes.Internal, "get manual closed trades: %v", err)
	}
	for _, t := range closed {
		closedAt := ""
		if t.ClosedAt != nil {
			closedAt = t.ClosedAt.Format(time.RFC3339)
		}
		entries = append(entries, &managementv1.ManualJournalEntry{
			TradeId:       t.TradeID,
			Symbol:        t.Symbol,
			Direction:     t.Direction,
			TradingStyle:  t.TradingStyle,
			SetupType:     t.SetupType,
			EntryPrice:    t.EntryPrice,
			StopLoss:      t.StopLoss,
			Tp1Price:      t.TP1Price,
			Tp2Price:      t.TP2Price,
			Tp3Price:      t.TP3Price,
			ExitPrice:     t.ExitPrice,
			RiskPercent:   t.RiskPercent,
			TotalLotSize:  t.TotalLotSize,
			RrRatio:       t.RRRatio,
			RMultiple:     t.RMultiple,
			GrossPnl:      t.GrossPnL,
			Outcome:       t.Outcome,
			Session:       t.Session,
			IsOpen:        false,
			OpenedAt:      t.OpenedAt.Format(time.RFC3339),
			ClosedAt:      closedAt,
			BrokerOrderId: t.BrokerOrderID,
		})
	}

	return &managementv1.GetManualJournalResponse{
		Entries:     entries,
		TotalClosed: int32(totalClosed),
	}, nil
}

// GetHealth returns the service health status.
func (s *ManagementServer) GetHealth(_ context.Context, _ *managementv1.GetHealthRequest) (*managementv1.GetHealthResponse, error) {
	return &managementv1.GetHealthResponse{
		Status:          "ok",
		DbConnected:     true,
		BrokerConnected: true,
		ActiveTrades:    int32(s.monitor.TradeCount()),
	}, nil
}
