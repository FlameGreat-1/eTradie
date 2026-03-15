package infra

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/keepalive"

	"github.com/flamegreat/etradie/src/gateway/internal/observability"
)

// EngineClient manages the gRPC connection to the Python engine.
type EngineClient struct {
	Conn *grpc.ClientConn
	log  zerolog.Logger
}

// NewEngineClient dials the Python engine gRPC server.
func NewEngineClient(address string) (*EngineClient, error) {
	log := observability.Logger("grpc_client")

	conn, err := grpc.NewClient(
		address,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                30 * time.Second,
			Timeout:             10 * time.Second,
			PermitWithoutStream: true,
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("grpc_client: dial %s: %w", address, err)
	}

	log.Info().
		Str("address", address).
		Msg("engine_grpc_client_connected")

	return &EngineClient{Conn: conn, log: log}, nil
}

// HealthCheck checks the engine gRPC server health.
func (c *EngineClient) HealthCheck(ctx context.Context) bool {
	client := grpc_health_v1.NewHealthClient(c.Conn)

	checkCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	resp, err := client.Check(checkCtx, &grpc_health_v1.HealthCheckRequest{})
	if err != nil {
		c.log.Error().Err(err).Msg("engine_health_check_failed")
		return false
	}
	return resp.GetStatus() == grpc_health_v1.HealthCheckResponse_SERVING
}

// Close gracefully shuts down the gRPC connection.
func (c *EngineClient) Close() error {
	err := c.Conn.Close()
	if err != nil {
		c.log.Error().Err(err).Msg("engine_grpc_client_close_failed")
		return err
	}
	c.log.Info().Msg("engine_grpc_client_closed")
	return nil
}
