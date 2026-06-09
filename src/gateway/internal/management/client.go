package management

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/rs/zerolog"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	managementv1 "github.com/flamegreat-1/etradie/proto/management/v1"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/pkg/resilience"
)

// Client is the Gateway's gRPC client for Module C (Trade Management).
// Used exclusively by the NotifyExecutionCompleted handler to forward
// filled trade details to Module C for lifecycle management.
type Client struct {
	client    managementv1.ManagementServiceClient
	conn      *grpc.ClientConn
	timeoutMs int
	log       zerolog.Logger
}

// NewClient creates a gRPC connection to the Management service.
// The connection is lazy — it connects on first use.
func NewClient(addr string, timeoutMs int) (*Client, error) {
	log := observability.Logger("management_client")

	conn, err := grpc.NewClient(addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(10*1024*1024)),
		// Inject the W3C traceparent into outbound metadata so the
		// management server continues the gateway's trace. No-op when
		// tracing is disabled (global tracer is a no-op).
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
	)
	if err != nil {
		return nil, fmt.Errorf("management grpc client: dial %s: %w", addr, err)
	}

	log.Info().Str("addr", addr).Msg("management_grpc_client_connected")

	return &Client{
		client:    managementv1.NewManagementServiceClient(conn),
		conn:      conn,
		timeoutMs: timeoutMs,
		log:       log,
	}, nil
}

// RegisterFilledTrade sends the complete trade context to Module C
// for management lifecycle takeover. Called by the Gateway's
// NotifyExecutionCompleted handler.
func (c *Client) RegisterFilledTrade(ctx context.Context, req *managementv1.RegisterFilledTradeRequest) (string, error) {
	callCtx, cancel := context.WithTimeout(ctx, time.Duration(c.timeoutMs)*time.Millisecond)
	defer cancel()

	idempotencyKey := req.GetBrokerOrderId()
	if idempotencyKey == "" {
		idempotencyKey = uuid.New().String()
	}

	// Forward the JWT authorization header from the incoming Gateway
	// request to the outgoing Management gRPC call. gRPC incoming
	// metadata is NOT automatically copied to outgoing metadata.
	metadataKVs := []string{"x-idempotency-key", idempotencyKey}
	if rawToken := auth.RawTokenFromContext(callCtx); rawToken != "" {
		metadataKVs = append(metadataKVs, "authorization", "Bearer "+rawToken)
	}
	retryCtx := metadata.AppendToOutgoingContext(callCtx, metadataKVs...)

	var resp *managementv1.RegisterFilledTradeResponse
	operation := func() error {
		var err error
		resp, err = c.client.RegisterFilledTrade(retryCtx, req)
		return err
	}

	isRetryable := func(err error) bool {
		st, ok := status.FromError(err)
		if !ok {
			return false
		}
		return st.Code() == codes.Unavailable || st.Code() == codes.DeadlineExceeded || st.Code() == codes.Internal
	}

	if err := resilience.Retry(callCtx, resilience.DefaultRetryConfig, isRetryable, operation); err != nil {
		c.log.Error().Err(err).Str("broker_order_id", req.GetBrokerOrderId()).Msg("management_rpc_failed")
		return "", fmt.Errorf("management register trade: %w", err)
	}

	if !resp.GetSuccess() {
		return "", fmt.Errorf("management register trade: %s", resp.GetMessage())
	}

	c.log.Info().
		Str("trade_id", resp.GetTradeId()).
		Msg("trade_registered_with_module_c")

	return resp.GetTradeId(), nil
}

// GetManualJournal calls the management GetManualJournal RPC to fetch
// the authenticated user's manually-executed / reconciled trades
// (origin = MANUAL_RECONCILED) within a window, both open and closed.
// Powers the trading-plan Daily Execution Journal composite view.
//
// The caller's JWT is forwarded from the incoming context so the
// management auth interceptor resolves the same user (identical to the
// dashboard's other management reads). Retries on transient codes.
func (c *Client) GetManualJournal(
	ctx context.Context,
	req *managementv1.GetManualJournalRequest,
) (*managementv1.GetManualJournalResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, time.Duration(c.timeoutMs)*time.Millisecond)
	defer cancel()

	if rawToken := auth.RawTokenFromContext(callCtx); rawToken != "" {
		callCtx = metadata.AppendToOutgoingContext(callCtx, "authorization", "Bearer "+rawToken)
	}

	var resp *managementv1.GetManualJournalResponse
	operation := func() error {
		var err error
		resp, err = c.client.GetManualJournal(callCtx, req)
		return err
	}
	isRetryable := func(err error) bool {
		st, ok := status.FromError(err)
		if !ok {
			return false
		}
		return st.Code() == codes.Unavailable || st.Code() == codes.DeadlineExceeded
	}
	if err := resilience.Retry(callCtx, resilience.DefaultRetryConfig, isRetryable, operation); err != nil {
		return nil, fmt.Errorf("management get manual journal: %w", err)
	}
	return resp, nil
}

// Close closes the underlying gRPC connection.
func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}
