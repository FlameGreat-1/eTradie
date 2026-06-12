package server

import (
	"context"

	"github.com/rs/zerolog"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// PanicRecoveryInterceptor returns a unary server interceptor that
// recovers any panic raised by a downstream handler, logs it with the
// failing method for post-mortem analysis, and returns a generic
// codes.Internal error to the caller. Without it a single panicking
// RPC would unwind the serving goroutine and take the process down.
//
// Place this FIRST in the interceptor chain so it wraps every other
// interceptor and the handler itself.
func PanicRecoveryInterceptor(log zerolog.Logger) grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req interface{},
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (resp interface{}, err error) {
		defer func() {
			if r := recover(); r != nil {
				observability.LogPanicRecovery(log, r, info.FullMethod)
				err = status.Errorf(codes.Internal, "internal server error")
			}
		}()
		return handler(ctx, req)
	}
}
