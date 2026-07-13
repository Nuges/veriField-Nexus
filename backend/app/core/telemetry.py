import logging
import time
from typing import Any, Dict

from fastapi import FastAPI, Request
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (ConsoleSpanExporter,
                                            SimpleSpanProcessor)
from opentelemetry.trace import Tracer

# Initialize standard python logger
logger = logging.getLogger("verifield.telemetry")

# Global metrics cache
_metrics: Dict[str, Any] = {
    "activities_processed_total": 0,
    "trust_score_calculations_total": 0,
    "compliance_runs_total": 0,
    "compliance_violations_total": 0,
    "db_query_duration_seconds_sum": 0.0,
    "http_requests_total": {},
}

# OpenTelemetry Tracer setup
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()
# Output traces to Console for structured visibility
tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
tracer: Tracer = trace.get_tracer("verifield-nexus")


def get_tracer() -> Tracer:
    return tracer


# --- Metrics tracking helper methods ---
def increment_metric(name: str, labels: dict = None):
    global _metrics
    if labels:
        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        key = f"{name}{{{label_str}}}"
    else:
        key = name

    _metrics[key] = _metrics.get(key, 0) + 1


def record_timing(name: str, duration: float):
    global _metrics
    _metrics[name] = _metrics.get(name, 0.0) + duration


def get_prometheus_metrics() -> str:
    """Format stored metrics as a Prometheus-compatible string representation."""
    lines = []
    for key, val in _metrics.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                lines.append(f"{key}_{sub_key} {sub_val}")
        else:
            lines.append(f"{key} {val}")
    return "\n".join(lines)


# --- FastAPI Instrumentation hook ---
def setup_telemetry(app: FastAPI):
    """Hooks OpenTelemetry instrumentation into the FastAPI application instance."""
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    # Custom requests count middleware
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Log request attributes
        method = request.method
        path = request.url.path
        status = response.status_code

        increment_metric(
            "http_requests_total",
            {"method": method, "path": path, "status": str(status)},
        )
        record_timing("http_request_duration_seconds", duration)

        return response
