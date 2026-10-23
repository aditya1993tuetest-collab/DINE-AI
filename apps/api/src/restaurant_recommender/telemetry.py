"""OpenTelemetry setup with privacy-safe defaults and optional OTLP export."""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from restaurant_recommender.config import Settings


def configure_telemetry(app: FastAPI, engine: Engine, settings: Settings) -> None:
    """Instrument HTTP and SQL without recording bodies, prompts, or SQL parameters."""

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:  # pragma: no cover - dependencies are mandatory in runtime images
        return

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": settings.telemetry_service_name,
                "deployment.environment": settings.app_env,
            }
        )
    )
    if settings.otel_exporter_otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        tracer_provider=provider,
        enable_commenter=False,
    )
