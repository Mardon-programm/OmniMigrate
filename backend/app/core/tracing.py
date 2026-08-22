from __future__ import annotations

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import settings

logger = structlog.get_logger(__name__)

_tracer_provider: TracerProvider | None = None


def setup_tracing() -> None:
    """Initialize OpenTelemetry tracing.

    - If OTEL_EXPORTER_OTLP_ENDPOINT is set → export to collector via OTLP/gRPC.
    - Otherwise → console output (development) or no-op (production without collector).
    """
    global _tracer_provider

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.environment,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=True,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(
            "OTel tracing enabled",
            endpoint=settings.otel_exporter_otlp_endpoint,
        )
    elif settings.debug:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("OTel tracing enabled (console export)")

    trace.set_tracer_provider(provider)
    _tracer_provider = provider


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    if _tracer_provider:
        _tracer_provider.shutdown()
