package management

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	managementv1 "github.com/flamegreat/etradie/proto/management/v1"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
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

	resp, err := c.client.RegisterFilledTrade(callCtx, req)
	if err != nil {
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

// Close closes the underlying gRPC connection.
func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}
