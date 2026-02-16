"""TracerProvider + MeterProvider setup for Axiom via OpenTelemetry."""

from __future__ import annotations

import socket
import logging
import uuid as _uuid

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

from ..config.telemetry import (
    AXIOM_DATASET,
    CLOUD_PLATFORM,
    AXIOM_API_TOKEN,
    AXIOM_ENVIRONMENT,
    OTEL_SERVICE_NAME,
    AXIOM_TRACES_ENDPOINT,
    AXIOM_METRICS_ENDPOINT,
    OTEL_TRACES_BATCH_SIZE,
    OTEL_TRACES_EXPORT_INTERVAL_MS,
    OTEL_METRICS_EXPORT_INTERVAL_MS,
)

logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None


def _build_resource() -> Resource:
    attrs: dict[str, str] = {
        "service.name": OTEL_SERVICE_NAME,
        "deployment.environment": AXIOM_ENVIRONMENT,
        "host.name": socket.gethostname(),
        "service.instance.id": _uuid.uuid4().hex[:12],
    }
    if CLOUD_PLATFORM:
        attrs["cloud.platform"] = CLOUD_PLATFORM
    try:
        import torch

        if torch.cuda.is_available():
            attrs["gpu.device.name"] = torch.cuda.get_device_name(0)
            attrs["gpu.device.count"] = str(torch.cuda.device_count())
    except Exception:  # noqa: BLE001
        pass
    return Resource.create(attrs)


def _axiom_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {AXIOM_API_TOKEN}",
        "X-Axiom-Dataset": AXIOM_DATASET,
    }


def init_otel() -> None:
    """Create and register global TracerProvider + MeterProvider. Idempotent."""
    global _tracer_provider, _meter_provider  # noqa: PLW0603
    if _tracer_provider is not None:
        return

    resource = _build_resource()
    headers = _axiom_headers()

    # Traces
    span_exporter = OTLPSpanExporter(endpoint=AXIOM_TRACES_ENDPOINT, headers=headers)
    span_processor = BatchSpanProcessor(
        span_exporter,
        max_export_batch_size=OTEL_TRACES_BATCH_SIZE,
        schedule_delay_millis=OTEL_TRACES_EXPORT_INTERVAL_MS,
    )
    tp = TracerProvider(resource=resource)
    tp.add_span_processor(span_processor)
    trace.set_tracer_provider(tp)
    _tracer_provider = tp

    # Metrics
    metric_exporter = OTLPMetricExporter(endpoint=AXIOM_METRICS_ENDPOINT, headers=headers)
    reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=OTEL_METRICS_EXPORT_INTERVAL_MS,
    )
    mp = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(mp)
    _meter_provider = mp

    logger.info("OTel initialized: traces=%s metrics=%s", AXIOM_TRACES_ENDPOINT, AXIOM_METRICS_ENDPOINT)


def shutdown_otel() -> None:
    """Flush and shutdown both providers. Idempotent."""
    global _tracer_provider, _meter_provider  # noqa: PLW0603
    if _tracer_provider is not None:
        _tracer_provider.force_flush()
        _tracer_provider.shutdown()
        _tracer_provider = None
    if _meter_provider is not None:
        _meter_provider.force_flush()
        _meter_provider.shutdown()
        _meter_provider = None


__all__ = ["init_otel", "shutdown_otel"]
