import logging
import time

from fastapi import Request
from fastapi.responses import Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Histogram,
                               generate_latest)
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("verifield.observability")

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP Request Latency", ["method", "endpoint"]
)

DB_QUERY_COUNT = Counter(
    "db_queries_total", "Total Database Queries", ["domain", "operation"]
)

ACTIVE_SESSIONS = Counter(
    "active_websocket_sessions", "Total Active WebSocket Sessions", ["stream"]
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to intercept all requests and track their latency and status
    codes for Prometheus monitoring.
    """

    async def dispatch(self, request: Request, call_next):
        method = request.method
        # Only track base path to avoid cardinality explosion with path params (e.g. /projects/123)
        endpoint = request.url.path.split("/")[0:4]
        endpoint_str = "/".join(endpoint)

        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint_str, http_status=status_code
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint_str).observe(
                duration
            )

        return response


def metrics_endpoint():
    """
    Exposes the /metrics endpoint for Prometheus scrapers.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def setup_observability(app):
    """
    Wires the observability engine into the FastAPI application.
    """
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])
    logger.info("Observability Engine: Prometheus tracing initialized")
