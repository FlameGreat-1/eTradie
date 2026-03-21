package watcher

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	gatewayv1 "github.com/flamegreat-1/etradie/proto/gateway/v1"
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

// ConfirmSetup calls the Gateway's ConfirmSetup RPC.
func (g *GatewayGRPCClient) ConfirmSetup(ctx context.Context, symbol, analysisID, traceID string) (*ConfirmResult, error) {
	callCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	resp, err := g.client.ConfirmSetup(callCtx, &gatewayv1.ConfirmSetupRequest{
		Symbol:     symbol,
		AnalysisId: analysisID,
		TraceId:    traceID,
	})
	if err != nil {
		return nil, fmt.Errorf("gateway confirm setup: %w", err)
	}

	return &ConfirmResult{
		Confirmed:       resp.GetConfirmed(),
		LTFConfirmation: resp.GetLtfConfirmation(),
		Reason:          resp.GetReason(),
	}, nil
}

// NotifyExecutionCompleted informs the Gateway that an instant order was filled.
// Sends the complete Order context so the Gateway can forward everything to Module C.
func (g *GatewayGRPCClient) NotifyExecutionCompleted(ctx context.Context, order *models.Order, brokerOrderID string, fillPrice, slippage float64) error {
	callCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

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
