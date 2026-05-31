package watcher

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"

	gatewayv1 "github.com/flamegreat-1/etradie/proto/gateway/v1"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// GatewayGRPCClient implements GatewayPort by calling the Gateway's
// ConfirmSetup RPC over gRPC. This is the core implementation.
type GatewayGRPCClient struct {
	client gatewayv1.GatewayServiceClient
	conn   *grpc.ClientConn
}

// NewGatewayGRPCClient creates a gRPC connection to the Gateway
// service at the given address. The connection is lazy — it will
// connect on first use. Must call Close() on shutdown.
func NewGatewayGRPCClient(addr string) (*GatewayGRPCClient, error) {
	log := observability.Logger("gateway_client")

	conn, err := grpc.NewClient(addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(10*1024*1024)),
	)
	if err != nil {
		return nil, fmt.Errorf("gateway grpc client: dial %s: %w", addr, err)
	}

	log.Info().Str("addr", addr).Msg("gateway_grpc_client_connected")

	return &GatewayGRPCClient{
		client: gatewayv1.NewGatewayServiceClient(conn),
		conn:   conn,
	}, nil
}

// ConfirmSetupParams holds optional structural parameters for the
// lightweight LTF confirmation path, including HTF invalidation fields.
type ConfirmSetupParams struct {
	OBUpper      float64
	OBLower      float64
	LTFTimeframe string
	Direction    string
	EntryPrice   float64

	// HTF invalidation layer fields.
	StopLoss     float64 // The approved candidate's stop loss level
	HTFTimeframe string  // The HTF timeframe the OB was detected on (e.g. "H4")
}

// ConfirmSetup calls the Gateway's ConfirmSetup RPC.
func (g *GatewayGRPCClient) ConfirmSetup(ctx context.Context, symbol, analysisID, traceID string) (*ConfirmResult, error) {
	return g.ConfirmSetupWithParams(ctx, symbol, analysisID, traceID, nil)
}

// ConfirmSetupWithParams calls the Gateway's ConfirmSetup RPC with
// optional structural parameters for the lightweight LTF path.
func (g *GatewayGRPCClient) ConfirmSetupWithParams(ctx context.Context, symbol, analysisID, traceID string, params *ConfirmSetupParams) (*ConfirmResult, error) {
	callCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	// Forward JWT token from incoming context to outbound Gateway call.
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		callCtx = metadata.AppendToOutgoingContext(callCtx, "authorization", "Bearer "+rawToken)
	}

	req := &gatewayv1.ConfirmSetupRequest{
		Symbol:     symbol,
		AnalysisId: analysisID,
		TraceId:    traceID,
	}

	// Attach structural parameters for lightweight LTF confirmation
	if params != nil {
		req.ObUpper = params.OBUpper
		req.ObLower = params.OBLower
		req.LtfTimeframe = params.LTFTimeframe
		req.Direction = params.Direction
		req.EntryPrice = params.EntryPrice
		req.StopLoss = params.StopLoss
		req.HtfTimeframe = params.HTFTimeframe
	}

	resp, err := g.client.ConfirmSetup(callCtx, req)
	if err != nil {
		return nil, fmt.Errorf("gateway confirm setup: %w", err)
	}

	return &ConfirmResult{
		Confirmed:       resp.GetConfirmed(),
		LTFConfirmation: resp.GetLtfConfirmation(),
		Reason:          resp.GetReason(),
	}, nil
}

// CheckNewsWindow asks the Gateway whether a high-impact event affecting
// the symbol's currencies is imminent. Used by the watcher's LIMIT TTL
// loop to cancel a resting limit order before it fills into news.
func (g *GatewayGRPCClient) CheckNewsWindow(ctx context.Context, symbol, tradingStyle, traceID string) (*NewsWindowResult, error) {
	callCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	// Forward JWT token from incoming context to outbound Gateway call.
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		callCtx = metadata.AppendToOutgoingContext(callCtx, "authorization", "Bearer "+rawToken)
	}

	resp, err := g.client.CheckNewsWindow(callCtx, &gatewayv1.CheckNewsWindowRequest{
		Symbol:       symbol,
		TradingStyle: tradingStyle,
		TraceId:      traceID,
	})
	if err != nil {
		return nil, fmt.Errorf("gateway check news window: %w", err)
	}

	return &NewsWindowResult{
		Locked:        resp.GetLocked(),
		DataAvailable: resp.GetDataAvailable(),
		Reason:        resp.GetReason(),
		EventName:     resp.GetEventName(),
		Currency:      resp.GetCurrency(),
		MinutesUntil:  resp.GetMinutesUntil(),
	}, nil
}

// NotifyExecutionCompleted informs the Gateway that an instant order was filled.
// Sends the complete Order context so the Gateway can forward everything to Module C.
func (g *GatewayGRPCClient) NotifyExecutionCompleted(ctx context.Context, order *models.Order, brokerOrderID string, fillPrice, slippage float64) error {
	callCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	// Forward JWT token from incoming context to outbound Gateway call.
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		callCtx = metadata.AppendToOutgoingContext(callCtx, "authorization", "Bearer "+rawToken)
	}

	_, err := g.client.NotifyExecutionCompleted(callCtx, &gatewayv1.NotifyExecutionCompletedRequest{
		// Core fields.
		Symbol:        order.Symbol,
		BrokerOrderId: brokerOrderID,
		FillPrice:     fillPrice,
		Slippage:      slippage,
		LotSize:       order.LotSize,
		AnalysisId:    order.AnalysisID,
		TraceId:       order.WatcherID,

		// Full trade context for Module C handoff.
		Direction:       string(order.Direction),
		StopLoss:        order.StopLoss,
		Tp1Price:        order.TP1Price,
		Tp1Pct:          order.TP1Pct,
		Tp2Price:        order.TP2Price,
		Tp2Pct:          order.TP2Pct,
		Tp3Price:        order.TP3Price,
		Tp3Pct:          order.TP3Pct,
		RiskAmount:      order.RiskAmount,
		RiskPercent:     order.RiskPercent,
		RrRatio:         order.RRRatio,
		Grade:           order.Grade,
		TradingStyle:    string(order.TradingStyle),
		Session:         order.Session,
		ConfluenceScore: order.Confluence,
		ExecutionMode:   string(order.ExecutionMode),
		SetupType:       order.SetupType,
	})

	if err != nil {
		return fmt.Errorf("gateway notify execution: %w", err)
	}

	return nil
}

// Close closes the underlying gRPC connection.
func (g *GatewayGRPCClient) Close() error {
	if g.conn != nil {
		return g.conn.Close()
	}
	return nil
}
