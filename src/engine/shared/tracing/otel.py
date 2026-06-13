from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)

from engine.shared.exceptions import TracingError, TracingValidationError
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import TRACING_SPANS_CREATED, TRACING_SPANS_ERRORS

if TYPE_CHECKING:
    from opentelemetry.trace import Span, Tracer

logger = get_logger(__name__)

_tracer: Tracer | None = None
_provider: TracerProvider | None = None


def _validate_service_name(service_name: str) -> None:
    if not service_name or not service_name.strip():
        raise TracingValidationError("Service name cannot be empty")

    if len(service_name) > 256:
        raise TracingValidationError("Service name exceeds maximum length of 256")


def _validate_otlp_endpoint(endpoint: str) -> None:
    """Validate an OTLP endpoint string.

    Accepts the canonical OTLP gRPC form documented in .env.example:

        host:port            e.g. jaeger:4317

    Also accepts a full URL for back-compat with operators who
    supplied http(s) endpoints:

        scheme://host[:port] e.g. http://otel-collector:4317

    urlparse() treats 'jaeger:4317' as scheme='jaeger', path='4317'
    (parsed.hostname is None) which used to break the documented
    format. We now detect the bare host:port shape explicitly before
    falling back to urlparse() for full URLs.
    """
    if not endpoint or not endpoint.strip():
        raise TracingValidationError("OTLP endpoint cannot be empty")

    value = endpoint.strip()

    # Bare host:port (no scheme) -- the documented canonical form.
    if "://" not in value:
        host_part, _, port_part = value.partition(":")
        if not host_part:
            raise TracingValidationError(f"Invalid OTLP endpoint: missing host in {endpoint!r}")
        if port_part:
            if not port_part.isdigit():
                raise TracingValidationError(f"Invalid OTLP endpoint: non-numeric port in {endpoint!r}")
            port_num = int(port_part)
            if not (1 <= port_num <= 65535):
                raise TracingValidationError(f"Invalid OTLP endpoint: port out of range in {endpoint!r}")
        return

    # Full scheme://host[:port] URL form.
    try:
        parsed = urlparse(value)
        if not parsed.hostname:
            raise ValueError("Missing hostname")
    except Exception as e:
        raise TracingValidationError(f"Invalid OTLP endpoint: {e}") from e


def init_tracing(
    *,
    service_name: str,
    otlp_endpoint: str,
    insecure: bool = False,
    batch_export_timeout_ms: int = 30000,
    max_export_batch_size: int = 512,
) -> None:
    global _tracer, _provider

    _validate_service_name(service_name)
    _validate_otlp_endpoint(otlp_endpoint)

    try:
        resource = Resource.create({"service.name": service_name})
        _provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=insecure,
            timeout=batch_export_timeout_ms // 1000,
        )

        processor = BatchSpanProcessor(
            exporter,
            max_export_batch_size=max_export_batch_size,
            export_timeout_millis=batch_export_timeout_ms,
        )

        _provider.add_span_processor(processor)
        trace.set_tracer_provider(_provider)

        # W3C Trace Context propagator so the FastAPI server
        # instrumentation (engine.main.create_app) EXTRACTS the inbound
        # traceparent the gateway's engine HTTP client injects, and the
        # aiohttp client instrumentation below INJECTS it on every
        # outbound HTTP call (data providers, gateway metering). Without
        # a global propagator the engine would start a disconnected root
        # span per request. Matches the Go services' propagator.
        set_global_textmap(TraceContextTextMapPropagator())

        # Instrument the outbound aiohttp client so engine->provider and
        # engine->gateway HTTP calls carry the trace. Imported lazily so
        # the dependency is only touched on the tracing-enabled path.
        # ZeroMQ to mt-node is NOT instrumented (non-HTTP, opaque).
        from opentelemetry.instrumentation.aiohttp_client import (
            AioHttpClientInstrumentor,
        )

        AioHttpClientInstrumentor().instrument()

        _tracer = trace.get_tracer(service_name)

        logger.info(
            "tracing_initialized",
            extra={
                "service_name": service_name,
                "otlp_endpoint": otlp_endpoint,
                "insecure": insecure,
            },
        )

    except Exception as e:
        logger.error(
            "tracing_initialization_failed",
            extra={"error": str(e)},
        )
        raise TracingError(f"Failed to initialize tracing: {e}") from e


def get_tracer() -> Tracer:
    global _tracer

    if _tracer is None:
        logger.warning("tracer_not_initialized_using_noop")
        _tracer = trace.get_tracer("etradie-engine")

    return _tracer


@contextmanager
def create_span(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
    record_exception: bool = True,
) -> Iterator[Span]:
    tracer = get_tracer()

    with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
        try:
            TRACING_SPANS_CREATED.labels(span_name=name).inc()
            yield span

        except Exception as e:
            if record_exception:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))

            TRACING_SPANS_ERRORS.labels(
                span_name=name,
                error_type=type(e).__name__,
            ).inc()

            raise


def set_span_error(span: Span, error: Exception) -> None:
    span.record_exception(error)
    span.set_status(Status(StatusCode.ERROR, str(error)))


def shutdown_tracing(timeout_seconds: int = 30) -> None:
    global _provider

    try:
        if _provider is not None:
            _provider.shutdown()
            logger.info("tracing_shutdown_complete")
        else:
            logger.warning("tracing_provider_not_initialized")

    except Exception as e:
        logger.error(
            "tracing_shutdown_failed",
            extra={"error": str(e)},
        )
        raise TracingError(f"Failed to shutdown tracing: {e}") from e
