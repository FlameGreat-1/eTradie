"""OpenTelemetry distributed tracing setup.

Provides tracer initialisation and span-creation helpers.
Trace context is propagated through HTTP headers (W3C TraceContext)
and async context so that every operation in a pipeline cycle is
correlated end-to-end.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from opentelemetry.trace import Span, Tracer

_tracer: Tracer | None = None


def init_tracing(*, service_name: str, otlp_endpoint: str) -> None:
    """Initialise the OpenTelemetry tracer provider.

    Must be called exactly once during application startup.
    """
    global _tracer  # noqa: PLW0603

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)


def get_tracer() -> Tracer:
    """Return the application tracer — falls back to a no-op tracer if
    ``init_tracing`` has not been called.
    """
    global _tracer  # noqa: PLW0603
    if _tracer is None:
        _tracer = trace.get_tracer("etradie-engine")
    return _tracer


@contextmanager
def create_span(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Span]:
    """Context manager that creates and manages an OpenTelemetry span.

    Usage::

        with create_span("fetch_cot_data", attributes={"provider": "cftc"}) as span:
            result = await provider.fetch()
            span.set_attribute("items_count", len(result))
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
        yield span


def shutdown_tracing() -> None:
    """Flush and shut down the tracer provider gracefully."""
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()
