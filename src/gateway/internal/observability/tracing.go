package observability

import (
	"context"
	"fmt"
	"sync"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

var (
	tracer   trace.Tracer
	provider *sdktrace.TracerProvider
	initOnce sync.Once
)

// InitTracing initialises the OpenTelemetry trace pipeline.
// Must be called once at startup. The returned shutdown function
// must be called during graceful shutdown to flush pending spans.
//
// When otlpEndpoint is empty, tracing is treated as explicitly
// disabled: no OTLP dial is attempted, no exporter is constructed,
// and nil is returned for both values. Callers should treat a nil
// shutdown function as "tracing is off" and skip shutdown gracefully.
// This is the canonical opt-in pattern for telemetry: absent
// configuration means absent telemetry, not best-effort retries.
func InitTracing(ctx context.Context, serviceName, otlpEndpoint string) (func(context.Context) error, error) {
	if serviceName == "" {
		return nil, fmt.Errorf("tracing: service name cannot be empty")
	}
	if otlpEndpoint == "" {
		log := Logger("tracing")
		log.Info().
			Str("service_name", serviceName).
			Msg("tracing_disabled_no_otlp_endpoint_configured")
		return nil, nil
	}

	var initErr error
	var shutdownFn func(context.Context) error

	initOnce.Do(func() {
		conn, err := grpc.NewClient(
			otlpEndpoint,
			grpc.WithTransportCredentials(insecure.NewCredentials()),
		)
		if err != nil {
			initErr = fmt.Errorf("tracing: dial OTLP endpoint %s: %w", otlpEndpoint, err)
			return
		}

		exporter, err := otlptracegrpc.New(ctx, otlptracegrpc.WithGRPCConn(conn))
		if err != nil {
			initErr = fmt.Errorf("tracing: create exporter: %w", err)
			return
		}

		res, err := resource.New(ctx,
			resource.WithAttributes(semconv.ServiceNameKey.String(serviceName)),
		)
		if err != nil {
			initErr = fmt.Errorf("tracing: create resource: %w", err)
			return
		}

		provider = sdktrace.NewTracerProvider(
			sdktrace.WithBatcher(exporter,
				sdktrace.WithMaxExportBatchSize(512),
			),
			sdktrace.WithResource(res),
		)

		otel.SetTracerProvider(provider)
		// W3C Trace Context propagator: lets the gateway EXTRACT the
		// inbound traceparent (forwarded by Envoy/edge-ingress) so its
		// spans continue that trace, and INJECT traceparent on every
		// outbound hop (engine HTTP client, execution/management gRPC
		// client handlers). Without a global propagator set here, the
		// otelgrpc/HTTP instrumentation has nothing to carry context with
		// and each service would start a disconnected root span.
		otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
			propagation.TraceContext{},
			propagation.Baggage{},
		))
		tracer = provider.Tracer(serviceName)

		shutdownFn = provider.Shutdown

		log := Logger("tracing")
		log.Info().
			Str("service_name", serviceName).
			Str("otlp_endpoint", otlpEndpoint).
			Msg("tracing_initialized")
	})

	if initErr != nil {
		return nil, initErr
	}
	return shutdownFn, nil
}

// Tracer returns the global gateway tracer.
// Safe to call before InitTracing; returns a no-op tracer.
func Tracer() trace.Tracer {
	if tracer == nil {
		return otel.Tracer("etradie-gateway")
	}
	return tracer
}

// StartSpan creates a new span as a child of the context.
// Callers must call span.End() when the operation completes.
func StartSpan(ctx context.Context, name string, attrs ...attribute.KeyValue) (context.Context, trace.Span) {
	return Tracer().Start(ctx, name, trace.WithAttributes(attrs...))
}

// SetSpanError records an error on the span and sets its status to ERROR.
func SetSpanError(span trace.Span, err error) {
	span.RecordError(err)
	span.SetStatus(codes.Error, err.Error())
}
